import os
import platform
import re
import requests
import uuid
import time
import json
from pdf2image import convert_from_path
from PIL import Image
import cv2
import numpy as np

api_url = 'https://j62hf4827r.apigw.ntruss.com/custom/v1/36252/419b50901813e8d3bd6ae36720bd524ee6bcf6fa998bddef0be1771227c6ec85/general'
secret_key = 'dklWWHdaeFZsRmNybk11eEFTUUFFa3pnUHJ5RkhGWlQ='

#pdf_path = r'C:\Users\jdah5454\Desktop\dsf\test\pdfs\황병준-국문-재학증명서-202311021152.pdf'

name_patterns = [
    r"성\s*[_\s]*(명|병)\s*[:：]?\s*([가-힣]+)",  # 공백 없이 한글만 캡처
    r"성\s*[:：]?\s*([가-힣]+)",                # 공백 없이 한글만 캡처
]


student_number_patterns = [
    r"학\s*[._\s\-]*(번|먼)\s*[:：]?\s*([0-9\-]+)",
    r"학\s*번\s*[:：]?\s*([0-9\-]+)",
    r"학\s*\n\s*번\s*[:：]?\s*([0-9\-]+)",  # 줄바꿈
    r"학\s*번\s*\(\s*([0-9\-]+)\s*\)",  # 괄호
]


verification_number_patterns = [
    r"문\s*서\s*확\s*인\s*번\s*호\s*[:：]?\s*([A-Z0-9\-\/]+)",
    r"검증\s*[_\s]*(번호|코드)\s*[:：]?\s*([A-Z0-9\-]+)",
    r"Verification\s*Number\s*[:：]?\s*([A-Z0-9\-]+)",
]

def sanitize_text(text):
    if text:
        text = text.replace('\n', ' ').replace('\r', ' ')
        return re.sub(r'\s+', ' ', text).strip()
    return text

def get_student_info(pdf_path):
    extracted_name = None
    extracted_student_number = None
    extracted_verification_number = None

    try:
        # 운영 체제에 따라 poppler_path 설정
        if platform.system() == "Windows":
            poppler_path = os.path.join(os.getcwd(), 'tools', 'poppler', 'bin')
            images = convert_from_path(pdf_path, dpi=300, poppler_path=poppler_path)
        else:
            images = convert_from_path(pdf_path, dpi=300)

        if not images:
            print("이미지 변환 실패")
            return None, None, None

        # 모든 페이지 처리
        for page_num, page_image in enumerate(images, start=1):
            print(f"[INFO] 페이지 {page_num} OCR 처리 중...")
            page_image_cv = cv2.cvtColor(np.array(page_image), cv2.COLOR_RGB2BGR)

            image_path = f'page_{page_num}.jpg'
            cv2.imwrite(os.path.join(os.getcwd(), image_path), page_image_cv)

            # OCR 수행
            ocr_text = ocr_naver_api(image_path)
            print(f"페이지 {page_num} OCR 결과:")
            print(ocr_text)

            # 문서확인 번호 추출
            if not extracted_verification_number:
                for pattern in verification_number_patterns:
                    match = re.search(pattern, ocr_text)
                    if match:
                        extracted_verification_number = match.group(1).strip()
                        print(f"검증 번호 추출 성공: {extracted_verification_number}")
                        break

            # 이름 추출
            if not extracted_name:
                for pattern in name_patterns:
                    match = re.search(pattern, ocr_text)
                    if match:
                        extracted_name = match.group(2).strip().replace(' ', '')
                        print(f"이름 추출 성공: {extracted_name}")
                        break

            # 학번 추출
            if not extracted_student_number:
                for pattern in student_number_patterns:
                    match = re.search(pattern, ocr_text)
                    if match:
                        extracted_student_number = match.group(2).strip().replace('-', '')
                        print(f"학번 추출 성공: {extracted_student_number}")
                        break

            # 모든 정보 추출 시 중단
            if extracted_name and extracted_student_number and extracted_verification_number:
                break

        if extracted_name and extracted_student_number and extracted_verification_number:
            return extracted_name, extracted_student_number, extracted_verification_number
        else:
            print("이름, 학번 또는 검증 번호를 추출할 수 없습니다.")
            return extracted_name, extracted_student_number, extracted_verification_number

    except Exception as e:
        print(f"[ERROR] OCR 작업 중 오류가 발생했습니다: {e}")
        return None, None, None

def ocr_naver_api(image_path):
    # 이미지를 JPEG 포맷으로 변환하여 바이너리 데이터로 변환
    with open(image_path, 'rb') as f:
        image_data = f.read()

    request_json = {
        'images': [
            {
                'format': 'jpg',
                'name': os.path.basename(image_path)
            }
        ],
        'requestId': str(uuid.uuid4()),
        'version': 'V2',
        'timestamp': int(round(time.time() * 1000))
    }

    payload = {'message': json.dumps(request_json).encode('UTF-8')}
    files = [
        ('file', (os.path.basename(image_path), image_data, 'image/jpeg'))
    ]
    headers = {
        'X-OCR-SECRET': secret_key
    }

    try:
        response = requests.post(api_url, headers=headers, data=payload, files=files)
        if response.status_code == 200:
            result = response.json()
            # OCR 결과에서 텍스트 추출
            text = ""
            for field in result.get('images', [])[0].get('fields', []):
                text += field.get('inferText', '') + '\n'
            return text.strip()
        else:
            print(f"[ERROR] Naver OCR API 호출 실패: {response.status_code}, {response.text}")
            return ""
    except Exception as e:
        print(f"[ERROR] Naver OCR API 호출 중 오류 발생: {e}")
        return ""

# if __name__ == '__main__':
#     pdf_path = os.path.join(os.getcwd(), r'C:\Users\jdah5454\Desktop\dsf\test\pdfs\황병준-국문-재학증명서-202311021152.pdf')
#     extracted_name, extracted_student_number, extracted_verification_number = get_student_info(pdf_path)
#
#     if extracted_name:
#         print("이름:", extracted_name)
#     else:
#         print("이름을 찾을 수 없습니다.")
#
#     if extracted_student_number:
#         print("학번:", extracted_student_number)
#     else:
#         print("학번을 찾을 수 없습니다.")
#
#     if extracted_verification_number:
#         print("검증 번호:", extracted_verification_number)
#     else:
#         print("검증 번호를 찾을 수 없습니다.")
