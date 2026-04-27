# ISP Chatbot NLP - Hybrid System

Sistem chatbot layanan pelanggan ISP yang menggabungkan kecepatan **Rule Engine**, akurasi statistik **SVM**, dan kecerdasan semantik **SBERT**.

## 🚀 Fitur Utama
- **Hybrid Intent Classification**:
    1. **Layer 1 (Rule-based)**: Menggunakan token matching teroptimasi untuk respon instan.
    2. **Layer 2 (Machine Learning)**: LinearSVC (SVM) dengan probabilitas terkalibrasi.
    3. **Layer 3 (Semantic Similarity)**: SBERT (`paraphrase-multilingual`) untuk memahami makna kalimat yang kompleks/daerah.
- **Monitoring Dashboard**: Dashboard analitik berbasis Streamlit untuk memantau distribusi intent, performa engine, matriks evaluasi (Confusion Matrix), dan manajemen eskalasi CS/NOC.
- **Integrasi SmartOLT**: Pengecekan status perangkat pelanggan (Online, LOS, Power Fail) secara real-time via API.
- **Telegram Bot Interface**: Mendukung interaksi teks, pengiriman lokasi (coverage check), dan foto (bukti gangguan).
- **Role Management**: Sistem autentikasi untuk Admin, CS, dan NOC.

## 🛠️ Instalasi & Persiapan

1. **Virtual Environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .\.venv\Scripts\activate   # Windows
   ```

2. **Dependensi**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Konfigurasi**:
   Salin `.env.example` ke `.env` dan isi kredensial Telegram, Database PostgreSQL, dan SmartOLT.

## 💻 Cara Menjalankan

### 1. Jalankan API Backend (FastAPI)
```bash
uvicorn src.api_fastapi:app --host 127.0.0.1 --port 8931
```

### 2. Jalankan Dashboard Monitoring (Streamlit)
```bash
streamlit run src/dashboard.py
```

### 3. Jalankan Telegram Bot
```bash
python src/telegram_bot.py
```

## 🧠 Training Model ML
Untuk melatih ulang model SVM berdasarkan dataset terbaru:
```bash
python -m src.models.train_intent_model --dataset data/intent_dataset.csv
```