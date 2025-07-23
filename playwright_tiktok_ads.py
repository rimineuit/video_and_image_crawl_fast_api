from playwright.sync_api import sync_playwright
import json
import gc
import time

def crawl_tiktok_videos(url, limit=1000):
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
            viewport={"width": 1280, "height": 720},
            bypass_csp=True,
            java_script_enabled=True
        )

        # Smart resource blocking
        def route_filter(route, request):
            blocked_types = ["image", "font", "stylesheet", "media"]
            blocked_keywords = ["analytics", "tracking", "collect", "adsbygoogle"]
            if (
                request.resource_type in blocked_types or
                any(keyword in request.url.lower() for keyword in blocked_keywords)
            ):
                return route.abort()
            return route.continue_()

        context.route("**/*", route_filter)
        
        page = context.new_page()
        page.goto(url)
        page.wait_for_load_state("domcontentloaded")
        print(f"Navigated to {url}")

        # === 1. Click cookie/banner if exists ===
        try:
            banner = page.wait_for_selector("#ccModuleBannerWrap > div > div > div > div", timeout=5000)
            banner.click()
            print("Banner clicked.")
        except:
            print("Banner not found or clickable.")

        # === 2. Fill language input ===
        try:
            input_field = page.wait_for_selector('input[placeholder="Nhập/chọn từ danh sách"]', timeout=5000)
            input_field.fill("vi")
            print("Filled input field with 'vi'.")
        except:
            print("Input field not found.")
        time.sleep(1)

        # === 3. Select dropdown item ===
        try:
            dropdown_item = page.wait_for_selector('body > div:nth-child(11) > div > div > div > div > div.byted-select-popover-panel-inner > div:nth-child(20)', timeout=5000)
            dropdown_item.click()
            print("Dropdown option selected.")
        except:
            print("Dropdown not found or failed to select.")

        # === 4. Wait for videos to appear ===
        try:
            page.wait_for_selector('div.index-mobile_cardWrapper__SgzEk blockquote[data-video-id]', timeout=10000)
            print("Video elements loaded.")
        except:
            print("Video elements not found. Exiting.")
            return

        collected_videos = []
        seen_video_ids = set()
        empty_attempts = 0

        while len(collected_videos) < limit:
            iframe_elements = page.query_selector_all('div.index-mobile_cardWrapper__SgzEk blockquote[data-video-id]')
            
            new_videos = []
            for iframe in iframe_elements:
                video_id = iframe.get_attribute('data-video-id')
                if video_id and video_id not in seen_video_ids:
                    seen_video_ids.add(video_id)
                    new_videos.append({
                        'video_id': video_id,
                        'url': f"https://www.tiktok.com/@_/video/{video_id}"
                    })

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
                # 👉 Scroll lên trước để tránh stuck DOM
                page.evaluate("window.scrollBy(0, -200)")
                page.wait_for_timeout(500)

                # 👉 Scroll tới nút View More rồi click
                view_more_btn.scroll_into_view_if_needed()
                page.wait_for_timeout(500)
                view_more_btn.click()
                print("Clicked 'View More'")

                try:
                    page.wait_for_function(
                        f'document.querySelectorAll("blockquote[data-video-id]").length > {len(seen_video_ids)}',
                        timeout=5000
                    )
                except:
                    print("Waited but no new videos appeared. Sleeping 2s.")
                    page.wait_for_timeout(2000)
            else:
                print("No 'View More' button found. Ending crawl.")
                break


            # Clear memory
            del iframe_elements, new_videos
            gc.collect()


        final_videos = collected_videos[:limit]

        browser.close()
        return final_videos

# Run example
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python playwright_tiktok_ads.py [limit]")
        sys.exit(1)
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    result = crawl_tiktok_videos("https://ads.tiktok.com/business/creativecenter/inspiration/popular/pc/vi", limit=limit)
    print("Result:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
