import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env", override=True)

API_BASE_URL = "http://127.0.0.1:8000"
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "").strip()

st.set_page_config(page_title="ISP Chatbot Monitoring", layout="wide")

st.title("📊 ISP Chatbot Monitoring Dashboard")
st.sidebar.header("Konfigurasi")

if not ADMIN_TOKEN:
    st.sidebar.error("⚠️ ADMIN_TOKEN belum diatur")

@st.cache_data(ttl=10)  # Cache data selama 10 detik untuk efisiensi
def fetch_stats():
    if not ADMIN_TOKEN:
        st.session_state["api_error"] = "ADMIN_TOKEN belum diatur Dashboard tidak dapat mengambil data."
        return None
    headers = {"x-admin-token": ADMIN_TOKEN}
    try:
        r = requests.get(f"{API_BASE_URL}/admin/stats", headers=headers, timeout=5)
        if r.status_code == 401:
            st.session_state["api_error"] = "401: Token Admin tidak valid"
            return None
        r.raise_for_status()
        st.session_state["api_error"] = None
        return r.json()
    except requests.exceptions.ConnectionError:
        st.session_state["api_error"] = f"Tidak dapat terhubung ke {API_BASE_URL}."
        return None
    except Exception as e:
        st.session_state["api_error"] = f"Terjadi kesalahan: {str(e)}"
        return None

def toggle_outage(status, message):
    headers = {"x-admin-token": ADMIN_TOKEN}
    payload = {"enabled": status, "message": message}
    try:
        r = requests.post(f"{API_BASE_URL}/admin/outage", json=payload, headers=headers, timeout=5)
        r.raise_for_status()
        st.cache_data.clear()  # Bersihkan cache agar data terbaru segera muncul
        return True
    except Exception as e:
        st.error(f"Gagal update status: {e}")
        return False

# Sidebar - Pengaturan Auto Refresh
auto_refresh = st.sidebar.checkbox("Auto Refresh (30s)", value=True)
data = fetch_stats()

if data:
    st.sidebar.success("✅ Terhubung ke API")
    st.sidebar.write(f"Update terakhir: {datetime.now().strftime('%H:%M:%S')}")

    # Row 1: Key Metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        total_msg = sum(data["intent_distribution"].values())
        st.metric("Total Traffic", f"{total_msg} Pesan")
    with col2:
        uptime_min = data["uptime_seconds"] // 60
        st.metric("Uptime Server", f"{uptime_min} Menit")
    with col3:
        is_outage = data["outage_status"]["enabled"]
        st.metric("Status Gangguan", "AKTIF" if is_outage else "NORMAL", 
                  delta_color="inverse" if is_outage else "normal")

    st.divider()

    # Row 2: Charts
    tab1, tab2, tab3 = st.tabs(["📈 Analitik Intent", "📋 Log Eskalasi", "⚙️ Manajemen Sistem"])
    
    with tab1:
        st.subheader("Distribusi NLU Intent")
        if data["intent_distribution"]:
            df_intent = pd.DataFrame(
                list(data["intent_distribution"].items()), 
                columns=["Intent", "Count"]
            ).sort_values(by="Count", ascending=False)
            
            fig = px.bar(df_intent, x="Intent", y="Count", color="Count", 
                         color_continuous_scale="Blues", labels={'Count':'Jumlah Pesan'})
            st.plotly_chart(fig, use_container_width=True, theme="streamlit")

            # Pie Chart untuk Status
            st.divider()
            st.subheader("Status Distribusi (Auto vs Escalation)")
            df_status = pd.DataFrame(
                list(data["status_distribution"].items()), 
                columns=["Status", "Count"]
            )
            fig_pie = px.pie(df_status, names="Status", values="Count", 
                             color="Status", hole=0.4,
                             color_discrete_map={"AUTO_RESPONSE": "#3498db", "TO_CS": "#f39c12", "TO_NOC": "#e74c3c", "OK": "#2ecc71"})
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("Menunggu data interaksi pertama...")

    with tab2:
        st.subheader("Log Eskalasi Terakhir (TO_CS / TO_NOC)")
        if data["recent_escalations"]:
            df_esc = pd.DataFrame(data["recent_escalations"])
            st.dataframe(
                df_esc, 
                use_container_width=True,
                column_config={
                "status": st.column_config.TextColumn("Status", help="Tujuan eskalasi (CS/NOC)"),
                }
            )
        else:
            st.info("Belum ada chat yang dialihkan ke CS atau NOC.")

    with tab3:
        st.subheader("Pusat Kendali")
        with st.container(border=True):
            st.write("### 🚨 Mode Gangguan Massal")
            new_status = st.toggle("Aktifkan Broadcast Gangguan", value=is_outage)
            msg = st.text_area("Pesan untuk User", value=data["outage_status"]["message"], 
                               help="Pesan ini akan dikirim ke user saat bot mendeteksi gangguan.")
            
            if st.button("Update Status"):
                if toggle_outage(new_status, msg):
                    st.toast("Konfigurasi sistem berhasil disimpan!", icon="✅")
                    st.rerun()

    # Script untuk auto-refresh sederhana
    if auto_refresh:
        import time
        # Refresh setiap 10 detik
        time.sleep(10)
        st.rerun()
else:
    error_msg = st.session_state.get("api_error", "Koneksi ke API gagal.")
    st.error(f"❌ {error_msg}")
    
    st.info("💡 Pastikan Anda menjalankan: `uvicorn src.api_fastapi:app --reload` di terminal.")
    
    if st.button("Coba Hubungkan Lagi"):
        st.rerun()

st.caption(f"ISP Chatbot Monitoring System v1.1 | API: {API_BASE_URL}")