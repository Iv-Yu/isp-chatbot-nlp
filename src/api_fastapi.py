from __future__ import annotations
import os
import random
import secrets
from datetime import datetime
try:
    # Python 3.9+: zoneinfo in stdlib
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from .chatbot.rule_engine import RuleEngine
from .chatbot.rules import FALLBACK_RESPONSES
from .chatbot.response_router import route_intent
from .chatbot import tickets
from .nlp.entity_extractor import EntityExtractor

BASE_DIR = Path(__file__).resolve().parent.parent
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
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")
DOMAIN_KEYWORDS = {
    "internet", "wifi", "wipi", "paket", "tagihan", "bayar", "billing", "kabel",
    "modem", "los", "lampu", "cs", "noc", "teknisi", "pasang", "upgrade",
    "downgrade", "ganti", "password", "sandi", "tiket", "gangguan", "lemot", "putus",
}

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

_OUTAGE_STATE = {
    "enabled": os.getenv(OUTAGE_ENV_FLAG, "").lower() in {"1", "true", "on"},
    "message": OUTAGE_MESSAGE,
}

def _check_admin(token: str | None):
    if not ADMIN_TOKEN:
        raise HTTPException(
            status_code=500,
            detail="Fitur admin tidak dikonfigurasi di server (ADMIN_TOKEN kosong)."
        )
    if not token or not secrets.compare_digest(token, ADMIN_TOKEN):
        raise HTTPException(status_code=401, detail="Token admin tidak valid atau tidak ada.")
@app.get("/health")
async def health_check():
    return {"status": "ok"}

def _predict(message: str) -> ChatResponse:
    if not message.strip():
        raise HTTPException(status_code=400, detail="Pesan tidak boleh kosong.")

    entity = entity_extractor.extract(message)

    def _time_greet() -> str:
        # Create timezone-aware now if possible
        try:
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

    # 1. Mode Gangguan Massal (Prioritas Tertinggi)
    if _OUTAGE_STATE["enabled"]:
        outage_reply = f"{_time_greet()}! {_OUTAGE_STATE['message']}"
        return ChatResponse(
            intent="gangguan_massal",
            confidence=1.0,
            entity=entity,
            status="TO_NOC",
            reply=outage_reply,
        )

    # 2. Deteksi menggunakan RuleEngine yang baru
    # Metode ini langsung mengembalikan intent, respons spesifik, dan status
    rule_intent, specific_response, status = rule_engine.detect_with_response(message)

    # 3. Jika RuleEngine menemukan kecocokan yang kuat
    if rule_intent != "fallback":
        # Untuk greeting: tambahkan sapaan waktu kecuali respons sudah
        # mengandung sapaan (mis. "Selamat malam", "Waalaikumsalam") atau
        # pesan pengguna sudah menyertakan kata sapaan.
        final_reply = specific_response
        if rule_intent == "greeting":
            resp_lower = specific_response.strip().lower()
            msg_lower = message.strip().lower()
            # jika respons sudah dimulai dengan sapaan kebahasaan, jangan tambahkan prefix
            if not (
                resp_lower.startswith(("selamat", "waalaikumsalam", "assalamu"))
                or any(g in msg_lower for g in ("selamat", "assalam", "assalamu"))
            ):
                final_reply = f"{time_greet()}! {specific_response}"

        return ChatResponse(
            intent=rule_intent,
            confidence=1.0,  # Keyakinan 100% karena berbasis aturan
            entity=entity,
            status=status,
            reply=final_reply,
        )

    # 4. RuleEngine fallback: gunakan fallback response statis (rules-only design)
    fallback_intent = "fallback"
    fallback_conf = 0.0
    fallback_status = route_intent(fallback_intent)
    fallback_reply = random.choice(FALLBACK_RESPONSES)
    if APPLY_TIME_GREETING in {"all"}:
        if not fallback_reply.strip().lower().startswith(("selamat", "waalaikumsalam", "assalamu")):
            fallback_reply = f"{time_greet()}! {fallback_reply}"

    return ChatResponse(
        intent=fallback_intent,
        confidence=fallback_conf,
        entity=entity,
        status=fallback_status,
        reply=fallback_reply,
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
async def set_outage_status(payload: OutageRequest, x_admin_token: str | None = Header(default=None, convert_underscores=False)):
    _check_admin(x_admin_token)
    _OUTAGE_STATE["enabled"] = payload.enabled
    if payload.message:
        _OUTAGE_STATE["message"] = payload.message
    return OutageStatus(enabled=_OUTAGE_STATE["enabled"], message=_OUTAGE_STATE["message"])
