from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import time

def crawl_comment_threads(
    url: str,
    headless: bool = False,
    max_scrolls: int = 10,
    click_rounds_per_thread: int = 8,
):
    """
    Trả về: list[dict] dạng:
    [
      {"text": "<comment-level-1 text>", "replies": ["<comment-level-2 text>", ...]},
      ...
    ]
    Logic:
    - Cuộn để load đủ comment
    - Duyệt từng thread (DivCommentObjectWrapper)
      - Trong MỖI thread: bấm hết các nút 'Xem ... câu trả lời' / 'View ... replies'
      - Sau đó trích xuất text của comment-level-1 và comment-level-2 trong thread đó
    """
    def _dedupe_preserve_order(items):
        seen = set()
        out = []
        for x in items:
            if x not in seen:
                seen.add(x)
                out.append(x)
        return out

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
        page.wait_for_timeout(3000)
        # Sau khi page.goto và wait_for_load_state
        page.wait_for_timeout(5000)  # đợi 5 giây cho chắc chắn các overlay hiển thị

        # Thử tìm nút Skip (theo text)
        try:
            skip_btn = page.locator("div.TUXButton-label:has-text('Skip')")
            if skip_btn.is_visible():
                skip_btn.click(timeout=2000)
                page.wait_for_timeout(1000)  # chờ trang load lại sau khi Skip
        except Exception:
            pass

        # Đợi ít nhất 1 comment xuất hiện
        top_level_any = page.locator('span[data-e2e="comment-level-1"]')
        try:
            top_level_any.first.wait_for(timeout=15000)
        except PlaywrightTimeoutError:
            page.mouse.wheel(0, 600)
            page.wait_for_timeout(3000)
            top_level_any.first.wait_for(timeout=10000)

        # Cuộn để load đủ các thread
        scrolls = 0
        last_count = 0
        thread_selector = 'div.e16z10169'  # DivCommentObjectWrapper (class mang hậu tố hash)
        threads = page.locator(thread_selector)
        while scrolls < max_scrolls:
            try:
                threads.last.scroll_into_view_if_needed(timeout=2000)
            except Exception:
                page.mouse.wheel(0, 1200)
            page.wait_for_timeout(800)

            curr_count = threads.count()
            if curr_count <= last_count:
                scrolls += 1
            else:
                last_count = curr_count
                scrolls = 0
            # refresh handle
            threads = page.locator(thread_selector)

        # Helper: trong từng thread, click hết các nút 'Xem ... câu trả lời'
        def _open_all_replies_for_thread(thread):
            def _click_once(container) -> int:
                # gom nhiều selector mềm, giới hạn trong container của thread
                candidates = []
                for sel in [
                    "span:has-text('Xem')",
                    "span:has-text('câu trả lời')",
                    "span:has-text('View')",
                    "span:has-text('replies')",
                    "div[role='button']:has-text('Xem')",
                    "div[role='button']:has-text('View')",
                ]:
                    candidates.append(container.locator(sel))

                clicked = 0
                for loc in candidates:
                    n = loc.count()
                    for i in range(n):
                        try:
                            btn = loc.nth(i)
                            # tránh bấm những phần tử không thuộc block "Xem trả lời"
                            # ưu tiên khu vực 'DivViewRepliesContainer' nếu có
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
                clicked_now = _click_once(thread)
                if clicked_now == 0:
                    break
                page.wait_for_timeout(600)
                rounds += 1

        # Duyệt từng thread và trích xuất
        results = []
        total_threads = threads.count()
        for idx in range(total_threads):
            thread = threads.nth(idx)
            try:
                # Scroll thread vào viewport để đảm bảo lazy-load phần replies
                thread.scroll_into_view_if_needed(timeout=1500)
            except Exception:
                pass

            # Mở hết replies trong thread hiện tại
            try:
                _open_all_replies_for_thread(thread)
            except Exception:
                # không fail toàn bộ nếu thread này lỗi
                pass

            # Lấy text cmt gốc (level-1) trong thread
            top_texts = []
            tops = thread.locator('span[data-e2e="comment-level-1"]')
            for el in tops.all():
                try:
                    t = el.inner_text().strip()
                    if t:
                        top_texts.append(t)
                except Exception:
                    pass

            # Lấy text replies (level-2) chỉ TRONG thread này
            reply_texts = []
            replies = thread.locator('span[data-e2e="comment-level-2"]')
            for el in replies.all():
                try:
                    t = el.inner_text().strip()
                    if t:
                        reply_texts.append(t)
                except Exception:
                    pass

            # Nếu có nhiều span level-1 trong cùng wrapper, mình lấy cái đầu làm "gốc" (thường chỉ 1)
            if len(top_texts) == 0 and len(reply_texts) == 0:
                continue

            thread_obj = {
                "text": top_texts[0] if top_texts else "",
                "replies": _dedupe_preserve_order(reply_texts),
            }
            results.append(thread_obj)

        context.close()
        browser.close()
        return results


if __name__ == "__main__":
    print(crawl_comment_threads("https://www.tiktok.com/@cotuyenhoala/video/7527196260919512328"))