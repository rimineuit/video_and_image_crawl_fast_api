from playwright.sync_api import sync_playwright
import json

def crawl_tiktok_videos(url, limit=1000, output_file="tiktok_videos.json"):
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
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
            viewport={"width": 1280, "height": 800},
            permissions=["geolocation"],
            geolocation={"latitude": 21.028511, "longitude": 105.804817},
            timezone_id="Asia/Ho_Chi_Minh"
        )
        page = context.new_page()

        page.goto(url)
        page.wait_for_load_state("domcontentloaded")
        print(f"Navigated to {url}")
        # === 1. Wait for and click the banner ===
        try:
            banner = page.wait_for_selector("#ccModuleBannerWrap > div > div > div > div", timeout=5000)
            banner.click()
            print("Banner clicked.")
        except:
            print("Banner not found or clickable.")

        # === 2. Wait for input field and fill it ===
        try:
            input_field = page.wait_for_selector('input[placeholder="Nhập/chọn từ danh sách"]', timeout=5000)
            input_field.fill("vi")
            print("Filled input field with 'vi'.")
        except:
            print("Input field not found.")
        import time
        time.sleep(1)
        # === 3. Wait for dropdown and click the first item ===
        try:
            dropdown_item = page.wait_for_selector('body > div:nth-child(11) > div > div > div > div > div.byted-select-popover-panel-inner > div:nth-child(20)', timeout=5000)
            dropdown_item.click()
            print("Dropdown option selected.")
        except:
            print("Dropdown not found or failed to select.")

        # === 4. Wait for video elements to appear ===
        try:
            page.wait_for_selector('div.index-mobile_cardWrapper__SgzEk blockquote[data-video-id]', timeout=10000)
            print("Video elements loaded.")
        except:
            print("Video elements not found. Exiting.")
            return

        collected_videos = []
        empty_attempts = 0

        while len(collected_videos) < limit:
            iframe_elements = page.query_selector_all('div.index-mobile_cardWrapper__SgzEk blockquote[data-video-id]')
            new_videos = [
                {
                    'video_id': iframe.get_attribute('data-video-id'),
                    'url': f"https://www.tiktok.com/@_/video/{iframe.get_attribute('data-video-id')}"
                }
                for iframe in iframe_elements
                if iframe.get_attribute('data-video-id') not in [v['video_id'] for v in collected_videos]
            ]

            if not new_videos:
                empty_attempts += 1
                print(f"No new videos found. Empty attempts: {empty_attempts}")
                if empty_attempts >= 3:
                    print("No videos collected for 3 consecutive attempts. Ending crawl.")
                    break
            else:
                empty_attempts = 0

            collected_videos.extend(new_videos)
            print(f"Found {len(collected_videos)} videos so far...")

            if len(collected_videos) >= limit:
                print(f"Reached the limit of {limit} videos. Ending crawl.")
                break

            view_more_btn = page.query_selector('div[data-testid="cc_contentArea_viewmore_btn"]')
            if view_more_btn:
                view_more_btn.click()
                page.wait_for_timeout(2000)
            else:
                print("No 'View More' button found. Ending crawl.")
                break

        final_videos = collected_videos[:limit]
        print(f"Results saved to {output_file}")

        browser.close()
        
        return final_videos
        
import sys
# Example usage
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python playwright_tiktok_ads.py [limit]")
        sys.exit(1)
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    result = crawl_tiktok_videos("https://ads.tiktok.com/business/creativecenter/inspiration/popular/pc/vi", limit=limit, output_file="tiktok_videos.json")
    print("Result:")
    print(json.dumps(result, indent=2, ensure_ascii=False))