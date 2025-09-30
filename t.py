from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import time
def crawl_comments(url: str, headless: bool = False, max_scrolls: int = 10):
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

        # Điều hướng, tránh treo ở networkidle
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(5000)  # Chờ thêm 3 giây để chắc chắn trang đã tải xong

        # Chờ item bình luận đầu tiên (level-1)
        comment_items = page.locator('span[data-e2e="comment-level-1"]')
        try:
            comment_items.first.wait_for(timeout=15000)
        except PlaywrightTimeoutError:
            # Thử cuộn nhẹ để kích hoạt lazy load
            page.mouse.wheel(0, 20)
            page.wait_for_timeout(10000)
            comment_items.first.wait_for(timeout=10000)

        # Cuộn để tải thêm bình luận (nếu cần)
        scrolls = 0
        last_count = 0
        while scrolls < max_scrolls:
            try:
                # cuộn vào vùng comment và lăn bánh xe để load thêm
                comment_items.last.scroll_into_view_if_needed(timeout=3000)
                time.sleep(10)
            except:
                # fallback: cuộn trang
                page.mouse.wheel(0, 120)

            page.wait_for_timeout(1200)
            curr_count = comment_items.count()
            if curr_count <= last_count:
                scrolls += 1
            else:
                last_count = curr_count
                scrolls = 0  # reset nếu có thêm items

        # Thu thập text bình luận
        texts = [el.inner_text().strip() for el in comment_items.all() if el.inner_text().strip()]

        # Đóng
        context.close()
        browser.close()
        return texts
    
if __name__ == "__main__":
    print(crawl_comments("https://www.tiktok.com/@cotuyenhoala/video/7527196260919512328"))