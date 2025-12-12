# Capstone Project — Chatbot Layanan ISP Berbasis NLP (Rule-based)

## 🎯 Deskripsi Singkat
Proyek ini merupakan implementasi chatbot layanan pelanggan Internet Service Provider (ISP)
berbasis Natural Language Processing (NLP) menggunakan pendekatan rule-based.

Sistem ini mampu:
- Mendeteksi intent pelanggan
- Memberikan jawaban otomatis untuk pertanyaan dasar
- Mengeskalasi kasus yang kompleks ke Customer Service (CS)
- Mendeteksi kasus teknis untuk diteruskan ke NOC

Sistem terdiri dari:
- NLP Engine (normalisasi + rule engine)
- REST API (FastAPI)
- CLI untuk demo
- Endpoint dummy CS & NOC

---

## 🚀 Cara Menjalankan

### 1. Jalankan CLI


```powershell
python src/main_cli.py
```


### 2. Jalankan API Server


```powershell
uvicorn src.api_fastapi:app --reload
```

Akses API:
- POST `/chat` atau `/predict` → mengembalikan `intent`, `confidence`, `status` (AUTO_RESPONSE/TO_CS/TO_NOC), `reply`, dan `entity` (jika terdeteksi)
- POST `/cs/escalate`
- POST `/noc/escalate`

Catatan: endpoint eskalasi hanya dummy untuk keperluan tugas (membuat tiket mock di memori, tanpa integrasi eksternal).

---

## 🧠 Arsitektur


User → Chatbot → NLP Engine → Rules → Response
↓
Escalation Router
(AUTO_RESPONSE / TO_CS / TO_NOC)


---

## 📄 Fitur Utama

### ✔ NLP Engine
- Pattern scoring
- Token matching
- Threshold scoring
- Intent detection

### ✔ Sistem Eskalasi (sesuai proposal)
- AUTO_RESPONSE → chatbot menjawab
- TO_CS → fallback
- TO_NOC → gangguan teknis (kabel putus, gangguan)

### ✔ API Endpoints
- `/chat`
- `/cs/escalate`
- `/noc/escalate`

---

## 📦 Struktur Folder


src/
chatbot/
nlp_processor.py
rule_engine.py
rules.py
response_router.py
main_cli.py
api_fastapi.py


---

## 📞 Developer
Ivan Yusuf Sholy Khudin  
Teknik Informatika — UNP Kediri
