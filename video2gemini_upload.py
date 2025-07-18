#!/usr/bin/env python3
"""
video2gemini_upload.py
Tải video ▶️  Upload vào Gemini ▶️  In JSON upload ▶️  Xoá file.
"""

import os
import sys
import uuid
import subprocess
from pathlib import Path
import requests
import json



TMP_DIR = Path("tmp/my_videos")
TMP_DIR.mkdir(parents=True, exist_ok=True)

def download_video(url: str) -> Path:
    """Dùng yt-dlp tải video YouTube (đã merge audio) về TMP_DIR, trả Path."""
    out_path = TMP_DIR / f"{uuid.uuid4()}.mp4"
    cmd = [
        "yt-dlp",
        "-f", "b",
        "-o", str(out_path),
        url,
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode:
        print(res.stderr)
        sys.exit("yt-dlp thất bại")
    if not out_path.exists():
        sys.exit("Không tìm thấy file sau khi tải")
    return out_path

def upload_gemini(file_path: Path, api_key: str) -> dict:
    """Upload video lên Gemini ➜ trả JSON phản hồi (chỉ upload)."""
    with file_path.open("rb") as f:
        upload_url = f"https://generativelanguage.googleapis.com/upload/v1beta/files?key={api_key}"
        r = requests.post(
            upload_url,
            files={"file": (file_path.name, f, "video/mp4")},
            timeout=120,
        )
    r.raise_for_status()
    return r.json()          # {'file': {...}}

def main():
    if len(sys.argv) < 3:
        sys.exit("Cách dùng: python video2gemini_upload.py <gemini_api_key> <YouTube_URL>")
    gemini_api_key = sys.argv[1].strip()
    yt_url = sys.argv[2].strip()
    video  = download_video(yt_url)

    try:
        upload_resp = upload_gemini(video, gemini_api_key)
        print(json.dumps(upload_resp, indent=2, ensure_ascii=False))
    finally:
        if video.exists():
            video.unlink(missing_ok=True)

if __name__ == "__main__":
    main()
