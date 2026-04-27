import os
import requests
import logging
import time
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

class SmartOLT:
    # Class-level cache to persist across instances if necessary
    _cached_onus = None
    _last_fetch_time = 0
    CACHE_TTL = 1200  # 20 minutes (3 calls per hour limit)

    def _interpret_signal(self, power_val: str) -> str:
        """Mengonversi nilai string power ke label yang mudah dipahami."""
        try:
            # Ekstrak angka saja (misal "-19.50" dari "-19.50 dBm")
            val = float(''.join(c for c in power_val if c in "0123456789.-"))
            if -23.0 <= val <= -8.0:
                return f"🟢 {val} dBm (Sangat Bagus)"
            elif -26.0 <= val < -23.0:
                return f"🟡 {val} dBm (Normal/Cukup)"
            else:
                return f"🔴 {val} dBm (Buruk/Redaman Tinggi)"
        except (ValueError, TypeError):
            return f"⚪ {power_val}"

    def __init__(self, api_url: Optional[str] = None, api_token: Optional[str] = None):
        # Jika tidak dipasing, ambil langsung dari env agar fastapi.py lebih bersih
        self.api_url = (api_url or os.getenv("SMARTOLT_API_URL", "")).rstrip('/')
        self.api_token = api_token or os.getenv("SMARTOLT_API_TOKEN")
        self.session = requests.Session()
        if self.api_token:
            logger.info(f"SmartOLT Client diinisialisasi dengan token: {self.api_token[:4]}***")

    def get_customer_device_status(self, customer_id: str) -> str:
        """
        Mengambil status perangkat dari SmartOLT dan mengembalikan pesan string.
        """
        if not self.api_url or not self.api_token:
            logger.warning("SmartOLT API URL atau Token belum dikonfigurasi.")
            return ""

        current_time = time.time()
        
        # Check if cache is still valid
        if SmartOLT._cached_onus and (current_time - SmartOLT._last_fetch_time < SmartOLT.CACHE_TTL):
            logger.info("Menggunakan data SmartOLT dari cache.")
            onus = SmartOLT._cached_onus
        else:
            onus = self._fetch_all_onus()
            if onus:
                SmartOLT._cached_onus = onus
                SmartOLT._last_fetch_time = current_time
            elif SmartOLT._cached_onus:
                # If fetch fails but we have old data, use it as fallback
                logger.warning("Fetch gagal, menggunakan cache lama.")
                onus = SmartOLT._cached_onus
            else:
                return "Gagal mengambil status perangkat dari sistem SmartOLT."

        search_term = str(customer_id).strip().lower()
        onu = None

        for item in onus:
            sn = str(item.get("sn", "")).strip().lower()
            mac = str(item.get("mac_address", "")).strip().lower()
            desc = str(item.get("description", "")).strip().lower()
            name = str(item.get("name", "")).strip().lower()
            pppoe_user = str(item.get("username", "")).strip().lower()
            external_id = str(item.get("external_id", "")).strip().lower()
            onu_ext_id = str(item.get("onu_external_id", "")).strip().lower()
            
            # Mencocokkan ID Pelanggan (External ID), SN, MAC, atau Username PPPoE
            if search_term in [sn, mac, name, desc, pppoe_user, external_id, onu_ext_id] or search_term in desc or search_term in external_id:
                onu = item
                break
        
        if not onu:
            logger.info(f"User {customer_id} tidak ditemukan di SmartOLT.")
            return f"Maaf kak, Username/ID {customer_id} tidak ditemukan di sistem kami."

        ext_id = onu.get("onu_external_id") or onu.get("external_id")
        
        # Ambil informasi lengkap secara real-time (Status, Sinyal, dan Riwayat)
        full_info = None
        if ext_id:
            full_info = self._get_onu_full_info(ext_id)

        if full_info:
            onu_status = str(full_info.get("status", onu.get("status"))).lower()
            optical_power = full_info.get("rx_power") or full_info.get("signal")
            # SmartOLT Full Info menggunakan key yang bervariasi tergantung tipe ONU
            last_online = full_info.get("last_down_time") or full_info.get("last_online") or \
                          full_info.get("last_dereg_time") or full_info.get("last_up_time") or \
                          onu.get("last_online_at") or onu.get("last_online")
        else:
            onu_status = onu.get("status", "tidak diketahui").lower()
            optical_power = onu.get("signal")
            last_online = onu.get("last_online_at") or onu.get("last_online")

        onu_name = onu.get("name", "Tanpa Nama")
        onu_sn = onu.get("sn", "N/A")
        # Mengambil alamat dari data cache atau data full info jika tersedia
        onu_address = onu.get("address") or (full_info.get("address") if full_info else None)

        logger.info(f"SmartOLT: Berhasil menemukan data for {customer_id}. Status: {onu_status}")

        res = f"📌 **Detail Perangkat:**\n"
        res += f"👤 Nama: {onu_name}\n"
        res += f"🆔 SN: `{onu_sn}`\n"
        if onu_address:
            res += f"📍 Alamat: {onu_address}\n"
        res += "\n"

        if onu_status == "online":
            res += "✅ **Status: ONLINE**\n"
            if optical_power:
                res += f"📶 Sinyal: {self._interpret_signal(str(optical_power))}\n\n"
            res += "💡 *Koneksi kakak saat ini terpantau normal dari sisi server.*"
        elif onu_status == "power fail":
            res += "⚡ **Status: POWER FAIL**\n"
            if last_online:
                res += f"🕒 Terakhir Aktif: {last_online}\n"
            res += "❌ *Modem kakak terdeteksi mati listrik.* Mohon pastikan adaptor terpasang dengan benar dan listrik di lokasi menyala ya kak. Jika masih terkendala silahkan kirimkan sharelokasi untuk kunjungan teknisi ya kak"
        elif onu_status == "los":
            res += "🔴 **Status: LOS (Kabel Putus)**\n"
            if last_online:
                res += f"🕒 Terakhir Aktif: {last_online}\n"
            res += "❌ *Terdeteksi gangguan fisik pada kabel fiber.* Mohon cek apakah ada tekukan tajam atau kabel yang terlepas dari modem kak. Jika masih terkendala silahkan kirimkan sharelokasi untuk kunjungan teknisi ya kak"
        elif onu_status == "offline":
            res += "⚠️ **Status: OFFLINE**\n"
            if last_online:
                res += f"🕒 Terakhir Aktif: {last_online}\n"
            res += "❌ *Modem kakak tidak terdeteksi oleh sistem.* Mohon pastikan adaptor menyala dan kabel fiber tidak tertekuk ya kak. Jika masih terkendala silahkan kirimkan sharelokasi untuk kunjungan teknisi ya kak"
        else:
            res += f"❓ **Status: {onu_status.upper()}**\n"
            res += "Mohon hubungi CS untuk pengecekan manual."

        return res

    def _get_onu_full_info(self, onu_external_id: str) -> Optional[dict]:
        """Mengambil informasi lengkap ONU secara real-time (Status, Sinyal, Riwayat)."""
        try:
            headers = {
                "X-Token": self.api_token,
                "Content-Type": "application/json"
            }
            response = requests.get(
                f"{self.api_url}/api/onu/get_onu_full_status_info/{onu_external_id}",
                headers=headers,
                timeout=20
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("status") is True or data.get("status") == "success":
                    return data.get("response")
            return None
        except Exception as e:
            logger.error(f"Error saat mengambil full info ({onu_external_id}): {e}")
            return None

    def _fetch_all_onus(self) -> list:
        """Helper to call the API and handle rate limits/errors."""
        try:
            logger.info("Memanggil API SmartOLT (Get All ONUs Details) ke server...")
            headers = {
                "X-Token": self.api_token,
                "Content-Type": "application/json"
            }
            
            response = requests.get(
                f"{self.api_url}/api/onu/get_all_onus_details",
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 429:
                logger.error("SmartOLT API Rate Limit tercapai (3 calls/hour)!")
                return []
                
            response.raise_for_status()
            data = response.json()

            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                return data.get("response") or data.get("onus") or []
            return []
        except Exception as e:
            logger.error(f"Error saat mengambil data dari SmartOLT: {e}")
            return []