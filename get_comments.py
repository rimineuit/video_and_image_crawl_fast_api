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
def get_comments(url, limit):
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process"
            ])
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720},
        )
        page = context.new_page()

        try:
            page.goto(url, timeout=60000)
            page.wait_for_load_state("domcontentloaded")
            page.wait_for_selector("#main-content-video_detail span[data-e2e='comment-level-1']", timeout=30000)

            seen = set()
            all_comments = []

            def harvest():
                nonlocal all_comments, seen
                nodes = page.query_selector_all(
                    "#main-content-video_detail div.css-16omhll-DivCommentContentWrapper.e16z10162"
                )
                for node in nodes:
                    text_el = node.query_selector("span")
                    likes_el = node.query_selector("div[role='button']")
                    text = (text_el.inner_text().strip() if text_el else "")
                    likes = (likes_el.inner_text().strip() if likes_el else "0")
                    if not text:
                        continue
                    key = (text, likes)
                    if key not in seen:
                        seen.add(key)
                        all_comments.append({"text": text, "likes": likes})

            # lần đầu
            harvest()

            prev_count = len(all_comments)
            stale_rounds = 0

            while len(all_comments) < limit and stale_rounds < 3:
                # Scroll xuống cuối
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(2.5)  # chờ comment mới load
                harvest()

                if len(all_comments) == prev_count:
                    stale_rounds += 1
                else:
                    prev_count = len(all_comments)
                    stale_rounds = 0

            return all_comments[:limit]

        finally:
            context.close()
            browser.close()

# ===== CLI Runner =====
if __name__ == "__main__":
    try:
        url = str(sys.argv[1])
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 100
        result = get_comments(url, limit=limit)
        log("Result:")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:
        log(f"Unexpected error: {e}", "FATAL")
        sys.exit(1)
