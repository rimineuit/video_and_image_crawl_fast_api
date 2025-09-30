from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import time
from urllib.parse import urljoin

def crawl_comment_threads(
    url: str,
    headless: bool = False,
    max_scrolls: int = 10,
    click_rounds_per_thread: int = 8,
    base_url: str = "https://www.tiktok.com",
):
    """
    Trả về list[dict]:
    [
      {
        "text": "<comment-level-1 text>",
        "user": {
            "user_handle": "ha.",
            "display_name": "ha.",
            "profile_url": "https://www.tiktok.com/@ha."
        },
        "replies": [
          {
            "text": "<comment-level-2 text>",
            "user": {
                "user_handle": "...",
                "display_name": "...",
                "profile_url": "https://www.tiktok.com/@..."
            }
          },
          ...
        ]
      },
      ...
    ]
    Ghi chú: TikTok không lộ numeric user_id trong DOM trang video. Ở đây dùng handle như ID ổn định.
    """

    def _dedupe_preserve_order(items):
        seen = set()
        out = []
        for x in items:
            key = repr(x)  # dict/list unhashable -> repr để khử trùng lặp sơ bộ
            if key not in seen:
                seen.add(key)
                out.append(x)
        return out

    def _extract_user_from_level(thread, level: int):
        """
        Tìm user ở mức level (1 cho cmt gốc, 2 cho reply) trong phạm vi thread/container.
        Trả về tuple (handle, display_name, profile_url) hoặc (None, None, None).
        """
        try:
            user_box = thread.locator(f'[data-e2e="comment-username-{level}"]').first
            # a[href="/@handle"]
            link = user_box.locator("a").first
            href = link.get_attribute("href") or ""
            # handle
            handle = None
            if "/@" in href:
                handle = href.split("/@")[-1].split("?")[0].strip().strip("/")
            # display name nằm trong <p> bên trong user_box (nếu có)
            display_name = None
            try:
                dn = user_box.locator("p").first.inner_text().strip()
                display_name = dn or handle
            except Exception:
                display_name = handle
            profile_url = urljoin(base_url, f"/@{handle}") if handle else None
            if handle:
                return handle, display_name, profile_url
        except Exception:
            pass
        return None, None, None

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )
        context = browser.new_context(
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/117.0.0.0 Safari/537.36"),
            viewport={"width": 1280, "height": 720},
            bypass_csp=True,
            java_script_enabled=True,
        )
        page = context.new_page()

        # Điều hướng
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_load_state("domcontentloaded")

        # Đợi 5s rồi bấm Skip nếu có
        page.wait_for_timeout(5000)
        try:
            skip_btn = page.locator("div.TUXButton-label:has-text('Skip')")
            if skip_btn.first.is_visible():
                skip_btn.first.click(timeout=2000)
                page.wait_for_timeout(1000)
        except Exception:
            pass

        # Chờ ít nhất 1 comment xuất hiện
        top_level_any = page.locator('span[data-e2e="comment-level-1"]')
        try:
            top_level_any.first.wait_for(timeout=15000)
        except PlaywrightTimeoutError:
            page.mouse.wheel(0, 600)
            page.wait_for_timeout(3000)
            top_level_any.first.wait_for(timeout=10000)

        # Cuộn để load đủ các thread (wrapper của từng cmt gốc)
        # Lưu ý: lớp hash có thể đổi; dùng 'DivCommentObjectWrapper' theo mẫu e16z10169
        thread_selector = "div.e16z10169"
        threads = page.locator(thread_selector)

        scrolls = 0
        last_count = 0
        while scrolls < max_scrolls:
            try:
                if threads.count() > 0:
                    threads.last.scroll_into_view_if_needed(timeout=2000)
                else:
                    page.mouse.wheel(0, 1200)
            except Exception:
                page.mouse.wheel(0, 1200)
            page.wait_for_timeout(800)

            curr_count = threads.count()
            if curr_count <= last_count:
                scrolls += 1
            else:
                last_count = curr_count
                scrolls = 0
            threads = page.locator(thread_selector)

        # Helper: mở hết "Xem ... câu trả lời" trong PHẠM VI 1 thread
        def _open_all_replies_for_thread(thread):
            def _click_once(container) -> int:
                clicked = 0
                for sel in [
                    "span:has-text('Xem')",
                    "span:has-text('câu trả lời')",
                    "span:has-text('View')",
                    "span:has-text('replies')",
                    "div[role='button']:has-text('Xem')",
                    "div[role='button']:has-text('View')",
                ]:
                    loc = container.locator(sel)
                    n = loc.count()
                    for i in range(n):
                        try:
                            btn = loc.nth(i)
                            if not btn.is_visible():
                                continue
                            btn.scroll_into_view_if_needed(timeout=1000)
                            btn.click(timeout=2000)
                            clicked += 1
                            page.wait_for_timeout(400)
                        except Exception:
                            pass
                return clicked

            rounds = 0
            while rounds < click_rounds_per_thread:
                c = _click_once(thread)
                if c == 0:
                    break
                page.wait_for_timeout(600)
                rounds += 1

        results = []
        total_threads = threads.count()
        for idx in range(total_threads):
            thread = threads.nth(idx)
            try:
                thread.scroll_into_view_if_needed(timeout=1500)
            except Exception:
                pass

            # Mở hết replies trong thread
            try:
                _open_all_replies_for_thread(thread)
            except Exception:
                pass

            # --- CMT GỐC (level-1) ---
            root_text = ""
            try:
                root_span = thread.locator('span[data-e2e="comment-level-1"]').first
                root_text = (root_span.inner_text() or "").strip()
            except Exception:
                pass

            h1, dn1, p1 = _extract_user_from_level(thread, level=1)
            root_user = {
                "user_handle": h1,
                "display_name": dn1,
                "profile_url": p1,
            }

            # --- REPLIES (level-2) ---
            # Cách ghép đơn giản: zip danh sách username-2 và comment-level-2 theo thứ tự xuất hiện.
            reply_user_boxes = thread.locator('[data-e2e="comment-username-2"]')
            reply_text_spans = thread.locator('span[data-e2e="comment-level-2"]')

            replies = []
            n_users = reply_user_boxes.count()
            n_texts = reply_text_spans.count()
            n = min(n_users, n_texts)

            for i in range(n):
                text = ""
                try:
                    text = (reply_text_spans.nth(i).inner_text() or "").strip()
                except Exception:
                    text = ""

                # Bọc lại node để dùng chung extractor
                sub_container = reply_user_boxes.nth(i)
                h2, dn2, p2 = (None, None, None)
                try:
                    # tái sử dụng hàm bằng cách truyền một "container" là node user-2
                    h2, dn2, p2 = _extract_user_from_level(thread=thread.locator(":scope"), level=2)
                    # Nếu extractor theo thread tổng thể không ra đúng vị trí,
                    # fallback: bóc trực tiếp từ sub_container
                    if not h2:
                        try:
                            link2 = sub_container.locator("a").first
                            href2 = link2.get_attribute("href") or ""
                            if "/@" in href2:
                                h2 = href2.split("/@")[-1].split("?")[0].strip().strip("/")
                            try:
                                dn2 = sub_container.locator("p").first.inner_text().strip() or h2
                            except Exception:
                                dn2 = h2
                            p2 = urljoin(base_url, f"/@{h2}") if h2 else None
                        except Exception:
                            pass
                except Exception:
                    pass

                replies.append({
                    "text": text,
                    "user": {
                        "user_handle": h2,
                        "display_name": dn2,
                        "profile_url": p2,
                    }
                })

            results.append({
                "text": root_text,
                "user": root_user,
                "replies": _dedupe_preserve_order(replies),
            })

        context.close()
        browser.close()
        return results

import sys
import json
if __name__ == "__main__":
    url = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 100
    results = crawl_comment_threads(
    url,
    headless=True,
    max_scrolls=10,
    click_rounds_per_thread=8,
    )
    print(json.dumps(results, ensure_ascii=False))