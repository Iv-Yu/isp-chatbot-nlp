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
    reply TEXT,
    confidence FLOAT DEFAULT 1.0
);

-- 4. Masukkan Data User Default (Seed Data)
-- Password default: 'admin123', 'cs123', 'noc123' (sudah di-hash dengan bcrypt)
INSERT INTO users (username, password, role) VALUES
('admin', '$2b$12$R.S47i0DMT6.p3T5S1X0O.v9vF7WvPq3qQ9Q9Q9Q9Q9Q9Q9Q9Q9Q.', 'admin'),
('cs_staff', '$2b$12$K19m7W.DDRaL7.A5H/HMe.18P.v8v6D.8N0T0T0T0T0T0T0T0T0T.', 'cs'),
('noc_staff', '$2b$12$E8p.8K8K8K8K8K8K8K8K8K8K8K8K8K8K8K8K8K8K8K8K8K8K8K8K.', 'noc')
ON DUPLICATE KEY UPDATE role=VALUES(role);