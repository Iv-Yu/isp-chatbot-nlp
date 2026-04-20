from __future__ import annotations
import os
import random
from collections import Counter, defaultdict
import secrets
import mysql.connector
from datetime import datetime
import time
import logging
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
from .chatbot.rules import FALLBACK_RESPONSES
from .chatbot.response_router import route_intent
from .chatbot import tickets
from .nlp.entity_extractor import EntityExtractor

# Application start time for uptime calculation
_start_time = time.time()
# Setup logging
# Penampung statistik intent di memori (reset jika server restart)
_intent_counts = Counter()
_status_counts = Counter()
_intent_status_counts = defaultdict(Counter)
_recent_escalations = []
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
LOG_FILE = DATA_DIR / "chat_logs.csv"
DB_FILE = DATA_DIR / "chatbot.db"

# Pastikan direktori data ada
DATA_DIR.mkdir(exist_ok=True)

load_dotenv(BASE_DIR / ".env")

def get_db_connection():
    """Membuat koneksi ke database MySQL XAMPP."""
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "isp_chatbot"),
        autocommit=True
    )

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OUTAGE_ENV_FLAG = "OUTAGE_MODE"
TIMEZONE = os.getenv("TIMEZONE", "Asia/Jakarta")
APPLY_TIME_GREETING = os.getenv("APPLY_TIME_GREETING", "greeting").lower()  # all|greeting|none

def init_db():
    """Inisialisasi database MySQL untuk user dan logging."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
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
                id INT AUTO_INCREMENT PRIMARY KEY,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                chat_id BIGINT,
                message TEXT,
                intent VARCHAR(50),
                status VARCHAR(20),
                reply TEXT
            )
        ''')
        # Tabel Chats (Status Aktif)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chats (
                chat_id BIGINT PRIMARY KEY,
                last_message TEXT,
                status VARCHAR(20),
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
    except Exception as e:
        logger.error(f"Gagal inisialisasi MySQL: {e}")
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

def _get_chat_status(chat_id: Optional[int]) -> str:
    """Mengambil status terakhir chat dari database."""
    if chat_id is None: return "OK"
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM chats WHERE chat_id = %s", (chat_id,))
        result = cursor.fetchone()
        return result[0] if result else "OK"
    except Exception:
        return "OK"
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

init_db()

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
rule_engine = RuleEngine(min_score=1)
# ML classifier removed for clarity; fallback handled by rules and static responses
entity_extractor = EntityExtractor()

app = FastAPI(title="ISP Chatbot Intent API")

# --- Model Pydantic (Tidak Berubah) ---
class ChatRequest(BaseModel):
    message: str
    chat_id: Optional[int] = None

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
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        # Ambil semua sesi yang berstatus eskalasi dari tabel chats
        query = "SELECT * FROM chats WHERE status IN ('TO_CS', 'TO_NOC') ORDER BY updated_at DESC"
        cursor.execute(query)
        rows = cursor.fetchall()
        for row in rows:
            active_sessions.append({
                "chat_id": row["chat_id"],
                "message": row["last_message"],
                "status": row["status"],
                "timestamp": row["updated_at"].strftime("%Y-%m-%d %H:%M:%S")
            })
    except Exception as e:
        logger.error(f"Error fetching active sessions: {e}")
    finally:
        if conn: conn.close()

    return StatsResponse(
        intent_distribution=dict(_intent_counts),
        status_distribution=dict(_status_counts),
        intent_status_distribution={k: dict(v) for k, v in _intent_status_counts.items()},
        uptime_seconds=uptime,
        outage_status=OutageStatus(enabled=_OUTAGE_STATE["enabled"], message=_OUTAGE_STATE["message"]),
        recent_escalations=active_sessions
    )

def _update_chat_session(chat_id: Optional[int], message: str, status: str):
    """Memperbarui session chat aktif di database."""
    if chat_id is None: return
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = """
            INSERT INTO chats (chat_id, last_message, status)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE last_message=%s, status=%s, updated_at=CURRENT_TIMESTAMP
        """
        cursor.execute(query, (chat_id, message, status, message, status))
        conn.commit()
    except Exception as e:
        logger.error(f"Gagal update session chat: {e}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

def _log_escalation(chat_id: Optional[int], message: str, intent: str, status: str):
    """Mencatat pesan ke dalam daftar eskalasi memori untuk dashboard."""
    if status not in ["TO_CS", "TO_NOC"]: return
    _recent_escalations.append({
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "chat_id": chat_id,
        "message": message[:100] + "..." if len(message) > 100 else message,
        "intent": intent,
        "status": status
    })
    if len(_recent_escalations) > 20: _recent_escalations.pop(0)

def _save_to_db(message: str, intent: str, status: str, reply: str, chat_id: Optional[int] = None):
    """Menyimpan interaksi chat ke database MySQL."""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = """
            INSERT INTO chat_logs (chat_id, message, intent, status, reply)
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(query, (chat_id, message, intent, status, reply))
        conn.commit()
    except Exception as e:
        logger.error(f"Gagal menyimpan log ke DB: {e}")
    finally:
        if conn and conn.is_connected():
            if cursor: cursor.close()
            conn.close()

def _load_stats_from_db():
    """Memuat statistik dari database MySQL saat startup."""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT chat_id, message, intent, status, timestamp FROM chat_logs")
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
                    "status": status
                })
        del _recent_escalations[:-20]
    except Exception as e:
        logger.error(f"Gagal memuat statistik dari DB: {e}")
    finally:
        if conn and conn.is_connected():
            if cursor: cursor.close()
            conn.close()

async def health_check():
    return {"status": "ok"}

@app.get("/")
async def root():
    """Root endpoint to verify the API is running."""
    return {"message": "ISP Chatbot Intent API is running. Send POST requests to /chat"}

def _predict(message: str, chat_id: Optional[int] = None) -> ChatResponse:
    """
    Internal logic to predict intent and generate a response.
    
    Flow:
    1. Protocol handling -> 2. Outage check -> 3. Rule Engine -> 4. Post-processing
    """
    if not message.strip():
        raise HTTPException(status_code=400, detail="Pesan tidak boleh kosong.")

    # Cek status sesi saat ini sebelum memproses
    current_session_status = _get_chat_status(chat_id)

    # Handle special internal protocols from Telegram Bot
    if message.startswith("__IDENTITY__:"):
        identity_val = message.replace("__IDENTITY__:", "")
        _intent_counts["provide_identity"] += 1
        
        # Jika user sedang dalam eskalasi, pertahankan status tersebut agar masuk log staff
        status = current_session_status if current_session_status in ["TO_CS", "TO_NOC"] else "OK"
        
        _status_counts[status] += 1
        _intent_status_counts["provide_identity"][status] += 1
        logger.info(f"Protocol IDENTITY received for chat_id: {chat_id}")
        _save_to_db(message, "provide_identity", status, f"Identitas {identity_val} berhasil diterima.", chat_id)
        _update_chat_session(chat_id, message, status)
        _log_escalation(chat_id, f"📌 ID: {identity_val}", "provide_identity", status)
        return ChatResponse(intent="provide_identity", confidence=1.0, status=status, reply=f"Identitas {identity_val} berhasil diterima.")
    
    if message.startswith("__LOCATION__:"):
        loc_val = message.replace("__LOCATION__:", "")
        _intent_counts["provide_location"] += 1
        
        status = current_session_status if current_session_status in ["TO_CS", "TO_NOC"] else "OK"
        
        _status_counts[status] += 1
        _intent_status_counts["provide_location"][status] += 1
        logger.info(f"Protocol LOCATION received for chat_id: {chat_id}")
        _save_to_db(message, "provide_location", status, "Lokasi berhasil dipetakan.", chat_id)
        _update_chat_session(chat_id, message, status)
        _log_escalation(chat_id, f"📍 Lokasi: {loc_val[:50]}", "provide_location", status)
        return ChatResponse(intent="provide_location", confidence=1.0, status=status, reply="Lokasi berhasil dipetakan.")

    # Handle Protocol Foto/Screenshot
    if message == "__PHOTO_SENT__":
        _intent_counts["provide_screenshot"] += 1
        status = current_session_status if current_session_status in ["TO_CS", "TO_NOC"] else "OK"
        
        _status_counts[status] += 1
        _intent_status_counts["provide_screenshot"][status] += 1
        logger.info(f"Screenshot received for chat_id: {chat_id}")
        _save_to_db(message, "provide_screenshot", status, "User mengirimkan gambar/screenshot.", chat_id)
        _update_chat_session(chat_id, "User mengirimkan gambar", status)
        _log_escalation(chat_id, "🖼️ [Gambar/Screenshot]", "provide_screenshot", status)
        return ChatResponse(intent="provide_screenshot", confidence=1.0, status=status, reply="Gambar berhasil diterima kak, kami lampirkan ke laporan ya 🙏")

    entity = entity_extractor.extract(message)

    # 1. Mode Gangguan Massal (Prioritas Tertinggi)
    if _OUTAGE_STATE["enabled"]:
        outage_reply = f"{time_greet()}! {_OUTAGE_STATE['message']}"
        _intent_counts["gangguan_massal"] += 1
        _status_counts["TO_NOC"] += 1
        _intent_status_counts["gangguan_massal"]["TO_NOC"] += 1
        
        # Simpan ke DB agar tidak kosong di dashboard
        _save_to_db(message, "gangguan_massal", "TO_NOC", outage_reply, chat_id)
        _update_chat_session(chat_id, message, "TO_NOC")
        
        return ChatResponse(
            intent="gangguan_massal",
            confidence=1.0,
            entity=entity,
            status="TO_NOC",  # Status internal tetap TO_NOC
            reply=outage_reply,
        )

    # 2. Deteksi menggunakan RuleEngine yang baru
    # Metode ini langsung mengembalikan intent, respons spesifik, dan status
    intent, base_reply, status = rule_engine.detect_with_response(message)

    # 3. Tentukan confidence dan siapkan data fallback jika perlu
    if intent == "fallback":
        confidence = 0.0
        base_reply = random.choice(FALLBACK_RESPONSES)
    else:
        confidence = 1.0

    # 4. Post-processing: Apply time-based greetings
    final_reply = base_reply
    resp_lower = base_reply.strip().lower()
    msg_lower = message.strip().lower()
    
    should_greet = (APPLY_TIME_GREETING == "all") or (APPLY_TIME_GREETING == "greeting" and intent == "greeting")
    already_greeted = resp_lower.startswith(("selamat", "waalaikumsalam", "assalamu")) or \
                      any(g in msg_lower for g in ("selamat", "assalam", "assalamu"))

    if should_greet and not already_greeted:
        final_reply = f"{time_greet()}! {base_reply}"

    # Jika user sudah dalam antrean, paksa status pesan ini tetap eskalasi
    if current_session_status in ["TO_CS", "TO_NOC"]:
        status = current_session_status

    _intent_counts[intent] += 1
    _status_counts[status] += 1
    _intent_status_counts[intent][status] += 1

    # Catat pesan ke log eskalasi dashboard
    _log_escalation(chat_id, message, intent, status)

    # Simpan ke Database MySQL secara permanen
    _save_to_db(message, intent, status, final_reply, chat_id)

    # Update session chat aktif
    _update_chat_session(chat_id, message, status)

    logger.info(f"ChatID: {chat_id} | Intent: {intent} | Status: {status} | Msg: {message[:20]}...")

    return ChatResponse(
        intent=intent,
        confidence=confidence,
        entity=entity,
        status=status,
        reply=final_reply,
    )

# --- Endpoint API (Tidak Berubah, hanya endpoint /predict dihapus) ---
@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Menerima pesan chat dan mengembalikan intent, balasan, serta status."""
    return _predict(request.message, request.chat_id)

@app.post("/admin/login")
async def login(req: LoginRequest):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT username, role FROM users WHERE username = %s AND password = %s", (req.username, req.password))
        user = cursor.fetchone()
        if user:
            return {"status": "success", "role": user["role"], "username": user["username"]}
        raise HTTPException(status_code=401, detail="Username atau password salah")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    finally:
        if conn and conn.is_connected():
            if cursor: cursor.close()
            conn.close()

@app.get("/admin/chat-history/{chat_id}", tags=["Admin"])
async def get_chat_history(chat_id: int, _ = Depends(verify_admin_token)):
    """Mengambil seluruh riwayat percakapan untuk satu user tertentu."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        query = "SELECT timestamp, message, intent, status, reply FROM chat_logs WHERE chat_id = %s ORDER BY timestamp ASC"
        cursor.execute(query, (chat_id,))
        rows = cursor.fetchall()
        for row in rows:
            if isinstance(row["timestamp"], datetime):
                row["timestamp"] = row["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
        return rows
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching history: {e}")
    finally:
        if conn and conn.is_connected():
            if cursor: cursor.close()
            conn.close()

@app.get("/admin/logs/all", tags=["Admin"])
async def get_all_logs(_ = Depends(verify_admin_token)):
    """Mengambil seluruh log percakapan dari database untuk keperluan training."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        query = "SELECT timestamp, chat_id, message, intent, status, reply FROM chat_logs ORDER BY timestamp DESC"
        cursor.execute(query)
        rows = cursor.fetchall()
        return rows
    except Exception as e:
        logger.error(f"Error fetching all logs: {e}")
        raise HTTPException(status_code=500, detail="Gagal mengambil data log dari database.")
    finally:
        if conn and conn.is_connected():
            if cursor: cursor.close()
            conn.close()

@app.post("/admin/reply-chat", tags=["Admin"])
async def reply_to_user(req: ReplyRequest, _ = Depends(verify_admin_token)):
    """Mengirim balasan manual dari staff ke Telegram user."""
    if not TELEGRAM_TOKEN:
        raise HTTPException(status_code=500, detail="Bot token tidak dikonfigurasi")
    
    import requests as py_requests
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    formatted_msg = f"📩 *Balasan dari {req.staff_name.upper()}:*\n\n{req.reply_message}"
    
    res = py_requests.post(url, json={"chat_id": req.chat_id, "text": formatted_msg, "parse_mode": "Markdown"})
    if res.status_code == 200:
        _save_to_db(f"MANUAL_REPLY_FROM_{req.staff_name}", "manual_response", "OK", req.reply_message, req.chat_id)
        # Set status menjadi OK agar hilang dari antrean eskalasi di dashboard
        _update_chat_session(req.chat_id, f"Replied by {req.staff_name}", "OK")
        return {"status": "sent"}
    raise HTTPException(status_code=400, detail="Gagal mengirim pesan ke Telegram")

@app.post("/admin/users", tags=["Admin"])
async def create_user(req: UserCreateRequest, _ = Depends(verify_admin_token)):
    """Membuat user CS atau NOC baru."""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Cek apakah username sudah ada
        cursor.execute("SELECT username FROM users WHERE username = %s", (req.username,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Username sudah terdaftar.")
        
        # Tambahkan user baru
        cursor.execute("INSERT INTO users (username, password, role) VALUES (%s, %s, %s)", 
                       (req.username, req.password, req.role))
        conn.commit()
        return {"status": "success", "message": f"User {req.username} berhasil dibuat."}
    except Exception as e:
        if isinstance(e, HTTPException): raise e
        logger.error(f"Error creating user: {e}")
        raise HTTPException(status_code=500, detail="Terjadi kesalahan database.")
    finally:
        if conn and conn.is_connected():
            if cursor: cursor.close()
            conn.close()

# Backwards compatibility: some clients (legacy telegram bot) still call `/predict`.
# Keep this wrapper to avoid 404s until all clients are migrated.
@app.post("/predict", response_model=ChatResponse)
async def predict_compat(request: ChatRequest) -> ChatResponse:
    return _predict(request.message, request.chat_id)

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

# Panggil fungsi muat data saat aplikasi pertama kali dijalankan
_load_stats_from_db()
