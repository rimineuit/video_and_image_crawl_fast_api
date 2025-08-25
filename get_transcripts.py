# get_transcripts.py
import json
import subprocess
import os
import sys
from pathlib import Path

INPUT_FILE = "trend_videos.json"
OUTPUT_DIR = Path("transcripts")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def run(cmd):
    print("Running:", " ".join(cmd))
    return subprocess.run(cmd, check=True, capture_output=True, text=True)

# Đảm bảo yt-dlp có trong môi trường hiện tại
try:
    run([sys.executable, "-m", "yt_dlp", "--version"])
except subprocess.CalledProcessError:
    print("[INFO] Installing yt-dlp into current venv...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-U", "yt-dlp"])

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    videos = json.load(f)

for v in videos:
    video_id = v["video_id"]
    url = v["url"]

    # Đích: transcripts/<video_id>.vtt
    outtmpl = str(OUTPUT_DIR / f"{video_id}.%(ext)s")

    # Thử phụ đề người đăng (preferred)
    cmd = [
        sys.executable, "-m", "yt_dlp",
        "--skip-download",
        "--write-sub",
        "--sub-lang", "vie-VN",
        "--sub-format", "vtt",
        "-o", outtmpl,
        url
    ]

    try:
        run(cmd)
        print(f"[OK] Saved: {OUTPUT_DIR / (video_id + '.vtt')}")
        continue
    except subprocess.CalledProcessError as e:
        print(f"[WARN] No publisher subtitles or error. stderr:\n{e.stderr}")

    # Fallback: auto subtitles nếu có
    fallback_cmd = [
        sys.executable, "-m", "yt_dlp",
        "--skip-download",
        "--write-auto-sub",
        "--sub-lang", "vie-VN",
        "--sub-format", "vtt",
        "-o", outtmpl,
        url
    ]
    try:
        run(fallback_cmd)
        print(f"[OK][auto] Saved: {OUTPUT_DIR / (video_id + '.vtt')}")
    except subprocess.CalledProcessError as e:
        print(f"[FAIL] Could not get subtitles for {video_id}. stderr:\n{e.stderr}")
