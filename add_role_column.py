# add_role_column.py

import sqlite3

DATABASE = 'A_registration.db'


def add_role_column():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # `role` 컬럼이 이미 존재하는지 확인
    cursor.execute("PRAGMA table_info(users);")
    columns = [info[1] for info in cursor.fetchall()]

    if 'role' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user';")
        print("`role` 컬럼이 성공적으로 추가되었습니다.")
    else:
        print("`role` 컬럼이 이미 존재합니다.")

    conn.commit()
    conn.close()


if __name__ == "__main__":
    add_role_column()

# python add_role_column.py <- role 컬럼을 추가