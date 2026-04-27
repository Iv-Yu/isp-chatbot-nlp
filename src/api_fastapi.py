from __future__ import annotations
import os
import random
from collections import Counter, defaultdict
import secrets
import psycopg2
from psycopg2 import pool, extras
from sklearn.metrics import confusion_matrix
from datetime import datetime
import time
import logging
from contextlib import contextmanager
from sklearn.metrics import confusion_matrix, accuracy_score, precision_recall_fscore_support
# Tambahkan ini untuk meredam log warning dari transformers
import warnings
os.environ["TOKENIZERS_PARALLELISM"] = "false"
warnings.filterwarnings("ignore", message=".*position_ids.*")

from passlib.context import CryptContext
try:
    # Python 3.9+: zoneinfo in stdlib
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None
from pathlib import Path
from typing import Optional, Dict, List
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Header, Depends
from pydantic import BaseModel
from .chatbot.rule_engine import RuleEngine
from .chatbot.rules import INTENT_RULES, FALLBACK_RESPONSES
from .chatbot.semantic_engine import SemanticEngine
from .chatbot.ml_engine import MLEngine
from .chatbot.response_router import route_intent
from .chatbot.smart_olt import SmartOLT
from .chatbot import tickets
from .nlp.entity_extractor import EntityExtractor

# Application start time for uptime calculation
_start_time = time.time()
# Setup logging
# Penampung statistik intent di memori (reset jika server restart)
_intent_counts = Counter()

# Daftar kata kunci yang terlalu umum (ambigu) jika berdiri sendiri
AMBIGUOUS_KEYWORDS = {"internet", "wifi", "koneksi", "sinyal", "paket", "bayar", "tagihan", "speed", "tes", "cek", "halo", "i", "p", "test"}

_status_counts = Counter()
_intent_status_counts = defaultdict(Counter)
_recent_escalations = []
logger = logging.getLogger(__name__)

# Konfigurasi Hashing Password
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
LOG_FILE = DATA_DIR / "chat_logs.csv"
DB_FILE = DATA_DIR / "chatbot.db"

# Pastikan direktori data ada
DATA_DIR.mkdir(exist_ok=True)

load_dotenv(BASE_DIR / ".env")

# Inisialisasi Connection Pool
db_config = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "9432"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
    "dbname": os.getenv("DB_NAME", "isp_chatbot"),
}

connection_pool = None

def init_pool() -> bool:
    """Inisialisasi connection pool secara eksplisit."""
    global connection_pool
    if connection_pool is not None:
        return True

    try:
        connection_pool = pool.ThreadedConnectionPool(
            1, 10,
            **db_config
        )
        logger.info("Database connection pool initialized successfully.")
        return True
    except Exception as e:
        logger.error(f"Gagal membuat connection pool: {e}")
        connection_pool = None
        return False

@contextmanager
def get_db_conn():
    """Context manager untuk koneksi database PostgreSQL dari pool."""
    if not connection_pool:
        raise Exception("Database connection pool is not initialized")
    conn = connection_pool.getconn()
    try:
        yield conn
    finally:
        connection_pool.putconn(conn)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "").strip().strip('"').strip("'")
OUTAGE_ENV_FLAG = "OUTAGE_MODE"
TIMEZONE = os.getenv("TIMEZONE", "Asia/Jakarta")
APPLY_TIME_GREETING = os.getenv("APPLY_TIME_GREETING", "greeting").lower()  # all|greeting|none

def init_db():
    """Inisialisasi database PostgreSQL untuk user dan logging."""
    try:
        with get_db_conn() as conn:
            conn.autocommit = True
            with conn.cursor() as cursor:
                # Tabel User
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        username VARCHAR(50) PRIMARY KEY,
                        password VARCHAR(255) NOT NULL,
                        role VARCHAR(20) NOT NULL
                    )
                ''')
                # Tabel Logs
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS chat_logs (
                        id SERIAL PRIMARY KEY,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        chat_id BIGINT,
                        message TEXT,
                        intent VARCHAR(50),
                        status VARCHAR(20),
                        reply TEXT,
                        confidence FLOAT DEFAULT 1.0,
                        msg_id BIGINT DEFAULT NULL
                    )
                ''')
                
                # Cek apakah kolom msg_id sudah ada di PostgreSQL
                cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='chat_logs' AND column_name='msg_id'")
                if not cursor.fetchone():
                    logger.info("Menambahkan kolom msg_id ke tabel chat_logs...")
                    cursor.execute("ALTER TABLE chat_logs ADD COLUMN msg_id BIGINT DEFAULT NULL")
            
    except Exception as e:
        logger.error(f"Gagal inisialisasi PostgreSQL: {e}")

def _is_chat_escalated(chat_id: Optional[int]) -> bool:
    """Checks if the chat's latest status is an escalation status."""
    if chat_id is None: return False
    try:
        with get_db_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT status FROM chat_logs WHERE chat_id = %s ORDER BY id DESC LIMIT 1", (chat_id,))
                result = cursor.fetchone()
                latest_status = result[0] if result else "OK" # Default to OK if no logs
                return latest_status in ["TO_CS", "TO_NOC", "STAFF_REPLY"]
    except Exception:
        return False

def _get_chat_status(chat_id: Optional[int]) -> str:
    """Mengambil status terakhir chat dari database."""
    if chat_id is None: return "OK"
    try:
        with get_db_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT status FROM chat_logs WHERE chat_id = %s ORDER BY id DESC LIMIT 1", (chat_id,))
                result = cursor.fetchone()
                return result[0] if result else "OK"
    except Exception:
        return "OK"

def time_greet(now: datetime | None = None) -> str:
    """Return localized greeting based on hour. Accepts optional `now` for testing.

    Uses `TIMEZONE` env when available. Returns one of: Selamat pagi/siang/sore/malam.
    """
    try:
        if now is None:
            if ZoneInfo is not None:
                now = datetime.now(tz=ZoneInfo(TIMEZONE))
            else:
                now = datetime.now()
    except Exception:
        now = datetime.now()

    hour = now.hour
    if 5 <= hour < 11:
        return "Selamat pagi"
    if 11 <= hour < 15:
        return "Selamat siang"
    if 15 <= hour < 18:
        return "Selamat sore"
    return "Selamat malam"
OUTAGE_MESSAGE = os.getenv(
    "OUTAGE_MESSAGE",
    "Sedang ada gangguan massal di jaringan kami. Tim sedang menanganinya, mohon tunggu dan coba lagi beberapa saat.",
)
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "").strip().strip('"').strip("'")
# --- Inisialisasi Objek ---
# Gunakan ambang minimal 1 agar single-token intents (mis. 'halo', 'hai') terdeteksi

# Define TECHNICAL_INTENTS for outage mode logic
TECHNICAL_INTENTS = [
    "gangguan_umum",
    "gangguan_lemot_umum",
    "kabel_putus",
    "gangguan_aplikasi",
    "gangguan_rute",
    "gangguan_massal" # This intent is assigned when outage mode is active
]
rule_engine = RuleEngine(min_score=1)
semantic_engine = SemanticEngine()
ml_engine = MLEngine()
entity_extractor = EntityExtractor()
smart_olt_client = SmartOLT() # Sekarang client ini mandiri mengambil config dari env

app = FastAPI(title="ISP Chatbot Intent API")

@app.on_event("startup")
async def startup_event():
    """Inisialisasi sistem saat server dijalankan."""
    if init_pool():
        init_db()
        _load_stats_from_db()
        logger.info("Application startup: DB initialized and stats loaded.")
    else:
        logger.critical("Application startup: Database connection pool could not be established.")

# --- Model Pydantic (Tidak Berubah) ---
class ChatRequest(BaseModel):
    message: str
    chat_id: Optional[int] = None
    msg_id: Optional[int] = None

class ChatResponse(BaseModel):
    intent: str
    confidence: float
    entity: Optional[str] = None
    status: str
    reply: str

class TicketResponse(BaseModel):
    ticket_id: str
    status: str = "RECEIVED"

class OutageRequest(BaseModel):
    enabled: bool
    message: Optional[str] = None

class OutageStatus(BaseModel):
    enabled: bool
    message: str

class StatsResponse(BaseModel):
    intent_distribution: Dict[str, int]
    status_distribution: Dict[str, int]
    intent_status_distribution: Dict[str, Dict[str, int]]
    uptime_seconds: int
    outage_status: OutageStatus
    recent_escalations: List[Dict]

class LoginRequest(BaseModel):
    username: str
    password: str

class ReplyRequest(BaseModel):
    chat_id: int
    reply_message: str
    staff_name: str
    reply_to_msg_id: Optional[int] = None

class UserCreateRequest(BaseModel):
    username: str
    password: str
    role: str

_OUTAGE_STATE = {
    "enabled": os.getenv(OUTAGE_ENV_FLAG, "").lower() in {"1", "true", "on"},
    "message": OUTAGE_MESSAGE,
}

async def verify_admin_token(x_admin_token: Optional[str] = Header(default=None)):
    """Dependency to verify admin token."""
    if not ADMIN_TOKEN:
        logger.error("ADMIN_TOKEN is not configured in environment.")
        raise HTTPException(
            status_code=500,
            detail="Fitur admin tidak dikonfigurasi di server (ADMIN_TOKEN kosong)."
        )
    if not x_admin_token or not secrets.compare_digest(x_admin_token, ADMIN_TOKEN):
        raise HTTPException(status_code=401, detail="Token admin tidak valid atau tidak ada.")

@app.get("/admin/stats", response_model=StatsResponse, tags=["Admin"])
async def get_admin_stats(_ = Depends(verify_admin_token)):
    """Returns various statistics for the admin dashboard."""
    conn = None
    active_sessions = []
    uptime = int(time.time() - _start_time)
    
    try:
        with get_db_conn() as conn:
            with conn.cursor(cursor_factory=extras.RealDictCursor) as cursor:
                # Mengambil chat yang status terakhirnya ADALAH eskalasi atau sedang dibalas staff (Bukan OK)
                query = """
                    SELECT cl.*
                    FROM chat_logs cl
                    INNER JOIN (
                        SELECT chat_id, MAX(id) as max_id
                        FROM chat_logs
                        GROUP BY chat_id
                    ) AS latest_logs ON cl.id = latest_logs.max_id AND cl.chat_id = latest_logs.chat_id
                    WHERE cl.status != 'OK' AND cl.chat_id IN (SELECT DISTINCT chat_id FROM chat_logs WHERE status IN ('TO_CS', 'TO_NOC', 'STAFF_REPLY'))
                    ORDER BY cl.timestamp DESC;
                """
                cursor.execute(query)
                rows = cursor.fetchall()
                for row in rows:
                    active_sessions.append({
                        "chat_id": row["chat_id"],
                        "message": row["message"],
                        "intent": row.get("intent", "n/a"),
                        "confidence": row.get("confidence", 1.0),
                        "status": row["status"],
                        "timestamp": row["timestamp"].strftime("%Y-%m-%d %H:%M:%S"),
                    })
    except Exception as e:
        logger.error(f"Error fetching active sessions: {e}")

    return StatsResponse(
        intent_distribution=dict(_intent_counts),
        status_distribution=dict(_status_counts),
        intent_status_distribution={k: dict(v) for k, v in _intent_status_counts.items()},
        uptime_seconds=uptime,
        outage_status=OutageStatus(enabled=_OUTAGE_STATE["enabled"], message=_OUTAGE_STATE["message"]),
        recent_escalations=active_sessions
    )

def _log_escalation(chat_id: Optional[int], message: str, intent: str, status: str, confidence: float = 1.0):
    """Mencatat pesan ke dalam daftar eskalasi memori untuk dashboard."""
    if status not in ["TO_CS", "TO_NOC"]: return
    _recent_escalations.append({
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "chat_id": chat_id,
        "message": message[:100] + "..." if len(message) > 100 else message,
        "intent": intent,
        "status": status,
        "confidence": round(confidence, 2)
    })
    if len(_recent_escalations) > 20: _recent_escalations.pop(0)

def _save_to_db(message: str, intent: str, status: str, reply: str, chat_id: Optional[int] = None, confidence: float = 1.0, msg_id: Optional[int] = None):
    """Menyimpan interaksi chat ke database PostgreSQL."""
    try:
        with get_db_conn() as conn:
            conn.autocommit = True
            with conn.cursor() as cursor:
                query = """
                    INSERT INTO chat_logs (chat_id, message, intent, status, reply, confidence, msg_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(query, (chat_id, message, intent, status, reply, confidence, msg_id))
    except Exception as e:
        logger.error(f"Gagal menyimpan log ke DB: {e}")

def _load_stats_from_db():
    """Memuat statistik dari database PostgreSQL saat startup."""
    try:
        with get_db_conn() as conn:
            with conn.cursor(cursor_factory=extras.RealDictCursor) as cursor:
                cursor.execute("SELECT chat_id, message, intent, status, timestamp, confidence, msg_id FROM chat_logs")
                rows = cursor.fetchall()
                
                for row in rows:
                    intent = row["intent"]
                    status = row["status"]
                    _intent_counts[intent] += 1
                    _status_counts[status] += 1
                    _intent_status_counts[intent][status] += 1
                    
                    if status in ["TO_CS", "TO_NOC"]:
                        _recent_escalations.append({
                            "timestamp": row["timestamp"].strftime("%H:%M:%S") if isinstance(row["timestamp"], datetime) else str(row["timestamp"]),
                            "chat_id": row["chat_id"],
                            "message": row["message"],
                            "intent": intent,
                            "status": status,
                            "confidence": row.get("confidence", 1.0),
                            "msg_id": row.get("msg_id")
                        })
        del _recent_escalations[:-20]
    except Exception as e:
        logger.error(f"Gagal memuat statistik dari DB: {e}")

@app.get("/admin/evaluation-matrix", tags=["Admin"])
async def get_evaluation_matrix(_ = Depends(verify_admin_token)):
    """Menghitung Confusion Matrix berdasarkan log yang ada di database."""
    try:
        with get_db_conn() as conn:
            with conn.cursor(cursor_factory=extras.RealDictCursor) as cursor:
                # Ambil data di mana kita punya intent asli (asumsi dari pesan user) 
                # dan intent yang diprediksi bot
                cursor.execute("SELECT intent, message FROM chat_logs WHERE intent != 'fallback' LIMIT 500")
                rows = cursor.fetchall()
                
                if not rows:
                    return {"labels": [], "matrix": []}

                y_true = []
                y_pred = []
                
                for row in rows:
                    msg = row['message']
                    # Gunakan label dari database sebagai 'True'
                    # (Pastikan Anda sudah memvalidasi label ini di DB agar valid untuk Bab 4)
                    y_true.append(row['intent'])
                    
                    # Jalankan simulasi Hybrid Logic (Rule -> ML -> Semantic)
                    # Kita panggil detect_with_response tapi abaikan reply/status-nya
                    r_intent, _, _ = rule_engine.detect_with_response(msg)
                    
                    if r_intent == "fallback":
                        ml_res = ml_engine.predict(msg, threshold_design=0.5)
                        p_intent = ml_res[0]
                        if p_intent == "fallback":
                            sem_res = semantic_engine.detect(msg, threshold=0.6)
                            p_intent = sem_res[0] if sem_res[0] else "fallback"
                    else:
                        p_intent = r_intent
                        
                    y_pred.append(p_intent or "fallback")
                
                # Pastikan semua label yang muncul di y_true maupun y_pred terdaftar
                labels = sorted(list(set(y_true) | set(y_pred)))
                cm = confusion_matrix(y_true, y_pred, labels=labels)

                # Hitung akurasi keseluruhan
                overall_accuracy = accuracy_score(y_true, y_pred)

                # Hitung precision, recall, f1-score per label
                # 'average=None' akan mengembalikan skor untuk setiap label
                # 'zero_division=0' akan menangani kasus di mana sebuah label tidak memiliki sampel true/predicted
                precision, recall, f1_score, _ = precision_recall_fscore_support(
                    y_true, y_pred, labels=labels, average=None, zero_division=0
                )

                # Format metrik per-label
                per_label_metrics = {}
                for i, label in enumerate(labels):
                    per_label_metrics[label] = {
                        "precision": round(precision[i], 4),
                        "recall": round(recall[i], 4),
                        "f1_score": round(f1_score[i], 4),
                    }
                
                return {
                    "labels": labels,
                    "matrix": cm.tolist(),
                    "summary": {
                        "total": len(rows),
                        "algorithm": "Hybrid (Rule, Naive Bayes, SBERT)",
                        "overall_accuracy": round(overall_accuracy, 4),
                        "per_label_metrics": per_label_metrics,
                    }
                }
    except Exception as e:
        logger.error(f"Error generating matrix: {e}")
        raise HTTPException(status_code=500, detail="Gagal menghitung matrix.")

async def health_check():
    return {"status": "ok"}

@app.get("/")
async def root():
    """Root endpoint to verify the API is running."""
    return {"message": "ISP Chatbot Intent API is running. Send POST requests to /chat"}

def _predict(message: str, chat_id: Optional[int] = None, msg_id: Optional[int] = None) -> ChatResponse:
    """
    Internal logic to predict intent and generate a response.
    
    Flow:
    1. Protocol handling -> 2. Outage check -> 3. Rule Engine -> 4. Post-processing
    """
    if not message.strip():
        raise HTTPException(status_code=400, detail="Pesan tidak boleh kosong.")

    start_proc = time.time()

    # Ambil status saat ini untuk mengecek apakah sedang eskalasi
    current_status = _get_chat_status(chat_id)
    is_escalated = current_status in ["TO_CS", "TO_NOC", "STAFF_REPLY"]

    # Handle special internal protocols from Telegram Bot
    if message.startswith("__IDENTITY__:"):
        identity_val = message.replace("__IDENTITY__:", "").strip()
        _intent_counts["provide_identity"] += 1
        
        status = current_status if is_escalated else "AUTO_RESPONSE"
        
        # Ambil status perangkat menggunakan modul SmartOLT yang sudah kita buat
        smartolt_reply_part = smart_olt_client.get_customer_device_status(identity_val)
        logger.info(f"SmartOLT Integration: Respon untuk {identity_val} -> {smartolt_reply_part}")

        _status_counts[status] += 1
        _intent_status_counts["provide_identity"][status] += 1
        logger.info(f"Protocol IDENTITY received for chat_id: {chat_id}")

        final_identity_reply = smartolt_reply_part if smartolt_reply_part else "Maaf kak, terjadi kendala saat pengecekan ID."

        _save_to_db(message, "provide_identity", status, final_identity_reply, chat_id, 1.0, msg_id)
        _log_escalation(chat_id, f"📌 ID: {identity_val}", "provide_identity", status, 1.0)
        return ChatResponse(intent="provide_identity", confidence=1.0, status=status, reply=final_identity_reply)
    
    if message.startswith("__LOCATION__:"):
        loc_val = message.replace("__LOCATION__:", "")
        _intent_counts["provide_location"] += 1
        status = current_status if is_escalated else "AUTO_RESPONSE"
        
        _status_counts[status] += 1
        _intent_status_counts["provide_location"][status] += 1
        logger.info(f"Protocol LOCATION received for chat_id: {chat_id}")
        _save_to_db(message, "provide_location", status, "Lokasi berhasil dipetakan.", chat_id, 1.0, msg_id)
        _log_escalation(chat_id, f"📍 Lokasi: {loc_val[:50]}", "provide_location", status, 1.0)
        return ChatResponse(intent="provide_location", confidence=1.0, status=status, reply="Lokasi berhasil dipetakan.")

    # Handle Protocol Foto/Screenshot
    if message == "__PHOTO_SENT__":
        _intent_counts["provide_screenshot"] += 1
        status = current_status if is_escalated else "AUTO_RESPONSE"
        
        _status_counts[status] += 1
        _intent_status_counts["provide_screenshot"][status] += 1
        logger.info(f"Screenshot received for chat_id: {chat_id}")
        _save_to_db(message, "provide_screenshot", status, "User mengirimkan gambar/screenshot.", chat_id, 1.0, msg_id)
        _log_escalation(chat_id, "🖼️ [Gambar/Screenshot]", "provide_screenshot", status, 1.0)
        return ChatResponse(intent="provide_screenshot", confidence=1.0, status=status, reply="Gambar berhasil diterima kak, kami lampirkan ke laporan ya 🙏")

    entity = entity_extractor.extract(message)

    # 2. Deteksi Intent (Multi-Layer Hybrid Logic)
    # Layer 1: Rule Engine (Exact/Token Match)
    rule_intent, rule_reply, status = rule_engine.detect_with_response(message)
    
    intent: str = rule_intent if rule_intent is not None else "fallback"
    base_reply: str = rule_reply if rule_reply is not None else ""
    
    # KUNCI STATUS: Jika sudah eskalasi, jangan biarkan intent baru mereset status ke AUTO_RESPONSE
    if is_escalated:
        status = current_status
    elif intent != "fallback":
        status = route_intent(intent) # intent is guaranteed to be str here
        
    confidence = 1.0
    
    tokens = rule_engine.preprocess(message)
    is_short_input = len(tokens) <= 1
    is_ambiguous = is_short_input and len(tokens) > 0 and tokens[0] in AMBIGUOUS_KEYWORDS

    if intent == "fallback":
        # Layer 2: ML Engine (SVM - Klasifikasi Statistik)
        logger.info(f"RuleEngine fallback, trying MLEngine for: {message}")
        
        # Jika input ambigu, kita pasang threshold sangat tinggi (0.95)
        if is_ambiguous:
            ml_threshold = 0.95
        else:
            # Threshold moderat untuk menyeimbangkan false positive
            ml_threshold = 0.7 if is_short_input else 0.5

        # Unpack dan pastikan tipe data adalah string untuk menghindari error Pylance
        ml_res = ml_engine.predict(message, threshold_design=ml_threshold)
        ml_intent_val, ml_score = ml_res[0], ml_res[1]

        if ml_intent_val is not None and str(ml_intent_val) != "fallback":
            intent = str(ml_intent_val)
            confidence = float(ml_score)
            status = route_intent(intent)
            # Ambil respons default dari rules berdasarkan intent hasil ML
            for rule in INTENT_RULES:
                if rule["name"] == intent:
                    base_reply = rule["mappings"][0]["response"]
                    break
        else:
            # Layer 3: Semantic Engine (Metode Kesamaan TF-IDF Teroptimasi)
            logger.info(f"MLEngine low confidence, applying Similarity Scoring for: {message}")
            
            # Jika ambigu, naikkan threshold ke level hampir mustahil (0.98)
            if is_ambiguous:
                sem_threshold = 0.98
            else:
                sem_threshold = 0.85 if is_short_input else 0.6
                
            # Gunakan penanganan tuple yang aman untuk menghindari "size mismatch"
            sem_res = semantic_engine.detect(message, threshold=sem_threshold)
            sem_intent = sem_res[0] if len(sem_res) > 0 else None
            sem_score = sem_res[1] if len(sem_res) > 1 else 0.0
            sem_reply = sem_res[2] if len(sem_res) > 2 else ""

            if sem_intent is not None:
                intent = str(sem_intent)
                confidence = float(sem_score)
                base_reply = str(sem_reply)
                status = route_intent(intent)
            else:
                # Final Fallback jika semua engine gagal
                confidence = 0.0
                base_reply = random.choice(FALLBACK_RESPONSES)

    # --- Tentukan Final Reply, Intent, dan Status ---
    final_intent: str = intent
    final_status: str = status
    final_reply: str = base_reply

    # Override jika mode gangguan massal aktif DAN intentnya adalah teknis
    if _OUTAGE_STATE["enabled"] and str(final_intent) in TECHNICAL_INTENTS:
        final_reply = f"{time_greet()}! {_OUTAGE_STATE['message']}"
        final_status = "TO_NOC"
        final_intent = "gangguan_massal" # Ganti intent untuk logging/statistik
    else:
        # 4. Post-processing: Terapkan salam berdasarkan waktu (hanya jika tidak di-override oleh gangguan)
        resp_lower = (base_reply or "").strip().lower()
        msg_lower = message.strip().lower()
        
        should_greet = (APPLY_TIME_GREETING == "all") or (APPLY_TIME_GREETING == "greeting" and final_intent == "greeting")
        already_greeted = resp_lower.startswith(("selamat", "waalaikumsalam", "assalamu")) or \
                          any(g in msg_lower for g in ("selamat", "assalam", "assalamu"))

        if should_greet and not already_greeted:
            final_reply = f"{time_greet()}! {base_reply}"

    _intent_counts[final_intent] += 1
    _status_counts[final_status] += 1
    _intent_status_counts[final_intent][final_status] += 1

    _log_escalation(chat_id, message, str(final_intent), final_status, confidence)

    # Simpan ke Database MySQL secara permanen (termasuk status eskalasi dan confidence)
    _save_to_db(message, str(final_intent), final_status, str(final_reply), chat_id, confidence, msg_id)

    proc_time = round(time.time() - start_proc, 3)
    logger.info(f"ChatID: {chat_id} | Intent: {final_intent} | Status: {final_status} | Time: {proc_time}s")

    return ChatResponse(
        intent=final_intent,
        confidence=confidence,
        entity=entity,
        status=final_status,
        reply=final_reply,
    )

# --- Endpoint API (Tidak Berubah, hanya endpoint /predict dihapus) ---
@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Menerima pesan chat dan mengembalikan intent, balasan, serta status."""
    return _predict(request.message, request.chat_id, request.msg_id)

@app.post("/admin/login")
async def login(req: LoginRequest):
    username = req.username.strip()
    logger.info(f"Mencoba login untuk user: '{username}'")
    try:
        with get_db_conn() as conn:
            with conn.cursor(cursor_factory=extras.RealDictCursor) as cursor:
                cursor.execute("SELECT username, password, role FROM users WHERE LOWER(username) = LOWER(%s)", (username,))
                user = cursor.fetchone()
                
                if not user:
                    logger.warning(f"User '{username}' tidak ditemukan.")
                    raise HTTPException(status_code=401, detail="Username atau password salah")

                stored_pw = user["password"]
                plain_password = req.password[:72] # Bcrypt limit

                # 1. Cek menggunakan hash
                if pwd_context.identify(stored_pw) and pwd_context.verify(plain_password, stored_pw):
                    return {"status": "success", "role": user["role"], "username": user["username"]}
                
                # 2. Fallback untuk plain-text (Migrasi)
                if plain_password == stored_pw:
                    logger.info(f"Migrasi password ke hash untuk user: {username}")
                    conn.autocommit = True
                    new_hash = pwd_context.hash(plain_password)
                    cursor.execute("UPDATE users SET password = %s WHERE username = %s", (new_hash, user["username"]))
                    return {"status": "success", "role": user["role"], "username": user["username"]}

                logger.warning(f"Password salah untuk user: {username}")

        raise HTTPException(status_code=401, detail="Username atau password salah")
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error(f"LOGIN CRITICAL ERROR: {error_msg}")
        if "no backends available" in error_msg:
            raise HTTPException(status_code=500, detail="Server error: Library enkripsi (bcrypt) belum terinstal.")
        raise HTTPException(status_code=500, detail=f"Database error: {error_msg}")

@app.get("/admin/chat-history/{chat_id}", tags=["Admin"])
async def get_chat_history(chat_id: int, _ = Depends(verify_admin_token)):
    """Mengambil seluruh riwayat percakapan untuk satu user tertentu."""
    try:
        with get_db_conn() as conn:
            with conn.cursor(cursor_factory=extras.RealDictCursor) as cursor:
                query = "SELECT id, timestamp, message, intent, status, reply, msg_id FROM chat_logs WHERE chat_id = %s ORDER BY timestamp DESC"
                cursor.execute(query, (chat_id,))
                rows = cursor.fetchall()
                for row in rows:
                    if isinstance(row.get("timestamp"), datetime):
                        row["timestamp"] = row["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
                    else:
                        row["timestamp"] = str(row.get("timestamp", ""))
                return rows
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching history: {e}")

@app.get("/admin/logs/all", tags=["Admin"])
async def get_all_logs(_ = Depends(verify_admin_token)):
    """Mengambil seluruh log percakapan dari database untuk keperluan training."""
    try:
        with get_db_conn() as conn:
            with conn.cursor(cursor_factory=extras.RealDictCursor) as cursor:
                query = "SELECT timestamp, chat_id, message, intent, status, reply FROM chat_logs ORDER BY timestamp DESC"
                cursor.execute(query)
                rows = cursor.fetchall()
                return rows
    except Exception as e:
        logger.error(f"Error fetching all logs: {e}")
        raise HTTPException(status_code=500, detail="Gagal mengambil data log dari database.")

@app.post("/admin/reply-chat", tags=["Admin"])
async def reply_to_user(req: ReplyRequest, _ = Depends(verify_admin_token)):
    """Mengirim balasan manual dari staff ke Telegram user."""
    if not TELEGRAM_TOKEN:
        raise HTTPException(status_code=500, detail="Bot token tidak dikonfigurasi")
    
    import requests as py_requests
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    
    # Menambahkan identitas staf pada pesan agar user tahu dibalas oleh manusia
    formatted_reply = f"🧑‍💻 *Staf ({req.staff_name}) membalas:*\n\n{req.reply_message}"
    
    payload = {"chat_id": req.chat_id, "text": formatted_reply, "parse_mode": "Markdown"}
    # Gunakan fitur reply asli Telegram jika msg_id tersedia
    if req.reply_to_msg_id:
        payload["reply_to_message_id"] = int(req.reply_to_msg_id)
        
    res = py_requests.post(url, json=payload)
    if res.status_code == 200:
        # Ubah status menjadi 'STAFF_REPLY' agar log percakapan tidak langsung hilang dari dashboard
        # Sertakan juga msg_id asal yang dibalas agar tersimpan di database
        _save_to_db(f"MANUAL_REPLY_FROM_{req.staff_name}", "manual_response", "STAFF_REPLY", 
                    formatted_reply, req.chat_id, 1.0, req.reply_to_msg_id)
        return {"status": "sent"}
    raise HTTPException(status_code=400, detail="Gagal mengirim pesan ke Telegram")

@app.post("/admin/resolve-chat", tags=["Admin"])
async def resolve_chat(req: Dict, _ = Depends(verify_admin_token)):
    """Menandai sesi chat sebagai selesai (OK)."""
    chat_id = req.get("chat_id")
    if not chat_id:
        raise HTTPException(status_code=400, detail="Chat ID diperlukan")
    
    # Status 'OK' akan memicu query SQL untuk menyembunyikan sesi ini dari daftar antrean aktif
    _save_to_db("SESSION_RESOLVED_BY_STAFF", "resolve", "OK", "Sesi diselesaikan oleh staff.", chat_id, 1.0)
    return {"status": "resolved"}

@app.post("/admin/users", tags=["Admin"])
async def create_user(req: UserCreateRequest, _ = Depends(verify_admin_token)):
    """Membuat user CS atau NOC baru."""
    try:
        with get_db_conn() as conn:
            conn.autocommit = True
            with conn.cursor() as cursor:
                # Cek apakah username sudah ada
                cursor.execute("SELECT username FROM users WHERE username = %s", (req.username,))
                if cursor.fetchone():
                    raise HTTPException(status_code=400, detail="Username sudah terdaftar.")
                
                # Potong password ke 72 karakter sebelum di-hash
                hashed_password = pwd_context.hash(req.password[:72])
                
                # Tambahkan user baru
                cursor.execute("INSERT INTO users (username, password, role) VALUES (%s, %s, %s)", 
                               (req.username, hashed_password, req.role))
        return {"status": "success", "message": f"User {req.username} berhasil dibuat."}
    except Exception as e:
        if isinstance(e, HTTPException): raise e
        logger.error(f"Error creating user: {e}")
        raise HTTPException(status_code=500, detail="Terjadi kesalahan database.")

# Backwards compatibility: some clients (legacy telegram bot) still call `/predict`.
# Keep this wrapper to avoid 404s until all clients are migrated.
@app.post("/predict", response_model=ChatResponse)
async def predict_compat(request: ChatRequest) -> ChatResponse:
    return _predict(request.message, request.chat_id, request.msg_id)

@app.post("/cs/escalate", response_model=TicketResponse)
async def escalate_cs(request: ChatRequest) -> TicketResponse:
    tid = tickets.create_ticket("CS", request.message)
    return TicketResponse(ticket_id=tid)

@app.post("/noc/escalate", response_model=TicketResponse)
async def escalate_noc(request: ChatRequest) -> TicketResponse:
    tid = tickets.create_ticket("NOC", request.message)
    return TicketResponse(ticket_id=tid)

@app.get("/admin/outage", response_model=OutageStatus, tags=["admin"])
async def get_outage_status():
    return OutageStatus(enabled=_OUTAGE_STATE["enabled"], message=_OUTAGE_STATE["message"])

@app.post("/admin/outage", response_model=OutageStatus, tags=["admin"])
async def set_outage_status(payload: OutageRequest, _ = Depends(verify_admin_token)):
    _OUTAGE_STATE["enabled"] = payload.enabled
    if payload.message:
        _OUTAGE_STATE["message"] = payload.message
    return OutageStatus(enabled=_OUTAGE_STATE["enabled"], message=_OUTAGE_STATE["message"])
