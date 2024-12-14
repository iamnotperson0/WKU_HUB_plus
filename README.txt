WKU INFO HUB+
프로젝트 개요
WKU INFO HUB+는 강의실 예약 및 교수님과의 면담 예약 서비스를 제공하는 시스템입니다. 학생과 교수님 간의 효율적인 소통과 공간 관리를 목표로 개발되었습니다.

개발 환경
Back-End: Flask, Python
Front-End: HTML, CSS, JavaScript
Database: JSON 파일을 사용하여 데이터 관리
UI 통합: flaskPro 프로젝트에서 제공한 HTML UI를 SETP 프로젝트에 통합

주요 기능

맵
네비게이션, 내 위치 GPS

강의실 예약 관리
강의실의 예약 가능/불가능한 시간대를 시각적으로 표시
예약 및 취소 기능 제공
로그인 여부에 따라 접근 제어 (/building/<building_name>/service, /building/<building_name>/reserve)

교수님 면담 예약 관리
각 교수님의 면담 스케줄을 동적으로 표시
예약 가능/불가능한 시간대를 시각적으로 제공
예약 링크의 활성화 및 비활성화 상태 동적 관리
로그인 없이 접근 가능 (/building/<building_name>/professor/<professor_name>)

데이터 관리
교수님 데이터는 data.py에서 관리
각 교수님의 스케줄은 professor_schedules.json 파일에서 관리
스케줄과 교수님 데이터를 동적으로 연동

사용 방법
강의실 예약
/building/<building_name>/floor/<floor_number>/<room_name> 경로로 접속하여 강의실 시간표 확인
사용 가능한 시간대를 선택하여 예약 진행
예약 시 관리자 계정에서 허가/거부 -> 사용자한테 여부 메일 전송

교수님 면담 예약
/building/<building_name>/professor/<professor_name> 경로로 접속하여 교수님 스케줄 확인
예약 가능한 시간대를 선택하여 예약 진행
예약 시 교수님께 이메일 전송-> 허가/거부 선택 ->사용자한테 여부 메일 전송

회원가입
OCR로 원광대PDF 내용 추출, 이메일 인증(인증메일 발송)

로그인
강의실 예약 관련 서비스(/service, /reserve)는 로그인 후에만 이용 가능
로그인하지 않을 경우 "로그인이 필요한 서비스입니다." 팝업 메시지 표시

역할 분담
김*희: 잘료 수집 및 보조
최*진: 풀스택
조*연: 풀스택
황*준: 풀스택

자세한건 ppt로 확인
