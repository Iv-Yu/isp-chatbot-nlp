INTENT_RULES = [
    {
        "name": "greeting",
        "strict": True,  # hanya cocok kalau kalimat pendek (logika di rule_engine)
        "patterns": [
            "hai",
            "halo",
            "hello",
            "assalamualaikum",
            "assalamu'alaikum",
            "ass wr wb",
            "selamat pagi",
            "selamat siang",
            "selamat sore",
            "selamat malam",
            "pagi",
            "siang",
            "sore",
            "malam"
        ],
        "responses": [
            "Hai! Silakan bertanya ya kak!, saya siap bantu.",
            "Halo kak! Ada yang bisa saya bantu?",
            "Waalaikumsalam kak, ada yang bisa dibantu?"
        ]
    },
    {
        "name": "gangguan_umum",
        "patterns": [
            "internet mati",
            "internet mati total",
            "koneksi mati",
            "wifi mati",
            "wifi ga nyala",
            "wifi nggak nyala",
            "wifi tidak nyala",
            "wifi tidak menyediakan internet",
            "kok wifinya tidak menyediakan internet",
            "ga bisa internetan",
            "nggak bisa internetan",
            "tidak bisa internetan",
            "tidak bisa dipakai internetan",
            "ga bisa dipakai apa apa",
            "ga bisa dibuat apa apa",
            "nggak bisa dibuat apa apa",
            "wifi ga bisa dibuat apa apa",
            "wifi tidak bisa digunakan",
            "wifi nggak bisa digunakan",
            "koneksi sering putus",
            "putus putus",
            "sinyal putus putus",
            "suka disconnect",
            "sering disconnect",
            "buat buka tiktok lemot",
            "tiktok lemot",
            "scroll sosmed cuma loading",
            "scroll sosmed cuman loading",
            "sosmed cuma muter muter",
            "sosmed muter muter terus",
            "youtube muter muter",
            "netflix muter muter",
            "netflix buffering terus",
            "gak bisa buka apa apa",
            "nggak bisa buka apa apa",
            "ga bisa browsing",
        ],
        "responses": [
            "Mohon maaf atas ketidaknyamanannya kak , boleh kirim foto lampu modem/ONT sekarang? Nanti kami bantu cek dari sistem.",
            "Maaf ya kak, untuk cek gangguannya boleh info ID Pelanggan + kondisi lampu modem (Power, LOS, Internet)?"
        ]
    },
    {
        "name": "gangguan_lemot_umum",
        "patterns": [
            "lemot banget",
            "lemot",
            "kok lemot banget ya",
            "kok lemot ya",
            "kenapa lemot ya",
            "lemot kak",
            "kak lemot",
            "internet lemot",
            "koneksi lemot",
            "wifi lemot",
            "wifinya lemot",
            "loading terus",
            "cuma loading aja",
            "kok wifinya lemot"
        ],
        "responses": [
            "Maaf kak, bisa dijelaskan lebih detail kendala yang dialami? 🙏\n"
            "- Untuk akses apa ya kak? (misal YouTube, TikTok, game, Zoom, dsb)\n"
            "- Sejak jam berapa terasa lemot?\n\n"
            "Kalau boleh, silakan kirim *screenshot* atau foto kendalanya ya kak, supaya kami bisa analisa lebih tepat. 😊"
        ]
    },
    {
        "name": "kabel_putus",
        "patterns": [
            "kabel putus",
            "kabel optik putus",
            "fo putus",
            "kabel fiber putus",
            "kabel internet putus",
            "kabel di tiang putus",
            "tiang roboh",
            "tiang tumbang",
            "kabel ketarik",
            "kabel ketimpa pohon",
            "lampu merah",
            "lampunya merah",
            "indikator merah",
            "los merah",
            "los menyala merah",
            "kabel jatuh ke jalan"
        ],
        "responses": [
            "Waduh, kabel putus ya kak \nMohon kirim lokasi lengkap dan foto kondisi kabel kalau memungkinkan, supaya tim teknisi kami bisa segera cek lapangan.",
            "Terima kasih infonya kak. Untuk kendala kabel putus, kami butuh lokasi detail agar teknisi bisa dijadwalkan ke lokasi."
        ]
    },
    {
        "name": "cek_tagihan",
        "patterns": [
            "cek tagihan",
            "cek billing",
            "tagihan saya berapa",
            "tagihan bulan ini berapa",
            "tunggakan saya berapa",
            "sisa tunggakan",
            "cek invoice",
            "lihat invoice",
            "tagihan internet",
            "tagihan wifi",
            "tagihan tiap bulan",
            "berapa tagihan saya"
        ],
        "responses": [
            "Untuk cek tagihan, silakan kirim ID Pelanggan atau nomor telepon yang terdaftar ya kak. Nanti kami infokan nominal dan status pembayarannya. "
        ]
    },
    {
        "name": "pembayaran",
        "patterns": [
            "cara bayar",
            "cara pembayaran",
            "pembayarannya gimana",
            "pembayarannya bagaimana",
            "gimana pembayarannya",
            "bagaimana cara pembayarannya",
            "bayar",
            "mau bayar",
            "kak mau bayar",
            "saya mau bayar",
            "bayarnya lewat apa",
            "bayar lewat apa",
            "bayarnya pakai apa",
            "bayar pakai apa",
            "bayarnya gimana",
            "cara bayarnya gimana",
            "pembayaran lewat apa",
            "bisa bayar dimana",
            "bayarnya kemana",
            "transfer kemana",
            "rekening berapa",
            "nomor rekening berapa",
            "no rekening berapa",
            "metode pembayaran",
            "bisa bayar pakai apa",
            "bisa bayar via apa",
            "pembayaran internet",
            "pembayaran wifi"
        ],
        "responses": [
            "Pembayaran dapat dilakukan melalui rekening dan metode yang tertera di informasi resmi kami ya kak. \nUntuk instruksi lengkap dan daftar channel pembayaran, kakak bisa cek di menu pembayaran di aplikasi/website atau hubungi CS.",
            "Untuk pembayaran, kami mendukung transfer bank dan beberapa metode lain. Detil lengkap bisa dilihat di informasi resmi kami atau ditanyakan ke CS bila diperlukan."
        ]
    },
    {
        "name": "cek_coverage",
        "patterns": [
            "bisa dipasang di sini",
            "bisa dipasang disini",
            "bisa pasang disini",
            "bisa pasang di sini",
            "daerah ini bisa dipasang",
            "daerah sini bisa dipasang",
            "sudah tercover",
            "sudah ter cover",
            "sudah ter cover belum",
            "sudah terjangkau belum",
            "daerah rejomulyo bisa dipasang",
            "rejomulyo sudah tercover",
            "rejomuyo sudah tercover",
            "daerah saya sudah tercover",
            "daerah saya sudah terjangkau"
        ],
        "responses": [
            "Untuk cek ketersediaan jaringan di lokasi kakak, mohon kirim nama daerah lengkap dan bila bisa share lokasi (pin point) ya kak. 😊\n"
            "Data coverage akan dicek oleh tim CS, dan kakak akan dihubungi kembali jika area tersebut sudah terjangkau."
        ]
    },
    {
        "name": "berhenti_langganan",
        "patterns": [
            "berhenti langganan",
            "stop langganan",
            "putus langganan",
            "cabut wifi",
            "cabut pemasangan",
            "cabut aja wifinya",
            "pemutusan layanan",
            "putus saja langganannya",
            "saya mau berhenti langganan",
            "saya mau putus langganan"
        ],
        "responses": [
            "Wah, maaf ya kak kalau selama ini layanan kami kurang berkenan di hati kakak 🙏\n"
            "Untuk proses pemutusan layanan/berhenti langganan, data kakak perlu dicek dan diproses oleh tim CS untuk mengetahui masih ada tunggakan pembayaran atau tidak ya kak.\n"
            "Silahkan untuk mengembalikan Perangkat ONT/Modem beserta adaptor ke kantor kami ya kak, nanti akan *diteruskan ke CS* untuk dibantu proses lebih lanjut."
        ]
    },
    {
        "name": "ganti_password_wifi",
        "patterns": [
            "ganti sandi",
            "ganti password",
            "ganti password wifi",
            "ubah password wifi",
            "ubah sandi wifi",
            "lupa password wifi",
            "lupa sandi wifi",
            "saya lupa sandi wifi",
            "saya lupa password wifi"
        ],
        "responses": [
            "Untuk ganti password WiFi, kakak bisa ikuti panduan di https://pendik.id/panduan ya. 😊\n\n"
            "Secara umum langkahnya seperti ini:\n"
            "1. Buka browser di HP/PC yang terhubung ke WiFi.\n"
            "2. Ketik alamat `http://192.168.1.1` di kolom address bar.\n"
            "3. Login dengan username & password modem (biasanya username 'user' dan password juga 'user', atau yang pernah dikirim teknisi).\n"
            "4. Masuk ke menu *WLAN (WLAN Settings)*.\n"
            "5. Klik WLAN SSID Configurtion Ganti nama WiFi (SSID) dan sandi/password sesuai keinginan.\n"
            "6. Simpan perubahan, lalu sambungkan ulang perangkat ke WiFi dengan password baru.\n\n"
            "Kalau kesulitan atau tidak bisa login ke modem, kakak bisa kirim ID Pelanggan, nanti *diteruskan ke NOC* untuk dibantu lebih lanjut. 🙏"
        ]
    },
    {
        "name": "jam_operasional",
        "patterns": [
            "jam berapa buka",
            "jam berapa tutup",
            "jam operasional",
            "sampai jam berapa ya",
            "cs sampai jam berapa",
            "admin sampai jam berapa",
            "kantor sampai jam berapa"
        ],
        "responses": [
            "Layanan Customer Service aktif setiap hari pukul 08.00–21.00 WIB ya kak. 😊\n"
            "Laporan gangguan teknis masih bisa diteruskan di luar jam tersebut dan akan dibantu oleh tim NOC."
        ]
    },
    {
        "name": "info_paket",
        "patterns": [
            "info paket",
            "paket",
            "harga paket",
            "harga bulanan",
            "biaya bulanan",
            "biaya per bulan",
            "langganan",
            "langganan wifi",
            "paket internet",
            "paket wifi",
            "pasang baru",
            "pasang wifi",
            "pasang wifi baru",
            "instalasi wifi",
            "pemasangan wifi",
            "biaya pasang baru",
            "biaya pemasangan",
            "promo wifi",
            "promo internet",
            "promo 100 mbps",
            "paket 30 mbps",
            "paket 50 mbps",
            "paket 75 mbps",
            "paket 100 mbps",
            "paket 150 mbps",
            "paket 200 mbps",
            "upto 30 mbps",
            "upto 50 mbps",
            "upto 75 mbps",
            "upto 100 mbps",
            "upto 150 mbps",
            "upto 200 mbps",
            "paket 100 mbps gimana",
            "paket 50 mbps kena berapa",
            "paket 30 mbps kena berapa"
        ],
        "responses": [
            "Berikut gambaran paket internet kami kak (detail dan update harga bisa dicek di https://pendik.id/pricing):\n"
            "- Beberapa pilihan kecepatan mulai dari 30 Mbps sampai 200 Mbps per bulan.\n"
            "- Instalasi/pemasangan gratis, kakak cukup membayar biaya bulanan di awal (bulan pertama).\n\n"
            "Untuk info paling update dan lengkap, silakan cek langsung di https://pendik.id/pricing ya. Kakak tertarik paket kecepatan berapa?"
        ]
    },
    {
        "name": "opsi_layanan",
        "patterns": [
            "bisa bantu apa saja",
            "bisa ngapain aja",
            "fitur chatbot ini apa",
            "kamu bisa apa",
            "bisa bantu apa",
            "kamu bisa bantu apa",
            "fungsi chatbot ini apa",
            "ini chatbot bisa apa aja"
        ],
        "responses": [
            "Aku bisa bantu:\n"
            "- Cek info paket & biaya bulanan\n"
            "- Jawab pertanyaan dasar soal gangguan\n"
            "- Pandu cek kondisi modem/ONT\n"
            "- Beri info cara pembayaran\n"
            "- Tandai laporan untuk diteruskan ke CS atau NOC kalau perlu penanganan lanjutan "
        ]
    },
    {
        "name": "cek_status_tiket",
        "patterns": [
            "cek status tiket",
            "status tiket",
            "cek tiket",
            "cek status ticket",
            "status ticket",
            "cek status tiket saya"
        ],
        "responses": [
            "Silakan sebutkan ID tiket Anda (contoh: CS-1234 atau NOC-5678), saya akan cek statusnya untuk Anda."
        ]
    },
    {
        "name": "goodbye",
        "patterns": [
            "terima kasih",
            "makasih",
            "makasih kak",
            "sudah cukup",
            "itu saja",
            "udah cukup",
            "dadah",
            "dah dulu",
            "sampai jumpa",
            "sampai ketemu lagi",
            "thank you",
            "thanks"
        ],
        "responses": [
            "Terima kasih sudah menghubungi kami ya kak. Kalau ada kendala lagi, tinggal chat aja. ",
            "Sip kak, semoga membantu. Kalau nanti ada gangguan atau pertanyaan lagi, boleh hubungi kami kapan saja. "
        ]
    }
]

FALLBACK_RESPONSES = [
    "Maaf kak, saya belum paham maksud pertanyaan kakak. Bisa dijelaskan lagi dengan kata lain?",
    "Sepertinya pertanyaannya di luar daftar yang saya pahami kak. Coba gunakan kata kunci seperti info paket, gangguan layanan, pembayaran, atau kabel putus ya kak. "
]
