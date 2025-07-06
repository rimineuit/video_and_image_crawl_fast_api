from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import subprocess
import json
import sys
import os
import re

app = FastAPI()
env = os.environ.copy()

env["PYTHONIOENCODING"] = "utf-8"
env["PYTHONUTF8"] = "1"
        
class VideoBody(BaseModel):
    url: str
    
    
@app.middleware("http")
async def log_request(request: Request, call_next):
    body = await request.body()
    print("📥 RAW request body:", body.decode("utf-8", errors="replace"))
    response = await call_next(request)
    return response

@app.post("/youtube/upload")
async def youtube_upload(body: VideoBody):
    # Làm sạch URL khỏi dấu ; nếu có
    clean_url = body.url.strip().rstrip(';')

    # Đường dẫn tuyệt đối tới script (nếu cần)
    script_path = "video2gemini_upload.py"  # hoặc /app/video2gemini_uploads.py nếu dùng Railway

    cmd = ["python", script_path, clean_url]
    print("🔧 subprocess args:", cmd)

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=900,
            env=env
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="⏱️ Quá thời gian xử lý")

    if proc.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail=f"yt-dlp/Gemini error:\n{proc.stderr}"
        )

    # Tìm đoạn JSON trong stdout
    import re
    try:
        json_text_match = re.search(r"{[\s\S]+}", proc.stdout)
        if not json_text_match:
            raise ValueError("Không tìm thấy đoạn JSON hợp lệ trong stdout")
        json_text = json_text_match.group(0)
        result_json = json.loads(json_text)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Không parse được JSON từ script: {e}\nSTDOUT:\n{proc.stdout}"
        )

    return result_json


class ImageBody(BaseModel):
    url: str

@app.post("/image/upload")
async def image_upload(body: ImageBody):
    clean_url = body.url.strip().rstrip(';')

    # Tùy theo vị trí file script
    script_path = "image2gemini_upload.py"  # hoặc "/app/image2gemini_upload.py"
    cmd = [sys.executable, script_path, clean_url]
    print("🖼️ subprocess args:", cmd)

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
            env=os.environ  # hoặc bạn có thể tùy chỉnh biến môi trường ở đây
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="⏱️ Xử lý quá thời gian")

    if proc.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi khi chạy script:\n{proc.stderr}"
        )

    try:
        json_text_match = re.search(r"{[\s\S]+}", proc.stdout)
        if not json_text_match:
            raise ValueError("Không tìm thấy JSON hợp lệ trong stdout")
        json_text = json_text_match.group(0)
        result_json = json.loads(json_text)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi parse JSON từ output: {e}\nSTDOUT:\n{proc.stdout}"
        )

    return result_json

class TikTokBody(BaseModel):
    url: str
    browser_type: str = "firefox"  # Mặc định là Firefox, có thể thay đổi
    
@app.post("/tiktok/get_video_links_and_metadata")
async def tiktok_get_video_links_and_metadata(body: TikTokBody):
    clean_url = body.url.strip().rstrip(';')
    browser_type = body.browser_type.strip().lower()
    script_path = "get_tiktok_video_links_and_metadata.py"
    cmd = [sys.executable, script_path, clean_url, browser_type]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=900,
            encoding="utf-8",
            env=env
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="⏱️ Quá thời gian xử lý")
    
    if proc.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi khi chạy script:\n{proc.stderr}"
        )
        
    try:
        # Lấy phần output sau chữ "Result"
        result_start = proc.stdout.find("Result:")
        if result_start == -1:
            raise ValueError("Không tìm thấy đoạn 'Result' trong stdout")

        json_part = proc.stdout[result_start:]  # phần sau "Result"
        print("🔍 JSON part:", json_part)
        # Tìm JSON mảng đầu tiên bắt đầu bằng [ và kết thúc bằng ]
        json_match = re.search(r"\[\s*{[\s\S]*?}\s*\]", json_part)
        
        if not json_match:
            raise ValueError("Không tìm thấy JSON hợp lệ trong stdout")

        json_text = json_match.group(0)
        result_json = json.loads(json_text)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi parse JSON từ output: {e}\n\n--- STDOUT ---\n{proc.stdout}"
        )
    return result_json


