from playwright.sync_api import sync_playwright
import json
import gc
import time
import sys

# ===== Constants =====
BLOCKED_TYPES = {"image", "font", "stylesheet", "media"}
BLOCKED_KEYWORDS = {"analytics", "tracking", "collect", "adsbygoogle"}

# ===== Logging =====
def log(msg, level="INFO"):
    print(f"[{level}] {msg}")

# ===== Main Crawler =====
def get_audio_used_count(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process"
            ]
        )

        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720},
            bypass_csp=True,
            java_script_enabled=True
        )

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

            # Close banner if present
            try:
                music_count = page.wait_for_selector(
                    'h2[data-e2e="music-video-count"]', 
                    timeout=10000
                )
                text = music_count.inner_text()

                gc.collect()
            except Exception as e:
                log(f"Failed to find music count element: {e}", "WARNING")
        except Exception as e:
            log(f"Error during page navigation: {e}", "ERROR")
            return {"error": str(e)}
        finally:
            page.close()
            context.close()
            browser.close()
            return text 

import re

def parse_count(text):
    """
    Chuyển chuỗi số + đơn vị (K, M, B) sang số nguyên.
    Ví dụ: '203.7K videos' -> 203700
    """
    # Tìm số và đơn vị
    match = re.search(r'([\d,.]+)\s*([KMB]?)', text.strip(), re.IGNORECASE)
    if not match:
        return None

    number_str, suffix = match.groups()
    number = float(number_str.replace(',', ''))

    # Nhân theo đơn vị
    multiplier = {
        '': 1,
        'K': 1_000,
        'M': 1_000_000,
        'B': 1_000_000_000
    }.get(suffix.upper(), 1)

    return int(number * multiplier)

# ===== CLI Runner =====
if __name__ == "__main__":
    try:
        url = str(sys.argv[1])
        result = parse_count(get_audio_used_count(url))
        log("Result:")
        print(json.dumps({"use_count": result}, indent=2, ensure_ascii=False))
    except Exception as e:
        log(f"Unexpected error: {e}", "FATAL")
        sys.exit(1)
