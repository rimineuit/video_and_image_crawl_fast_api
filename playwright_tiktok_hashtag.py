from playwright.sync_api import sync_playwright
import json
import gc
import time
import sys
from urllib.parse import unquote, urljoin
import json
import math
from pathlib import Path

SAMESITE_MAP = {
    "lax": "Lax",
    "strict": "Strict",
    "no_restriction": "None",
}

def load_cookies_for_playwright(json_path, for_domains=None):
    """
    Đọc cookies từ file (định dạng Chrome/Extensions) và chuyển sang
    định dạng mà Playwright context.add_cookies chấp nhận.

    for_domains: list[str] các domain giữ lại (ví dụ ["ads.tiktok.com", ".tiktok.com"])
                 Nếu None -> giữ tất cả.
    """
    data = json.loads(Path(json_path).read_text(encoding="utf-8"))

    def domain_ok(d):
        if not for_domains:
            return True
        # match chính xác hoặc subdomain (xử lý cả tiền tố ".")
        d_norm = d.lstrip(".").lower()
        for want in for_domains:
            w_norm = want.lstrip(".").lower()
            if d_norm == w_norm or d_norm.endswith("." + w_norm):
                return True
        return False

    seen = set()
    out = []
    for c in data:
        dom = c.get("domain", "")
        if not domain_ok(dom):
            continue

        name = c.get("name")
        value = c.get("value", "")
        path = c.get("path", "/") or "/"

        # map sameSite
        ss_raw = c.get("sameSite")
        ss = SAMESITE_MAP.get(str(ss_raw).lower(), None) if isinstance(ss_raw, str) else None

        # map expires
        expires = None
        if not c.get("session", False):
            # Chrome export có thể là float; Playwright cần int
            exp = c.get("expirationDate")
            if isinstance(exp, (int, float)):
                expires = int(math.floor(exp))

        # Tạo tuple key để loại trùng (ưu tiên cái đến sau nếu trùng)
        key = (dom, path, name)
        if key in seen:
            # đã có cookie cùng (domain, path, name) -> skip hoặc thay thế
            # Ở đây chọn thay thế: xóa cái cũ rồi thêm cái mới
            out = [ck for ck in out if (ck["domain"], ck["path"], ck["name"]) != key]
        seen.add(key)

        ck = {
            "name": name,
            "value": value,
            "domain": dom,
            "path": path,
            "secure": bool(c.get("secure", False)),
            "httpOnly": bool(c.get("httpOnly", False)),
        }
        if ss:
            ck["sameSite"] = ss
        if expires is not None:
            ck["expires"] = expires

        out.append(ck)

    return out


BASE_URL = "https://www.tiktok.com/music/"


# ===== Constants =====
TIKTOK_URL = "https://ads.tiktok.com/business/creativecenter/inspiration/popular/hashtag/pc/vi"
BLOCKED_TYPES = {"image", "font", "stylesheet", "media"}
BLOCKED_KEYWORDS = {"analytics", "tracking", "collect", "adsbygoogle"}

# ===== Logging =====
def log(msg, level="INFO"):
    print(f"[{level}] {msg}")

# ===== Dropdown Helper =====
def select_dropdown_option(page, placeholder_text, value, option_selector):
    try:
        input_field = page.wait_for_selector(f'input[placeholder="{placeholder_text}"]', timeout=5000)
        input_field.fill(value)
        page.wait_for_timeout(1000)
        dropdown_item = page.wait_for_selector(option_selector, timeout=5000)
        dropdown_item.click()
        page.wait_for_timeout(1000)
        log("Dropdown option selected successfully.")
        return True
    except Exception as e:
        log(f"Dropdown selection failed: {e}", "ERROR")
        return False

# ===== Main Crawler =====
COOKIE_FILE = "tiktok_cookies.json"  # đường dẫn đến file JSON bạn đưa ở trên

def crawl_tiktok_audio(url, limit=1000):
    with sync_playwright() as p:
        browser = p.chromium.launch(
        headless=True,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process",
            "--proxy-server=http://27.79.213.13:16000"  # 👈 chèn proxy ở đây
        ]
    )


        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720},
            bypass_csp=True,
            java_script_enabled=True
        )

        # === NẠP COOKIES TRƯỚC KHI MỞ TRANG ===
        try:
            cookies = load_cookies_for_playwright(
                COOKIE_FILE,
                for_domains=["ads.tiktok.com", ".tiktok.com"]
            )
            if cookies:
                context.add_cookies(cookies)
                log(f"Loaded {len(cookies)} cookies into context.")
            else:
                log("No cookies loaded (empty after filtering).", "WARN")
        except Exception as e:
            log(f"Failed to load cookies: {e}", "ERROR")
        def route_filter(route, request):
            if request.resource_type in BLOCKED_TYPES or any(k in request.url.lower() for k in BLOCKED_KEYWORDS):
                return route.abort()
            return route.continue_()
        
        context.route("**/*", route_filter)
        page = context.new_page()
        try:
            page.goto(url)
            page.wait_for_load_state("domcontentloaded")
            log(f"Navigated to {url}")

            try:
                page.wait_for_selector('span.CardPc_titleText__RYOWo', timeout=10000)
                log("Video elements loaded.")
            except:
                log("Video elements not found. Exiting.", "ERROR")
                return []
            
            page.wait_for_timeout(5000)  # Đợi chút để các video đầu tiên tải xong

            collected = []
            seen_ids = set()
            empty_attempts = 0

            while len(collected) < limit:
                video_elements = page.query_selector_all('span.CardPc_titleText__RYOWo')
                new_found = 0

                for el in video_elements[-20:]:  # Chỉ check các phần tử mới nhất
                    hashtag = el.inner_text().strip()
                    if hashtag and hashtag not in seen_ids:
                        seen_ids.add(hashtag)
                        collected.append({"hashtag": hashtag})
                        new_found += 1

                if new_found == 0:
                    empty_attempts += 1
                    log(f"No new videos found. Attempt {empty_attempts}/3")
                    if empty_attempts >= 3:
                        log("No new videos for 3 consecutive attempts. Stopping.")
                        break
                else:
                    empty_attempts = 0

                log(f"Collected {len(collected)} / {limit} videos...")

                if len(collected) < limit:
                    # Scroll xuống để load thêm
                    page.mouse.wheel(0, 1500)  
                    page.wait_for_timeout(2000)  # Chờ dữ liệu mới load
                else:
                    break

                gc.collect()

            return collected[:limit]

        finally:
            context.close()
            browser.close()

# ===== CLI Runner =====
if __name__ == "__main__":
    try:
        limit = int(sys.argv[1]) if len(sys.argv) > 1 else 10
        result = crawl_tiktok_audio(TIKTOK_URL, limit=limit)
        log("Result:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as e:
        log(f"Unexpected error: {e}", "FATAL")
        sys.exit(1)
