import os
 # 보안키
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'sdjfklj347892djhfsdmfhsdk73894'
#
#
# import fitz  # PyMuPDF
#
# # PDF 파일 열기
# pdf_path = r"C:\Users\jdah5454\Desktop\dsf\test\pdfs\황병준-국문-재학증명서-202311021152.pdf"
# doc = fitz.open(pdf_path)
#
# # 첫 번째 페이지 가져오기
# page = doc.load_page(0)
#
# # 텍스트 블록들 가져오기
# text_blocks = page.get_text("blocks")
#
# # 각 블록의 좌표 출력
# for block in text_blocks:
#     x0, y0, x1, y1, text, _, _ = block
#     print(f"텍스트: {text}, 좌표: ({x0}, {y0}), ({x1}, {y1})")
# requirements.txt