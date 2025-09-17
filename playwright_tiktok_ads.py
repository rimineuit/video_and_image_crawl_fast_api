from playwright.sync_api import sync_playwright
import json
import gc
import time
import sys

# ===== Constants =====
TIKTOK_URL = "https://ads.tiktok.com/business/creativecenter/inspiration/popular/pc/vi"
# Block resource types - giữ những cần thiết cho scraping
BLOCKED_TYPES = {
    "image", 
    "font", 
    "stylesheet", 
    "media",
    "websocket",  # real-time connections không cần
    "manifest",   # app manifests
    "texttrack",  # video captions/subtitles
    "eventsource" # server-sent events
}

# Block URLs chứa keywords này
BLOCKED_KEYWORDS = {
    # Analytics & Tracking
    "analytics", "tracking", "collect", "adsbygoogle",
    "googletagmanager", "gtag", "facebook.com/tr", "pixel",
    "doubleclick", "googlesyndication", "googleadservices",
    
    # Social widgets & embeds (không cần cho scraping)
    "widget", "embed", "share-button", "social",
    
    # Ads & Marketing
    "adsystem", "advertising", "marketing", "campaign",
    
    # Monitoring & Error reporting
    "sentry", "bugsnag", "rollbar", "logrocket", "hotjar",
    
    # CDN assets không cần thiết
    "webfont", "woff", "woff2", "ttf", "eot",
    
    # Video/Audio (nếu không cần preview)
    "mp4", "webm", "ogg", "mp3", "wav",  # uncomment nếu muốn block media files
}

# Optional: Block specific domains hoàn toàn
BLOCKED_DOMAINS = {
    "google-analytics.com",
    "googletagmanager.com", 
    "doubleclick.net",
    "facebook.com",
    "connect.facebook.net",
    "analytics.tiktok.com",  # TikTok's own analytics
}

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
def crawl_tiktok_videos(url, limit=1000, type_filter="thịnh hành", period="7"):
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
            url = request.url.lower()
            
            # Block by resource type
            if request.resource_type in BLOCKED_TYPES:
                return route.abort()
            
            # Block by keywords in URL
            if any(keyword in url for keyword in BLOCKED_KEYWORDS):
                return route.abort()
            
            # Block by domain (optional)
            if any(domain in url for domain in BLOCKED_DOMAINS):
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
                "việt nam",
                'div.byted-select-popover-panel-inner span.byted-high-light:has-text("Việt Nam")'
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
            
            
            # 1) Mở dropdown (không gán .wait_for() vào biến)
            dropdown = page.locator('#ccContentContainer > div.BannerLayout_listWrapper__2FJA_ > div > div.PopularList_listSearcher__Bko2l.index-mobile_listSearcher__rKZAb > div.ListFilter_container__DwDsk.index-mobile_container__3wl4i.PopularList_sorter__N_G9_.index-mobile_filters__LxraM > div:nth-child(1) > div.ListFilter_RightSearchWrap__UyaKk > div > span.byted-select.byted-select-size-md.byted-select-single.byted-can-input-grouped.CcRimlessSelect_ccRimSelector__m4xdd.index-mobile_ccRimSelector__S2lLr.index-mobile_sortWrapSelect__2Yw1N > span > span > span > div')
            dropdown.click()  # click tự đợi visible + enabled

            # 2) Chọn option theo text - thu hẹp selector để chỉ còn 1 node
            option = page.locator('div.byted-select-option div', has_text=type_filter).first
            option.click()
            page.wait_for_timeout(10000)
            
            log(f"Filter type '{type_filter}' selected.")
            
            page.wait_for_selector('#tiktokPeriodSelect > span > div > div', timeout=10000)

            period_button = page.query_selector('#tiktokPeriodSelect > span > div > div')
            if period_button:
                period_button.click()
                page.wait_for_selector(f"div.creative-component-single-line:has-text('{period} ngày qua')", timeout=5000)

                month_period = page.query_selector(f"div.creative-component-single-line:has-text('{period} ngày qua')")
                if month_period:
                    month_period.click()
                    log(f"Đã chọn khoảng thời gian '{period}'.")
            else:
                log("Không tìm thấy nút chọn khoảng thời gian.", "ERROR")
                return []
            
            page.wait_for_timeout(10000)

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
import os
import re
import sys
from typing import List, Dict, Tuple, Optional
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv


def save_trending_video_tiktok(videos: List[Dict], period: int, type_filter: str):
    """Lưu danh sách video TikTok vào PostgreSQL (nhanh, đơn giản).
       Yêu cầu: tiktok_trend_capture_detail(video_id PK, url)"""
    if not videos:
        print("No videos to save.")
        return

    load_dotenv()
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL not found in environment (.env).")

    # dedup theo video_id để tránh chèn trùng không cần thiết
    seen = set()
    vids = []
    for v in videos:
        vid = v.get("video_id")
        url = v.get("url")
        if not vid or not url:
            continue
        if vid in seen:
            continue
        seen.add(vid)
        vids.append(v)

    try:
        with psycopg2.connect(db_url) as conn:
            with conn.cursor() as cur:
                # (tùy chọn) tăng tốc commit cho batch này
                cur.execute("SET LOCAL synchronous_commit TO OFF;")

                # 1) UPSERT vào DETAIL trước (2 cột)
                detail_rows = [(v["video_id"], v["url"]) for v in vids]
                if detail_rows:
                    execute_values(
                        cur,
                        """
                        INSERT INTO tiktok_trend_capture_detail (video_id, url)
                        VALUES %s
                        ON CONFLICT (video_id) DO UPDATE SET url = EXCLUDED.url
                        """,
                        detail_rows,
                        template="(%s,%s)",
                        page_size=5000,
                    )

                # 2) XÓA capture theo period + type_dropdown
                cur.execute(
                    "DELETE FROM tiktok_trend_capture WHERE period=%s AND type_dropdown=%s",
                    (period, type_filter),
                )

                # 3) INSERT mới toàn bộ capture (không cần ON CONFLICT)
                capture_rows = [
                    (v["video_id"], v["url"], period, type_filter, v.get("ranking"))
                    for v in vids
                ]
                if capture_rows:
                    execute_values(
                        cur,
                        """
                        INSERT INTO tiktok_trend_capture
                            (video_id, url, period, type_dropdown, ranking)
                        VALUES %s
                        """,
                        capture_rows,
                        template="(%s,%s,%s,%s,%s)",
                        page_size=5000,
                    )

                print(f"Detail upserted: {len(detail_rows)}, capture inserted: {len(capture_rows)}")

    except Exception as e:
        print(f"Database error: {e}")
            
# ===== CLI Runner =====
if __name__ == "__main__":
    try:
        limit = int(sys.argv[1]) if len(sys.argv) > 1 else 10
        type_filter = sys.argv[2] if len(sys.argv) > 2 else "Thích"
        period = sys.argv[3] if len(sys.argv) > 3 else "7"
        result = crawl_tiktok_videos(TIKTOK_URL, limit=limit, type_filter=type_filter, period=period)
        for idx, item in enumerate(result, start=1):
            item["ranking"] = idx

        log("Result:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        # filename = f"trend_videos.json"   

        # with open(filename, "w", encoding="utf-8") as f:
        #     json.dump(result, f, indent=2, ensure_ascii=False)

        # print(f"Kết quả đã lưu vào {filename}")
        # save_trending_video_tiktok(result, period=int(period), type_filter=type_filter)
    except Exception as e:
        log(f"Unexpected error: {e}", "FATAL")
        sys.exit(1)