from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import subprocess
import json
import sys
import os
import re
from fastapi.responses import Response
import tempfile
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Literal, Optional
app = FastAPI()
env = os.environ.copy()

env["PYTHONIOENCODING"] = "utf-8"
env["PYTHONUTF8"] = "1"
        
class VideoBody(BaseModel):
    url: str
    gemini_api_key: str
    
@app.middleware("http")
async def log_request(request: Request, call_next):
    body = await request.body()
    print("📥 RAW request body:", body.decode("utf-8", errors="replace"))
    response = await call_next(request)
    return response

@app.post("/video/upload")
async def youtube_upload(body: VideoBody):
    # Làm sạch URL khỏi dấu ; nếu có
    clean_url = body.url.strip().rstrip(';')
    gemini_api_key = body.gemini_api_key.strip()
    # Đường dẫn tuyệt đối tới script (nếu cần)
    script_path = "video2gemini_upload.py"  # hoặc /app/video2gemini_uploads.py nếu dùng Railway

    cmd = ["python", script_path, gemini_api_key ,clean_url]
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
    gemini_api_key: str

@app.post("/image/upload")
async def image_upload(body: ImageBody):
    clean_url = body.url.strip().rstrip(';')
    gemini_api_key = body.gemini_api_key.strip()
    # Tùy theo vị trí file script
    script_path = "image2gemini_upload.py"  # hoặc "/app/image2gemini_upload.py"
    cmd = [sys.executable, script_path, gemini_api_key, clean_url]
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

from typing import List

class TikTokBody(BaseModel):
    url: str  # Danh sách các URL TikTok
    browser_type: str = "chromium"  # Mặc định là Firefox
    label: str = "newest"  # Nhãn mặc định
    max_items: int = 30  # Số lượng video tối đa mỗi trang
    get_comments: str = "False"  # Mặc định không lấy bình luận

@app.post("/tiktok/get_video_links_and_metadata")
async def tiktok_get_video_links_and_metadata(body: TikTokBody):
    label = body.label.strip().lower()
    browser_type = body.browser_type.strip().lower()

    # Nối các URL thành một chuỗi cách nhau bởi dấu cách
    clean_url = body.url.strip()
    max_items = str(body.max_items).strip()
    script_path = "get_tiktok_video_links_and_metadata.py"
    get_comments = body.get_comments
    cmd = [sys.executable, script_path, browser_type, label, max_items, get_comments, clean_url]
    print(cmd)
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
        result_start = proc.stdout.find("Result:\n")
        if result_start == -1:
            raise ValueError("Không tìm thấy đoạn 'Result' trong stdout")

        json_part = proc.stdout[result_start:]  # phần sau "Result"
        # Tìm JSON mảng đầu tiên bắt đầu bằng [ và kết thúc bằng ]
        json_match = re.search(r"\[\s*{[\s\S]*?}\s*\]", json_part)
        
        if not json_match:
            raise ValueError("Không tìm thấy JSON hợp lệ trong stdout")

        json_text = json_match.group(0).replace("\n", "")
        result_json = json.loads(json_text)


    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi parse JSON từ output: {e}\n\n--- STDOUT ---\n{proc.stdout}"
        )
    return result_json

class TikTokCrawlAdsRequest(BaseModel):
    limit: str = '10'
@app.post("/tiktok/crawl_ads")
def crawl_ads(body: TikTokCrawlAdsRequest):
    limit = body.limit
    cmd = [sys.executable, "playwright_tiktok_ads.py", str(limit)]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=900,
            env=env,
            encoding='utf-8'
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
        result_start = proc.stdout.find("Result:\n")
        if result_start == -1:
            raise ValueError("Không tìm thấy đoạn 'Result' trong stdout")

        json_part = proc.stdout[result_start:]  # phần sau "Result"
        # Tìm JSON mảng đầu tiên bắt đầu bằng [ và kết thúc bằng ]
        json_match = re.search(r"\[\s*{[\s\S]*?}\s*\]", json_part)
        
        if not json_match:
            raise ValueError("Không tìm thấy JSON hợp lệ trong stdout")

        json_text = json_match.group(0).replace("\n", "")
        result_json = json.loads(json_text)


    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi parse JSON từ output: {e}\n\n--- STDOUT ---\n{proc.stdout}"
        )
    return result_json

class MetadataAdsRequest(BaseModel):
    urls: List[str]  # Danh sách các URL TikTok
    
@app.post("/tiktok/get_metadata_ads")
def get_metadata_ads():
    cmd = [sys.executable, "get_meta_data_video.py"]
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
            detail=f"Lỗi khi chạy script:\n{proc.stderr}"
        )
    try:
        # Lấy phần output sau chữ "Result"
        result_start = proc.stdout.find("Result:\n")
        if result_start == -1:
            raise ValueError("Không tìm thấy đoạn 'Result' trong stdout")

        json_part = proc.stdout[result_start:]  # phần sau "Result"
        # Tìm JSON mảng đầu tiên bắt đầu bằng [ và kết thúc bằng ]
        json_match = re.search(r"\[\s*{[\s\S]*?}\s*\]", json_part)
        
        if not json_match:
            raise ValueError("Không tìm thấy JSON hợp lệ trong stdout")

        json_text = json_match.group(0).replace("\n", "")
        result_json = json.loads(json_text)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi parse JSON từ output: {e}\n\n--- STDOUT ---\n{proc.stdout}"
        )
    return result_json

class MusicUrl(BaseModel):
    urls: str  # Danh sách các URL TikTok
    
@app.post("/tiktok/get_audio_use_count")
def get_audio_use_count(body: MusicUrl):
    url = body.urls.strip().rstrip(';')
    if not url:
        raise HTTPException(status_code=400, detail="URL không được để trống")
    cmd = [sys.executable, "get_audio_use_count.py", url]
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
            detail=f"Lỗi khi chạy script:\n{proc.stderr}"
        )
    try:
        # Lấy phần output sau chữ "Result"
        result_start = proc.stdout.find("Result:\n")
        if result_start == -1:
            raise ValueError("Không tìm thấy đoạn 'Result' trong stdout")
        json_part = proc.stdout[result_start:]  # phần sau "Result"
        # Tìm JSON mảng đầu tiên bắt đầu bằng [ và kết thúc bằng ]
        json_match = re.search(r"\{\s*[\s\S]*?\s*\}", json_part)
        if not json_match:
            raise ValueError("Không tìm thấy JSON hợp lệ trong stdout")
        json_text = json_match.group(0).replace("\n", "")
        result_json = json.loads(json_text)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi parse JSON từ output: {e}\n\n--- STDOUT ---\n{proc.stdout}"
        )
    return result_json


class Hashtag(BaseModel):
    hashtag: str  # Danh sách các URL TikTok
    
@app.post("/tiktok/get_hashtag_use_count")
def get_hashtag_use_count(body: Hashtag):
    hashtag = body.hashtag.strip().rstrip(';')
    if not hashtag:
        raise HTTPException(status_code=400, detail="URL không được để trống")
    cmd = [sys.executable, "get_hashtag_use_count.py", hashtag]
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
            detail=f"Lỗi khi chạy script:\n{proc.stderr}"
        )
    try:
        # Lấy phần output sau chữ "Result"
        result_start = proc.stdout.find("Result:\n")
        if result_start == -1:
            raise ValueError("Không tìm thấy đoạn 'Result' trong stdout")
        json_part = proc.stdout[result_start:]  # phần sau "Result"
        # Tìm JSON mảng đầu tiên bắt đầu bằng [ và kết thúc bằng ]
        json_match = re.search(r"\{\s*[\s\S]*?\s*\}", json_part)
        if not json_match:
            raise ValueError("Không tìm thấy JSON hợp lệ trong stdout")
        json_text = json_match.group(0).replace("\n", "")
        result_json = json.loads(json_text)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi parse JSON từ output: {e}\n\n--- STDOUT ---\n{proc.stdout}"
        )
    return result_json



import os
import sys
import json
import re
import subprocess
from fastapi import HTTPException

@app.post("/tiktok/crawl_audio")
def crawl_ads(body: TikTokCrawlAdsRequest):
    # 1) Chuẩn hoá limit
    try:
        limit = int(body.limit)
    except Exception:
        raise HTTPException(status_code=400, detail="`limit` phải là số nguyên")

    # 2) Ép UTF-8 cho tiến trình con
    base_env = os.environ.copy()
    if 'env' in globals() and isinstance(env, dict):
        base_env.update(env)
    base_env.update({
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8"
    })

    cmd = [sys.executable, "playwright_tiktok_audio.py", str(limit)]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,               # chuyển bytes -> str
            encoding="utf-8",        # QUAN TRỌNG: ép UTF-8
            errors="replace",        # tránh UnicodeDecodeError
            timeout=900,
            env=base_env
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="⏱️ Quá thời gian xử lý")

    if proc.returncode != 0:
        # Trả stderr đã là UTF-8 nên không vỡ ký tự
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi khi chạy script:\n{proc.stderr}"
        )

    # 3) Tìm mảng JSON đầu tiên trong stdout bằng cách đếm ngoặc
    import json

    def extract_first_json_array(text: str) -> str | None:
        """
        Tìm mảng JSON đầu tiên trong text bằng JSONDecoder.raw_decode.
        Bỏ qua những đoạn như '[INFO]' vì không decode được thành JSON.
        Trả về substring JSON (dạng chuỗi) nếu tìm thấy, ngược lại None.
        """
        decoder = json.JSONDecoder()

        # Ưu tiên tìm sau 'Result:' để tránh log lặt vặt phía trước
        start_pos = text.find("Result:")
        search_text = text[start_pos:] if start_pos != -1 else text

        for i, ch in enumerate(search_text):
            if ch == '[':
                try:
                    obj, end = decoder.raw_decode(search_text[i:])  # decode từ vị trí '['
                    if isinstance(obj, list):
                        return search_text[i:i+end]  # cắt đúng lát JSON
                except Exception:
                    continue  # không hợp lệ -> thử '[' kế tiếp
        return None

    stdout = proc.stdout

    json_text = extract_first_json_array(stdout)
    if not json_text:
        raise HTTPException(
            status_code=500,
            detail="Không tìm thấy mảng JSON hợp lệ trong stdout.\n--- STDOUT ---\n" + stdout
        )

    try:
        result_json = json.loads(json_text)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi parse JSON: {e}\n--- JSON trích ra ---\n{json_text}\n--- STDOUT ---\n{stdout}"
        )

    return result_json


@app.post("/tiktok/crawl_hashtag")
def crawl_ads(body: TikTokCrawlAdsRequest):
    limit = body.limit
    cmd = [sys.executable, "playwright_tiktok_hashtag.py", str(limit)]
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
            detail=f"Lỗi khi chạy script:\n{proc.stderr}"
        )
        
    try:
        # Lấy phần output sau chữ "Result"
        result_start = proc.stdout.find("Result:\n")
        if result_start == -1:
            raise ValueError("Không tìm thấy đoạn 'Result' trong stdout")

        json_part = proc.stdout[result_start:]  # phần sau "Result"
        # Tìm JSON mảng đầu tiên bắt đầu bằng [ và kết thúc bằng ]
        json_match = re.search(r"\[\s*{[\s\S]*?}\s*\]", json_part)
        
        if not json_match:
            raise ValueError("Không tìm thấy JSON hợp lệ trong stdout")

        json_text = json_match.group(0).replace("\n", "")
        result_json = json.loads(json_text)


    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi parse JSON từ output: {e}\n\n--- STDOUT ---\n{proc.stdout}"
        )
    return result_json

class TikTokCrawlCommentsRequest(BaseModel):
    url: str
    limit: int = 100
@app.post("/tiktok/get_comments")
def crawl_ads(body: TikTokCrawlCommentsRequest):
    limit = body.limit
    url = body.url.strip().rstrip(';')
    cmd = [sys.executable, "get_comments.py", url, str(limit)]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=900,
            encoding="utf-8",    # <- ép cha decode UTF-8
            errors="replace",
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
        result_start = proc.stdout.find("Result:\n")
        if result_start == -1:
            raise ValueError("Không tìm thấy đoạn 'Result' trong stdout")

        json_part = proc.stdout[result_start:]  # phần sau "Result"
        # Tìm JSON mảng đầu tiên bắt đầu bằng [ và kết thúc bằng ]
        json_match = re.search(r"\[\s*{[\s\S]*?}\s*\]", json_part)
        
        if not json_match:
            raise ValueError("Không tìm thấy JSON hợp lệ trong stdout")

        json_text = json_match.group(0).replace("\n", "")
        result_json = json.loads(json_text)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi parse JSON từ output: {e}\n\n--- STDOUT ---\n{proc.stdout}"
        )
    return result_json

class EasyCrawlRequest(BaseModel):
    url: str
    type_output: str = "html"
@app.post("/get_html")
def crawl_easy(body: EasyCrawlRequest):
    url = body.url
    type_output = body.type_output
    try:
        result = subprocess.run(
            [sys.executable, "get_html.py", url, type_output],
            capture_output=True,
            text=True,
            check=True,
            env=env,
            encoding='utf-8'
        )
        matches = re.findall(r"\{.*\}", result.stdout, re.DOTALL)
        json_str = matches[-1] if matches else None
        if not json_str:
            return {
                "error": "Không tìm thấy JSON trong stdout",
                "stdout": result.stdout
            }
        return json.loads(json_str)
    except subprocess.CalledProcessError as e:
        return {"error": "Script lỗi", "details": e.stderr}
    except Exception as e:
        return {"error": "Lỗi không xác định", "details": str(e)}

class TranscriptRequest(BaseModel):
    url: str
    
@app.post("/get_transcript")
def get_transcript(body: TranscriptRequest):
    url = body.url.strip().rstrip(';')
    if not url:
        raise HTTPException(status_code=400, detail="URL không được để trống")
    cmd = [sys.executable, "get_transcripts.py", url]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=900,
            env=env,
            encoding='utf-8'
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
        result_start = proc.stdout.find("Result:\n")
        if result_start == -1:
            raise ValueError("Không tìm thấy đoạn 'Result' trong stdout")
        json_part = proc.stdout[result_start:]  # phần sau "Result"
        # Tìm JSON mảng đầu tiên bắt đầu bằng { và kết thúc bằng }
        json_match = re.search(r"\{\s*[\s\S]*?\s*\}", json_part)
        if not json_match:
            raise ValueError("Không tìm thấy JSON hợp lệ trong stdout")
        json_text = json_match.group(0).replace("\n", "")
        result_json = json.loads(json_text)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi parse JSON từ output: {e}\n\n--- STDOUT ---\n{proc.stdout}"
        )
    return result_json

class DBURL(BaseModel):
    url: str
    

@app.post("/get_pruned_groups")
def get_pruned_groups(body: DBURL):
    url = body.url.strip().rstrip(';')
    if not url:
        raise HTTPException(status_code=400, detail="URL không được để trống")
    cmd = [sys.executable, "groups_pruned.py", "--db-url", url]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=900,
            env=env,
            encoding='utf-8'
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="⏱️ Quá thời gian xử lý")
    if proc.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi khi chạy script:\n{proc.stderr}"
        )
    def _extract_first_json_array(s: str) -> str | None:
        # Tìm và cắt mảng JSON đầu tiên bằng đếm ngoặc an toàn với chuỗi/escape
        start = s.find('[')
        if start == -1:
            return None
        depth = 0
        in_str = False
        esc = False
        for i in range(start, len(s)):
            ch = s[i]
            if in_str:
                if esc:
                    esc = False
                elif ch == '\\':
                    esc = True
                elif ch == '"':
                    in_str = False
            else:
                if ch == '"':
                    in_str = True
                elif ch == '[':
                    depth += 1
                elif ch == ']':
                    depth -= 1
                    if depth == 0:
                        return s[start:i+1]
        return None

    def parse_stdout_to_json(stdout: str):
        # 1) Thử parse trực tiếp (trường hợp script in JSON thuần)
        try:
            return json.loads(stdout)
        except json.JSONDecodeError:
            pass

        # 2) Tìm JSON đầu tiên bất kỳ ({...} hoặc [...]) bằng raw_decode
        dec = json.JSONDecoder()
        for i, ch in enumerate(stdout):
            if ch in '[{':
                try:
                    obj, end = dec.raw_decode(stdout[i:])
                    return obj
                except json.JSONDecodeError:
                    continue

        # 3) Trường hợp biết producer in RA MỘT MẢNG [...]: dùng match ngoặc
        arr = _extract_first_json_array(stdout)
        if arr is not None:
            return json.loads(arr)

        # 4) Fallback: NDJSON (mỗi dòng là 1 JSON object)
        items = []
        for line in stdout.splitlines():
            line = line.strip()
            if not line or line[0] not in '{[':
                continue
            try:
                items.append(json.loads(line))
            except Exception:
                pass
        if items:
            return items

        raise ValueError("Không tìm thấy JSON hợp lệ trong stdout")

    # ===== Chỗ gọi trong FastAPI =====
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=900,
        env=env,
        encoding='utf-8'
    )

    if proc.returncode != 0:
        raise HTTPException(status_code=500, detail=f"Script error: {proc.stderr}")

    try:
        result_json = parse_stdout_to_json(proc.stdout)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi parse JSON từ output: {e}\n\n--- STDOUT ---\n{proc.stdout}"
        )

    return result_json


class PosterRequest(BaseModel):
    images: List[str] = Field(..., description="Danh sách URL/path ảnh (lấy tối đa 6)")
    text: str = Field(..., description="Overlay text")
    fmt: Literal["jpeg", "png"] = Field("jpeg", description="Định dạng ảnh xuất")
    quality: Optional[int] = Field(90, description="Chỉ dùng cho JPEG 0–100")
    scale: int = Field(2, description="Device scale factor khi render ảnh")
    wait: Literal["load", "domcontentloaded", "networkidle", "commit"] = Field(
        "networkidle", description="Chiến lược chờ tải trang"
    )
    # Nếu poster_generator.py nằm nơi khác, chỉnh tại đây
    script_path: str = Field("poster_generator.py", description="Đường dẫn script sinh poster")

@app.post("/generate-poster")
def generate_poster(body: PosterRequest):
    if not body.images:
        raise HTTPException(status_code=400, detail="Thiếu danh sách ảnh")

    # Thư mục tạm để chứa html + ảnh => auto cleanup khi ra khỏi with
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        html_path = tmpdir_path / "poster.html"
        img_ext = "jpg" if body.fmt == "jpeg" else "png"
        img_path = tmpdir_path / f"poster.{img_ext}"

        # Lắp command gọi script
        cmd = [sys.executable, body.script_path, *body.images, "-t", body.text, "-o", str(html_path)]
        if body.fmt == "jpeg":
            cmd += ["--jpeg", str(img_path)]
            if body.quality is not None:
                cmd += ["--quality", str(int(body.quality))]
        else:
            cmd += ["--png", str(img_path)]

        # Có thể truyền thêm scale/wait vào script nếu bạn bổ sung tham số tương ứng
        # Ở đây script đã có --scale/--wait nên ta truyền luôn:
        cmd += ["--scale", str(int(body.scale)), "--wait", body.wait]

        try:
            proc = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=900,
                encoding="utf-8",
            )
        except subprocess.TimeoutExpired:
            raise HTTPException(status_code=504, detail="⏱️ Quá thời gian xử lý")

        if proc.returncode != 0:
            err = proc.stderr.decode("utf-8", "replace")  # chỉ để hiển thị lỗi
            raise HTTPException(status_code=500, detail=f"Script error:\n{err}")

        if not img_path.exists():
            # fallback: đôi khi người dùng truyền sai fmt, thử dò file còn lại
            other = tmpdir_path / ("poster.png" if img_ext == "jpg" else "poster.jpg")
            if other.exists():
                img_path = other
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"Không tìm thấy ảnh đầu ra: {img_path}",
                )

        # Đọc bytes rồi trả về octet-stream; vì dùng TemporaryDirectory nên file sẽ tự xoá
        data = img_path.read_bytes()

        # Bạn muốn octet-stream, mình set đúng như yêu cầu
        headers = {
            "Content-Disposition": f'inline; filename="{img_path.name}"'
        }
        return Response(content=data, media_type="application/octet-stream", headers=headers)
    
    
class MakeVideoRequest(BaseModel):
    scripts: List[str]
    fps: str
    show_script: str
    id_folder: str
import shutil
def delete_resource(script_dir='./script', audio_dir='./audio', image_dir='./image'):
    shutil.rmtree(script_dir)
    shutil.rmtree(audio_dir)
    shutil.rmtree(image_dir)

from starlette.background import BackgroundTask
from fastapi.responses import FileResponse
@app.post("/generate-video")
def generate_video(body: MakeVideoRequest):
    scripts = body.scripts
    id_folder = body.id_folder
    show_script = body.show_script
    fps = body.fps
    cmd = [sys.executable, "make_video_from_image.py", id_folder, fps, show_script , json.dumps(scripts, ensure_ascii=False)]
    print(cmd)
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=900,
        env=env,
        encoding='utf-8'
    )
    if proc.returncode != 0:
        raise HTTPException(status_code=500, detail=f"Script error: {proc.stderr}")
    
    video_path = './audio/my_video.mp4'
    return FileResponse(path=video_path, media_type="video/mp4", filename="video.mp4",background=BackgroundTask(lambda: delete_resource))
    
    

class GetBatchJobContentGemini(BaseModel):
    job_name: str
    gemini_api: str
    
from google import genai
from google.genai import types
import json

@app.post("/get_batch_job_content_gemini")
def get_batch_job_content_gemini(body: GetBatchJobContentGemini):
    job_name = body.job_name
    gemini_api = body.gemini_api
    client = genai.Client(api_key=gemini_api)
    
    batch_job = client.batches.get(name=job_name)
    if batch_job.state.name == "JOB_STATE_SUCCEEDED":
        result = None
        for i, inline_response in enumerate(batch_job.dest.inlined_responses):
            result = json.loads(inline_response.response.text)
        
        return {
            "status": batch_job.state.name,
            "response": result
        }
    else:
        return {
            "status": batch_job.state.name,
            "response": "" 
        }

    
    