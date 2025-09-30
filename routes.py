import asyncio
import json
import urllib.parse  # Import for URL encoding

from playwright.async_api import Page
from crawlee import Request
from crawlee.crawlers import PlaywrightCrawlingContext
from crawlee.router import Router
from datetime import datetime, timezone
import pytz

def convert_timestamp_to_vn_time(timestamp: int) -> str:
    # Khởi tạo timezone
    vn_tz = pytz.timezone("Asia/Ho_Chi_Minh")
    
    # Dùng timezone-aware UTC datetime (chuẩn mới)
    dt_utc = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    
    # Chuyển sang Asia/Ho_Chi_Minh
    dt_vn = dt_utc.astimezone(vn_tz)
    
    return dt_vn.strftime("%Y-%m-%d %H:%M:%S")


router = Router[PlaywrightCrawlingContext]()

# --- Cấu hình chung ---
MAX_COMMENTS = 50
SCROLL_PAUSE_MS = 1000

import re

def normalize_views(view_str: str) -> int:
    """
    Chuyển chuỗi lượt xem (vd: '1.2M', '15K', '732') thành số nguyên.
    """
    view_str = view_str.strip().upper().replace(",", "")  # '1.2m' → '1.2M'

    match = re.match(r'^([\d\.]+)([MK]?)$', view_str)
    if not match:
        return 0

    number_str, suffix = match.groups()
    number = float(number_str)

    if suffix == 'M':
        return int(number * 1_000_000)
    elif suffix == 'K':
        return int(number * 1_000)
    else:
        return int(number)

async def extract_video_metadata(page: Page) -> list[dict]:
    """
    Trích xuất danh sách video với URL và lượt xem (đã chuẩn hóa).
    Trả về dạng: [{'url': ..., 'views': int}, ...]
    """
    results = []
    video_items = await page.query_selector_all('[data-e2e="user-post-item"]')

    for item in video_items:
        link_el = await item.query_selector('a[href*="/video/"]')
        href = await link_el.get_attribute('href') if link_el else None

        views_el = await item.query_selector('[data-e2e="video-views"]')
        views_text = await views_el.inner_text() if views_el else None

        if href and views_text:
            results.append({
                'url': href,
                'views': normalize_views(views_text)
            })

    return results

# --- Handler mặc định: crawl trang profile để lấy link video ---
@router.handler(label='newest')
async def newest_handler(context: PlaywrightCrawlingContext) -> None:
    url = context.request.url
    context.log.info(f'Start profile crawl: {url}')

    # Lấy giới hạn số video cần crawl
    limit = context.request.user_data.get('limit', 10)
    if not isinstance(limit, int) or limit <= 0:
        raise ValueError('`limit` must be a positive integer')

    # Đợi user-post hoặc nút load-more hiển thị
    await context.page.locator('[data-e2e="user-post-item"]').first.wait_for(timeout=3000)

    collected = {}
    retries = 0
    MAX_RETRIES = 3
    length_collected = 0
    while len(collected) < limit and retries < MAX_RETRIES:
        links = await extract_video_metadata(context.page)
        for item in links:
            url = item['url']
            if url not in collected:
                collected[url] = item['views']
        
        context.log.info(f'Found {len(collected)} video links so far...')

        if len(collected) >= limit:
            break

        # Scroll xuống và chờ load thêm nội dung
        await context.page.evaluate('window.scrollBy(0, window.innerHeight);')
        await asyncio.sleep(3)  # Chờ nội dung load xong
        if len(collected) > length_collected:
            length_collected = len(collected)
            retries = 0  # reset retries if new items found
        else: 
            retries += 1

    # Tạo danh sách link video và lượt xem từ collected
    final_links = [{'url': url, 'views': views} for url, views in collected.items()]

    if not final_links:
        raise RuntimeError('No video links found on profile page')
    context.log.info(f'Queued {len(final_links)} video requests')
    # Trả về danh sách link video và lượt xem
    await context.push_data(final_links[:limit])

@router.handler(label='popular')
async def popular_handler(context: PlaywrightCrawlingContext) -> None:
    url = context.request.url
    context.log.info(f'Start profile crawl: {url}')

    # Lấy giới hạn số video cần crawl
    limit = context.request.user_data.get('limit', 10)
    if not isinstance(limit, int) or limit <= 0:
        raise ValueError('`limit` must be a positive integer')
    
    # Chuyển sang tab Popular nếu có
    await context.page.locator('button[aria-label="Popular"]').first.wait_for(timeout=30000)
    popular_btn = await context.page.query_selector('button[aria-label="Popular"]')
    if popular_btn:
        await popular_btn.click()
        context.log.info('Switched to Popular tab')
        
    # Đợi user-post hoặc nút load-more hiển thị
    await context.page.locator('[data-e2e="user-post-item"], main button').first.wait_for(timeout=30000)

    # Click vào nút load-more nếu có
    btn = await context.page.query_selector('main button')
    if btn:
        await btn.click()
        
    collected = {}
    retries = 0
    MAX_RETRIES = 50

    while len(collected) < limit and retries < MAX_RETRIES:
        links = await extract_video_metadata(context.page)
        for item in links:
            url = item['url']
            if url not in collected:
                collected[url] = item['views']

        context.log.info(f'Found {len(collected)} video links so far...')

        if len(collected) >= limit:
            break

        # Scroll xuống và chờ load thêm nội dung
        await context.page.evaluate('window.scrollBy(0, window.innerHeight);')
        await asyncio.sleep(1)  # Chờ nội dung load xong

        retries += 1

    # Tạo danh sách link video và lượt xem từ collected
    final_links = [{'url': url, 'views': views} for url, views in collected.items()]

    if not final_links:
        raise RuntimeError('No video links found on profile page')
    context.log.info(f'Queued {len(final_links)} video requests')
    # Trả về danh sách link video và lượt xem
    await context.push_data(final_links[:limit])
from urllib.parse import urljoin
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

async def extract_comment_threads_from_page(
    page,
    *,
    base_url: str = "https://www.tiktok.com",
    max_scrolls: int = 10,
    click_rounds_per_thread: int = 8,
) -> list[dict]:
    """
    Trả về list[dict] dạng:
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
    """

    def _dedupe_preserve_order(items):
        seen = set()
        out = []
        for x in items:
            key = repr(x)  # dict/list unhashable -> dùng repr để khử trùng lặp sơ bộ
            if key not in seen:
                seen.add(key)
                out.append(x)
        return out

    async def _extract_user_from_level(thread, level: int):
        """
        Tìm user ở mức level (1 cho cmt gốc, 2 cho reply) trong phạm vi thread/container.
        Trả về (handle, display_name, profile_url) hoặc (None, None, None).
        """
        try:
            user_box = thread.locator(f'[data-e2e="comment-username-{level}"]').first
            # a[href="/@handle"]
            link = user_box.locator("a").first
            href = await link.get_attribute("href") or ""
            handle = None
            if "/@" in href:
                handle = href.split("/@")[-1].split("?")[0].strip().strip("/")
            # display name nằm trong <p> (nếu có)
            display_name = None
            try:
                dn = (await user_box.locator("p").first.inner_text()).strip()
                display_name = dn or handle
            except Exception:
                display_name = handle
            profile_url = urljoin(base_url, f"/@{handle}") if handle else None
            if handle:
                return handle, display_name, profile_url
        except Exception:
            pass
        return None, None, None

    # --- đảm bảo trang đã load phần comment ---
    try:
        await page.wait_for_timeout(5000)
        # bấm "Skip" nếu có
        try:
            skip_btn = page.locator("div.TUXButton-label:has-text('Skip')").first
            if await skip_btn.is_visible():
                await skip_btn.click(timeout=2000)
                await page.wait_for_timeout(800)
        except Exception:
            pass

        await page.mouse.wheel(0, 300)
        await page.wait_for_timeout(1500)

        top_level_any = page.locator('span[data-e2e="comment-level-1"]')
        try:
            await top_level_any.first.wait_for(timeout=15000)
        except PlaywrightTimeoutError:
            await page.mouse.wheel(0, 800)
            await page.wait_for_timeout(3000)
            await top_level_any.first.wait_for(timeout=10000)
    except Exception:
        # Không có comment
        return []

    # selector wrapper từng thread (comment gốc)
    thread_selector = "div.e16z10169"  # lớp hash có thể thay đổi theo phiên bản
    threads = page.locator(thread_selector)

    # --- cuộn để load đủ threads ---
    scrolls = 0
    last_count = 0
    while scrolls < max_scrolls:
        try:
            if await threads.count() > 0:
                await threads.last.scroll_into_view_if_needed(timeout=1500)
            else:
                await page.mouse.wheel(0, 1200)
        except Exception:
            await page.mouse.wheel(0, 1200)
        await page.wait_for_timeout(600)

        curr_count = await threads.count()
        if curr_count <= last_count:
            scrolls += 1
        else:
            last_count = curr_count
            scrolls = 0
        threads = page.locator(thread_selector)

    # --- helper: mở tất cả "Xem ... câu trả lời" trong phạm vi 1 thread ---
    async def _open_all_replies_for_thread(thread):
        async def _click_once(container) -> int:
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
                n = await loc.count()
                for i in range(n):
                    try:
                        btn = loc.nth(i)
                        if not await btn.is_visible():
                            continue
                        await btn.scroll_into_view_if_needed(timeout=800)
                        await btn.click(timeout=1500)
                        clicked += 1
                        await page.wait_for_timeout(300)
                    except Exception:
                        pass
            return clicked

        rounds = 0
        while rounds < click_rounds_per_thread:
            c = await _click_once(thread)
            if c == 0:
                break
            await page.wait_for_timeout(500)
            rounds += 1

    # --- duyệt và gom kết quả ---
    results = []
    total_threads = await threads.count()
    for idx in range(total_threads):
        thread = threads.nth(idx)
        try:
            await thread.scroll_into_view_if_needed(timeout=1000)
        except Exception:
            pass

        try:
            await _open_all_replies_for_thread(thread)
        except Exception:
            pass

        # cmt gốc
        root_text = ""
        try:
            root_span = thread.locator('span[data-e2e="comment-level-1"]').first
            root_text = ((await root_span.inner_text()) or "").strip()
        except Exception:
            pass

        h1, dn1, p1 = await _extract_user_from_level(thread, level=1)
        root_user = {"user_handle": h1, "display_name": dn1, "profile_url": p1}

        # replies
        reply_user_boxes = thread.locator('[data-e2e="comment-username-2"]')
        reply_text_spans = thread.locator('span[data-e2e="comment-level-2"]')

        replies = []
        n_users = await reply_user_boxes.count()
        n_texts = await reply_text_spans.count()
        n = min(n_users, n_texts)

        for i in range(n):
            text = ""
            try:
                text = ((await reply_text_spans.nth(i).inner_text()) or "").strip()
            except Exception:
                text = ""

            sub_container = reply_user_boxes.nth(i)
            h2, dn2, p2 = (None, None, None)
            try:
                # thử extractor theo level 2 trong thread
                h2, dn2, p2 = await _extract_user_from_level(thread, level=2)
                if not h2:
                    # fallback: lấy trực tiếp từ sub_container
                    try:
                        link2 = sub_container.locator("a").first
                        href2 = await link2.get_attribute("href") or ""
                        if "/@" in href2:
                            h2 = href2.split("/@")[-1].split("?")[0].strip().strip("/")
                        try:
                            dn2 = (await sub_container.locator("p").first.inner_text()).strip() or h2
                        except Exception:
                            dn2 = h2
                        p2 = urljoin(base_url, f"/@{h2}") if h2 else None
                    except Exception:
                        pass
            except Exception:
                pass

            replies.append({
                "text": text,
                "user": {"user_handle": h2, "display_name": dn2, "profile_url": p2}
            })

        results.append({
            "text": root_text,
            "user": root_user,
            "replies": _dedupe_preserve_order(replies),
        })

    return results

# --- Handler xử lý từng video riêng lẻ ---
@router.handler(label='video')
async def video_handler(context: PlaywrightCrawlingContext) -> None:
    url = context.request.user_data.get('url') or context.request.url
    get_comments = context.request.user_data.get('get_comments')
    context.log.info(f'Start video crawl: {url}')
    
    # Lấy dữ liệu JSON từ trang
    elem = await context.page.query_selector('#__UNIVERSAL_DATA_FOR_REHYDRATION__')
    if not elem:
        raise RuntimeError('No JSON data element found on video page')
    
    raw = await elem.text_content()
    data_json = json.loads(raw)
    item_struct = data_json['__DEFAULT_SCOPE__']['webapp.video-detail']['itemInfo']['itemStruct']
    
    # Tạo item cơ bản
    item = {
        'author': {
            'nickname': item_struct['author']['nickname'],
            'id': item_struct['author']['id'],
            'handle': item_struct['author']['uniqueId'],
            'signature': item_struct['author']['signature'],
            'followers': item_struct['authorStats']['followerCount'],
            'following': item_struct['authorStats']['followingCount'],
            'hearts': item_struct['authorStats']['heart'],
            'videos': item_struct['authorStats']['videoCount'],
        },
        'description': item_struct['desc'],
        'tags': [t['hashtagName'] for t in item_struct.get('textExtra', []) if t.get('hashtagName')],
        'hearts': item_struct['stats']['diggCount'],
        'shares': item_struct['stats']['shareCount'],
        'comments': item_struct['stats']['commentCount'],
        'plays': item_struct['stats']['playCount'],
        'saves': int(item_struct['stats']['collectCount']),  # <--- thêm dòng này
        'video_url': url,
        'thumbnail': item_struct['video']['cover'],
        'publishedAt': convert_timestamp_to_vn_time(int(item_struct['createTime']))
    }
    
    await context.page.evaluate('window.scrollBy(0, window.innerHeight);')
    comments = set()
    previous = 0
    while len(comments) < MAX_COMMENTS:
        await context.page.wait_for_selector('span[data-e2e="comment-level-1"]', timeout=30000)
        await context.page.wait_for_timeout(5000)
        els = await context.page.query_selector_all('span[data-e2e="comment-level-1"]')
        for c in els:
            comments.add((await c.inner_text()).strip())
        
        if len(comments) == previous:
            # Không thêm được comment mới → dừng
            break
        previous = len(comments)
        # Scroll để load thêm
        await context.page.evaluate('window.scrollBy(0, window.innerHeight);')
        await context.page.wait_for_timeout(SCROLL_PAUSE_MS)
    
    item['comments_content'] = list(comments)[:MAX_COMMENTS]
    context.log.info(f'Collected {len(item["comments_content"])} comments')
    
    # Lưu kết quả
    await context.push_data(item)

@router.handler(label='trending_videos_search')
async def trending_videos_search(context: PlaywrightCrawlingContext) -> None:
    url = context.request.url
    context.log.info(f'Start trending videos search crawl: {url}')
    # Wait for the search button and click it
    await context.page.locator('button[data-e2e="nav-search"]').first.click(timeout=30000)
    # Không đợi visible, chỉ cần attach là đủ
    await context.page.wait_for_selector('ul[data-e2e="search-transfer"] li[data-e2e="search-transfer-guess-search-item"]', state='attached', timeout=30000)

    await context.page.wait_for_timeout(5000) 
    # Extract text and generate search URL from the list items
    list_items = await context.page.query_selector_all('li[data-e2e="search-transfer-guess-search-item"]')
    trending_videos = []

    for item in list_items:
        title_el = await item.query_selector('h4')
        title = await title_el.inner_text() if title_el else None
        
        if title:
            # Encode the title to create a search URL
            encoded_title = urllib.parse.quote(title)
            search_url = f"https://www.tiktok.com/search?q={encoded_title}"
            
            trending_videos.append({'title': title, 'url': search_url})

    context.log.info(f'Collected trending videos: {trending_videos}')
    
    # Save the results
    await context.push_data(trending_videos)
    

@router.handler(label='tiktok_ads_get_url_trending_videos')
async def tiktok_ads(context: PlaywrightCrawlingContext) -> None:
    # Get limit from user data
    limit = context.request.user_data.get('limit', 10)
    if not isinstance(limit, int) or limit <= 0:
        raise ValueError('`limit` must be a positive integer')

    url = context.request.url
    context.log.info(f'Start trending videos search crawl: {url}')
    
    collected_videos = []
    retries = 0
    MAX_RETRIES = 10

    while len(collected_videos) < limit and retries < MAX_RETRIES:
        # Extract video IDs and URLs
        iframe_elements = await context.page.query_selector_all('div.index-mobile_cardWrapper__SgzEk blockquote[data-video-id]')
        new_videos = [
            {
                'video_id': await iframe.get_attribute('data-video-id'),
                'url': f"https://www.tiktok.com/@_/video/{await iframe.get_attribute('data-video-id')}"
            }
            for iframe in iframe_elements
            if await iframe.get_attribute('data-video-id') not in [v['video_id'] for v in collected_videos]
        ]
        collected_videos.extend(new_videos)

        context.log.info(f'Found {len(collected_videos)} videos so far...')
        
        if len(collected_videos) >= limit:
            break
            
        # Try to click "View More" button if available
        view_more_btn = await context.page.query_selector('div[data-testid="cc_contentArea_viewmore_btn"]')
        if view_more_btn:
            await view_more_btn.click()
            await context.page.wait_for_timeout(2000)  # Wait for new content to load
        else:
            # If no button found, we've reached the end
            break

        retries += 1

    # Trim to limit and save results
    final_videos = collected_videos[:limit]
    context.log.info(f'Collected {len(final_videos)} videos')
    await context.push_data(final_videos)