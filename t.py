import json

def list_unique_music_ids_with_eer_filter(file_path, eer_threshold=1.0):
    with open(file_path, "r", encoding="utf-8") as f:
        video_data = json.load(f)

    # Lọc video có eer_score >= 1
    filtered_videos = [v for v in video_data if v.get("eer_score", 0) >= eer_threshold]

    # Tập hợp các music.id duy nhất
    music_ids = set()
    for item in filtered_videos:
        music = item.get("music", {})
        music_id = music.get("id")
        if music_id:
            music_ids.add(music_id)

    # Hiển thị kết quả
    print(f"Tổng số video có eer_score >= {eer_threshold}: {len(filtered_videos)}")
    print(f"Tổng số music.id duy nhất: {len(music_ids)}\n")

    for idx, mid in enumerate(sorted(music_ids), 1):
        print(f"{idx}. {mid}")

if __name__ == "__main__":
    list_unique_music_ids_with_eer_filter("tiktok_video_data.json", eer_threshold=2.0)
