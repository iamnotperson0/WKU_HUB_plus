import sqlite3
import os


A_DATABASE = os.path.join(os.path.dirname(__file__), 'A_registration.db')
B_DATABASE = os.path.join(os.path.dirname(__file__), 'B_database.db')
C_DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'C_database.db')


def get_c_db_connection():
    conn = sqlite3.connect(C_DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_reservations_table():
    """C_database.db에 reservations 테이블을 생성."""
    conn = sqlite3.connect(C_DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reservations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room TEXT NOT NULL,
            week TEXT NOT NULL,
            day TEXT NOT NULL,
            hour TEXT NOT NULL,
            building_name TEXT NOT NULL,
            floor_number TEXT NOT NULL,
            student_name TEXT NOT NULL,
            student_id TEXT NOT NULL,
            email TEXT NOT NULL,
            status TEXT DEFAULT '대기 중'
        )
    ''')
    conn.commit()
    conn.close()


def get_a_db_connection():
    conn = sqlite3.connect(A_DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def get_b_db_connection():
    conn = sqlite3.connect(B_DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def verify_student(name, student_number):
    conn = get_b_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM students WHERE name = ? AND student_number = ?', (name, student_number))
    student = cursor.fetchone()
    conn.close()
    return student is not None

# A 데이터베이스 초기화 함수
def initialize_a_database():
    conn = sqlite3.connect(A_DATABASE)
    cursor = conn.cursor()

    # users 테이블 생성 (verification_number 컬럼 포함)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            pdf_path TEXT,
            name TEXT,
            student_number TEXT,
            verification_number TEXT  -- 새로운 컬럼 추가
        )
    ''')
    conn.commit()
    conn.close()





# B 데이터베이스 초기화 함수
def initialize_b_database():
    conn = get_b_db_connection()
    cursor = conn.cursor()


    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            student_number TEXT NOT NULL
        )
    ''')


    # 기존 데이터가 없다면 초기 데이터 추가
    initial_data = [
        ('최현진', '20230101'),
        ('김도희', '20222222'),
        ('황병준', '20212238'),
        ('조승연', '20230101'),
    ]


    # 각각의 학생이 이미 존재하는지 확인하고, 존재하지 않으면 추가
    for name, student_number in initial_data:
        cursor.execute('SELECT COUNT(*) FROM students WHERE name = ? AND student_number = ?', (name, student_number))
        count = cursor.fetchone()[0]
        if count == 0:  # 데이터가 없다면 추가
            cursor.execute('INSERT INTO students (name, student_number) VALUES (?, ?)', (name, student_number))


    conn.commit()
    conn.close()


def initialize_professor_appointments_table():
    """C_database.db에 professor_appointments 테이블 생성"""
    conn = sqlite3.connect(C_DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS professor_appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            professor_name TEXT NOT NULL,
            week TEXT NOT NULL,
            day TEXT NOT NULL,
            hour TEXT NOT NULL,
            student_name TEXT NOT NULL,
            student_number TEXT NOT NULL,
            email TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()


def save_reservation_to_c_database(data, status='대기 중'):
    """C_database.db에 예약 데이터를 저장합니다."""
    print(f"Saving reservation to: {C_DATABASE_PATH}")  # 데이터베이스 경로 출력
    conn = sqlite3.connect(C_DATABASE_PATH)
    cursor = conn.cursor()
    # 테이블 생성 (이미 존재하면 무시됨)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reservations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room TEXT NOT NULL,
            week TEXT NOT NULL,
            day TEXT NOT NULL,
            hour TEXT NOT NULL,
            building_name TEXT NOT NULL,
            floor_number TEXT NOT NULL,
            student_name TEXT NOT NULL,
            student_id TEXT NOT NULL,
            email TEXT NOT NULL DEFAULT '',
            status TEXT DEFAULT '대기 중'
        )
    ''')
    conn.commit()
    # 데이터 삽입 (email 컬럼 포함)
    try:
        cursor.execute('''
            INSERT INTO reservations (room, week, day, hour, building_name, floor_number, student_name, student_id, email, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['room'], data['week'], data['day'], data['hour'],
            data['building_name'], data['floor_number'],
            data['student_name'], data['student_id'],
            data['email'],
            status
        ))
        conn.commit()
        reservation_id = cursor.lastrowid  # 새로 생성된 예약 ID
        print(f"예약이 C_database.db에 성공적으로 저장되었습니다: {data}")
    except sqlite3.Error as e:
        print(f"예약 저장 오류: {e}")
        raise e  # 오류를 다시 발생시켜 상위에서 처리할 수 있도록 함
    finally:
        conn.close()
    return reservation_id  # 예약 ID 반환


def fetch_reservations():
    """C_database.db에서 저장된 예약 데이터를 조회합니다."""
    conn = sqlite3.connect(C_DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM reservations')
    rows = cursor.fetchall()
    conn.close()
    return rows


def save_professor_appointment(data):
    """C_database.db에 교수님 면담 예약 데이터를 저장"""
    conn = sqlite3.connect(C_DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO professor_appointments (professor_name, week, day, hour, student_name, student_number, email)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        data['professor_name'], data['week'], data['day'], data['hour'],
        data['student_name'], data['student_number'], data['email']
    ))
    conn.commit()
    conn.close()


def reset_reservations_table():
    """C_database.db의 reservations 테이블을 초기화(모든 데이터 삭제)합니다."""
    conn = sqlite3.connect(C_DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM reservations')  # 모든 데이터 삭제
    conn.commit()
    conn.close()
    print("reservations 테이블이 초기화되었습니다.")


if __name__ == '__main__':
    initialize_a_database()
    initialize_b_database()
    initialize_reservations_table()
    initialize_professor_appointments_table()
    reset_reservations_table()
    print("데이터베이스가 초기화되었습니다.")
