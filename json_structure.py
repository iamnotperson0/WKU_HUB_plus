import os
import json


def fix_json_structure():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    json_dir = os.path.join(current_dir, 'campus_building_floors')

    for building_folder in os.listdir(json_dir):
        building_path = os.path.join(json_dir, building_folder)
        if os.path.isdir(building_path):
            for file in os.listdir(building_path):
                if file.endswith('.json'):
                    file_path = os.path.join(building_path, file)
                    with open(file_path, 'r+', encoding='utf-8') as f:
                        try:
                            data = json.load(f)
                        except json.JSONDecodeError as e:
                            print(f"JSON 디코딩 오류 발생: {file_path} - {e}")
                            continue

                        modified = False  # 변경 여부 추적

                        for room in data.get('rooms', []):
                            for week, days in room.items():
                                if week == "name":
                                    continue
                                for day, times in days.items():
                                    if not isinstance(times, dict):
                                        # 만약 day의 값이 dict가 아니라면, 시간을 추가
                                        room[week][day] = {}
                                        modified = True

                                    if day == "Wednesday" and "10:00" not in room[week][day]:
                                        room[week][day]["10:00"] = {"status": "Available for reservation"}
                                        modified = True

                        if modified:
                            f.seek(0)
                            json.dump(data, f, ensure_ascii=False, indent=4)
                            f.truncate()
                            print(f"수정된 파일: {file_path}")
                        else:
                            print(f"수정할 필요 없음: {file_path}")


if __name__ == '__main__':
    fix_json_structure()
    print("JSON 데이터 구조 수정 완료.")
