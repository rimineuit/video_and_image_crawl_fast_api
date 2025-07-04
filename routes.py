import asyncio
import json

from playwright.async_api import Page
from crawlee import Request
from crawlee.crawlers import PlaywrightCrawlingContext
from crawlee.router import Router

router = Router[PlaywrightCrawlingContext]()

# --- Cấu hình chung ---
MAX_COMMENTS = 50
SCROLL_PAUSE_MS = 1000

# --- Helper: extract video links from user page ---
async def extract_video_links(page: Page) -> list[Request]:
    links: list[Request] = []
    elements = await page.query_selector_all('[data-e2e="user-post-item"] a')
    for el in elements:
        href = await el.get_attribute('href')
        if href and '/video/' in href:
            links.append(Request.from_url(
                href, label='video', user_data={'url': href}
            ))
    return links

# --- Handler mặc định: crawl trang profile để lấy link video ---
@router.default_handler
async def default_handler(context: PlaywrightCrawlingContext) -> None:
    url = context.request.url
    context.log.info(f'Start profile crawl: {url}')
    
    # Lấy giới hạn số video cần crawl
    limit = context.request.user_data.get('limit', 10)
    if not isinstance(limit, int) or limit <= 0:
        raise ValueError('`limit` must be a positive integer')
    
    # Chờ nội dung đầu tiên hoặc nút load-more
    await context.page.locator('[data-e2e="user-post-item"], main button').first.wait_for()
    
    # Nếu có nút load-more thì click
    btn = await context.page.query_selector('main button')
    if btn:
        await btn.click()
    
    # Bắt đầu scroll bất đồng bộ
    scroll_task = asyncio.create_task(context.infinite_scroll())
    
    # Trong khi chưa đạt limit, tiếp tục lấy link, ngược lại hủy scroll
    while not scroll_task.done():
        links = await extract_video_links(context.page)
        if len(links) >= limit:
            scroll_task.cancel()
            break
        await asyncio.sleep(0.2)
    
    # Thêm request cho bước video handler
    to_add = (await extract_video_links(context.page))[:limit]
    if not to_add:
        raise RuntimeError('No video links found on profile page')
    await context.add_requests(to_add)
    context.log.info(f'Queued {len(to_add)} video requests')

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
    }
    
    # Crawl comment (tối đa MAX_COMMENTS)
    comments = set()
    previous = 0
    while len(comments) < MAX_COMMENTS:
        await context.page.wait_for_selector('span[data-e2e="comment-level-1"] p', timeout=10000)
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
