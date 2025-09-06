#!/usr/bin/env python3
"""
Database Setup Script for Exam Monitoring System
This script creates the database and tables
"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import sys

# Database connection settings
DB_CONFIG = {
    'host': 'localhost',
    'user': 'postgres',
    'password': 'postgres',
    'port': 5432
}

def create_database():
    """Create the exam_monitoring database"""
    try:
        # Connect to PostgreSQL server
        conn = psycopg2.connect(**DB_CONFIG)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = 'exam_monitoring'")
        exists = cursor.fetchone()
        
        if exists:
            print("✅ Database 'exam_monitoring' already exists")
        else:
            # Create database
            cursor.execute("CREATE DATABASE exam_monitoring")
            print("✅ Database 'exam_monitoring' created successfully")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error creating database: {e}")
        return False

def create_tables():
    """Create tables in the exam_monitoring database"""
    try:
        # Connect to exam_monitoring database
        conn = psycopg2.connect(
            host='localhost',
            database='exam_monitoring',
            user='postgres',
            password='postgres',
            port=5432
        )
        cursor = conn.cursor()
        
        # Create tables
        tables_sql = [
            # Users table
            """
            CREATE TABLE IF NOT EXISTS users (
                id BIGSERIAL PRIMARY KEY,
                username VARCHAR(255) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                name VARCHAR(255) NOT NULL,
                role VARCHAR(50) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            );
            """,
            
            # Exams table
            """
            CREATE TABLE IF NOT EXISTS exams (
                id BIGSERIAL PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                description TEXT,
                duration_minutes INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by VARCHAR(255) NOT NULL,
                status VARCHAR(50) NOT NULL DEFAULT 'DRAFT'
            );
            """,
            
            # Questions table
            """
            CREATE TABLE IF NOT EXISTS questions (
                id BIGSERIAL PRIMARY KEY,
                text TEXT NOT NULL,
                correct_answer VARCHAR(10) NOT NULL,
                exam_id BIGINT REFERENCES exams(id)
            );
            """,
            
            # Question options table
            """
            CREATE TABLE IF NOT EXISTS question_options (
                question_id BIGINT REFERENCES questions(id),
                option_key VARCHAR(10),
                option_value TEXT
            );
            """,
            
            # Exam sessions table
            """
            CREATE TABLE IF NOT EXISTS exam_sessions (
                id BIGSERIAL PRIMARY KEY,
                exam_id BIGINT REFERENCES exams(id),
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ended_at TIMESTAMP,
                status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE',
                student_id BIGINT REFERENCES users(id)
            );
            """,
            
            # Session students table
            """
            CREATE TABLE IF NOT EXISTS session_students (
                session_id BIGINT REFERENCES exam_sessions(id),
                student_username VARCHAR(255)
            );
            """,
            
            # Student answers table
            """
            CREATE TABLE IF NOT EXISTS student_answers (
                session_id BIGINT REFERENCES exam_sessions(id),
                student_username VARCHAR(255),
                answers TEXT
            );
            """,
            
            # Detection history table
            """
            CREATE TABLE IF NOT EXISTS detection_history (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(id),
                detection_type VARCHAR(50) NOT NULL,
                detection_count INTEGER DEFAULT 0,
                last_detection TIMESTAMP,
                alert_count INTEGER DEFAULT 0,
                last_alert TIMESTAMP
            );
            """,
            
            # Student detections table
            """
            CREATE TABLE IF NOT EXISTS student_detections (
                id BIGSERIAL PRIMARY KEY,
                session_id BIGINT REFERENCES exam_sessions(id),
                student_username VARCHAR(255) NOT NULL,
                detection_type VARCHAR(50) NOT NULL,
                detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                alert_sent BOOLEAN DEFAULT FALSE,
                alert_message TEXT
            );
            """
        ]
        
        for sql in tables_sql:
            cursor.execute(sql)
        
        conn.commit()
        print("✅ All tables created successfully")
        
        # Insert default users
        insert_users_sql = """
        INSERT INTO users (username, password, name, role, created_at) VALUES
        ('admin', '$2a$10$N.zmdr9k7uOCQb376NoUnuTJ8iKyVhUx0p4rJhK8QjK8QjK8QjK8Q', 'Administrator', 'ADMIN', CURRENT_TIMESTAMP),
        ('student1', '$2a$10$N.zmdr9k7uOCQb376NoUnuTJ8iKyVhUx0p4rJhK8QjK8QjK8QjK8Q', 'John Doe', 'STUDENT', CURRENT_TIMESTAMP),
        ('student2', '$2a$10$N.zmdr9k7uOCQb376NoUnuTJ8iKyVhUx0p4rJhK8QjK8QjK8QjK8Q', 'Jane Smith', 'STUDENT', CURRENT_TIMESTAMP)
        ON CONFLICT (username) DO NOTHING;
        """
        
        cursor.execute(insert_users_sql)
        conn.commit()
        print("✅ Default users inserted")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        return False

def main():
    """Main function"""
    print("🗄️  Setting up Exam Monitoring Database")
    print("=" * 50)
    
    # Create database
    if not create_database():
        return
    
    # Create tables
    if not create_tables():
        return
    
    print("\n✅ Database setup completed successfully!")
    print("\nYou can now:")
    print("1. Run the Spring Boot application: mvn spring-boot:run")
    print("2. View the database: python simple_db_viewer.py")
    print("3. Access the application at: http://localhost:8080")

if __name__ == "__main__":
    main()
