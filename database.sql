-- 1. Buat Database
-- (Jalankan secara manual: CREATE DATABASE isp_chatbot;)

-- 2. Tabel untuk Manajemen User (Administrator, CS, NOC)
CREATE TABLE IF NOT EXISTS users (
    username VARCHAR(50) PRIMARY KEY,
    password VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL
);

-- 3. Tabel untuk Logging Percakapan dan Data Training
CREATE TABLE IF NOT EXISTS chat_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    chat_id BIGINT,
    message TEXT,
    intent VARCHAR(50),
    status VARCHAR(20),
    reply TEXT,
    confidence FLOAT DEFAULT 1.0,
    msg_id BIGINT DEFAULT NULL
);

-- 4. Masukkan Data User Default (Seed Data)
-- Catatan: Gunakan teks biasa jika ingin mencoba fitur auto-migration di API
INSERT INTO users (username, password, role) VALUES
('admin', 'admin123', 'admin'),
('cs_staff', 'cs123', 'cs'),
('noc_staff', 'noc123', 'noc')
ON CONFLICT (username) DO UPDATE SET role=EXCLUDED.role;