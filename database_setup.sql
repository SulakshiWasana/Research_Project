-- PostgreSQL Database Setup for Exam Monitoring System
-- Run this script to create the database and user

-- Create database
CREATE DATABASE exam_monitoring;

-- Create user (optional, you can use existing postgres user)
-- CREATE USER exam_user WITH PASSWORD 'exam_password';
-- GRANT ALL PRIVILEGES ON DATABASE exam_monitoring TO exam_user;

-- Connect to the exam_monitoring database
\c exam_monitoring;

-- The tables will be created automatically by Hibernate when the Spring Boot application starts
-- This is because we have 'spring.jpa.hibernate.ddl-auto=create-drop' in application.yml

-- If you want to create tables manually, here are the SQL statements:

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL,
    created_at TIMESTAMP,
    last_login TIMESTAMP
);

-- Exams table
CREATE TABLE IF NOT EXISTS exams (
    id BIGSERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    duration_minutes INTEGER NOT NULL,
    created_at TIMESTAMP,
    created_by VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL
);

-- Questions table
CREATE TABLE IF NOT EXISTS questions (
    id BIGSERIAL PRIMARY KEY,
    text TEXT NOT NULL,
    correct_answer VARCHAR(10) NOT NULL,
    exam_id BIGINT REFERENCES exams(id)
);

-- Question options table
CREATE TABLE IF NOT EXISTS question_options (
    question_id BIGINT REFERENCES questions(id),
    option_key VARCHAR(10),
    option_value TEXT
);

-- Exam sessions table
CREATE TABLE IF NOT EXISTS exam_sessions (
    id BIGSERIAL PRIMARY KEY,
    exam_id BIGINT REFERENCES exams(id),
    started_at TIMESTAMP,
    ended_at TIMESTAMP,
    status VARCHAR(50) NOT NULL,
    student_id BIGINT REFERENCES users(id)
);

-- Session students table
CREATE TABLE IF NOT EXISTS session_students (
    session_id BIGINT REFERENCES exam_sessions(id),
    student_username VARCHAR(255)
);

-- Student answers table
CREATE TABLE IF NOT EXISTS student_answers (
    session_id BIGINT REFERENCES exam_sessions(id),
    student_username VARCHAR(255),
    answers TEXT
);

-- Detection history table
CREATE TABLE IF NOT EXISTS detection_history (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id),
    detection_type VARCHAR(50) NOT NULL,
    detection_count INTEGER DEFAULT 0,
    last_detection TIMESTAMP,
    alert_count INTEGER DEFAULT 0,
    last_alert TIMESTAMP
);

-- Student detections table
CREATE TABLE IF NOT EXISTS student_detections (
    id BIGSERIAL PRIMARY KEY,
    session_id BIGINT REFERENCES exam_sessions(id),
    student_username VARCHAR(255) NOT NULL,
    detection_type VARCHAR(50) NOT NULL,
    detected_at TIMESTAMP,
    alert_sent BOOLEAN DEFAULT FALSE,
    alert_message TEXT
);

-- Insert default users
INSERT INTO users (username, password, name, role, created_at) VALUES
('admin', '$2a$10$N.zmdr9k7uOCQb376NoUnuTJ8iKyVhUx0p4rJhK8QjK8QjK8QjK8Q', 'Administrator', 'ADMIN', NOW()),
('student1', '$2a$10$N.zmdr9k7uOCQb376NoUnuTJ8iKyVhUx0p4rJhK8QjK8QjK8QjK8Q', 'John Doe', 'STUDENT', NOW()),
('student2', '$2a$10$N.zmdr9k7uOCQb376NoUnuTJ8iKyVhUx0p4rJhK8QjK8QjK8QjK8Q', 'Jane Smith', 'STUDENT', NOW())
ON CONFLICT (username) DO NOTHING;

-- Note: The password hash above is for 'password123' - you should change this in production

