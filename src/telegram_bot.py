# -*- coding: utf-8 -*-
import os
import requests
import time
import re
import random
import logging
from typing import Optional

from telegram import ChatAction, Update
from telegram.ext import Filters, MessageHandler, Updater, CallbackContext, CommandHandler

# Load .env
from dotenv import load_dotenv
load_dotenv()

# Mengatur logging untuk melihat error (Dipindahkan ke atas agar tidak NameError)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Config dari env
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHATBOT_API_URL = os.getenv("CHATBOT_API_URL", "http://127.0.0.1:8931/chat")
# Pastikan URL tidak berakhir dengan slash untuk konsistensi
CHATBOT_API_URL = CHATBOT_API_URL.rstrip('/')

# --- Kode Diagnostik untuk Memverifikasi Token ---
if TELEGRAM_TOKEN:
    # Tampilkan beberapa karakter awal dan akhir untuk verifikasi
    logger.info(f"Bot diinisialisasi dengan token: {TELEGRAM_TOKEN[:6]}...{TELEGRAM_TOKEN[-4:]}")
else:
    logger.error("TELEGRAM_TOKEN tidak ditemukan di environment.")
# --- Akhir Kode Diagnostik ---

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN tidak ditemukan di environment variable. Set dulu ya kak.")

# In-memory per-user state, cocok untuk development
# Untuk production, pertimbangkan database (Redis, dll)
USER_STATE: dict = {}

# === Respon Statis untuk Fallback ===
FALLBACK_RESPONSES = [
    "Maaf kak, bisa diperjelas lagi pertanyaannya? Aku masih belajar nih.",
    "Waduh, aku kurang paham maksud kakak. Coba pakai kata kunci lain ya.",
    "Maaf, saya tidak mengerti. Mungkin bisa ditanyakan ke Customer Service kami?",
]


def get_state(chat_id: int) -> dict:
    """Mengambil atau membuat state untuk user berdasarkan chat_id."""
    if chat_id not in USER_STATE:
        USER_STATE[chat_id] = {
            "pending": None,        # Aksi yang sedang ditunggu (misal: 'need_identity')
            "pending_queue": [],    # Antrian aksi jika butuh beberapa input
            "last_intent": None,    # Intent terakhir yang terdeteksi
        }
    return USER_STATE[chat_id]


def start(update: Update, context: CallbackContext) -> None:
    """Handler untuk command /start."""
    update.message.reply_text('Halo! Saya Jenggala Bot, siap membantu Anda. Silakan ketik pertanyaan Anda.')

def handle_message(update: Update, context: CallbackContext) -> None:
    """Fungsi utama untuk menangani pesan teks dari user."""
    chat_id = update.message.chat_id
    user_text = update.message.text
    state = get_state(chat_id)

    # Menampilkan indikator "sedang mengetik"
    context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

    # =====================================================
    # 1. Logika untuk menangani input yang ditunggu (pending)
    # =====================================================
    pending_action = state.get("pending")

    if pending_action == "need_identity":
        handle_pending_identity(update, context)
        return
    if pending_action == "need_location":
        handle_pending_location(update, context)
        return

    # =====================================================
    # 2. Regex untuk menangkap ID Pelanggan atau nama
    # =====================================================
    # Regex untuk ID Pelanggan format 'bolt<angka>-<angka>'
    id_match = re.search(r"\bolt\d+-\d+\b", user_text, flags=re.I)
    if id_match:
        handle_pending_identity(update, context, pre_captured_id=id_match.group(0))
        return

    # Regex sederhana untuk menangkap 'nama saya <nama>'
    name_match = re.search(r"(?i)\bnama(?: saya)? [:\-]? ([A-Za-z][A-Za-z ]{2,80})$", user_text.strip())
    if name_match:
        handle_pending_identity(update, context, pre_captured_id=name_match.group(1).strip())
        return

    # =====================================================
    # 3. Jika tidak ada, teruskan ke API (NLU)
    # =====================================================
    try:
        # Kirim pesan ke API chatbot
        response = requests.post(
            CHATBOT_API_URL,
            json={"message": user_text, "chat_id": chat_id},
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()

        reply_text = payload.get("reply") or random.choice(FALLBACK_RESPONSES)
        intent = payload.get("intent")
        state["last_intent"] = intent

        # Periksa apakah API meminta info tambahan
        check_and_queue_pending_actions(state, reply_text, intent)

        # Kirim balasan dari API
        update.message.reply_text(reply_text)

        # Jika status adalah eskalasi, informasikan ke user
        if payload.get("status") in ["TO_CS", "TO_NOC"]:
            logger.info(f"Eskalasi terdeteksi untuk chat_id {chat_id}: {payload.get('status')}")

        # Proses antrian aksi (input identitas/lokasi)
        process_pending_queue(update, context)

    except requests.exceptions.RequestException as e:
        logger.error(f"Error calling chatbot API for chat_id {chat_id}: {e}")
        update.message.reply_text("Maaf, saya sedang tidak dapat terhubung ke server. Coba lagi nanti.")
    except Exception:
        logger.error("An unexpected error occurred in handle_message", exc_info=True)
        update.message.reply_text("Maaf kak, terjadi kesalahan internal. Tim kami sedang menanganinya.")

def handle_pending_identity(update: Update, context: CallbackContext, pre_captured_id: Optional[str] = None):
    """Menangani pesan yang dianggap sebagai identitas (nama/ID)."""
    chat_id = update.message.chat_id
    state = get_state(chat_id)
    name_or_id = pre_captured_id or update.message.text.strip()

    state["pending"] = None  # Selesaikan aksi 'need_identity'
    state["last_intent"] = "provide_identity"

    update.message.reply_text(f"Baik kak {name_or_id}, datanya kami cek dulu ya 🙏\nMohon tunggu sebentar.")

    try:
        # Kirim data identitas ke backend (fire-and-forget)
        payload = {"message": f"__IDENTITY__:{name_or_id}", "chat_id": chat_id}
        requests.post(CHATBOT_API_URL, json=payload, timeout=5)
        logger.info(f"Sent identity to API for chat_id {chat_id}")
    except requests.exceptions.RequestException:
        logger.warning(f"Could not send IDENTITY info for chat_id {chat_id}")

    # Lanjutkan ke antrian berikutnya jika ada
    process_pending_queue(update, context)

def handle_location(update: Update, context: CallbackContext) -> None:
    """Menangani input lokasi dari user (share location atau teks)."""
    chat_id = update.message.chat_id
    state = get_state(chat_id)

    # Reset pending state terkait lokasi
    if state.get("pending") == "need_location":
        state["pending"] = None
    
    # Ambil data lokasi
    location = update.message.location
    if location:
        loc_text = f"Lat:{location.latitude}, Lon:{location.longitude}"
    else:
        loc_text = update.message.text.strip()

    state["last_intent"] = "provide_location"
    update.message.reply_text(f"Terima kasih kak. Lokasi sudah kami terima, kami cek ya 🙏")

    try:
        # Kirim data lokasi ke backend
        payload = {"message": f"__LOCATION__:{loc_text}", "chat_id": chat_id}
        requests.post(CHATBOT_API_URL, json=payload, timeout=5)
        logger.info(f"Sent location to API for chat_id {chat_id}")
    except requests.exceptions.RequestException:
        logger.warning(f"Could not send LOCATION info for chat_id {chat_id}")
    
    # Lanjutkan ke antrian berikutnya
    process_pending_queue(update, context)

def handle_photo(update: Update, context: CallbackContext) -> None:
    """Menangani kiriman foto atau screenshot dari user."""
    chat_id = update.message.chat_id
    
    update.message.reply_text("Gambar berhasil diterima kak, kami lampirkan ke laporan ya 🙏")

    try:
        # Kirim sinyal ke API bahwa ada foto yang dikirim
        payload = {"message": "__PHOTO_SENT__", "chat_id": chat_id}
        requests.post(CHATBOT_API_URL, json=payload, timeout=5)
        logger.info(f"Sent photo notification to API for chat_id {chat_id}")
    except requests.exceptions.RequestException:
        logger.warning(f"Could not send PHOTO info for chat_id {chat_id}")

    process_pending_queue(update, context)

def handle_pending_location(update: Update, context: CallbackContext):
    """Wrapper untuk menangani pesan teks yang dianggap sebagai lokasi."""
    return handle_location(update, context)

def check_and_queue_pending_actions(state: dict, reply_text: str, intent: Optional[str]):
    """Menganalisa balasan API untuk mengantrikan permintaan info lanjutan."""
    pending_fields = []
    text_low = reply_text.lower()

    # Kumpulan kata kunci untuk deteksi
    identity_keywords = ["id pelanggan", "nomor pelanggan", "nama terdaftar"]
    location_keywords = ["alamat", "lokasi", "share lokasi", "pin point"]

    # Aturan berdasarkan intent
    if intent in ("gangguan_umum", "cek_tagihan", "berhenti_langganan"):
        if "need_identity" not in pending_fields:
            pending_fields.append("need_identity")
    if intent in ("cek_coverage", "cek_coverage_area"):
        if "need_location" not in pending_fields:
            pending_fields.append("need_location")

    # Aturan berdasarkan kata kunci di balasan
    if any(k in text_low for k in identity_keywords):
        if "need_identity" not in pending_fields:
            pending_fields.append("need_identity")
    if any(k in text_low for k in location_keywords):
        if "need_location" not in pending_fields:
            pending_fields.append("need_location")

    # Tambahkan ke antrian jika ada
    if pending_fields:
        q = state["pending_queue"]
        for field in pending_fields:
            if field not in q: # Hindari duplikat
                q.append(field)


def process_pending_queue(update: Update, context: CallbackContext):
    """Memproses antrian dan meminta input selanjutnya dari user."""
    state = get_state(update.message.chat_id)

    # Jika tidak ada aksi yang sedang berjalan dan ada antrian
    if not state["pending"] and state["pending_queue"]:
        next_action = state["pending_queue"].pop(0)
        state["pending"] = next_action
        time.sleep(0.5)  # Jeda sedikit agar tidak terasa spam

        if next_action == "need_location":
            update.message.reply_text("Boleh minta alamat lengkap atau share lokasinya kak? 🙏")
        elif next_action == "need_identity":
            update.message.reply_text("Boleh diinfokan ID Pelanggan atau nama lengkap yang terdaftar kak? 🙏")

def main() -> None:
    """Fungsi utama untuk menjalankan bot."""
    updater = Updater(TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher

    # Tambahkan handler
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    dp.add_handler(MessageHandler(Filters.location, handle_location))
    dp.add_handler(MessageHandler(Filters.photo | Filters.document, handle_photo))

    # Mulai bot
    try:
        updater.start_polling(clean=True) # clean=True menghapus pesan lama yang tertunda
    except Exception as e:
        logger.error(f"Gagal memulai bot: {e}")
        return

    logger.info("Bot Telegram sedang berjalan...")
    updater.idle()


if __name__ == "__main__":
    main()
