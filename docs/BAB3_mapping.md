**BAB 3 — Mapping Implementasi ke Kode (Ringkasan untuk Skripsi)**

Dokumen ini menjelaskan bagaimana komponen dan alur program pada repositori ini sesuai dengan Bab 3 metodologi penelitian Anda. Gunakan teks ini sebagai referensi langsung atau salin ke dokumen skripsi.

1. Jenis Penelitian & Model Pengembangan
- Jenis: Penelitian Pengembangan (Development Research). Repositori ini berisi artefak hasil pengembangan (kode sumber, dataset contoh, dan skrip pengujian).
- Model pengembangan: Waterfall terstruktur dengan iterasi kecil pada fase pengujian dan penyempurnaan rule (lihat `analysis_and_improve.py` dan `src/models/train_intent_model.py` untuk artefak eksperimen dan evaluasi).

2. Tahapan Waterfall → File / Modul terkait
- Analisis Kebutuhan
  - Sumber: `data/intent_dataset.csv`, `data/labeled_examples.csv`, `src/datasheet/*` (hasil evaluasi, misclassifications). Digunakan untuk mengidentifikasi intent, pola, dan noise.
- Perancangan Sistem
  - Arsitektur & alur terimplementasi di `src/api_fastapi.py` (entrypoint API), `src/telegram_bot.py` (frontend), dan `src/chatbot/*` (engine rule, router, preprocessor).
  - Diagram: sediakan gambaran UML/DFD di dokumen skripsi; jika perlu, file `docs/diagrams/` dapat ditambahkan.
- Implementasi
  - Modul utama:
    - `src/chatbot/nlp_preprocess.py`: tokenisasi, stopword removal, stemming (Sastrawi).
    - `src/chatbot/rule_engine.py`: pencocokan pola, scoring rule, dan mode debug (`INTENT_DEBUG`).
    - `src/chatbot/rules.py`: definisi intent, pattern, dan template respons.
    - `src/api_fastapi.py`: endpoint `POST /chat` yang memanggil processor dan mereturn `intent, confidence, reply`.
    - `src/telegram_bot.py`: implementasi frontend Telegram (long-polling), pending state untuk slot-filling.
- Pengujian
  - Skrip & test:
    - `src/tests/` berisi unit/integration tests (contoh `test_rule_engine.py`, `test_nlp_preprocess.py`).
    - `demo_cli_run.py` atau `src/demo_cli_run.py` untuk simulasi lokal percakapan.
  - Logging: jalankan `INTENT_DEBUG=1` untuk mengumpulkan trace matching rule (lihat `src/chatbot/rule_engine.py` untuk format trace). Simpan hasil `journalctl` atau `/tmp/uvicorn_out.log` sebagai bukti eksperimen.
- Pemeliharaan
  - File `src/analysis_and_improve.py` dan `src/chatbot/rules.py` ditujukan untuk iterasi rule dan perbaikan berdasarkan misclassifications.

3. Variabel Penelitian → Artefak pengukuran
- Metode NLP rule-based: implementasi di `src/chatbot/rule_engine.py` dan `src/chatbot/rules.py`.
- Context-Aware Fallback Engine: alur fallback dan scoring terdapat di `src/chatbot/response_router.py` dan `src/chatbot/rule_engine.py` (pilihan fallback ketika tidak ada rule yang lolos threshold, dan trace debug untuk relevansi).
- Adaptive Response Delay (ARD): implementasi ARD dapat ditemukan atau diaktifkan di bagian API/bot (opsional), catat eksperimen ARD di `src/analysis_and_improve.py`.

4. Instrumen & Dataset
- Dataset contoh: `data/intent_dataset.csv`, `data/labeled_examples.csv`.
- Instrumen pengukuran: gunakan log response time (server-side timestamps), file `data/hasil_evaluasi_chatbot_v2.csv` untuk hasil uji, dan kuesioner (simpan di `docs/questionnaire/` jika tersedia).

5. Prosedur Eksperimen & Pengumpulan Data
- Jalankan server API (systemd unit atau `uvicorn`) dan Telegram bot; simulasikan skenario uji via `curl` atau `demo_cli_run.py` untuk mengumpulkan metrik.
- Contoh perintah untuk mengumpulkan trace:
  - Jalankan API dengan debug: `INTENT_DEBUG=1 uvicorn src.api_fastapi:app --host 0.0.0.0 --port 8121` dan simpan output.
  - Kirim percakapan uji via `curl` dan simpan respons serta timestamp.

6. Analisis Data & Visualisasi
- Sediakan skrip analisis di `src/evaluate_dataset.py` yang menghasilkan confusion matrix, akurasi (%), dan ringkasan waktu respons. Hasil analisis disimpan ke `datasheet/`.

7. Lampiran yang Disarankan untuk Skripsi
- `docs/BAB3_mapping.md` (ini)
- Contoh log `journalctl -u nlp-api.service` (file teks)
- CSV hasil evaluasi (`datasheet/hasil_evaluasi_chatbot_v2.csv`)
- Diagram arsitektur (`docs/diagrams/`)
- Instruksi reproducibility (`REPOSITORY_GUIDE.md`)

Gunakan bagian-bagian di atas sebagai paragraf dan tabel di Bab 3 — setiap subseksi metodologi dapat dikaitkan langsung dengan file dan eksperimen yang ada di repositori.

