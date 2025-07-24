from playwright.sync_api import sync_playwright
import json
import gc
import time
import sys

# ===== Constants =====
TIKTOK_URL = "https://ads.tiktok.com/business/creativecenter/inspiration/popular/pc/vi"
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
def crawl_tiktok_videos(url, limit=1000):
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
                banner = page.wait_for_selector("#ccModuleBannerWrap div div div div", timeout=5000)
                banner.click()
                page.wait_for_timeout(1000)
                log("Banner clicked.")
            except:
                log("Banner not found or clickable.")

            # Set language to Vietnamese
            select_dropdown_option(
                page,
                "Nhập/chọn từ danh sách",
                "vi",
                'div.byted-select-popover-panel-inner div:nth-child(20)'
            )
            
            # ===== Kiểm tra đã chọn ngôn ngữ là "Việt Nam" =====
            try:
                lang_selector = page.wait_for_selector(
                    "#ccModuleBannerWrap div div div div span span span span div span:nth-child(1)",
                    timeout=5000
                )
                current_lang = lang_selector.inner_text().strip()
                if current_lang != "Việt Nam":
                    raise ValueError(f"Ngôn ngữ hiện tại là '{current_lang}', không phải 'Việt Nam'")
                log("Đã xác nhận ngôn ngữ là 'Việt Nam'.")
            except Exception as e:
                log(f"Lỗi khi kiểm tra ngôn ngữ: {e}", "ERROR")
                return []

            # # Sort by Likes ("Lượt thích")
            # try:
            #     trending_button = page.wait_for_selector(
            #         '#ccContentContainer > div.BannerLayout_listWrapper__2FJA_ > div > div.PopularList_listSearcher__Bko2l.index-mobile_listSearcher__rKZAb > div.ListFilter_container__DwDsk.index-mobile_container__3wl4i.PopularList_sorter__N_G9_.index-mobile_filters__LxraM > div:nth-child(1) > div.ListFilter_RightSearchWrap__UyaKk > div > span.byted-select.byted-select-size-md.byted-select-single.byted-can-input-grouped.CcRimlessSelect_ccRimSelector__m4xdd.index-mobile_ccRimSelector__S2lLr.index-mobile_sortWrapSelect__2Yw1N', timeout=5000
            #     )
            #     trending_button.click()
            #     page.wait_for_timeout(1000)

            #     likes_option = page.wait_for_selector('div[data-option-id="SelectOption35"]', timeout=5000)
            #     likes_option.click()
            #     page.wait_for_timeout(2000)
            #     log("Sorted by 'Lượt thích'.")
            # except Exception as e:
            #     log(f"Failed to sort by likes: {e}", "ERROR")

            # Wait for video elements
            

            try:
                page.wait_for_selector('blockquote[data-video-id]', timeout=10000)
                log("Video elements loaded.")
            except:
                log("Video elements not found. Exiting.", "ERROR")
                return []

            collected = []
            seen_ids = set()
            empty_attempts = 0

            while len(collected) < limit:
                video_elements = page.query_selector_all('blockquote[data-video-id]')
                new_found = 0

                for el in video_elements[-20:]:  # Only scan the most recent ones
                    video_id = el.get_attribute("data-video-id")
                    if video_id and video_id not in seen_ids:
                        seen_ids.add(video_id)
                        collected.append({
                            'video_id': video_id,
                            'url': f"https://www.tiktok.com/@_/video/{video_id}"
                        })
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

                if len(collected) >= limit:
                    break

                view_more = page.query_selector('div[data-testid="cc_contentArea_viewmore_btn"]')
                if view_more:
                    view_more.scroll_into_view_if_needed()
                    page.wait_for_timeout(500)
                    view_more.click()
                    log("Clicked 'View More' button.")
                    try:
                        page.wait_for_function(
                            f'document.querySelectorAll("blockquote[data-video-id]").length > {len(seen_ids)}',
                            timeout=10000
                        )
                    except:
                        page.wait_for_timeout(2000)
                else:
                    log("No 'View More' button found. Stopping.")
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
        result = crawl_tiktok_videos(TIKTOK_URL, limit=limit)
        log("Result:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as e:
        log(f"Unexpected error: {e}", "FATAL")
        sys.exit(1)
