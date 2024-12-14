import sys
import os
import re
import time
import smtplib
import urllib
import sqlite3
import json
import requests
from dotenv import load_dotenv
from functools import wraps
from flask import Flask, render_template, jsonify, abort, redirect, url_for, request, make_response, flash
from math import cos, radians
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config
from itsdangerous import URLSafeTimedSerializer
from email.message import EmailMessage

from db_utils import get_a_db_connection, get_b_db_connection, initialize_reservations_table, \
    save_reservation_to_c_database, save_professor_appointment, initialize_professor_appointments_table, \
    initialize_a_database, initialize_b_database, get_c_db_connection, verify_student

from ocr_cross import get_student_info

ADMIN_EMAIL = 'wkuplushubadmin@wku.ac.kr'

NAVER_API_KEY_ID = "4ujqbc87ks"  # 네이버 클라이언트 ID
NAVER_API_SECRET_KEY = "VXBFMWDVbZIkybh9OMznWQkphaeIk9u7oLyviAWB"  # 네이버 클라이언트 Secret Key

current_dir = os.path.dirname(os.path.abspath(__file__))
module_dir = os.path.join(current_dir, 'extract_spectific_word')
sys.path.append(module_dir)

BUILDINGS_JSON_PATH = os.path.join(os.path.dirname(__file__), 'make_json_file_data', 'buildings.json')
PROFESSOR_DATA_JSON_PATH = os.path.join(os.path.dirname(__file__), 'make_json_file_data', 'professor_data.json')
PROFESSOR_SCHEDULES_JSON_PATH = os.path.join(os.path.dirname(__file__), 'make_json_file_data',
                                             'professor_schedules.json')

load_dotenv()  # .env 파일 로드
sender_email = os.getenv("GMAIL_USER")
sender_password = os.getenv("GMAIL_PASS")

# Flask 앱의 SECRET_KEY 사용

def sanitize_text(text):
    if text:
        text = text.replace('\n', ' ').replace('\r', ' ')
        return re.sub(r'\s+', ' ', text).strip()
    return text

def generate_confirmation_token(email):
    """이메일을 기반으로 인증 토큰 생성"""
    return serializer.dumps(email, salt='email-confirm')

def confirm_token(token, expiration=3600):
    """인증 토큰 검증 (기본 유효 기간: 1시간)"""
    try:
        email = serializer.loads(token, salt='email-confirm', max_age=expiration)
        return email
    except Exception:
        return False

def load_buildings():
    with open(BUILDINGS_JSON_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_professor_data():
    with open(PROFESSOR_DATA_JSON_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_professor_schedules():
    with open(PROFESSOR_SCHEDULES_JSON_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def add_verification_number_column():
    # 데이터베이스 연결
    conn = sqlite3.connect(A_DATABASE)
    cursor = conn.cursor()

    # 테이블에 'verification_number' 컬럼 추가
    try:
        cursor.execute('''
            ALTER TABLE users ADD COLUMN verification_number TEXT
        ''')
        conn.commit()
        print("verification_number 컬럼이 users 테이블에 추가되었습니다.")
    except sqlite3.OperationalError:
        print("이미 verification_number 컬럼이 존재하거나 다른 오류가 발생했습니다.")
    finally:
        conn.close()


buildings = load_buildings()
professor_data = load_professor_data()
professor_schedules = load_professor_schedules()

app = Flask(__name__,
            static_folder=os.path.join(os.path.dirname(__file__), 'static'),
            template_folder=os.path.join(os.path.dirname(__file__), 'templates'))
app.config.from_object(Config)

serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])

# 데이터베이스 경로 설정
A_DATABASE = os.path.join(os.path.dirname(__file__), 'A_registration.db')  # A 데이터베이스
B_DATABASE = os.path.join(os.path.dirname(__file__), 'B_database.db')  # B 데이터베이스
C_DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'C_database.db')  # C 데이터베이스

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_email = request.cookies.get('user_email')
        if not user_email:
            flash('로그인이 필요한 서비스입니다.')  # Flash 메시지 설정
            return redirect(url_for('home'))  # 홈으로 리다이렉트
        return f(*args, **kwargs)

    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_email = request.cookies.get('user_email')
        if not user_email:
            flash('로그인이 필요한 서비스입니다.')
            return redirect(url_for('home'))  # 로그인 페이지 대신 홈 페이지로 리디렉션
        conn = get_a_db_connection()
        user = conn.execute('SELECT role FROM users WHERE email = ?', (user_email,)).fetchone()
        conn.close()
        if not user or user['role'] != 'admin':
            flash('접근 권한이 없습니다.')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

def calculate_bounds(buildings, buffer_meters=100):
    # 위도 1도 당 미터 변환
    delta_lat = buffer_meters / 111000  # 약 0.0009도

    # 평균 위도 계산
    avg_lat = sum([b['lat'] for b in buildings]) / len(buildings)
    delta_lng = buffer_meters / (111000 * cos(radians(avg_lat)))  # 약 0.0011도

    min_lat = min([b['lat'] for b in buildings]) - delta_lat
    max_lat = max([b['lat'] for b in buildings]) + delta_lat
    min_lng = min([b['lng'] for b in buildings]) - delta_lng
    max_lng = max([b['lng'] for b in buildings]) + delta_lng

    return {
        "southWest": {"lat": min_lat, "lng": min_lng},
        "northEast": {"lat": max_lat, "lng": max_lng}
    }

import smtplib
from email.message import EmailMessage
import os
# from flask import current_app as app

def send_email_gmail(to_email, subject, content, approve_url=None, decline_url=None):
    smtp_server = "smtp.gmail.com"
    smtp_port = 587

    sender_email = os.getenv("GMAIL_USER")
    sender_password = os.getenv("GMAIL_PASS")

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = to_email

    # HTML 이메일 내용 작성
    formatted_content = content.replace('\n', '<br>')
    html_content = """
    <html>
        <body>
            <p>{}</p>
    """.format(formatted_content)

    if approve_url and decline_url:
        html_content += """
            <p>
                <a href="{}" style="padding:10px; background-color:green; color:white; text-decoration:none; border-radius:5px; margin-right:10px;">승인</a>
                <a href="{}" style="padding:10px; background-color:red; color:white; text-decoration:none; border-radius:5px;">거절</a>
            </p>
        """.format(approve_url, decline_url)

    html_content += """
        </body>
    </html>
    """

    msg.add_alternative(html_content, subtype='html')

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.set_debuglevel(1)  # SMTP 디버그 출력 활성화 (개발 시에만 사용)
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
            # current_app을 함수 내부에서 임포트하여 사용
            from flask import current_app
            current_app.logger.info(f"이메일이 {to_email}로 성공적으로 전송되었습니다.")
    except smtplib.SMTPException as e:
        from flask import current_app
        current_app.logger.error(f"이메일 전송 실패: {e}")
        raise Exception(f"이메일 전송 중 오류가 발생했습니다: {e}")



def send_email_notification(to_email, subject, content):
    send_email_gmail(
        to_email=to_email,
        subject=subject,
        content=content
    )

@app.route('/')
def home():
    user_email = request.cookies.get('user_email')  # 쿠키에 저장된 이메일 확인
    is_admin = False  # 기본값 설정

    if user_email:
        conn = get_a_db_connection()
        user_role = conn.execute('SELECT role FROM users WHERE email = ?', (user_email,)).fetchone()
        conn.close()
        if user_role and user_role['role'] == 'admin':
            is_admin = True

    cards = []  # 로그인 여부와 관계없이 기본값 설정

    # 캠퍼스 경계 계산
    campus_bounds = calculate_bounds(buildings, buffer_meters=100)

    return render_template(
        'index.html',
        buildings=buildings,
        cards=cards,
        campus_bounds=campus_bounds,
        user_email=user_email,
        is_admin=is_admin  # 관리자 여부를 템플릿에 전달
    )

@app.route('/confirm/<token>', methods=['GET'])
def confirm_email(token):
    """사용자가 인증 링크를 클릭했을 때 실행"""
    email = confirm_token(token)  # 토큰에서 이메일 추출
    if not email:
        flash('인증 링크가 만료되었거나 유효하지 않습니다.', 'danger')
        return redirect(url_for('signup'))

    # A 데이터베이스에서 해당 이메일 사용자 인증 처리
    conn = get_a_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET is_verified = 1 WHERE email = ?", (email,))
    conn.commit()
    conn.close()

    flash('이메일 인증이 완료되었습니다!', 'success')
    return redirect(url_for('home'))


@app.route('/api/direction', methods=['GET'])
def get_direction():
    start = request.args.get('start')
    goal = request.args.get('goal')
    option = request.args.get('option', 'trafast')

    if not start or not goal:
        return jsonify({"error": "Missing required parameters: start or goal"}), 400

    # 네이버 Direction5 API 호출
    url = f"https://naveropenapi.apigw.ntruss.com/map-direction/v1/driving?start={start}&goal={goal}&option={option}"
    headers = {
        "X-NCP-APIGW-API-KEY-ID": NAVER_API_KEY_ID,
        "X-NCP-APIGW-API-KEY": NAVER_API_SECRET_KEY,
    }

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print("API 요청 실패:", response.text)  # 오류 로그 추가
        return jsonify({"error": "Failed to fetch directions", "details": response.text}), 500

    print("API 응답 성공:", response.json())  # 응답 데이터 로그 추가
    return jsonify(response.json())


@app.route('/building/<string:building_name>/service')
@login_required
def building_service(building_name):
    building = next((b for b in buildings if b['name'] == building_name), None)
    if building:
        departments = building.get('departments', [])
        return render_template('building_service.html', building=building, departments=departments)
    else:
        return "Service page not available for this building.", 404


@app.route('/building/<string:building_name>/details')  # url 이름 바꾸려면 details 말고 다른걸로 설정
def building_details(building_name):
    building = next((b for b in buildings if b['name'] == building_name), None)
    if building:
        return render_template('building_details.html', building=building)
    else:
        abort(404)


@app.route('/building/<string:building_name>/floor/<int:floor_number>')
def building_floor(building_name, floor_number):
    building = next((b for b in buildings if b['name'] == building_name), None)
    if not building:
        abort(404, description="Building not found")

    if "floors" not in building or floor_number not in building["floors"]:
        abort(404, description="Floor not found")

    floor_info = building["floors"][floor_number]
    images = floor_info["image"] if isinstance(floor_info["image"], list) else [floor_info["image"]]
    return render_template('floor.html', building=building, floor_number=floor_number, floor_info=floor_info,
                           images=images)


# 교수님 목록 페이지
@app.route('/building/<string:building_name>/floor/<int:floor_number>')
def show_professors(building_name, floor_number):
    department = None
    for building in buildings:
        if building["name"] == building_name:
            if 0 <= floor_number < len(building["departments"]):
                department = building["departments"][floor_number].get("name")
            break
    if not department:
        return "해당 층에는 학과 정보가 없습니다.", 404

    professors = professor_data.get(department, [])
    return render_template('professor_schedule.html', professors=professors, department=department)


@app.route('/building/<string:building_name>/service/<string:department_name>')
def department_service(building_name, department_name):
    professors = professor_data.get(building_name, {}).get(department_name, [])
    if not professors:
        return f"{department_name}에 대한 교수님 정보가 없습니다.", 404

    return render_template(
        'professor_schedule.html',
        professors=professors,
        department=department_name,
        building_name=building_name,
        floor_number=1
    )


# 교수님 상세 시간표 페이지
@app.route('/professor/<string:professor_name>/add_schedule', methods=['POST'])
def add_schedule(professor_name):
    day = request.form['day']
    time_slot = request.form['time_slot']
    subject = request.form['subject']
    room = request.form['room']

    # 해당 교수님의 시간표에 새 일정 추가
    if professor_name not in professor_schedules:
        professor_schedules[professor_name] = {}  # 새 교수님 시간표 초기화

    if day not in professor_schedules[professor_name]:
        professor_schedules[professor_name][day] = {}  # 요일 초기화

    professor_schedules[professor_name][day][time_slot] = {
        "subject": subject,
        "room": room
    }

    # 업데이트된 시간표 페이지로 리디렉션
    return redirect(url_for('show_professor_detail', professor_name=professor_name))


@app.route('/building/<string:building_name>/professor/<string:professor_name>', methods=['GET'])
def professor_schedule(building_name, professor_name):
    # JSON 데이터 로드
    try:
        with open(PROFESSOR_SCHEDULES_JSON_PATH, 'r', encoding='utf-8') as f:
            professor_schedules = json.load(f)
    except FileNotFoundError:
        professor_schedules = {}

    professor_schedule = professor_schedules.get(professor_name, {})

    # 모든 시간과 상태를 포함한 시간표 생성
    days = ["월요일", "화요일", "수요일", "목요일", "금요일"]
    time_slots = [f"{hour}:00" for hour in range(9, 20)]

    # 초기 상태: 모든 시간 공백으로 설정
    schedule_with_status = {day: {time: "" for time in time_slots} for day in days}

    # 예약 완료된 시간과 예약 가능 시간 채우기
    for day, times in professor_schedule.items():
        for time, status in times.items():
            if day in schedule_with_status and time in schedule_with_status[day]:
                schedule_with_status[day][time] = status  # "예약 완료" 또는 "예약 가능"

    return render_template(
        'professor_schedule_detail.html',
        room={"name": professor_name, "schedule": schedule_with_status},
        building_name=building_name
    )


@app.route('/reserve_professor_week', methods=['POST'])
def reserve_professor_week():
    data = request.json
    professor_name = data.get('name')
    week = data.get('week')
    day = data.get('day')
    hour = data.get('hour')  # 예: "11:00:00"

    # 로그인된 사용자 이메일 가져오기
    user_email = request.cookies.get('user_email')
    if not user_email:
        return jsonify({"success": False, "message": "로그인이 필요한 서비스입니다."}), 403

    # 데이터베이스에서 사용자 이름과 학번 가져오기
    conn = get_a_db_connection()
    user = conn.execute(
        "SELECT name, student_number FROM users WHERE email = ?",
        (user_email,)
    ).fetchone()
    conn.close()

    if not user:
        return jsonify({"success": False, "message": "사용자 정보를 찾을 수 없습니다."}), 404

    # sanitize_text 함수 적용
    student_name = sanitize_text(user['name'])
    student_number = sanitize_text(user['student_number'])

    # 예약 시간 형식 조정 ("11:00:00" -> "11:00")
    formatted_hour = hour[:5] if hour else ''

    # 교수님 이메일 찾기
    professor_email = None
    for building, departments in professor_data.items():
        for department, professors in departments.items():
            for professor in professors:
                if professor["name"] == professor_name:
                    professor_email = professor.get("email")
                    break

    if not professor_email:
        return jsonify({"success": False, "message": "교수님의 이메일 정보를 찾을 수 없습니다."}), 404

    # JSON 파일 업데이트 및 예약 처리
    try:
        with open(PROFESSOR_SCHEDULES_JSON_PATH, 'r+', encoding='utf-8') as f:
            schedules = json.load(f)
            week_schedule = schedules.setdefault(professor_name, {}).setdefault(f"{week}주차", {}).setdefault(day, {})
            if week_schedule.get(formatted_hour) == "예약 완료":
                return jsonify({"success": False, "message": "이미 예약된 시간입니다."}), 400
            week_schedule[formatted_hour] = {
                "status": "예약 완료",
                "student_name": student_name,
                "student_id": student_number
            }
            f.seek(0)
            json.dump(schedules, f, ensure_ascii=False, indent=4)
            f.truncate()
    except Exception as e:
        app.logger.error(f"예약 처리 중 오류: {e}")
        return jsonify({"success": False, "message": "예약 처리 중 오류가 발생했습니다."}), 500

    # 데이터베이스에 예약 정보 저장
    try:
        save_professor_appointment({
            "professor_name": professor_name,
            "week": week,
            "day": day,
            "hour": formatted_hour,
            "student_name": student_name,
            "student_number": student_number,
            "email": user_email
        })
    except Exception as e:
        return jsonify({"success": False, "message": f"데이터베이스 저장 실패: {e}"}), 500

    # 교수님 이메일 전송
    try:
        subject = "새로운 면담 예약 요청"
        content = f"{student_name} ({student_number}) 님이 {week}주차 {day} {formatted_hour}에 면담을 예약했습니다."

        # 승인 및 거절 링크 생성
        approve_url = f"{request.host_url}appointment/{professor_name}/approve?student_email={user_email}"
        decline_url = f"{request.host_url}appointment/{professor_name}/decline?student_email={user_email}"

        send_email_gmail(professor_email, subject, content, approve_url, decline_url)
    except Exception as e:
        app.logger.error(f"이메일 전송 실패: {e}")
        return jsonify({"success": False, "message": "예약은 완료되었지만 이메일 전송에 실패했습니다."}), 500

    return jsonify({"success": True, "message": "예약이 완료되었으며, 교수님께 이메일이 발송되었습니다."})


@app.route('/appointment/<string:professor_name>/approve', methods=['GET'])
def approve_appointment(professor_name):
    student_email = request.args.get('student_email')
    if not student_email:
        return "학생 이메일 정보가 누락되었습니다.", 400

    try:
        send_email_gmail(
            to_email=student_email,
            subject="면담 가능 알림",
            content=f"{professor_name} 교수님이 면담 가능하다고 확인하셨습니다.",
            approve_url="",
            decline_url=""
        )
        return "면담 가능 이메일이 발송되었습니다.", 200
    except Exception as e:
        app.logger.error(f"이메일 전송 실패: {e}")
        return "이메일 발송 중 오류가 발생했습니다.", 500

@app.route('/appointment/<string:professor_name>/decline', methods=['GET'])
def decline_appointment(professor_name):
    student_email = request.args.get('student_email')
    if not student_email:
        return "학생 이메일 정보가 누락되었습니다.", 400

    try:
        send_email_gmail(
            to_email=student_email,
            subject="면담 불가 알림",
            content=f"{professor_name} 교수님이 면담 불가하다고 확인하셨습니다.",
            approve_url="",
            decline_url=""
        )
        return "면담 불가 이메일이 발송되었습니다.", 200
    except Exception as e:
        app.logger.error(f"이메일 전송 실패: {e}")
        return "이메일 발송 중 오류가 발생했습니다.", 500

@app.route('/map/admin_redirect', methods=['GET'])
@admin_required
def admin_redirect():
    return redirect(url_for('admin_reservations'))

@app.route('/admin/reservations')
@admin_required
def admin_reservations():
    conn = get_c_db_connection()  # db_utils의 함수 사용
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM reservations')
    reservations = cursor.fetchall()
    conn.close()
    print(f"조회된 예약 수: {len(reservations)}")  # 디버그 로그 추가
    return render_template('admin_reservations.html', reservations=reservations)

@app.route('/admin/reservations/<int:reservation_id>/approve', methods=['POST'])
@admin_required
def approve_reservation(reservation_id):
    try:
        # 예약 상태를 '승인'으로 업데이트
        conn = get_c_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE reservations SET status = ? WHERE id = ?', ('승인', reservation_id))
        conn.commit()

        # 예약 정보 가져오기
        cursor.execute('SELECT * FROM reservations WHERE id = ?', (reservation_id,))
        reservation = cursor.fetchone()
        conn.close()

        if reservation:
            student_email = reservation['email']
            student_name = reservation['student_name']
            student_id = reservation['student_id']
            building_name = reservation['building_name']
            room_name = reservation['room']
            floor_number = reservation['floor_number']
            week = reservation['week']
            day = reservation['day']
            hour = reservation['hour']

            # JSON 파일 업데이트 (상태를 '예약 완료'로 변경)
            floor_json_path = os.path.join(
                os.path.dirname(__file__),
                'campus_building_floors',
                building_name,
                f"{floor_number}.json"
            )
            if not os.path.exists(floor_json_path):
                app.logger.error(f"Floor data not found: {floor_json_path}")
                flash("층 데이터가 존재하지 않습니다.")
                return redirect(url_for('admin_reservations'))

            try:
                with open(floor_json_path, 'r+', encoding='utf-8') as f:
                    floor_data = json.load(f)

                    # 방 찾기
                    room = next((r for r in floor_data['rooms'] if r['name'] == room_name), None)
                    if not room:
                        app.logger.error(f"Room not found: {room_name}")
                        flash("강의실을 찾을 수 없습니다.")
                        return redirect(url_for('admin_reservations'))

                    week_key = f"{week}주차"
                    if week_key in room and day in room[week_key] and hour in room[week_key][day]:
                        room[week_key][day][hour]['status'] = '예약 완료'
                        # JSON 파일 업데이트
                        f.seek(0)
                        json.dump(floor_data, f, ensure_ascii=False, indent=4)
                        f.truncate()
                    else:
                        app.logger.error("예약 정보를 JSON 파일에서 찾을 수 없습니다.")
                        flash("예약 정보를 JSON 파일에서 찾을 수 없습니다.")
                        return redirect(url_for('admin_reservations'))
            except Exception as e:
                app.logger.error(f"JSON 파일 업데이트 중 오류: {e}")
                flash("JSON 파일 업데이트 중 오류가 발생했습니다.")
                return redirect(url_for('admin_reservations'))

            subject = "강의실 예약 승인 알림"
            content = f"""
            안녕하세요, wkuhunpuls입니다 
            {student_name}님 
            요청하신 강의실 예약이 승인되었습니다.

            예약 상세 정보:
            - 건물: {building_name}
            - 강의실: {room_name}
            - 주차: {week}
            - 요일: {day}
            - 시간: {hour}
            """
            send_email_notification(student_email, subject, content)

            flash('예약이 승인되었습니다.')
        else:
            flash('예약 정보를 찾을 수 없습니다.')

    except Exception as e:
        app.logger.error(f"예약 승인 중 오류: {e}")
        flash('예약 승인 중 오류가 발생했습니다.')

    return redirect(url_for('admin_reservations'))

@app.route('/admin/reservations/<int:reservation_id>/decline', methods=['POST'])
@admin_required
def decline_reservation(reservation_id):
    try:
        # 예약 상태를 '거절'으로 업데이트
        conn = get_c_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE reservations SET status = ? WHERE id = ?', ('거절', reservation_id))
        conn.commit()

        # 예약 정보 가져오기
        cursor.execute('SELECT * FROM reservations WHERE id = ?', (reservation_id,))
        reservation = cursor.fetchone()
        conn.close()

        if reservation:
            student_email = reservation['email']
            student_name = reservation['student_name']
            student_id = reservation['student_id']
            building_name = reservation['building_name']
            room_name = reservation['room']
            floor_number = reservation['floor_number']
            week = reservation['week']
            day = reservation['day']
            hour = reservation['hour']

            # JSON 파일에서 예약 정보 제거
            floor_json_path = os.path.join(
                os.path.dirname(__file__),
                'campus_building_floors',
                building_name,
                f"{floor_number}.json"
            )
            if not os.path.exists(floor_json_path):
                app.logger.error(f"Floor data not found: {floor_json_path}")
                flash("층 데이터가 존재하지 않습니다.")
                return redirect(url_for('admin_reservations'))

            try:
                with open(floor_json_path, 'r+', encoding='utf-8') as f:
                    floor_data = json.load(f)

                    # 방 찾기
                    room = next((r for r in floor_data['rooms'] if r['name'] == room_name), None)
                    if not room:
                        app.logger.error(f"Room not found: {room_name}")
                        flash("강의실을 찾을 수 없습니다.")
                        return redirect(url_for('admin_reservations'))

                    week_key = f"{week}주차"
                    if week_key in room and day in room[week_key] and hour in room[week_key][day]:
                        # 예약 정보 제거
                        del room[week_key][day][hour]
                        # 필요하면 빈 day 또는 week_key 제거
                        if not room[week_key][day]:
                            del room[week_key][day]
                        if not room[week_key]:
                            del room[week_key]
                        # JSON 파일 업데이트
                        f.seek(0)
                        json.dump(floor_data, f, ensure_ascii=False, indent=4)
                        f.truncate()
                    else:
                        app.logger.error("예약 정보를 JSON 파일에서 찾을 수 없습니다.")
                        flash("예약 정보를 JSON 파일에서 찾을 수 없습니다.")
                        return redirect(url_for('admin_reservations'))
            except Exception as e:
                app.logger.error(f"JSON 파일 업데이트 중 오류: {e}")
                flash("JSON 파일 업데이트 중 오류가 발생했습니다.")
                return redirect(url_for('admin_reservations'))

            subject = "강의실 예약 거절 알림"
            content = f"""
            안녕하세요 wkuhubpuls입니다
            {student_name}님 

            요청하신 강의실 예약이 거절되었습니다.

            예약 상세 정보:
            - 건물: {building_name}
            - 강의실: {room_name}
            - 주차: {week}
            - 요일: {day}
            - 시간: {hour}
            """
            send_email_notification(student_email, subject, content)

            flash('예약이 거절되었습니다.')
        else:
            flash('예약 정보를 찾을 수 없습니다.')

    except Exception as e:
        app.logger.error(f"예약 거절 중 오류: {e}")
        flash('예약 거절 중 오류가 발생했습니다.')

    return redirect(url_for('admin_reservations'))

# 교수 면담 예약 거절 함수
@app.route('/admin/appointments/<int:appointment_id>/decline', methods=['POST'])
@admin_required
def decline_professor_appointment(appointment_id):
    try:
        # 면담 예약 상태를 '거절'으로 업데이트
        conn = sqlite3.connect(C_DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute('UPDATE professor_appointments SET status = ? WHERE id = ?', ('거절', appointment_id))
        conn.commit()

        # 면담 예약 정보 가져오기
        cursor.execute('SELECT * FROM professor_appointments WHERE id = ?', (appointment_id,))
        appointment = cursor.fetchone()
        conn.close()

        if appointment:
            student_email = appointment['email']
            student_name = appointment['student_name']
            student_id = appointment['student_number']
            professor_name = appointment['professor_name']
            week = appointment['week']
            day = appointment['day']
            hour = appointment['hour']

            # 사용자에게 거절 이메일 전송
            subject = "교수 면담 예약 거절 알림"
            content = f"""
            안녕하세요, {student_name}님 \n
            요청하신 교수 면담 예약이 거절되었습니다.\n
            예약 상세 정보:\n
            - 교수님: {professor_name}\n
            - 주차: {week}\n
            - 요일: {day}\n
            - 시간: {hour}\n
            """
            send_email_notification(student_email, subject, content)

            flash('교수 면담 예약이 거절되었습니다.')
        else:
            flash('면담 예약 정보를 찾을 수 없습니다.')

    except Exception as e:
        app.logger.error(f"교수 면담 예약 거절 중 오류: {e}")
        flash('교수 면담 예약 거절 중 오류가 발생했습니다.')

    return redirect(url_for('admin_appointments'))


# 허용된 이메일 리스트 정의
ALLOWED_PDF_ONLY = {"pdfonly1@example.com", "pdfonly2@example.com","aaa2@gmail.com"}  # PDF 검증만 수행
ALLOWED_ALL_BYPASS = {"bypass1@example.com", "bypass2@example.com","a1.@com"}  # 모든 검증 생략
ALLOWED_ADMINS = {"admin1@example.com", "admin2@example.com","aaa2@gmail.com"}  # 관리자 이메일 리스트

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        pdf_file = request.files.get('pdf')

        # 기본값 설정
        role = "user"
        is_verified = 0
        extracted_name = None
        extracted_student_number = None
        extracted_verification_number = None
        pdf_path = None

        # 우선순위 처리
        if email in ALLOWED_ALL_BYPASS:
            # 모든 검증 생략
            extracted_name = "테스트 사용자"
            extracted_student_number = "20230001"
            is_verified = 1
            if email in ALLOWED_ADMINS:
                role = "admin"  # 관리자 권한 부여
            print(f"[모든 검증 생략] 이메일: {email}, 이름: {extracted_name}, 학번: {extracted_student_number}, 역할: {role}")

        elif email in ALLOWED_PDF_ONLY:
            # PDF 검증 수행
            pdf_folder = os.path.join(os.path.dirname(__file__), 'pdfs')
            os.makedirs(pdf_folder, exist_ok=True)
            pdf_path = os.path.join(pdf_folder, pdf_file.filename)
            pdf_file.save(pdf_path)

            # PDF에서 이름, 학번, 검증 번호 추출
            extracted_name, extracted_student_number, extracted_verification_number = get_student_info(pdf_path)
            if not extracted_name or not extracted_student_number or not extracted_verification_number:
                flash('정보를 찾을수 없습니다 원광대학교 PDF를 첨부해주세요.')
                return redirect(request.url)

            is_verified = 1  # 이메일 인증 생략
            if email in ALLOWED_ADMINS:
                role = "admin"  # 관리자 권한 부여
            print(f"[PDF 검증만 수행] 이메일: {email}, 이름: {extracted_name}, 학번: {extracted_student_number}, 검증 번호: {extracted_verification_number}, 역할: {role}")

        else:
            # 일반 사용자 (PDF 검증 필수)
            if pdf_file:
                pdf_folder = os.path.join(os.path.dirname(__file__), 'pdfs')
                os.makedirs(pdf_folder, exist_ok=True)
                pdf_path = os.path.join(pdf_folder, pdf_file.filename)
                pdf_file.save(pdf_path)

                # PDF에서 이름, 학번, 검증 번호 추출
                extracted_name, extracted_student_number, extracted_verification_number = get_student_info(pdf_path)
                if not extracted_name or not extracted_student_number or not extracted_verification_number:
                    flash('PDF에서 이름, 학번, 검증 번호를 추출할 수 없습니다. 파일이 올바른지 확인해주세요.')
                    return redirect(request.url)  # PDF 검증 실패 시 회원가입 중단
            else:
                flash('PDF 파일이 필요합니다. 파일을 업로드해주세요.')
                return redirect(request.url)  # PDF 미업로드 시 회원가입 중단

            print(f"[일반 사용자] 이메일: {email}, 이름: {extracted_name}, 학번: {extracted_student_number}, 검증 번호: {extracted_verification_number}, 역할: {role}")

        # 비밀번호 해싱 및 사용자 정보 데이터베이스 저장
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        a_conn = get_a_db_connection()
        try:
            a_conn.execute(
                'INSERT INTO users (email, password, pdf_path, name, student_number, verification_number, is_verified, role) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                (email, hashed_password, pdf_path if pdf_file else None, extracted_name, extracted_student_number, extracted_verification_number, is_verified, role)
            )
            a_conn.commit()

            # 이메일 인증 메일 발송
            if is_verified == 0:
                token = generate_confirmation_token(email)
                confirm_url = url_for('confirm_email', token=token, _external=True)
                subject = "회원가입 이메일 인증 요청"
                content = f"""
                안녕하세요, {extracted_name}님 WKU HUB+ 입니다.<br>
                아래의 이메일 인증을 완료하고 저희 서비스를 이용해주세요.<br>
                <a href="{confirm_url}" style="padding:10px; background-color:#007BFF; color:white; text-decoration:none; border-radius:5px;">이메일 인증</a>
                """
                try:
                    send_email_gmail(email, subject, content)
                    flash('회원가입이 완료되었습니다! 이메일 인증을 진행해주세요.', 'success')
                except Exception as e:
                    flash(f"이메일 전송 중 오류가 발생했습니다: {e}", 'danger')
                    return redirect(url_for('home'))
            else:
                flash('회원가입이 완료되었습니다!', 'success')

            return redirect(url_for('home'))

        except sqlite3.IntegrityError:
            flash('이미 사용 중인 이메일입니다. 다른 이메일을 사용하세요.', 'warning')
            return redirect(request.url)
        finally:
            a_conn.close()

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['userName']
        password = request.form['userPassword']
        remember = 'remember' in request.form  # "아이디 기억하기" 체크박스 여부 확인

        # 데이터베이스 연결
        conn = get_a_db_connection()
        try:
            # 이메일을 기준으로 사용자 정보 조회
            user = conn.execute(
                "SELECT * FROM users WHERE email = ?",
                (email,)
            ).fetchone()

            if user and check_password_hash(user['password'], password):
                # 이메일 인증 여부 확인
                if not user['is_verified']:
                    flash('이메일 인증이 필요합니다. 이메일을 확인해주세요.', 'warning')
                    return redirect(url_for('home'))

                # 로그인 성공 처리
                response = make_response(redirect(url_for('home')))
                if remember:
                    # "아이디 기억하기" 선택 시 장기 쿠키 설정 (1년)
                    response.set_cookie('user_email', email, max_age=60 * 60 * 24 * 365)
                else:
                    # 세션 쿠키 설정
                    response.set_cookie('user_email', email)

                # 관리자 여부 확인
                if user['role'] == 'admin':
                    response.headers['Location'] = url_for('home')
                return response

            else:
                flash('잘못된 이메일 또는 비밀번호입니다.', 'danger')
                return redirect(url_for('home'))

        except Exception as e:
            flash(f'로그인 처리 중 오류가 발생했습니다: {e}', 'danger')
            return redirect(url_for('home'))

        finally:
            conn.close()

    # GET 요청일 경우 홈 페이지로 리디렉션
    return redirect(url_for('home'))

@app.route('/logout', methods=['POST'])
def logout():
    response = make_response(redirect(url_for('home')))
    response.set_cookie('user_email', '', expires=0)
    return response


# ---------------------강의실 시간표 예약 서비스 --------------------
@app.route('/building/<string:building_name>/reserve')
@login_required
def reserve_building(building_name):
    building = next((b for b in buildings if b['name'] == building_name), None)
    if not building:
        abort(404, description="Building not found")

    building_folder_path = os.path.join(os.path.dirname(__file__), 'campus_building_floors', building_name)
    if not os.path.exists(building_folder_path):
        abort(404, description="Building floor data not found")

    floors = sorted([f.replace('.json', '') for f in os.listdir(building_folder_path) if f.endswith('.json')],
                    key=lambda x: int(''.join(filter(str.isdigit, x))))
    return render_template('reserve_floors.html', building=building, floors=floors)

@app.route('/building/<string:building_name>/reserve/<string:floor_number>')
def reserve_floor(building_name, floor_number):
    building_name_decoded = urllib.parse.unquote(building_name)
    building = next((b for b in buildings if b['name'] == building_name_decoded), None)
    if not building:
        abort(404, description="Building not found")

    # 해당 건물과 층에 맞는 JSON 파일을 로드
    project_root = os.path.dirname(os.path.abspath(__file__))
    floor_json_path = os.path.join(project_root, 'campus_building_floors', building_name_decoded,
                                   f"{floor_number}.json")
    if not os.path.exists(floor_json_path):
        abort(404, description="Floor data not found")

    with open(floor_json_path, 'r', encoding='utf-8') as f:
        rooms = json.load(f)

    return render_template('reserve_floor.html', building=building, floor_number=floor_number, rooms=rooms)


@app.route('/building/<path:building_name>/floor/<string:floor_number>')
def get_floor_data(building_name, floor_number):
    building_name_decoded = urllib.parse.unquote(building_name)
    app.logger.debug(f"Decoded building name: {building_name_decoded}")

    project_root = os.path.dirname(os.path.abspath(__file__))

    # 수정된 부분: floor_number에 .json 확장자 추가
    floor_json_path = os.path.join(project_root, 'campus_building_floors', building_name_decoded,
                                   f"{floor_number}.json")

    app.logger.debug(f"Floor JSON Path: {floor_json_path}")

    if not os.path.exists(floor_json_path):
        app.logger.error(f"Floor data not found: {floor_json_path}")
        abort(404, description="Floor data not found")

    with open(floor_json_path, 'r', encoding='utf-8') as f:
        floor_data = json.load(f)

    app.logger.debug(f"Floor data loaded successfully for {building_name_decoded} {floor_number}")

    # rooms 키가 있는 경우 그대로 반환, 없는 경우 floor_data를 rooms 키의 값으로 설정
    if "rooms" in floor_data:
        return jsonify({"rooms": floor_data["rooms"]})
    return jsonify({"rooms": floor_data})


@app.route('/building/<path:building_name>/floor/<string:floor_number>/<path:room_name>', methods=['GET'])
def room_schedule(building_name, floor_number, room_name):
    # 건물 이름과 강의실 이름을 디코딩
    building_name_decoded = urllib.parse.unquote(building_name)
    room_name_decoded = urllib.parse.unquote(room_name)

    # JSON 파일 경로 설정
    project_root = os.path.dirname(os.path.abspath(__file__))
    floor_json_path = os.path.join(
        project_root, 'campus_building_floors', building_name_decoded, f"{floor_number}.json"
    )

    if not os.path.exists(floor_json_path):
        abort(404, description="Floor data not found")

    # JSON 파일 로드
    with open(floor_json_path, 'r', encoding='utf-8') as f:
        floor_data = json.load(f)

    # 강의실 정보 찾기
    rooms = floor_data.get('rooms', [])
    room = next((r for r in rooms if r['name'] == room_name_decoded), None)

    if not room:
        abort(404, description="Room not found")

    return render_template(
        'room_schedule.html', room_name=room_name_decoded,
        building_name=building_name_decoded, floor_number=floor_number
    )


@app.route('/building/<path:building_name>/floor/<string:floor_number>/<path:room_name>/<int:week>', methods=['GET'])
def get_room_schedule(building_name, floor_number, room_name, week):
    building_name_decoded = urllib.parse.unquote(building_name)
    room_name_decoded = urllib.parse.unquote(room_name)

    floor_json_path = os.path.join(
        os.path.dirname(__file__),
        'campus_building_floors',
        building_name_decoded,
        f"{floor_number}.json"
    )

    if not os.path.exists(floor_json_path):
        abort(404, description="Floor data not found")

    with open(floor_json_path, 'r', encoding='utf-8') as f:
        floor_data = json.load(f)

    room = next((r for r in floor_data.get('rooms', []) if r['name'] == room_name_decoded), None)

    if not room:
        abort(404, description="Room not found")

    # 주차별 시간표
    week_key = f"{week}주차"
    schedule = room.get(week_key, {})

    return jsonify({"schedule": schedule})


# 예약 처리 route
@app.route('/reserve', methods=['POST'])
def reserve_room():
    data = request.json
    room_name = data.get('room')
    week = data.get('week')
    day = data.get('day')
    hour = data.get('hour')
    building_name = data.get('building_name')
    floor_number = data.get('floor_number')

    user_email = request.cookies.get('user_email')
    if not user_email:
        print("사용자가 로그인하지 않았습니다.")
        return jsonify({"success": False, "message": "로그인이 필요한 서비스입니다."}), 403

    conn = get_a_db_connection()
    user = conn.execute(
        "SELECT name, student_number FROM users WHERE email = ?",
        (user_email,)
    ).fetchone()
    conn.close()

    if not user:
        print(f"사용자 정보를 찾을 수 없습니다: {user_email}")
        return jsonify({"success": False, "message": "사용자 정보를 찾을 수 없습니다."}), 404

    student_name = user['name']
    student_id = user['student_number']

    floor_json_path = os.path.join(os.path.dirname(__file__), 'campus_building_floors', building_name, f"{floor_number}.json")
    if not os.path.exists(floor_json_path):
        print(f"층 데이터가 존재하지 않습니다: {floor_json_path}")
        return jsonify({"success": False, "message": "층 데이터가 존재하지 않습니다."}), 404

    try:
        with open(floor_json_path, 'r+', encoding='utf-8') as f:
            floor_data = json.load(f)

            # Find the room
            room = next((r for r in floor_data['rooms'] if r['name'] == room_name), None)
            if not room:
                print(f"강의실을 찾을 수 없습니다: {room_name}")
                return jsonify({"success": False, "message": "강의실을 찾을 수 없습니다."}), 404

            week_key = f"{week}주차"
            if week_key not in room:
                room[week_key] = {}

            if day not in room[week_key]:
                room[week_key][day] = {}

            existing_reservation = room[week_key][day].get(hour)
            if existing_reservation:
                if isinstance(existing_reservation, dict):
                    status = existing_reservation.get('status', '')
                else:
                    status = existing_reservation  # 문자열일 경우 그대로 사용
                if status == "예약 완료":
                    print(f"이미 예약된 시간입니다: {building_name} {room_name} {week}주차 {day} {hour}")
                    return jsonify({"success": False, "message": "이미 예약된 시간입니다."}), 400

            # 예약 처리 (학생 정보 추가)
            room[week_key][day][hour] = {
                "status": "대기 중",
                "student_name": student_name,
                "student_id": student_id
            }

            # JSON 파일 업데이트
            f.seek(0)
            json.dump(floor_data, f, ensure_ascii=False, indent=4)
            f.truncate()

            # 데이터베이스 저장 데이터 구성
            reservation_data = {
                "room": room_name,
                "week": week,
                "day": day,
                "hour": hour,
                "building_name": building_name,
                "floor_number": floor_number,
                "student_name": student_name,
                "student_id": student_id,
                "email": user_email
            }

            # C_database.db에 저장
            print(f"예약 데이터를 저장합니다: {reservation_data}")
            save_reservation_to_c_database(reservation_data, status='대기 중')

    except Exception as e:
        print(f"예약 처리 중 오류가 발생했습니다: {e}")
        app.logger.error(f"Error processing reservation: {e}")
        return jsonify({"success": False, "message": "예약 처리 중 오류가 발생했습니다."}), 500

    print(f"예약이 성공적으로 처리되었습니다: {reservation_data}")
    return jsonify({"success": True, "message": "예약이 완료되었습니다."})


# 예약 가능한 시간 계산 함수
def get_available_times(room_data, week):
    all_hours = [f"{hour}:00" for hour in range(9, 20)]
    available_times = {day: all_hours.copy() for day in ["월요일", "화요일", "수요일", "목요일", "금요일"]}

    # 주차별 예약 데이터 확인
    week_key = f"{week}주차"
    if week_key not in room_data:
        return available_times

    unavailable_times = room_data.get(week_key, {})

    # 예약 불가능한 시간을 제외하고 예약 가능한 시간만 남김
    for day, hours in unavailable_times.items():
        for hour, status in hours.items():
            if status.get("status") == "예약 완료" and hour in available_times[day]:
                available_times[day].remove(hour)

    return available_times


@app.route('/professor_schedule/<string:professor_name>/<int:week>', methods=['GET'])
def get_professor_schedule(professor_name, week):
    try:
        with open(PROFESSOR_SCHEDULES_JSON_PATH, 'r', encoding='utf-8') as f:
            schedules = json.load(f)

        professor_schedule = schedules.get(professor_name, {}).get(f"{week}주차", {})
        for day, hours in professor_schedule.items():
            for hour, status in hours.items():
                if isinstance(status, dict):
                    professor_schedule[day][hour] = status.get("status", "예약 가능")

        return jsonify({"schedule": professor_schedule})
    except Exception as e:
        return jsonify({"error": f"데이터 로드 실패: {e}"}), 500


# -----------------------------------------관리자 페이지-----------------------------------------
@app.route('/admin')
@admin_required
def admin_dashboard():
    return render_template('admin_dashboard.html')
    # return render_template('admin_dashboard.html')

def add_email_column_to_reservations():
    conn = sqlite3.connect(C_DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("ALTER TABLE reservations ADD COLUMN email TEXT NOT NULL DEFAULT ''")
    conn.commit()
    conn.close()

if __name__ == '__main__':
    with app.app_context():
        add_verification_number_column()
        initialize_a_database()  # A 데이터베이스 초기화
        initialize_b_database()  # B 데이터베이스 초기화
        initialize_reservations_table()  # 데이터베이스 초기화
        initialize_professor_appointments_table()  # 테이블 초기화
    app.run(host='0.0.0.0', port=2001, debug=True)
