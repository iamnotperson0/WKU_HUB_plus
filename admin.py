
import sqlite3
from werkzeug.security import generate_password_hash
import os

# 데이터베이스 경로를 절대 경로로 지정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
A_DATABASE = os.path.join(BASE_DIR, 'A_registration.db')

def add_admin(email, password):
    try:
        # 타임아웃 설정 (초 단위)
        with sqlite3.connect(A_DATABASE, timeout=10) as conn:
            cursor = conn.cursor()

            # 비밀번호 해싱 (pbkdf2:sha256 방식 사용)
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

            # 관리자 추가 시 role과 is_verified 필드도 설정
            cursor.execute('''
                INSERT INTO users (email, password, role, is_verified) VALUES (?, ?, ?, ?)
            ''', (email, hashed_password, 'admin', 1))

            conn.commit()
            print(f"관리자 계정이 추가되었습니다: {email}")
    except sqlite3.OperationalError as e:
        print(f"데이터베이스 작업 중 오류 발생: {e}")
    except sqlite3.IntegrityError as e:
        print(f"데이터베이스 무결성 오류: {e}")
    except Exception as e:
        print(f"예상치 못한 오류 발생: {e}")


if __name__ == '__main__':
    admin_email = input("관리자 이메일을 입력하세요: ")
    admin_password = input("관리자 비밀번호를 입력하세요: ")
    add_admin(admin_email, admin_password)
