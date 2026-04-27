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
    st_autorefresh = None
    HAS_AUTOREFRESH = False

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env", override=True)

API_BASE_URL = "http://127.0.0.1:8931"
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "").strip()

st.set_page_config(page_title="ISP Chatbot Monitoring", layout="wide")

st.title("📊 ISP Chatbot Monitoring Dashboard")
st.sidebar.header("Konfigurasi")

# --- Sistem Login Sederhana ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["username"] = ""
    st.session_state["role"] = ""
    st.session_state["menu_choice"] = "📈 Analitik Intent"
    st.session_state["eval_data"] = None

if not st.session_state["logged_in"]:
    with st.form("login_form"):
        st.subheader("🔑 Login Staff")
        user = st.text_input("Username")
        pw = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            if not user.strip() or not pw.strip():
                st.warning("⚠️ Username dan Password tidak boleh kosong!")
            else:
                try:
                    r = requests.post(
                        f"{API_BASE_URL}/admin/login", 
                        json={"username": user, "password": pw},
                        timeout=5
                    )
                    if r.status_code == 200:
                        res = r.json()
                        st.session_state["logged_in"] = True
                        st.session_state["role"] = res["role"]
                        st.session_state["username"] = res["username"]
                        st.rerun()
                    elif r.status_code == 401:
                        st.error("❌ Username atau Password salah. Silakan coba lagi.")
                    elif r.status_code == 500:
                        detail = r.json().get("detail", "Terjadi kesalahan internal pada database server.")
                        st.error(f"❌ {detail}")
                    else:
                        st.error(f"❌ Error {r.status_code}: Gagal menghubungi server login.")
                except requests.exceptions.ConnectionError:
                    st.error("🖥️ Server API tidak aktif atau tidak dapat dihubungi. Pastikan FastAPI sudah dijalankan.")
                except Exception as e:
                    st.error(f"⚠️ Terjadi kesalahan sistem: {e}")
    st.stop()

# Sidebar Info User
st.sidebar.success(f"Masuk sebagai: **{st.session_state['username']}** ({st.session_state['role'].upper()})")
if st.sidebar.button("Logout"):
    st.session_state["logged_in"] = False
    st.rerun()

def send_reply(chat_id, msg, reply_to_id=None):
    headers = {"x-admin-token": ADMIN_TOKEN}
    payload = {"chat_id": chat_id, "reply_message": msg, "staff_name": st.session_state["username"], "reply_to_msg_id": reply_to_id}
    r = requests.post(f"{API_BASE_URL}/admin/reply-chat", json=payload, headers=headers)
    return r.status_code == 200

def resolve_chat(chat_id):
    headers = {"x-admin-token": ADMIN_TOKEN}
    payload = {"chat_id": chat_id, "staff_name": st.session_state["username"]}
    r = requests.post(f"{API_BASE_URL}/admin/resolve-chat", json=payload, headers=headers)
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

def fetch_evaluation_matrix():
    headers = {"x-admin-token": ADMIN_TOKEN}
    try:
        r = requests.get(f"{API_BASE_URL}/admin/evaluation-matrix", headers=headers, timeout=10)
        if r.status_code == 200:
            return r.json()
        return None
    except Exception:
        return None

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
    menu_options = ["📈 Analitik Intent", "📋 Log Eskalasi"]
    if st.session_state["role"] == "admin":
        menu_options += ["⚙️ Manajemen Sistem"]
    
    # Gunakan Sidebar untuk Navigasi agar posisi tidak reset saat rerun
    choice = st.sidebar.radio("Navigasi Menu", menu_options, key="menu_choice")
    
    # --- Konten Berdasarkan Pilihan Menu ---

    if choice == "📈 Analitik Intent":
        st.container()
        with st.container():
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

    elif choice == "📋 Log Eskalasi":
        st.subheader("💬 Antrean Chat & Eskalasi")
        role = st.session_state["role"]
        
        if data["recent_escalations"]:
            # Implementasi Logic Eskalasi Berbasis Peran (Bab 4)
            filtered_esc = data["recent_escalations"]
            if role == "noc":
                filtered_esc = [e for e in filtered_esc if e.get("status") in ["TO_NOC", "STAFF_REPLY"]]
                st.caption("🔍 Menampilkan antrean teknis (NOC)")
            elif role == "cs":
                filtered_esc = [e for e in filtered_esc if e.get("status") in ["TO_CS", "STAFF_REPLY"]]
                st.caption("🔍 Menampilkan antrean layanan & admin (CS)")
            else:
                st.caption("🔍 Menampilkan seluruh antrean sistem (Admin)")

            for i, esc in enumerate(filtered_esc):
                conf_score = esc.get('confidence', 1.0)
                with st.expander(f" User {esc['chat_id']} - {esc['timestamp']} ({esc['status']}) - Skor: {conf_score}"):
                    st.write(f"**Pesan Terakhir:** {esc['message']}")
                    st.write(f"**Intent Terdeteksi:** `{esc.get('intent', 'n/a')}`")
                    
                    if esc['chat_id'] is not None:
                        st.divider()
                        st.write("📜 **Riwayat Percakapan:**")
                        history = fetch_chat_history(esc['chat_id'])
                        
                        # Container dengan scrollbar manual (CSS hack Streamlit)
                        chat_container = st.container(height=300)
                        with chat_container:
                            for h in history:
                                col_msg, col_btn = st.columns([0.8, 0.2])
                                with col_msg:
                                    st.markdown(f"🕒 *{h['timestamp']}*")
                                    st.markdown(f"**User:** {h['message']}")
                                    if h.get('reply'): st.markdown(f"**Bot:** {h['reply']}")
                                with col_btn:
                                    if st.button("↩️ Reply", key=f"rep_{h['id']}"):
                                        st.session_state[f"reply_target_{esc['chat_id']}"] = h.get('msg_id')
                                        st.session_state[f"reply_text_preview_{esc['chat_id']}"] = h['message']
                                st.markdown("---")
                        
                        # --- Form Balas Pesan ---
                        target_msg_id = st.session_state.get(f"reply_target_{esc['chat_id']}")
                        preview = st.session_state.get(f"reply_text_preview_{esc['chat_id']}", "Pesan Terakhir")
                        
                        if target_msg_id:
                            col_inf, col_can = st.columns([0.8, 0.2])
                            col_inf.info(f"↪️ **Membalas:** *{preview[:50]}...*")
                            if col_can.button("Batal", key=f"can_{esc['chat_id']}"):
                                del st.session_state[f"reply_target_{esc['chat_id']}"]
                                st.rerun()
                        else:
                            st.info("💡 Klik tombol ↩️ untuk membalas pesan spesifik.")
                        
                        # --- Form Balas Pesan ---
                        with st.form(key=f"reply_form_{esc['chat_id']}", clear_on_submit=True):
                            # Gunakan chat_id sebagai key agar input tidak hilang saat refresh
                            # Ubah key agar unik di dalam form
                            reply_text = st.text_area("Tulis balasan...", key=f"reply_input_{esc['chat_id']}_form")
                            
                            col_btn1, col_btn2 = st.columns(2)
                            submit_button = col_btn1.form_submit_button("📤 Kirim Balasan", use_container_width=True)
                            resolve_button = col_btn2.form_submit_button("✅ Selesaikan Chat", use_container_width=True)

                            if submit_button:
                                if reply_text:
                                    if send_reply(esc['chat_id'], reply_text, target_msg_id):
                                        st.success("Berhasil mengirim balasan!")
                                        # Hapus state terkait target balasan jika ada
                                        if f"reply_target_{esc['chat_id']}" in st.session_state:
                                            del st.session_state[f"reply_target_{esc['chat_id']}"]
                                        if f"reply_text_preview_{esc['chat_id']}" in st.session_state:
                                            del st.session_state[f"reply_text_preview_{esc['chat_id']}"]
                                        time.sleep(1)
                                        st.rerun()
                                    else:
                                        st.error("Gagal mengirim balasan.")
                                else:
                                    st.warning("Pesan balasan tidak boleh kosong.")
                            
                            if resolve_button:
                                if resolve_chat(esc['chat_id']):
                                    st.success("Sesi chat berhasil diselesaikan.")
                                    time.sleep(1)
                                    st.rerun()
                    else:
                        st.warning("Chat ID tidak tersedia untuk membalas secara manual.")
        else:
            st.info("Belum ada chat yang dialihkan ke CS atau NOC.")

    elif choice == "⚙️ Manajemen Sistem":
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
            st.subheader("🧪 Matriks Evaluasi (Confusion Matrix)")
            if st.button("Generate Confusion Matrix"):
                st.session_state["eval_data"] = fetch_evaluation_matrix()
            
            # Tampilkan matrix jika data ada di session state
            if st.session_state["eval_data"]:
                eval_data = st.session_state["eval_data"]
                df_cm = pd.DataFrame(
                    eval_data["matrix"], 
                    index=eval_data["labels"], 
                    columns=eval_data["labels"]
                )
                
                fig_cm = px.imshow(
                    df_cm,
                    text_auto=True,
                    aspect="auto",
                    labels=dict(x="Prediksi Sistem", y="Label Sebenarnya", color="Jumlah"),
                    x=eval_data["labels"],
                    y=eval_data["labels"],
                    color_continuous_scale='RdBu_r'
                )
                st.plotly_chart(fig_cm, use_container_width=True)
                
                # Menampilkan Ringkasan Metrik (Pindahkan ke dalam blok IF)
                summary = eval_data.get("summary", {})
                col_acc, col_total = st.columns(2)
                accuracy_pct = summary.get("overall_accuracy", 0) * 100
                col_acc.metric("Overall Accuracy", f"{accuracy_pct:.2f}%")
                col_total.metric("Total Sampel Evaluasi", f"{summary.get('total', 0)} Chat")

                st.write("### 📋 Detail Metrik per Intent")
                metrics_dict = summary.get("per_label_metrics", {})
                if metrics_dict:
                    # Mengonversi dictionary metrik ke DataFrame untuk tabel
                    df_metrics = pd.DataFrame.from_dict(metrics_dict, orient='index')
                    df_metrics.columns = ["Precision", "Recall", "F1-Score"]
                    st.dataframe(df_metrics.style.format("{:.4f}"), use_container_width=True)
                else:
                    st.warning("Detail metrik per label tidak tersedia.")
                
                st.info(f"**Algoritma:** {summary.get('algorithm')}")
            elif st.session_state["eval_data"] is False:
                st.warning("Data tidak mencukupi untuk membuat matrix. Pastikan bot sudah memiliki riwayat percakapan.")

            st.divider()
            st.subheader("📥 Data Training")
            all_logs_data = fetch_all_logs()
            if all_logs_data:
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
        if st_autorefresh is not None:
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
