INTENT_RULES = [
    {
        "name": "greeting",
        "strict": True,
        "mappings": [
            {"pattern": "hai", "response": "Hai! Silakan bertanya ya kak!, saya siap bantu."},
            {"pattern": "halo", "response": "Halo kak! Ada yang bisa saya bantu?"},
            {"pattern": "hello", "response": "Halo kak! Ada yang bisa saya bantu?"},
            {"pattern": "assalamualaikum", "response": "Waalaikumsalam kak, ada yang bisa dibantu?"},
            {"pattern": "assalamu'alaikum", "response": "Waalaikumsalam kak, ada yang bisa dibantu?"},
            {"pattern": "ass wr wb", "response": "Waalaikumsalam kak, ada yang bisa dibantu?"},
            {"pattern": "selamat pagi", "response": "Selamat pagi! Ada yang bisa saya bantu?"},
            {"pattern": "pagi", "response": "Selamat pagi! Ada yang bisa saya bantu?"},
            {"pattern": "selamat siang", "response": "Selamat siang! Ada yang bisa saya bantu?"},
            {"pattern": "siang", "response": "Selamat siang! Ada yang bisa saya bantu?"},
            {"pattern": "selamat sore", "response": "Selamat sore! Ada yang bisa saya bantu?"},
            {"pattern": "sore", "response": "Selamat sore! Ada yang bisa saya bantu?"},
            {"pattern": "selamat malam", "response": "Selamat malam! Ada yang bisa saya bantu?"},
            {"pattern": "malam", "response": "Selamat malam! Ada yang bisa saya bantu?"},
        ]
    },
    {
        "name": "gangguan_umum",
        "mappings": [
            {"pattern": "internet mati", "response": "Mohon maaf atas ketidaknyamanannya kak, boleh kirim foto lampu modem/ONT sekarang? Nanti kami bantu cek dari sistem."},
            {"pattern": "internet mati total", "response": "Mohon maaf atas ketidaknyamanannya kak, boleh kirim foto lampu modem/ONT sekarang? Nanti kami bantu cek dari sistem."},
            {"pattern": "koneksi mati", "response": "Mohon maaf atas ketidaknyamanannya kak, boleh kirim foto lampu modem/ONT sekarang? Nanti kami bantu cek dari sistem."},
            {"pattern": "wifi mati", "response": "Mohon maaf atas ketidaknyamanannya kak, boleh kirim foto lampu modem/ONT sekarang? Nanti kami bantu cek dari sistem."},
            {"pattern": "internet pedot", "response": "Ngapunten sanget kak, internetnya terputus ya? Boleh kirim foto lampu modemnya? Nanti kami bantu cek dari sistem."},
            {"pattern": "ra iso konek", "response": "Mohon maaf kak, tidak bisa konek ya? Coba matikan modem 5 menit lalu nyalakan lagi. Kalau tetap ra iso, info ID Pelanggan ya."},
            {"pattern": "wifi trouble", "response": "Mohon maaf atas ketidaknyamanannya kak, boleh kirim foto lampu modem/ONT sekarang? Nanti kami bantu cek dari sistem."},
            {"pattern": "internet bermasalah", "response": "Mohon maaf kak, koneksinya bermasalah ya? Boleh diinfokan lampu modemnya warna apa?"},
            {"pattern": "ada kendala wifi", "response": "Mohon maaf atas ketidaknyamanannya kak, boleh kirim foto lampu modem/ONT sekarang? Nanti kami bantu cek dari sistem."},
            {"pattern": "wifi ga nyala", "response": "Mohon maaf atas ketidaknyamanannya kak, boleh kirim foto lampu modem/ONT sekarang? Nanti kami bantu cek dari sistem."},
            {"pattern": "wifi tidak menyediakan internet", "response": "Baik kak, jika WiFi terhubung tapi tidak ada internet, coba matikan modem selama 5 menit lalu nyalakan lagi. Jika masih sama, mohon kirim foto lampu indikator di modem ya."},
            {"pattern": "ga bisa internetan", "response": "Mohon maaf atas ketidaknyamanannya kak, boleh kirim foto lampu modem/ONT sekarang? Nanti kami bantu cek dari sistem."},
            {"pattern": "gabisa internetan", "response": "Mohon maaf atas ketidaknyamanannya kak, boleh kirim foto lampu modem/ONT sekarang? Nanti kami bantu cek dari sistem."},
            {"pattern": "mboten saget internetan", "response": "Ngapunten kak, mboten saget internetan nggih? Coba modem dipateni dilit (5 menit) terus urapke meneh. Kirim foto modem nggih."},
            {"pattern": "koneksi sering putus", "response": "Maaf ya kak, untuk cek gangguannya boleh info ID Pelanggan + kondisi lampu modem (Power, LOS, Internet)?"},
            {"pattern": "putus putus", "response": "Maaf ya kak, untuk cek gangguannya boleh info ID Pelanggan + kondisi lampu modem (Power, LOS, Internet)?"},
            {"pattern": "sering disconnect", "response": "Maaf ya kak, untuk cek gangguannya boleh info ID Pelanggan + kondisi lampu modem (Power, LOS, Internet)?"},
            {"pattern": "modem internet merah", "response": "Baik kak, jika lampu Internet di modem merah, coba matikan modem selama 5 menit lalu nyalakan lagi. Jika masih merah, mohon infokan ID Pelanggan ya."},
            {"pattern": "lampu internet mati", "response": "Baik kak, jika lampu Internet di modem mati, coba matikan modem selama 5 menit lalu nyalakan lagi. Jika masih mati, mohon infokan ID Pelanggan ya."},
            {"pattern": "modeme mati", "response": "Ngapunten kak, modemenya mati total atau lampunya saja? Coba cek adaptornya sudah tercolok kencang belum kak?"},
            {"pattern": "wifi nyala tapi ga ada internet", "response": "Baik kak, jika WiFi terhubung tapi tidak ada internet, coba matikan modem selama 5 menit lalu nyalakan lagi. Jika masih sama, mohon kirim foto lampu indikator di modem ya."},
            {"pattern": "ada ganggu", "response": "Mohon maaf atas ketidaknyamanannya kak. Bisa infokan ID Pelanggan atau nama yang terdaftar dulu? Atas nama siapa ya kak? Nanti kami cek dari sistem."},
            {"pattern": "ganggu", "response": "Mohon maaf atas ketidaknyamanannya kak. Bisa infokan ID Pelanggan atau nama yang terdaftar dulu? Atas nama siapa ya kak? Nanti kami cek dari sistem."},
            {"pattern": "ada gangguan", "response": "Mohon maaf atas ketidaknyamanannya kak. Bisa infokan ID Pelanggan atau nama yang terdaftar dulu? Atas nama siapa ya kak? Nanti kami cek dari sistem."},
            {"pattern": "gangguan", "response": "Mohon maaf atas ketidaknyamanannya kak. Bisa infokan ID Pelanggan atau nama yang terdaftar dulu? Atas nama siapa ya kak? Nanti kami cek dari sistem."},
        ]
    },
    {
        "name": "gangguan_lemot_umum",
        "mappings": [
            {"pattern": "lemot banget", "response": "Maaf kak, bisa dijelaskan lebih detail kendala yang dialami? 🙏\n- Untuk akses apa ya kak? (misal YouTube, TikTok, game, Zoom, dsb)\n- Sejak jam berapa terasa lemot?\n\nKalau boleh, silakan kirim screenshot atau foto kendalanya ya kak 😊"},
            {"pattern": "lemot", "response": "Maaf kak, bisa dijelaskan lebih detail kendala yang dialami? 🙏\n- Untuk akses apa ya kak? (misal YouTube, TikTok, game, Zoom, dsb)\n- Sejak jam berapa terasa lemot?\n\nKalau boleh, silakan kirim screenshot atau foto kendalanya ya kak 😊"},
            {"pattern": "lemot pol", "response": "Ngapunten sanget kak, lemot banget nggih? Kangge buka nopo mawon kak? Coba kirim screenshot speedtest-nya nggih."},
            {"pattern": "ngadat", "response": "Mohon maaf kak, koneksinya ngadat ya? Sejak jam berapa kak? Coba kami bantu cek rutenya."},
            {"pattern": "internet lemot", "response": "Maaf kak, bisa dijelaskan lebih detail kendala yang dialami? 🙏\n- Untuk akses apa ya kak? (misal YouTube, TikTok, game, Zoom, dsb)\n- Sejak jam berapa terasa lemot?\n\nKalau boleh, silakan kirim screenshot atau foto kendalanya ya kak 😊"},
            {"pattern": "loading terus", "response": "Maaf kak, bisa dijelaskan lebih detail kendala yang dialami? 🙏\n- Untuk akses apa ya kak? (misal YouTube, TikTok, game, Zoom, dsb)\n- Sejak jam berapa terasa lemot?\n\nKalau boleh, silakan kirim screenshot atau foto kendalanya ya kak 😊"},
        ]
    },
    {
        "name": "kabel_putus",
        "mappings": [
            {"pattern": "kabel putus", "response": "Waduh, kabel putus ya kak. Mohon kirim lokasi lengkap + foto kondisi kabel supaya teknisi bisa langsung cek lapangan."},
            {"pattern": "kabel optik putus", "response": "Waduh, kabel putus ya kak. Mohon kirim lokasi lengkap + foto kondisi kabel supaya teknisi bisa langsung cek lapangan."},
            {"pattern": "kabel ngglawer", "response": "Matur nuwun infonya kak, kabelnya menjuntai/ngglawer ya? Mohon sharelokasi dan foto kondisinya agar segera diperbaiki tim lapangan."},
            {"pattern": "kabel pedot", "response": "Waduh kabelnya pedot nggih kak? Nyuwun tulung kirim foto kabel sing pedot kalih alamat lengkap nggih, teknisi meluncur."},
            {"pattern": "tiang roboh", "response": "Terima kasih infonya kak. Untuk kendala tiang roboh, kami butuh lokasi detail agar teknisi bisa dijadwalkan."},
            {"pattern": "tiang tumbang", "response": "Terima kasih infonya kak. Untuk kendala tiang tumbang, kami butuh lokasi detail agar teknisi bisa dijadwalkan."},
            {"pattern": "los merah", "response": "Baik kak, jika lampu LOS merah itu indikasi ada masalah di kabel optik. Mohon kirim ID Pelanggan dan alamat lengkap agar bisa dijadwalkan pengecekan oleh teknisi."},
            {"pattern": "lampu merah", "response": "Baik kak, jika lampu LOS merah itu indikasi ada masalah di kabel optik. Mohon kirim ID Pelanggan dan alamat lengkap agar bisa dijadwalkan pengecekan oleh teknisi."},
        ]
    },
    {
        "name": "gangguan_aplikasi",
        "mappings": [
            {"pattern": "tiktok ga bisa", "response": "Baik kak, apakah kendalanya hanya terjadi di TikTok? 🙏\nMohon kirim screenshot errornya + jam kejadian ya kak, nanti kami cek apakah ini kendala rute atau CDN aplikasi."},
            {"pattern": "youtube lemot", "response": "Baik kak, apakah kendalanya hanya terjadi di YouTube? 🙏\nMohon kirim screenshot errornya + jam kejadian ya kak, nanti kami cek apakah ini kendala rute atau CDN aplikasi."},
            {"pattern": "netflix buffering", "response": "Baik kak, apakah kendalanya hanya terjadi di Netflix? 🙏\nMohon kirim screenshot errornya + jam kejadian ya kak, nanti kami cek apakah ini kendala rute atau CDN aplikasi."},
            {"pattern": "ml ping tinggi", "response": "Baik kak, apakah kendalanya hanya terjadi di game Mobile Legends? 🙏\nMohon kirim screenshot ping-nya + jam kejadian ya kak, nanti kami cek apakah ini kendala rute game."},
        ]
    },
    {
        "name": "gangguan_rute",
        "mappings": [
            {"pattern": "speedtest normal tapi lemot", "response": "Ini indikasinya kendala di jalur akses atau CDN aplikasi tertentu ya kak 🙏\nMohon kirim screenshot speedtest + screenshot error aplikasi, nanti kami cek rute server tujuan."},
            {"pattern": "cuma tiktok yang error", "response": "Ini indikasinya kendala di jalur akses atau CDN aplikasi tertentu ya kak 🙏\nMohon kirim screenshot speedtest + screenshot error aplikasi, nanti kami cek rute server tujuan."},
        ]
    },
    {
        "name": "cek_tagihan",
        "mappings": [
            {
                "pattern": "cek tagihan",
                "response": "Untuk cek tagihan, silakan kirim ID Pelanggan (misal: OLT4-250012) atau nama yang terdaftar ya kak. Atas nama siapa ya kak?"
            },
            {
                "pattern": "pira tagihane",
                "response": "Nyuwun tulung infokan ID Pelanggan utawi asmane sing terdaftar nggih kak, kersane kulo cek tagihane."
            },
            {
                "pattern": "tagihan saya berapa",
                "response": "Untuk cek tagihan, silakan kirim ID Pelanggan (misal: OLT4-250012) atau nama yang terdaftar ya kak. Atas nama siapa ya kak?"
            },
            {
                "pattern": "cek invoice",
                "response": "Untuk cek tagihan, silakan kirim ID Pelanggan (misal: OLT4-250012) atau nama yang terdaftar ya kak. Atas nama siapa ya kak?"
            },
        ]
    },
    {
        "name": "pembayaran",
        "mappings": [
            {"pattern": "cara bayar", "response": "Pembayaran dapat dilakukan melalui rekening dan metode yang tertera di informasi resmi kami ya kak."},
            {"pattern": "metode pembayaran", "response": "Untuk instruksi lengkap silakan cek menu pembayaran di aplikasi/website atau hubungi CS."},
        ]
    },
    {
        "name": "cek_coverage",
        "mappings": [
            {"pattern": "bisa pasang di sini", "response": "Untuk cek ketersediaan jaringan mohon kirim nama daerah lengkap atau share lokasi (pin point) ya kak 😊"},
            {"pattern": "tercover", "response": "Untuk cek ketersediaan jaringan mohon kirim nama daerah lengkap atau share lokasi (pin point) ya kak 😊"},
            {"pattern": "cek alamat saya", "response": "Untuk cek ketersediaan jaringan mohon kirim nama daerah lengkap atau share lokasi (pin point) ya kak 😊"},
            {"pattern": "daerah", "response": "Untuk cek ketersediaan jaringan mohon kirim nama daerah lengkap atau share lokasi (pin point) ya kak 😊"},
            {"pattern": "jaringannya sudah ada", "response": "Untuk cek ketersediaan jaringan mohon kirim nama daerah lengkap atau share lokasi (pin point) ya kak 😊"},
            {"pattern": "sudah ada jaringannya", "response": "Untuk cek ketersediaan jaringan mohon kirim nama daerah lengkap atau share lokasi (pin point) ya kak 😊"},
            {"pattern": "lokasi", "response": "Untuk cek ketersediaan jaringan mohon kirim nama daerah lengkap atau share lokasi (pin point) ya kak 😊"},
        ]
    },
    {
        "name": "berhenti_langganan",
        "mappings": [
            {"pattern": "berhenti langganan", "response": "Untuk proses berhenti langganan, mohon kirim ID Pelanggan atau nama yang terdaftar ya kak."},
            {"pattern": "cabut wifi", "response": "Untuk proses berhenti langganan, mohon kirim ID Pelanggan atau nama yang terdaftar ya kak."},
        ]
    },
    {
        "name": "ganti_password_wifi",
        "mappings": [
            {"pattern": "ganti password wifi", "response": "Untuk ganti password WiFi, kakak bisa ikuti panduan di https://pendik.id/panduan ya 😊\nAtau kirim ID Pelanggan jika ingin dibantu dari sistem."},
            {"pattern": "lupa password wifi", "response": "Untuk ganti password WiFi, kakak bisa ikuti panduan di https://pendik.id/panduan ya 😊\nAtau kirim ID Pelanggan jika ingin dibantu dari sistem."},
        ]
    },
    {
        "name": "jam_operasional",
        "mappings": [
            {"pattern": "jam operasional", "response": "Customer Service aktif pukul 08.00–21.00 WIB setiap hari ya kak 😊"},
            {"pattern": "cs sampai jam berapa", "response": "Customer Service aktif pukul 08.00–21.00 WIB setiap hari ya kak 😊"},
        ]
    },
    {
        "name": "info_paket",
        "mappings": [
            {"pattern": "info paket", "response": "Berikut gambaran paket internet kami kak (detail & harga terbaru ada di https://pendik.id/pricing).\nKakak tertarik paket berapa Mbps?"},
            {"pattern": "infoin paket", "response": "Berikut gambaran paket internet kami kak (detail & harga terbaru ada di https://pendik.id/pricing).\nKakak tertarik paket berapa Mbps?"},
            {"pattern": "infokan paket", "response": "Berikut gambaran paket internet kami kak (detail & harga terbaru ada di https://pendik.id/pricing).\nKakak tertarik paket berapa Mbps?"},
            {"pattern": "minta info paket", "response": "Berikut gambaran paket internet kami kak (detail & harga terbaru ada di https://pendik.id/pricing).\nKakak tertarik paket berapa Mbps?"},
            {"pattern": "harga paket", "response": "Berikut gambaran paket internet kami kak (detail & harga terbaru ada di https://pendik.id/pricing).\nKakak tertarik paket berapa Mbps?"},
            {"pattern": "pasang baru", "response": "Berikut gambaran paket internet kami kak (detail & harga terbaru ada di https://pendik.id/pricing).\nKakak tertarik paket berapa Mbps?"},
            {"pattern": "pasang wifi", "response": "Wah, pilihan bagus kak! Untuk pasang baru, kakak bisa cek paketnya di https://pendik.id/pricing. Tertarik paket yang mana?"},
            {"pattern": "langganan internet", "response": "Halo kak! Untuk mulai berlangganan, silakan pilih paketnya di https://pendik.id/pricing ya. Mau dibantu cek coverage lokasinya juga?"},
            {"pattern": "mau langganan", "response": "Halo kak! Untuk mulai berlangganan, silakan pilih paketnya di https://pendik.id/pricing ya. Mau dibantu cek coverage lokasinya juga?"},
            {"pattern": "upgrade paket", "response": "Tentu kak, untuk upgrade paket silakan infokan ID Pelanggan dan paket tujuan yang diinginkan ya."},
        ]
    },
    {
        "name": "opsi_layanan",
        "mappings": [
            {"pattern": "bisa bantu apa saja", "response": "Aku bisa bantu cek paket, cek gangguan, info pembayaran, dan panduan modem ya kak 😊"},
            {"pattern": "kamu bisa apa", "response": "Aku bisa bantu cek paket, cek gangguan, info pembayaran, dan panduan modem ya kak 😊"},
        ]
    },
    {
        "name": "cek_status_tiket",
        "mappings": [
            {"pattern": "cek status tiket", "response": "Silakan kirim ID Tiket (contoh: CS-1234 atau NOC-5678), nanti saya cek statusnya ya kak."},
        ]
    },
    {
        "name": "id_pelanggan",
        "mappings": [
            {"pattern": "OLT", "response": "Baik kak, ID Pelanggan sudah diterima. Mohon tunggu sebentar ya, saya cek dulu datanya 🙏"},
            {"pattern": "CS-", "response": "Baik kak, ID Pelanggan sudah diterima. Mohon tunggu sebentar ya, saya cek dulu datanya 🙏"},
            {"pattern": "GLN-", "response": "Baik kak, ID Pelanggan sudah diterima. Mohon tunggu sebentar ya, saya cek dulu datanya 🙏"},
            {"pattern": "ID pelanggan", "response": "Baik kak, ID Pelanggan sudah diterima. Mohon tunggu sebentar ya, saya cek dulu datanya 🙏"},
        ]
    },
    {
        "name": "goodbye",
        "mappings": [
            {"pattern": "terima kasih", "response": "Sama-sama kak! Senang bisa membantu 😊"},
            {"pattern": "terimakasih", "response": "Sama-sama kak! Senang bisa membantu 😊"},
            {"pattern": "trimakasih", "response": "Sama-sama kak! Senang bisa membantu 😊"},
            {"pattern": "makasih", "response": "Sama-sama kak! Kalau ada kendala lagi tinggal chat aja ya."},
            {"pattern": "makasi", "response": "Sama-sama kak! Kalau ada kendala lagi tinggal chat aja ya."},
            {"pattern": "sudah cukup", "response": "Baik kak. Terima kasih sudah menghubungi kami!"},
            {"pattern": "thank you", "response": "You're welcome! 😊"},
            {"pattern": "suwun", "response": "Sami-sami kak, matur nuwun kembali 😊 Kalau ada kendala lagi tinggal chat aja ya."},
            {"pattern": "matur suwun", "response": "Sami-sami kak, matur nuwun kembali 😊"},
            {"pattern": "oke", "response": "Baik kak. Kalau ada kendala lagi tinggal chat saya lagi ya 😊"},
            {"pattern": "ok", "response": "Baik kak. Kalau ada kendala lagi tinggal chat saya lagi ya 😊"},
            {"pattern": "okay", "response": "Baik kak. Kalau ada kendala lagi tinggal chat saya lagi ya 😊"},
        ]
    }
]


FALLBACK_RESPONSES = [
    "Maaf kak, saya belum paham maksud pertanyaan kakak. Bisa dijelaskan lagi dengan kata lain?",
    "Sepertinya pertanyaannya di luar daftar yang saya pahami kak. Coba gunakan kata kunci seperti info paket, gangguan layanan, pembayaran, atau kabel putus ya kak."
]
