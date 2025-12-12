# src/chatbot/response_router.py

"""
Routing keputusan hasil NLP sesuai flow CAPSTONE:
- AUTO_RESPONSE  → dijawab chatbot langsung
- TO_CS          → fallback atau kasus non-matching
- TO_NOC         → intent teknis (kabel putus, gangguan)
"""

TECHNICAL_INTENTS = ["kabel_putus", "gangguan_umum", "gangguan_lemot_umum", "gangguan_massal"]
CS_INTENTS = ["cek_coverage", "berhenti_langganan", "ganti_password_wifi"]


def route_intent(intent_name: str) -> str:
    # Jika intent tidak jelas → teruskan ke CS
    if intent_name == "fallback":
        return "TO_CS"

    # Jika intent adalah masalah teknis serius
    if intent_name in TECHNICAL_INTENTS:
        return "TO_NOC"

    # Intent khusus yang harus ditangani CS
    if intent_name in CS_INTENTS:
        return "TO_CS"

    # Selain itu → chatbot menjawab sendiri
    return "AUTO_RESPONSE"
