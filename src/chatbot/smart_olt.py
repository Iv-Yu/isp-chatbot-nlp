import os
import requests
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

class SmartOLT:
    def __init__(self, api_url: Optional[str] = None, api_token: Optional[str] = None):
        # Jika tidak dipasing, ambil langsung dari env agar fastapi.py lebih bersih
        self.api_url = (api_url or os.getenv("SMARTOLT_API_URL", "")).rstrip('/')
        self.api_token = api_token or os.getenv("SMARTOLT_API_TOKEN")
        if self.api_token:
            logger.info(f"SmartOLT Client diinisialisasi dengan token: {self.api_token[:4]}***")

    def get_customer_device_status(self, customer_id: str) -> str:
        """
        Mengambil status perangkat dari SmartOLT dan mengembalikan pesan string.
        """
        if not self.api_url or not self.api_token:
            logger.warning("SmartOLT API URL atau Token belum dikonfigurasi.")
            return ""

        try:
            headers = {
                "X-Token": self.api_token,
                "Content-Type": "application/json"
            }
            
            # Mengubah endpoint ke get_all_onus_details dengan metode GET
            # untuk mengambil seluruh data detail ONU dari sistem.
            response = requests.get(
                f"{self.api_url}/api/onu/get_all_onus_details",
                headers=headers,
                timeout=100
            )
            response.raise_for_status()
            data = response.json()

            # Melakukan filter manual untuk mencocokkan Username PPPoE pada field 'sn'
            onus = data.get("response", [])
            onu = next((item for item in onus if str(item.get("sn")) == customer_id), None)
            
            if not onu:
                return f"Maaf kak, Username/SN {customer_id} tidak ditemukan di sistem kami."

            onu_status = onu.get("status", "tidak diketahui").lower()
            optical_power = onu.get("signal") # rx_power
            last_online = onu.get("last_online_at") or onu.get("last_online")

            reply_parts = []
            if onu_status == "online":
                msg = "Perangkat Anda terdeteksi ONLINE."
                if optical_power:
                    msg += f" Power optik: {optical_power} dBm."
                reply_parts.append(msg)
            elif onu_status == "offline":
                reply_parts.append("Perangkat Anda terdeteksi OFFLINE.")
            else:
                reply_parts.append("Status perangkat tidak dapat dipastikan.")

            if last_online:
                reply_parts.append(f"Terakhir online: {last_online}.")

            return " ".join(reply_parts)

        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling SmartOLT API for ID {customer_id}: {e}")
            return "Gagal mengambil status perangkat dari sistem SmartOLT."
        except Exception as e:
            logger.error(f"Unexpected error processing SmartOLT response: {e}")
            return "Terjadi kesalahan saat memproses data SmartOLT."