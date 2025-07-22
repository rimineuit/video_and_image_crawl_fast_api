import os
import json

def calc_eer(hearts, comments, shares, saves, plays):
    if plays == 0:
        return 0
    return ((hearts * 1 + comments * 5 + shares * 7 + saves * 10) / plays) * 100

results = []

folder_path = "storage/datasets/default"  # thay bằng đường dẫn thực tế

for filename in os.listdir(folder_path):
    if filename.endswith(".json"):
        file_path = os.path.join(folder_path, filename)
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

            eer = calc_eer(
                hearts=data.get("hearts", 0),
                comments=data.get("comments", 0),
                shares=data.get("shares", 0),
                saves=data.get("saves", 0),
                plays=data.get("plays", 1),  # tránh chia cho 0
            )

            results.append({
                "video_url": data.get("video_url"),
                "eer": eer,
                "hearts": data.get("hearts", 0),
                "comments": data.get("comments", 0),
                "shares": data.get("shares", 0),
                "saves": data.get("saves", 0),
                "views": data.get("plays", 0),
            })

# # Sắp xếp giảm dần theo EER
# results.sort(key=lambda x: x["eer"], reverse=True)

# # In ra kết quả
# for item in results:
#     print(f"{item['video_url']}: EER = {item['eer']:.4f}%")

i = 0
for item in results:
    if item['eer'] > 2:
        i+= 1
print(f"\nTổng số video có EER > 2: {i}")
