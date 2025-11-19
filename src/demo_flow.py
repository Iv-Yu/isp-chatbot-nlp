"""Demo script for showing detect_with_status flow and optional API escalation.

Usage:
  python demo_flow.py         # interactive direct mode (calls engine)
  python demo_flow.py --api  # call HTTP endpoints on localhost:8000
"""
import argparse
import json
import sys

from chatbot.rule_engine import RuleEngine


def run_direct():
    engine = RuleEngine()
    print("Direct demo mode — ketik 'quit' untuk keluar")
    while True:
        try:
            text = input("You: ")
        except (EOFError, KeyboardInterrupt):
            print("\nBye")
            break
        if text.strip().lower() in ("quit", "exit"):
            print("Bye")
            break
        intent, reply, status = engine.detect_with_status(text)
        print(json.dumps({"intent": intent, "status": status, "reply": reply}, ensure_ascii=False, indent=2))


def run_api():
    try:
        import requests
    except Exception:
        print("'requests' library required for API mode. Install with: pip install requests")
        sys.exit(1)

    base = "http://127.0.0.1:8000"
    print("API demo mode — target:", base)
    print("Enter messages (quit to exit). If status is TO_CS/TO_NOC, demo will call escalation endpoint.")
    while True:
        try:
            text = input("You: ")
        except (EOFError, KeyboardInterrupt):
            print("\nBye")
            break
        if text.strip().lower() in ("quit", "exit"):
            print("Bye")
            break

        try:
            r = requests.post(base + "/chat", json={"message": text})
            data = r.json()
        except Exception as e:
            print("Error calling /chat:", e)
            continue

        print(json.dumps(data, ensure_ascii=False, indent=2))

        status = data.get("status")
        if status == "TO_CS":
            print("Escalating to CS...")
            r2 = requests.post(base + "/cs/escalate", json={"message": text})
            print(r2.json())
        elif status == "TO_NOC":
            print("Escalating to NOC...")
            r2 = requests.post(base + "/noc/escalate", json={"message": text})
            print(r2.json())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", action="store_true", help="Call HTTP API instead of engine directly")
    args = parser.parse_args()
    if args.api:
        run_api()
    else:
        run_direct()


if __name__ == "__main__":
    main()
