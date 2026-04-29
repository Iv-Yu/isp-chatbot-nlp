from __future__ import annotations
import os
import random
from collections import Counter, defaultdict
import secrets
import re
import psycopg2
from psycopg2 import pool, extras
from datetime import datetime
import time
import logging
from contextlib import contextmanager
import requests
from sklearn.metrics import confusion_matrix, accuracy_score, precision_recall_fscore_support
import numpy as np
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
from fastapi import FastAPI, HTTPException, Header, Depends, Form, Request
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
_engine_counts = Counter()

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

# State management sederhana untuk Fonnte (WhatsApp)
# Untuk produksi, disarankan menggunakan Redis atau database
FONNTE_USER_STATE: Dict[str, dict] = {}
FONNTE_TOKEN = os.getenv("FONNTE_TOKEN", "").strip()
FONNTE_API_URL = "https://api.fonnte.com/send"

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
    engine_distribution: Dict[str, int]
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

class FonnteWebhook(BaseModel):
    sender: str
    message: str
    name: Optional[str] = None
    location: Optional[str] = None
    image: Optional[str] = None


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
        engine_distribution=dict(_engine_counts),
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
                        # Gunakan pengecekan tipe untuk menghindari error Pylance indexing
                        p_intent = ml_res[0] if isinstance(ml_res, tuple) and len(ml_res) > 0 else "fallback"
                        if p_intent == "fallback":
                            sem_res = semantic_engine.detect(msg, threshold=0.6)
                            p_intent = sem_res[0] if isinstance(sem_res, tuple) and len(sem_res) > 0 and sem_res[0] else "fallback"
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

                # Konversi ke list dengan np.atleast_1d untuk menangani Union[float, ndarray] dari sklearn
                p_list = np.atleast_1d(precision).tolist()
                r_list = np.atleast_1d(recall).tolist()
                f_list = np.atleast_1d(f1_score).tolist()

                # Format metrik per-label
                per_label_metrics = {}
                for label, p, r, f in zip(labels, p_list, r_list, f_list):
                    per_label_metrics[label] = {
                        "precision": round(float(p), 4),
                        "recall": round(float(r), 4),
                        "f1_score": round(float(f), 4),
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

@app.post("/webhook/fonnte", tags=["Webhook"])
async def fonnte_webhook(
    request: Request,
    sender: str = Form(None),
    message: str = Form(None),
    data: Optional[FonnteWebhook] = None
):
    """
    Webhook endpoint cerdas untuk WhatsApp via Fonnte.
    Mendukung format Form Data, JSON, dan debugging data mentah.
    """
    if not FONNTE_TOKEN:
        logger.error("FONNTE_TOKEN belum dikonfigurasi.")
        raise HTTPException(status_code=500, detail="Server token misconfigured")

    # 1. Coba ambil dari Form Data (Mendukung Teks dan Share Location dari Fonnte)
    current_sender = sender
    current_message = message
    
    # Jika Fonnte mengirimkan share location (latitude,longitude)
    raw_location = data.location if data else None
    if not current_message and raw_location:
        current_message = raw_location

    # 2. Jika Form kosong, coba parsing body manual (antisipasi variasi Content-Type)
    if not current_sender or not current_message:
        try:
            # Cek apakah body berisi JSON
            raw_json = await request.json()

            # Handle Fonnte status/state update (bukan pesan chat)
            if raw_json and ("state" in raw_json or "stateid" in raw_json):
                logger.info(f"Fonnte status update ignored for device: {raw_json.get('device')}")
                return {"status": "ok", "detail": "state update ignored"}

            current_sender = raw_json.get("sender")
            # Gunakan message jika ada, jika tidak cek field location
            current_message = raw_json.get("message") or raw_json.get("location")
            if current_sender and current_message:
                logger.info("Data Fonnte berhasil diambil dari JSON body")
        except:
            pass

    if data and not current_sender:
        current_sender = data.sender
        current_message = data.message or data.location

    if not current_sender or not current_message:
        raw_body = await request.body()
        logger.warning(f"Webhook diterima tapi data tidak lengkap. Sender: {current_sender}, Msg: {current_message}. Raw Body: {raw_body.decode()}")
        return {"status": "ignored", "reason": "missing_data"}

    msg_text = current_message.strip()
    
    # Inisialisasi state user jika belum ada
    if current_sender not in FONNTE_USER_STATE:
        FONNTE_USER_STATE[current_sender] = {"pending": None, "queue": []}
    state = FONNTE_USER_STATE[current_sender]

    def send_reply(text: str):
        try:
            res = requests.post(FONNTE_API_URL, headers={"Authorization": FONNTE_TOKEN}, 
                          data={"target": current_sender, "message": text, "delay": "2"}, timeout=10)
            logger.info(f"Fonnte API Response to {current_sender}: {res.status_code} - {res.text}")
        except Exception as e:
            logger.error(f"Gagal mengirim balik ke Fonnte: {e}")

    try:
        # 1. Logika Pending Action (Slot Filling)
        if state["pending"] == "need_identity":
            state["pending"] = None
            msg_text = f"__IDENTITY__:{msg_text}"
        elif state["pending"] == "need_package":
            state["pending"] = None
            msg_text = f"__PACKAGE_SELECTED__:{msg_text}"
        elif state["pending"] == "need_nik":
            state["pending"] = None
            msg_text = f"__NIK__:{msg_text}"
        elif state["pending"] == "need_phone":
            state["pending"] = None
            msg_text = f"__PHONE__:{msg_text}"
        elif state["pending"] == "need_email":
            state["pending"] = None
            msg_text = f"__EMAIL__:{msg_text}"
        # Jika sedang menunggu lokasi, atau input mengandung koordinat (Share Location)
        elif state["pending"] == "need_location" or re.search(r"^-?\d+\.\d+,\s*-?\d+\.\d+$", msg_text):
            state["pending"] = None
            msg_text = f"__LOCATION__:{msg_text}"

        # 2. Logika Regex Capturing (Otomatis deteksi ID Pelanggan)
        # Mirip dengan handle_message di telegram_bot.py
        if not msg_text.startswith("__"):
            id_match = re.search(r"\bolt\d+-\d+\b", msg_text, flags=re.I)
            if id_match:
                send_reply(f"Baik kak {id_match.group(0)}, datanya kami cek dulu ya 🙏")
                msg_text = f"__IDENTITY__:{id_match.group(0)}"

        # 3. Jalankan Prediksi NLP
        chat_id_int = int(current_sender) if current_sender.isdigit() else None
        result = _predict(msg_text, chat_id=chat_id_int)

        # 4. Analisis balasan untuk antrean informasi lanjutan
        # (Porting logika dari check_and_queue_pending_actions)
        res_low = result.reply.lower()
        
        # Logic Slot Filling untuk Paket
        if any(k in res_low for k in ["pilih paket", "paket yang mana", "tertarik paket"]):
            if "need_package" not in state["queue"]: state["queue"].append("need_package")
            # Setelah paket dipilih, langsung antrekan permintaan data lainnya
            if "need_nik" not in state["queue"]: state["queue"].append("need_nik")
            if "need_phone" not in state["queue"]: state["queue"].append("need_phone")
            if "need_email" not in state["queue"]: state["queue"].append("need_email")

        # Logic Slot Filling untuk Identitas
        if result.intent != "provide_identity" and any(k in res_low for k in ["id pelanggan", "nomor pelanggan", "id anda"]):
            if "need_identity" not in state["queue"]: state["queue"].append("need_identity")
            
        # Logic Slot Filling untuk Lokasi
        if result.intent not in ["provide_location", "provide_identity"] and any(k in res_low for k in ["alamat", "lokasi", "share lokasi", "pin point"]):
            if "need_location" not in state["queue"]: state["queue"].append("need_location")

        # 5. Kirim balasan utama
        send_reply(result.reply)

        # 6. Proses Antrean (Minta input selanjutnya jika ada)
        if not state["pending"] and state["queue"]:
            next_action = state["queue"].pop(0)
            state["pending"] = next_action
            
            if next_action == "need_identity":
                send_reply("Boleh diinfokan ID Pelanggan atau nama lengkap yang terdaftar kak? 🙏")
            elif next_action == "need_location":
                send_reply("Boleh minta alamat lengkap atau share lokasinya kak? 🙏")
            elif next_action == "need_nik":
                send_reply("Boleh diinfokan NIK kakak sesuai KTP? 🙏")
            elif next_action == "need_phone":
                send_reply("Boleh diinfokan nomor HP aktif yang bisa dihubungi? 🙏")
            elif next_action == "need_email":
                send_reply("Boleh diinfokan alamat email aktif kakak? 🙏")
            elif next_action == "need_package":
                # Opsional: Jika ingin mengirim pesan tambahan saat meminta paket
                pass

        return {"status": "success", "intent": result.intent}

    except Exception as e:
        logger.error(f"Fonnte Webhook Error: {e}")
        return {"status": "error", "message": str(e)}


async def health_check():
    return {"status": "ok"}

@app.api_route("/", methods=["GET", "POST"])
async def root():
    """Root endpoint to verify the API is running."""
    return {
        "message": "ISP Chatbot Intent API is running.",
        "endpoints": {
            "telegram_webhook": "/chat",
            "whatsapp_fonnte_webhook": "/webhook/fonnte"
        }
    }

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
        
        # Ambil status perangkat menggunakan modul SmartOLT
        smartolt_reply_part = smart_olt_client.get_customer_device_status(identity_val)
        logger.info(f"SmartOLT Integration: Respon untuk {identity_val} -> {smartolt_reply_part}")

        _status_counts[status] += 1
        _intent_status_counts["provide_identity"][status] += 1
        logger.info(f"Protocol IDENTITY received for chat_id: {chat_id}")

        final_identity_reply = smartolt_reply_part if smartolt_reply_part else "Maaf kak, terjadi kendala saat pengecekan ID."

        _save_to_db(message, "provide_identity", status, final_identity_reply, chat_id, 1.0, msg_id)
        _log_escalation(chat_id, f"📌 ID: {identity_val}", "provide_identity", status, 1.0)
        return ChatResponse(intent="provide_identity", confidence=1.0, status=status, reply=final_identity_reply)

    if message.startswith("__PACKAGE_SELECTED__:"):
        pkg_val = message.replace("__PACKAGE_SELECTED__:", "").strip()
        _intent_counts["provide_package"] += 1
        status = current_status if is_escalated else "AUTO_RESPONSE"
        
        _status_counts[status] += 1
        _intent_status_counts["provide_package"][status] += 1
        reply_pkg = f"Siap kak, pilihan paket {pkg_val} sudah kami catat. Sekarang boleh bantu kirimkan lokasi pemasangannya (Share Location) ya kak? 🙏"
        _save_to_db(message, "provide_package", status, reply_pkg, chat_id, 1.0, msg_id)
        return ChatResponse(intent="provide_package", confidence=1.0, status=status, reply=reply_pkg)
    
    if message.startswith("__NIK__:"):
        nik_val = message.replace("__NIK__:", "").strip()
        _intent_counts["provide_nik"] += 1
        status = current_status if is_escalated else "AUTO_RESPONSE"
        
        _status_counts[status] += 1
        _intent_status_counts["provide_nik"][status] += 1
        reply_nik = "Terima kasih, NIK kakak sudah kami catat."
        _save_to_db(message, "provide_nik", status, reply_nik, chat_id, 1.0, msg_id)
        return ChatResponse(intent="provide_nik", confidence=1.0, status=status, reply=reply_nik)

    if message.startswith("__PHONE__:"):
        phone_val = message.replace("__PHONE__:", "").strip()
        _intent_counts["provide_phone"] += 1
        status = current_status if is_escalated else "AUTO_RESPONSE"
        
        _status_counts[status] += 1
        _intent_status_counts["provide_phone"][status] += 1
        reply_phone = "Terima kasih, nomor HP aktif kakak sudah kami catat."
        _save_to_db(message, "provide_phone", status, reply_phone, chat_id, 1.0, msg_id)
        return ChatResponse(intent="provide_phone", confidence=1.0, status=status, reply=reply_phone)

    if message.startswith("__EMAIL__:"):
        email_val = message.replace("__EMAIL__:", "").strip()
        _intent_counts["provide_email"] += 1
        status = current_status if is_escalated else "AUTO_RESPONSE"
        
        _status_counts[status] += 1
        _intent_status_counts["provide_email"][status] += 1
        reply_email = "Terima kasih, alamat email aktif kakak sudah kami catat."
        _save_to_db(message, "provide_email", status, reply_email, chat_id, 1.0, msg_id)
        return ChatResponse(intent="provide_email", confidence=1.0, status=status, reply=reply_email)

    if message.startswith("__LOCATION__:"):
        loc_val = message.replace("__LOCATION__:", "")
        _intent_counts["provide_location"] += 1
        status = current_status if is_escalated else "AUTO_RESPONSE"
        
        _status_counts[status] += 1
        _intent_status_counts["provide_location"][status] += 1
        logger.info(f"Protocol LOCATION received for chat_id: {chat_id}")
        _save_to_db(message, "provide_location", status, "Lokasi berhasil diterima.", chat_id, 1.0, msg_id)
        _log_escalation(chat_id, f"📍 Lokasi: {loc_val[:50]}", "provide_location", status, 1.0)
        return ChatResponse(intent="provide_location", confidence=1.0, status=status, reply="Lokasi berhasil diterima kak, kami lampirkan ke laporan ya 🙏.")

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
    engine_source = "rule_engine"
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
            ml_threshold = 0.6 if is_short_input else 0.4

        # Unpack dan pastikan tipe data adalah string untuk menghindari error Pylance
        ml_res = ml_engine.predict(message, threshold_design=ml_threshold)
        if isinstance(ml_res, tuple) and len(ml_res) == 2:
            ml_intent_val, ml_score = ml_res
        else:
            ml_intent_val = "fallback"
            ml_score = 0.0

        if ml_intent_val is not None and str(ml_intent_val) != "fallback":
            intent = str(ml_intent_val)
            engine_source = "ml_engine"
            confidence = round(float(ml_score), 4)
            status = route_intent(intent)
            # Ambil respons default dari rules berdasarkan intent hasil ML
            for rule in INTENT_RULES:
                if rule["name"] == intent:
                    base_reply = rule["mappings"][0]["response"]
                    break
        else:
            # Layer 3: Semantic Engine (Metode Kesamaan TF-IDF Teroptimasi)
            logger.info(f"MLEngine low confidence, applying Similarity Scoring for: {message}")
            
            # Jika input mengandung kata jawa atau mix, semantic seringkali lebih akurat dari ML
            if is_ambiguous:
                sem_threshold = 0.98
            else:
                sem_threshold = 0.80 if is_short_input else 0.55 # Sedikit diturunkan agar lebih sensitif
                
            # Gunakan penanganan tuple yang aman untuk menghindari "size mismatch"
            sem_res = semantic_engine.detect(message, threshold=sem_threshold)
            if isinstance(sem_res, tuple) and len(sem_res) == 3:
                sem_intent, sem_score, sem_reply = sem_res
            else:
                sem_intent, sem_score, sem_reply = None, 0.0, None

            if sem_intent is not None:
                intent = str(sem_intent)
                engine_source = "semantic_engine"
                confidence = float(sem_score)
                base_reply = str(sem_reply)
                status = route_intent(intent)
            else:
                # Final Fallback jika semua engine gagal
                confidence = 0.0
                engine_source = "fallback"
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
    _engine_counts[engine_source] += 1
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
    """Mengirim balasan manual dari staff ke Telegram user atau WhatsApp (Fonnte)."""

    # Deteksi Platform berdasarkan chat_id.
    # Heuristik: ID Telegram user saat ini < 10^10. Nomor WA (IDN 628...) > 10^11.
    is_whatsapp = req.chat_id > 10_000_000_000

    if is_whatsapp:
        if not FONNTE_TOKEN:
            raise HTTPException(status_code=500, detail="Fonnte token tidak dikonfigurasi")
        
        # WhatsApp (Fonnte) mendukung format *bold*
        formatted_reply = f"*🧑‍💻 Staf ({req.staff_name}) membalas:*\n\n{req.reply_message}"
        
        try:
            res = requests.post(
                FONNTE_API_URL,
                headers={"Authorization": FONNTE_TOKEN},
                data={
                    "target": str(req.chat_id),
                    "message": formatted_reply,
                    "delay": "2"
                },
                timeout=15
            )
            if res.status_code == 200:
                _save_to_db(f"MANUAL_REPLY_FROM_{req.staff_name}", "manual_response", "STAFF_REPLY", 
                            formatted_reply, req.chat_id, 1.0, None)
                return {"status": "sent", "platform": "whatsapp"}
            
            logger.error(f"Fonnte Error: {res.status_code} - {res.text}")
            raise HTTPException(status_code=400, detail=f"Gagal kirim WhatsApp: {res.text}")
        except Exception as e:
            logger.error(f"WhatsApp Reply Exception: {e}")
            raise HTTPException(status_code=500, detail=f"Koneksi Fonnte Error: {str(e)}")

    # Logic Telegram
    if not TELEGRAM_TOKEN:
        raise HTTPException(status_code=500, detail="Bot token tidak dikonfigurasi")
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    
    # Gunakan HTML parse mode agar lebih aman terhadap karakter spesial dibanding Markdown
    safe_name = req.staff_name.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    safe_msg = req.reply_message.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    formatted_reply_html = f"🧑‍💻 <b>Staf ({safe_name}) membalas:</b>\n\n{safe_msg}"

    payload = {"chat_id": req.chat_id, "text": formatted_reply_html, "parse_mode": "HTML"}

    # Gunakan fitur reply asli Telegram jika msg_id tersedia
    if req.reply_to_msg_id:
        payload["reply_to_message_id"] = int(req.reply_to_msg_id)
        
    res = requests.post(url, json=payload, timeout=15)
    if res.status_code == 200:
        _save_to_db(f"MANUAL_REPLY_FROM_{req.staff_name}", "manual_response", "STAFF_REPLY", 
                    formatted_reply_html, req.chat_id, 1.0, req.reply_to_msg_id)
        return {"status": "sent"}

    logger.error(f"Telegram API Error: {res.status_code} - {res.text}")
    error_detail = res.json().get("description", "Gagal mengirim pesan ke Telegram")
    raise HTTPException(status_code=400, detail=f"Telegram Error: {error_detail}")

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
