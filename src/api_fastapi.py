from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from chatbot.rule_engine import RuleEngine
from chatbot.rules import INTENT_RULES, FALLBACK_RESPONSES
from chatbot import tickets

app = FastAPI(title="Customer Service Chatbot API")

engine = RuleEngine()


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    intent: str
    reply: str
    status: str


class TicketRequest(BaseModel):
    ticket_id: str


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    intent, reply, status = engine.detect_with_status(request.message)

    return {
        "intent": intent,
        "reply": reply,
        "status": status,
    }


@app.post("/cs/escalate")
async def escalate_to_cs(request: ChatRequest):
    tid = tickets.create_ticket("CS", request.message)
    return {"ticket_id": tid, "message": "Laporan diteruskan ke Customer Service."}


@app.post("/noc/escalate")
async def escalate_to_noc(request: ChatRequest):
    tid = tickets.create_ticket("NOC", request.message)
    return {"ticket_id": tid, "message": "Laporan diteruskan ke tim NOC untuk penanganan teknis."}


@app.post("/ticket/status")
async def ticket_status(request: TicketRequest):
    status = tickets.get_ticket_status(request.ticket_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return {"ticket_id": request.ticket_id, "status": status}
