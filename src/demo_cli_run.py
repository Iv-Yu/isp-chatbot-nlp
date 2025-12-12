from chatbot.rule_engine import RuleEngine
from chatbot import tickets


def show(msg, intent, reply, status):
    print(f"> User:   {msg}")
    print(f"  - Intent: {intent}")
    print(f"  - Reply:  {reply}")
    print(f"  - Status: {status}\n")


def main():
    engine = RuleEngine(min_score=1)

    # 1. Greeting
    msg = "halo"
    intent, reply, status = engine.detect_with_status(msg)
    show(msg, intent, reply, status)

    # 2. Check billing
    msg = "cek tagihan"
    intent, reply, status = engine.detect_with_status(msg)
    show(msg, intent, reply, status)

    # 3. Technical issue -> kabel putus
    msg = "kabel putus"
    intent, reply, status = engine.detect_with_status(msg)
    show(msg, intent, reply, status)

    # Simulate escalate to NOC via API -> create ticket
    tid = tickets.create_ticket("NOC", "kabel putus di jalan")
    print(f"[Demo] Tiket dibuat: {tid}\n")

    # 4. User asks to check ticket status (intent asks for ID)
    msg = "cek status tiket"
    intent, reply, status = engine.detect_with_status(msg)
    show(msg, intent, reply, status)

    # 5. User provides ticket id -> simulate lookup
    msg = tid
    tstatus = tickets.get_ticket_status(msg)
    print(f"> User:   {msg}")
    print(f"  - Tiket Status: {tstatus}\n")


if __name__ == "__main__":
    main()
