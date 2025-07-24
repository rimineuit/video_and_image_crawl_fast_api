#!/usr/bin/env python3
"""
image2gemini_upload.py
Tải ảnh 🖼  Upload vào Gemini ➜ In JSON ➜ Xoá file.
"""

import os
import sys
import uuid
import requests
from pathlib import Path
from mimetypes import guess_type
import json

TMP_DIR = Path("/tmp/my_images")
TMP_DIR.mkdir(parents=True, exist_ok=True)

def download_image(url: str) -> Path:
    """Tải ảnh từ URL về TMP_DIR, trả Path."""
    ext = os.path.splitext(url)[-1] or ".jpg"
    filename = f"{uuid.uuid4()}{ext}"
    out_path = TMP_DIR / filename

    r = requests.get(url, timeout=30)
    if not r.ok:
        sys.exit("Lỗi tải ảnh")

    with out_path.open("wb") as f:
        f.write(r.content)

    return out_path

def upload_gemini(file_path: Path, gemini_api_key) -> dict:
    """Upload ảnh lên Gemini ➜ trả JSON phản hồi."""
    mime_type = guess_type(file_path.name)[0] or "image/jpeg"
    with file_path.open("rb") as f:
        upload_url = f"https://generativelanguage.googleapis.com/upload/v1beta/files?key={gemini_api_key}"
        r = requests.post(
            upload_url,
            files={"file": (file_path.name, f, mime_type)},
            timeout=60,
        )
    r.raise_for_status()
    return r.json()

def main():
    if len(sys.argv) < 3:
        sys.exit("Cách dùng: python image2gemini_upload.py <gemini_api_key> <Image_URL>")

    img_url = sys.argv[2].strip()
    img_file = download_image(img_url)
    gemini_api_key = sys.argv[1].strip()
    try:
        resp = upload_gemini(img_file, gemini_api_key)
        print(json.dumps(resp, indent=2, ensure_ascii=False))
    finally:
        if img_file.exists():
            img_file.unlink(missing_ok=True)

if __name__ == "__main__":
    main()
