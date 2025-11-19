from chatbot.rule_engine import RuleEngine


def main():
    print("=== Chatbot Layanan ISP (NLP Rule-based) ===")
    print("Ketik 'quit' untuk keluar.\n")

    engine = RuleEngine()

    while True:
        user_input = input("Kamu : ")

        if user_input.lower().strip() in ["quit", "exit"]:
            print("Bot  : Terima kasih kak 🙏")
            break

        intent, response, status = engine.detect_with_status(user_input)

        print(f"[Intent : {intent}]")
        print(f"[Status : {status}]")  # <-- highlight untuk capstone
        print(f"Bot    : {response}\n")


if __name__ == "__main__":
    main()
