from __future__ import annotations
import os
import random
from collections import Counter
import secrets
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
_recent_escalations = []
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

OUTAGE_ENV_FLAG = "OUTAGE_MODE"
TIMEZONE = os.getenv("TIMEZONE", "Asia/Jakarta")
APPLY_TIME_GREETING = os.getenv("APPLY_TIME_GREETING", "greeting").lower()  # all|greeting|none


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
    uptime_seconds: int
    outage_status: OutageStatus
    recent_escalations: List[Dict]


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
    uptime = int(time.time() - _start_time)
    return StatsResponse(
        intent_distribution=dict(_intent_counts),
        status_distribution=dict(_status_counts),
        uptime_seconds=uptime,
        outage_status=OutageStatus(enabled=_OUTAGE_STATE["enabled"], message=_OUTAGE_STATE["message"]),
        recent_escalations=_recent_escalations[::-1]  # Kirim yang terbaru dulu
    )
async def health_check():
    return {"status": "ok"}

@app.get("/")
async def root():
    """Root endpoint to verify the API is running."""
    return {"message": "ISP Chatbot Intent API is running. Send POST requests to /chat"}

def _predict(message: str) -> ChatResponse:
    """
    Internal logic to predict intent and generate a response.
    
    Flow:
    1. Protocol handling -> 2. Outage check -> 3. Rule Engine -> 4. Post-processing
    """
    if not message.strip():
        raise HTTPException(status_code=400, detail="Pesan tidak boleh kosong.")

    # Handle special internal protocols from Telegram Bot
    if message.startswith("__IDENTITY__:"):
        identity_val = message.replace("__IDENTITY__:", "")
        # Logika simpan identitas ke DB bisa di sini
        _intent_counts["provide_identity"] += 1
        _status_counts["OK"] += 1
        return ChatResponse(intent="provide_identity", confidence=1.0, status="OK", reply=f"Identitas {identity_val} berhasil diterima.")
    
    if message.startswith("__LOCATION__:"):
        loc_val = message.replace("__LOCATION__:", "")
        # Logika simpan lokasi ke DB bisa di sini
        _intent_counts["provide_location"] += 1
        _status_counts["OK"] += 1
        return ChatResponse(intent="provide_location", confidence=1.0, status="OK", reply="Lokasi berhasil dipetakan.")

    entity = entity_extractor.extract(message)

    # 1. Mode Gangguan Massal (Prioritas Tertinggi)
    if _OUTAGE_STATE["enabled"]:
        outage_reply = f"{time_greet()}! {_OUTAGE_STATE['message']}"
        _intent_counts["gangguan_massal"] += 1
        _status_counts["TO_NOC"] += 1
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

    _intent_counts[intent] += 1
    _status_counts[status] += 1

    # Catat pesan yang dieskalasi untuk ditampilkan di dashboard
    if status in ["TO_CS", "TO_NOC"]:
        _recent_escalations.append({
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "message": message[:100] + "..." if len(message) > 100 else message,
            "intent": intent,
            "status": status
        })
        if len(_recent_escalations) > 20: _recent_escalations.pop(0)

    logger.info(f"Intent: {intent} | Status: {status} | Msg: {message[:30]}...")

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
    return _predict(request.message)


# Backwards compatibility: some clients (legacy telegram bot) still call `/predict`.
# Keep this wrapper to avoid 404s until all clients are migrated.
@app.post("/predict", response_model=ChatResponse)
async def predict_compat(request: ChatRequest) -> ChatResponse:
    return _predict(request.message)

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
