import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import os
import time
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
try:
    from streamlit_autorefresh import st_autorefresh
    HAS_AUTOREFRESH = True
except ImportError:
    HAS_AUTOREFRESH = False

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env", override=True)

API_BASE_URL = "http://127.0.0.1:8000"
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "").strip()

st.set_page_config(page_title="ISP Chatbot Monitoring", layout="wide")

st.title("📊 ISP Chatbot Monitoring Dashboard")
st.sidebar.header("Konfigurasi")

# --- Sistem Login Sederhana ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    with st.form("login_form"):
        st.subheader("🔑 Login Staff")
        user = st.text_input("Username")
        pw = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            try:
                r = requests.post(f"{API_BASE_URL}/admin/login", json={"username": user, "password": pw})
                if r.status_code == 200:
                    res = r.json()
                    st.session_state["logged_in"] = True
                    st.session_state["role"] = res["role"]
                    st.session_state["username"] = res["username"]
                    st.rerun()
                elif r.status_code == 401:
                    st.error("Login Gagal. Cek kembali credentials Anda.")
                else:
                    st.error(f"❌ Error {r.status_code}: Gagal menghubungi server login.")
            except Exception as e:
                st.error(f"Koneksi API Gagal: {e}")
    st.stop()

# Sidebar Info User
st.sidebar.success(f"Masuk sebagai: **{st.session_state['username']}** ({st.session_state['role'].upper()})")
if st.sidebar.button("Logout"):
    st.session_state["logged_in"] = False
    st.rerun()

def send_reply(chat_id, msg):
    headers = {"x-admin-token": ADMIN_TOKEN}
    payload = {"chat_id": chat_id, "reply_message": msg, "staff_name": st.session_state["username"]}
    r = requests.post(f"{API_BASE_URL}/admin/reply-chat", json=payload, headers=headers)
    return r.status_code == 200

def fetch_all_logs():
    headers = {"x-admin-token": ADMIN_TOKEN}
    try:
        r = requests.get(f"{API_BASE_URL}/admin/logs/all", headers=headers, timeout=10)
        if r.status_code == 200:
            return r.json()
        return None
    except Exception:
        return None

def fetch_chat_history(chat_id):
    headers = {"x-admin-token": ADMIN_TOKEN}
    try:
        r = requests.get(f"{API_BASE_URL}/admin/chat-history/{chat_id}", headers=headers, timeout=5)
        if r.status_code == 200:
            return r.json()
        return []
    except Exception:
        return []

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

def add_user(username, password, role):
    headers = {"x-admin-token": ADMIN_TOKEN}
    payload = {"username": username, "password": password, "role": role}
    try:
        r = requests.post(f"{API_BASE_URL}/admin/users", json=payload, headers=headers, timeout=5)
        if r.status_code == 200:
            return True, "User berhasil ditambahkan!"
        else:
            detail = r.json().get("detail", "Gagal menambah user.")
            return False, detail
    except Exception as e:
        return False, str(e)

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
    tabs = ["📋 Log Eskalasi"]
    if st.session_state["role"] == "admin":
        tabs = ["📈 Analitik Intent"] + tabs + ["⚙️ Manajemen Sistem"]
    
    tab_objs = st.tabs(tabs)
    
    # Mapping tab berdasarkan role agar tidak salah index
    tab_map = {name: obj for name, obj in zip(tabs, tab_objs)}
    
    if "📈 Analitik Intent" in tab_map:
        with tab_map["📈 Analitik Intent"]:
            st.subheader("Analisis Performa Intent")
            if data["intent_status_distribution"]:
                # Menyiapkan data untuk Stacked Bar Chart
                rows = []
                for intent, statuses in data["intent_status_distribution"].items():
                    for status, count in statuses.items():
                        rows.append({"Intent": intent, "Status": status, "Jumlah": count})
                
                df_granular = pd.DataFrame(rows)
                
                # Stacked Bar Chart
                fig_stacked = px.bar(
                    df_granular, x="Intent", y="Jumlah", color="Status",
                    title="Status Penanganan per Intent",
                    color_discrete_map={"AUTO_RESPONSE": "#3498db", "TO_CS": "#f39c12", "TO_NOC": "#e74c3c", "OK": "#2ecc71"},
                    labels={"Jumlah": "Jumlah Pesan"}
                )
                st.plotly_chart(fig_stacked, use_container_width=True)

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

    with tab_map["📋 Log Eskalasi"]:
        st.subheader("💬 Antrean Chat & Eskalasi")
        role = st.session_state["role"]
        
        if data["recent_escalations"]:
            # Filter data berdasarkan role: NOC hanya lihat TO_NOC, CS hanya lihat TO_CS, Admin semua.
            filtered_esc = data["recent_escalations"]
            if role == "noc":
                filtered_esc = [e for e in filtered_esc if e["status"] == "TO_NOC"]
            elif role == "cs":
                filtered_esc = [e for e in filtered_esc if e["status"] == "TO_CS"]

            for i, esc in enumerate(filtered_esc):
                with st.expander(f" User {esc['chat_id']} - {esc['timestamp']} ({esc['status']})"):
                    st.write(f"**Pesan Terakhir:** {esc['message']}")
                    
                    if esc['chat_id'] is not None:
                        st.divider()
                        st.write("📜 **Riwayat Percakapan:**")
                        history = fetch_chat_history(esc['chat_id'])
                        
                        # Container dengan scrollbar manual (CSS hack Streamlit)
                        chat_container = st.container(height=300)
                        with chat_container:
                            for h in history:
                                st.markdown(f"🕒 *{h['timestamp']}*")
                                st.markdown(f"**User:** {h['message']}")
                                st.markdown(f"**Bot:** {h['reply']}")
                                st.markdown("---")
                        
                        st.write("💬 **Balas Pesan:**")
                        reply_text = st.text_area("Balasan Staff", key=f"reply_{i}")
                        if st.button("Kirim Balasan", key=f"btn_{i}"):
                            if reply_text:
                                if send_reply(esc['chat_id'], reply_text):
                                    st.success("Berhasil mengirim balasan!")
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error("Gagal mengirim balasan.")
                            else:
                                st.warning("Pesan balasan tidak boleh kosong.")
                    else:
                        st.warning("Chat ID tidak tersedia untuk membalas secara manual.")

        else:
            st.info("Belum ada chat yang dialihkan ke CS atau NOC.")

    if "⚙️ Manajemen Sistem" in tab_map:
        with tab_map["⚙️ Manajemen Sistem"]:
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
            
            st.divider()
            st.subheader("👤 Tambah Staff Baru (CS/NOC)")
            with st.form("add_user_form", clear_on_submit=True):
                new_user = st.text_input("Username Baru", placeholder="Contoh: staff_budi")
                new_pw = st.text_input("Password Baru", type="password")
                new_role = st.selectbox("Role", ["cs", "noc"], format_func=lambda x: x.upper())
                
                if st.form_submit_button("Tambah User"):
                    if new_user and new_pw:
                        success, msg = add_user(new_user, new_pw, new_role)
                        if success:
                            st.success(msg)
                        else:
                            st.error(f"Gagal: {msg}")
                    else:
                        st.warning("Username dan password tidak boleh kosong.")
            
            st.divider()
            st.subheader("📥 Data Training")
            all_logs_data = fetch_all_logs()
            if all_logs_data:
                # Convert list of dicts to CSV using Pandas
                df_logs = pd.DataFrame(all_logs_data)
                csv_buffer = df_logs.to_csv(index=False).encode('utf-8')
                
                st.download_button(
                    label="Download Chat Logs Terbaru (MySQL)",
                    data=csv_buffer,
                    file_name=f"chat_logs_training_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
            else:
                st.info("Belum ada data log yang tersedia di database.")

    # Script untuk auto-refresh sederhana
    if auto_refresh:
        if HAS_AUTOREFRESH:
            # Refresh setiap 30 detik tanpa efek flicker/gelap-terang
            st_autorefresh(interval=30000, key="datarefresh")
        else:
            st.sidebar.warning("⚠️ Library 'streamlit-autorefresh' tidak ditemukan. Jalankan: `pip install streamlit-autorefresh` untuk menghilangkan flicker.")
            time.sleep(10)
            st.rerun()
else:
    error_msg = st.session_state.get("api_error", "Koneksi ke API gagal.")
    st.error(f"❌ {error_msg}")
    
    st.info("💡 Pastikan Anda menjalankan: `uvicorn src.api_fastapi:app --reload` di terminal.")
    
    if st.button("Coba Hubungkan Lagi"):
        st.rerun()

st.caption(f"ISP Chatbot Monitoring System v1.1 | API: {API_BASE_URL}")