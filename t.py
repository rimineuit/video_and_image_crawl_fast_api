import os
import json

def load_all_json_data(folder_path="./storage/datasets/default") -> list[dict]:
    data_list = []

    for filename in os.listdir(folder_path):
        if filename.endswith(".json") and filename != "__metadata__.json":
            file_path = os.path.join(folder_path, filename)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    data_list.append(data)
            except Exception as e:
                print(f"Lỗi khi đọc file {filename}: {e}")

    return data_list

data = load_all_json_data()
print(json.dumps(data, indent=2, ensure_ascii=False))