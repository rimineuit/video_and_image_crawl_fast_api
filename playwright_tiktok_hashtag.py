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

# # ===== Main Crawler =====
# COOKIE_FILE = "tiktok_cookies.json"  # đường dẫn đến file JSON bạn đưa ở trên

# ===== Helper: bấm View More cho đến khi thấy thêm item =====
def click_view_more_until_new(page, item_selector: str, timeout_ms: int = 8000) -> bool:
    """
    Tìm và bấm nút 'Xem thêm'/'View more' (nhiều khả năng là <div> hoặc <button>),
    rồi chờ đến khi số lượng item (item_selector) tăng lên.
    Trả về True nếu có item mới xuất hiện, False nếu không tìm thấy nút hoặc không tăng.
    """
    before = page.eval_on_selector_all(item_selector, "els => els.length")
    # Các khả năng của nút View more trên Creative Center (thay đổi class thường xuyên)
    btn = page.locator(
        "button:has-text('Xem thêm'), div:has-text('Xem thêm'), "
        "button:has-text('View more'), div:has-text('View more'), "
        "div.ViewMoreBtn_viewMoreBtn__fOkv2, "
        "div:has(span:has-text('Xem thêm')), div:has(span:has-text('View more'))"
    )
    if btn.count() == 0:
        return False

    # Ưu tiên click cái hiển thị trong viewport
    target = btn.first
    try:
        target.scroll_into_view_if_needed()
        # Tránh bị overlay che
        page.wait_for_timeout(300)
        target.click(timeout=3000, force=True)
    except Exception:
        # thử thêm lần nữa bằng click JS
        try:
            target.evaluate("(el) => el.click()")
        except Exception:
            return False

    # Chờ số lượng item tăng
    try:
        page.wait_for_function(
            """(sel, before) => document.querySelectorAll(sel).length > before""",
            arg=(item_selector, before),
            timeout=timeout_ms,
        )
        return True
    except Exception:
        # Có thể trang load chậm, đợi thêm một nhịp ngắn rồi kiểm tra lại
        page.wait_for_timeout(1500)
        after = page.eval_on_selector_all(item_selector, "els => els.length")
        return after > before


# ===== Main Crawler (đổi phần load thêm từ scroll -> click View more) =====
def crawl_tiktok_audio(url, limit=1000):
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
            ]
        )

        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720},
            bypass_csp=True,
            java_script_enabled=True
        )

        # Block bớt tài nguyên phụ (giữ nguyên như code của bạn)
        BLOCKED_TYPES = {"image", "font", "stylesheet", "media"}
        BLOCKED_KEYWORDS = {"analytics", "tracking", "collect", "adsbygoogle"}

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

            ITEM_SELECTOR = "span.CardPc_titleText__RYOWo"

            try:
                page.wait_for_selector(ITEM_SELECTOR, timeout=10000)
                log("Hashtag elements loaded.")
            except:
                log("Hashtag elements not found. Exiting.", "ERROR")
                return []

            page.wait_for_timeout(2000)  # cho trang ổn định

            collected, seen_ids, empty_attempts = [], set(), 0

            while len(collected) < limit:
                # Lấy item hiện có
                items = page.query_selector_all(ITEM_SELECTOR)
                new_found = 0
                for el in items[-40:]:  # quét lô gần nhất
                    hashtag = (el.inner_text() or "").strip()
                    if hashtag and hashtag not in seen_ids:
                        seen_ids.add(hashtag)
                        collected.append({"hashtag": hashtag})
                        new_found += 1
                        if len(collected) >= limit:
                            break

                if new_found == 0:
                    empty_attempts += 1
                    log(f"No new items found. Attempt {empty_attempts}/3")
                else:
                    empty_attempts = 0

                log(f"Collected {len(collected)} / {limit} hashtags...")

                if len(collected) >= limit:
                    break

                # Thay vì scroll, bấm View more
                clicked = click_view_more_until_new(page, ITEM_SELECTOR, timeout_ms=10000)
                if not clicked:
                    # Không còn nút hoặc bấm không ra item mới -> dừng
                    if empty_attempts >= 3:
                        log("No new items after multiple attempts. Stopping.")
                        break
                    # Cho 1 nhịp nhỏ rồi thử vòng sau
                    page.wait_for_timeout(1200)

                gc.collect()

            return collected[:limit]

        finally:
            context.close()
            browser.close()


# ===== CLI Runner (giữ nguyên) =====
if __name__ == "__main__":
    try:
        TIKTOK_URL = "https://ads.tiktok.com/business/creativecenter/inspiration/popular/hashtag/pc/vi"
        limit = int(sys.argv[1]) if len(sys.argv) > 1 else 10
        result = crawl_tiktok_audio(TIKTOK_URL, limit=limit)
        log("Result:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as e:
        log(f"Unexpected error: {e}", "FATAL")
        sys.exit(1)