# 프로젝트 OCR 설치 번거로움을 위해 사용되는 파일

# pip install flask pytesseract pdf2image pillow

import os
import pytesseract
from PIL import Image

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
TESSDATA_DIR = os.path.join(PROJECT_ROOT, 'tools', 'tesseract', 'tessdata')

pytesseract.pytesseract.tesseract_cmd = os.path.join(PROJECT_ROOT, 'tools', 'tesseract', 'tesseract.exe')
custom_config = f'--tessdata-dir "{TESSDATA_DIR}"'

def init_tesseract():
    """Tesseract 초기화 및 한국어 데이터 존재 확인"""
    if not os.path.exists(TESSDATA_DIR):
        os.makedirs(TESSDATA_DIR)

    kor_traineddata = os.path.join(TESSDATA_DIR, 'kor.traineddata')
    if not os.path.exists(kor_traineddata):
        # 자동 다운로드 로직
        import urllib.request
        print("한국어 데이터 다운로드 중...")
        url = 'https://github.com/tesseract-ocr/tessdata/raw/main/kor.traineddata'
        urllib.request.urlretrieve(url, kor_traineddata)
        print("다운로드 완료!")

def ocr_image(image_path):
    """이미지에서 텍스트 추출"""
    image = Image.open(image_path)
    text = pytesseract.image_to_string(
        image,
        lang='kor',
        config=custom_config
    )
    return text

# 프로그램 시작 시 초기화
if __name__ == '__main__':
    try:
        init_tesseract()
        # 이미지 처리 코드...
    except Exception as e:
        print(f"오류 발생: {str(e)}")  # 회원가입 누르면 Windows PowerShell
