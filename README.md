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


```
