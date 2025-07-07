import asyncio
import json

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
    await context.page.locator('[data-e2e="user-post-item"], main button').first.wait_for(timeout=30000)

    # Click vào nút load-more nếu có
    btn = await context.page.query_selector('main button')
    if btn:
        await btn.click()
        
    collected = {}
    retries = 0
    MAX_RETRIES = 10

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
    await context.push_data(final_links)



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
    MAX_RETRIES = 10

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
    await context.push_data(final_links)
    
# --- Handler xử lý từng video riêng lẻ ---
@router.handler(label='video')
async def video_handler(context: PlaywrightCrawlingContext) -> None:
    url = context.request.user_data.get('url') or context.request.url
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
        'video_url': url,
        'thumbnail': item_struct['video']['cover'],
        'publishedAt': convert_timestamp_to_vn_time(int(item_struct['createTime']))
    }
    
    # Crawl comment (tối đa MAX_COMMENTS)
    comments = set()
    previous = 0
    while len(comments) < MAX_COMMENTS:
        await context.page.wait_for_selector('span[data-e2e="comment-level-1"] p', timeout=30000)
        await asyncio.sleep(1)
        els = await context.page.query_selector_all('span[data-e2e="comment-level-1"] p')
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
