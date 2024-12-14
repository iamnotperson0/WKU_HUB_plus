import json
import os

insert_info = {
    'Dr. Kim': {
        "월요일": {
            "1교시": {"subject": "컴퓨터 프로그래밍", "room": "101"},
            "3교시": {"subject": "자료 구조", "room": "102"}
        },
        "수요일": {
            "2교시": {"subject": "알고리즘", "room": "103"},
            "4교시": {"subject": "인공지능", "room": "104"}
        }
    },
    'Dr. Park': {
        "화요일": {
            "1교시": {"subject": "운영체제", "room": "201"},
            "3교시": {"subject": "컴퓨터 구조", "room": "202"}
        }
    }
}


current_file_name = os.path.splitext(os.path.basename(__file__))[0]
output_directory = os.path.join(os.path.dirname(__file__), f"{current_file_name}_data")

os.makedirs(output_directory, exist_ok=True)

json_file_path = os.path.join(output_directory, 'professor_schedules.json')

with open(json_file_path, 'w', encoding='utf-8') as f:
    json.dump(insert_info, f, ensure_ascii=False, indent=4)

print(f"파일이 생성되었습니다: {json_file_path}")