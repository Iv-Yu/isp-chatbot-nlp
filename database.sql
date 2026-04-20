-- 1. Buat Database
CREATE DATABASE IF NOT EXISTS isp_chatbot;
USE isp_chatbot;

-- 2. Tabel untuk Manajemen User (Administrator, CS, NOC)
CREATE TABLE IF NOT EXISTS users (
    username VARCHAR(50) PRIMARY KEY,
    password VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL
);

-- 3. Tabel untuk Logging Percakapan dan Data Training
CREATE TABLE IF NOT EXISTS chat_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    chat_id BIGINT,
    message TEXT,
    intent VARCHAR(50),
    status VARCHAR(20),
    reply TEXT
);

-- 4. Tabel untuk status chat aktif (Session Monitoring)
CREATE TABLE IF NOT EXISTS chats (
    chat_id BIGINT PRIMARY KEY,
    last_message TEXT,
    status VARCHAR(20),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 4. Masukkan Data User Default (Seed Data)
INSERT INTO users (username, password, role) VALUES
('admin', 'admin123', 'admin'),
('cs_staff', 'cs123', 'cs'),
('noc_staff', 'noc123', 'noc')
ON DUPLICATE KEY UPDATE role=VALUES(role);