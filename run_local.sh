#!/bin/bash

# 1. Pastikan folder logs tersedia
mkdir -p logs

# 2. Identifikasi path Python
PYTHON_EXEC=$(pwd)/venv/bin/python3

if [ ! -f "$PYTHON_EXEC" ]; then
    echo "Virtual environment tidak ditemukan. Menjalankan instalasi..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
fi

# 3. Jalankan API FastAPI di background
echo "🚀 Memulai API Chatbot di port 8121..."
PYTHONPATH=$(pwd) $PYTHON_EXEC -m uvicorn src.api_fastapi:app --host 0.0.0.0 --port 8121 --reload > logs/uvicorn_out.log 2>&1 &

# 4. Jalankan Dashboard Streamlit (Opsional)
# echo "📊 Memulai Dashboard Monitoring..."
# PYTHONPATH=$(pwd) $PYTHON_EXEC -m streamlit run src/dashboard.py --server.port 8501 > logs/streamlit.log 2>&1 &

echo "✅ Layanan dimulai. Gunakan 'tail -f logs/uvicorn_out.log' untuk memantau aktivitas."