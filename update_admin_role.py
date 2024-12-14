# update_admin_role.py

import sqlite3

DATABASE = 'A_registration.db'
ADMIN_EMAIL = 'wkuplushubadmin@wku.ac.kr'


def update_admin_role():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("SELECT role FROM users WHERE email = ?", (ADMIN_EMAIL,))
    user = cursor.fetchone()

    if user:
        if user[0] != 'admin':
            cursor.execute("UPDATE users SET role = 'admin' WHERE email = ?", (ADMIN_EMAIL,))
            conn.commit()
            print(f"{ADMIN_EMAIL}의 role이 'admin'으로 업데이트되었습니다.")
        else:
            print(f"{ADMIN_EMAIL}는 이미 'admin' 역할을 가지고 있습니다.")
    else:
        print(f"{ADMIN_EMAIL}에 해당하는 사용자를 찾을 수 없습니다.")

    conn.close()


if __name__ == "__main__":
    update_admin_role()

# 관리자 계정 업데이트
# consol command: python update_admin_role.py