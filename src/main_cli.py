import requests
import random
from chatbot.rules import INTENT_RULES, FALLBACK_RESPONSES

API_URL = "http://127.0.0.1:8000/predict"

def get_response_for_intent(intent: str) -> str:
    """
    Mencari dan mengembalikan teks respons acak untuk intent yang diberikan.
    """
    if intent == "fallback" or intent == "error":
        return random.choice(FALLBACK_RESPONSES)

    for rule in INTENT_RULES:
        if rule["name"] == intent:
            return random.choice(rule["responses"])
    
    # Jika intent dari model ML tidak ditemukan di rules.py, berikan fallback.
    return random.choice(FALLBACK_RESPONSES)


def get_prediction_from_api(message: str) -> tuple[str, float]:
    """
    Mengirim pesan ke API prediksi dan mendapatkan intent dan confidence.
    """
    try:
        payload = {"message": message}
        response = requests.post(API_URL, json=payload, timeout=10)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        data = response.json()
        return data.get("intent", "fallback"), data.get("confidence", 0.0)
    except requests.exceptions.RequestException as e:
        print(f"\n[Error] Tidak dapat terhubung ke API: {e}")
        return "error", 0.0


def main():
    """
    Loop utama untuk chat interaktif yang menggunakan API.
    """
    print("=== Chatbot Layanan ISP (Menggunakan Model ML via API) ===")
    print("Ketik 'quit' untuk keluar.\n")

    while True:
        user_input = input("Kamu : ")
        if user_input.lower().strip() in ["quit", "exit"]:
            print("Bot  : Terima kasih kak 🙏")
            break

        if not user_input.strip():
            continue

        # 1. Dapatkan prediksi intent dari API (yang menggunakan model ML)
        intent, confidence = get_prediction_from_api(user_input)

        # 2. Dapatkan teks respons berdasarkan intent yang diprediksi
        response_text = get_response_for_intent(intent)
        
        print(f"[Intent : {intent} (Confidence: {confidence:.2f})]")
        print(f"Bot    : {response_text}\n")


if __name__ == "__main__":
    main()
