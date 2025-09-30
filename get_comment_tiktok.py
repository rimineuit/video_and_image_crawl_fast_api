from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import time
from urllib.parse import urljoin
import sys
import json

def crawl_comment_threads(
    url: str,
    headless: bool = False,
    max_scrolls: int = 10,
    base_url: str = "https://www.tiktok.com",
):
    """
    Trả về list[dict]:
    [
      {
        "text": "<comment-level-1 text>",
        "user": {
            "user_handle": "...",
            "display_name": "...",
            "profile_url": "https://www.tiktok.com/@..."
        },
        "replies": [
          {
            "text": "<comment-level-2 text>",
            "user": { ... }
          },
          ...
        ]
      },
      ...
    ]
    - Nếu không có bình luận: trả về [].
    - Với mỗi thread: chỉ click 'Xem ... câu trả lời' đúng 1 lần (không chờ).
    """

    def _dedupe_preserve_order(items):
        seen = set()
        out = []
        for x in items:
            key = repr(x)
            if key not in seen:
                seen.add(key)
                out.append(x)
        return out

    def _extract_user_from_level(container, level: int):
        """Lấy (handle, display_name, profile_url) trong phạm vi container cho level 1/2."""
        try:
            user_box = container.locator(f'[data-e2e="comment-username-{level}"]').first
            link = user_box.locator("a").first
            href = link.get_attribute("href") or ""
            handle = None
            if "/@" in href:
                handle = href.split("/@")[-1].split("?")[0].strip().strip("/")
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

        # Đợi 5s rồi bấm Skip (nếu có), scroll nhẹ để kích hoạt lazy-load
        page.wait_for_timeout(5000)
        page.mouse.wheel(0, 300)
        page.wait_for_timeout(5000)
        
        try:
            skip_btn = page.locator("div.TUXButton-label:has-text('Skip')")
            if skip_btn.first.is_visible():
                skip_btn.first.click(timeout=1500)
        except Exception:
            pass

        # Thử chờ comment xuất hiện, nếu không có -> trả [] luôn
        top_level_any = page.locator('span[data-e2e="comment-level-1"]')
        try:
            top_level_any.first.wait_for(timeout=10000)
        except PlaywrightTimeoutError:
            # Không có bình luận
            context.close()
            browser.close()
            return []

        # Cuộn để load thêm các thread (container của cmt gốc)
        thread_selector = "div.e16z10169"  # DivCommentObjectWrapper (hash có thể đổi)
        threads = page.locator(thread_selector)

        scrolls = 0
        last_count = threads.count()
        # Nếu chưa có thread container, cố gắng scroll một ít
        if last_count == 0:
            page.mouse.wheel(0, 800)
            page.wait_for_timeout(600)
            threads = page.locator(thread_selector)
            last_count = threads.count()

        while scrolls < max_scrolls:
            try:
                if threads.count() > 0:
                    threads.last.scroll_into_view_if_needed(timeout=1200)
                else:
                    page.mouse.wheel(0, 1000)
            except Exception:
                page.mouse.wheel(0, 1000)

            page.wait_for_timeout(400)
            curr_count = threads.count()
            if curr_count <= last_count:
                scrolls += 1
            else:
                last_count = curr_count
                scrolls = 0
            threads = page.locator(thread_selector)

        # Helper: trong 1 thread, click tất cả "Xem ... câu trả lời" MỖI NÚT 1 LẦN (không lặp vòng/không chờ)
        def _click_view_replies_once(thread):
            selectors = [
                "span:has-text('Xem')",
                "span:has-text('câu trả lời')",
                "span:has-text('View')",
                "span:has-text('replies')",
                "div[role='button']:has-text('Xem')",
                "div[role='button']:has-text('View')",
            ]
            for sel in selectors:
                loc = thread.locator(sel)
                n = loc.count()
                for i in range(n):
                    try:
                        btn = loc.nth(i)
                        if btn.is_visible():
                            btn.scroll_into_view_if_needed(timeout=800)
                            # bấm 1 lần, không wait thêm
                            btn.click(timeout=1200)
                    except Exception:
                        pass

        results = []
        total_threads = threads.count()
        for idx in range(total_threads):
            thread = threads.nth(idx)
            try:
                thread.scroll_into_view_if_needed(timeout=800)
            except Exception:
                pass

            # Chỉ bấm 1 lần mọi nút "Xem ... câu trả lời" trong thread này
            try:
                _click_view_replies_once(thread)
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
            reply_user_boxes = thread.locator('[data-e2e="comment-username-2"]')
            reply_text_spans = thread.locator('span[data-e2e="comment-level-2"]')

            replies = []
            n = min(reply_user_boxes.count(), reply_text_spans.count())
            for i in range(n):
                # text
                try:
                    text = (reply_text_spans.nth(i).inner_text() or "").strip()
                except Exception:
                    text = ""

                # user (ưu tiên bóc trong box của từng reply)
                h2 = dn2 = p2 = None
                try:
                    sub_container = reply_user_boxes.nth(i)
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


if __name__ == "__main__":
    url = sys.argv[1]
    # limit không dùng trong logic hiện tại, vẫn nhận để tương thích CLI
    _ = int(sys.argv[2]) if len(sys.argv) > 2 else 100
    results = crawl_comment_threads(
        url,
        headless=True,
        max_scrolls=10,
    )
    print(json.dumps(results, ensure_ascii=False))
