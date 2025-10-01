import asyncio
import json
import urllib.parse  # Import for URL encoding

from playwright.async_api import Page
from crawlee import Request
from crawlee.crawlers import PlaywrightCrawlingContext
from crawlee.router import Router
from datetime import datetime, timezone
import pytz
# ========== Thêm ở đầu file ==========
CAPTCHA_MODAL_SEL = '#captcha-verify-container-main-page'
CAPTCHA_CLOSE_BTN = '#captcha_close_button'
CAPTCHA_REFRESH_BTN = '#captcha_refresh_button'
CAPTCHA_SWITCH_BTN = '#captcha_switch_button'  # (Audio)

class CaptchaDetected(RuntimeError):
    """Ném lỗi này để Crawler tự retry request hiện tại."""

async def _dismiss_captcha(page, logger, wait_ms: int = 1200) -> bool:
    """
    Cố gắng đóng CAPTCHA nếu có: Close -> Refresh -> Switch 'Audio'.
    Trả về True nếu CAPTCHA biến mất; False nếu vẫn còn.
    """
    try:
        modal = page.locator(CAPTCHA_MODAL_SEL)
        if await modal.count() == 0:
            return True  # không có captcha
        if await modal.first.is_visible():
            logger.info("CAPTCHA detected -> trying to dismiss...")

            # 1) thử Close
            try:
                close_btn = page.locator(CAPTCHA_CLOSE_BTN).first
                if await close_btn.count() and await close_btn.is_visible():
                    await close_btn.click(timeout=1500)
                    await page.wait_for_timeout(wait_ms)
            except Exception:
                pass

            # check lại
            if await modal.first.is_visible():
                # 2) thử Refresh
                try:
                    refresh_btn = page.locator(CAPTCHA_REFRESH_BTN).first
                    if await refresh_btn.count() and await refresh_btn.is_visible():
                        await refresh_btn.click(timeout=1500)
                        await page.wait_for_timeout(wait_ms)
                except Exception:
                    pass

            # check lại
            if await modal.first.is_visible():
                # 3) thử switch Audio (đôi khi dễ hơn)
                try:
                    switch_btn = page.locator(CAPTCHA_SWITCH_BTN).first
                    if await switch_btn.count() and await switch_btn.is_visible():
                        await switch_btn.click(timeout=1500)
                        await page.wait_for_timeout(wait_ms)
                except Exception:
                    pass

            # lần cuối kiểm tra
            if await modal.first.is_visible():
                logger.warning("CAPTCHA still visible after attempts.")
                return False

        return True
    except Exception:
        # nếu có lỗi bất ngờ, coi như chưa xử được
        return False

async def _guard_captcha_or_retry(page, logger):
    """
    Gọi ở MỖI BƯỚC QUAN TRỌNG.
    Nếu không bỏ được CAPTCHA -> ném CaptchaDetected để framework retry.
    """
    ok = await _dismiss_captcha(page, logger)
    if not ok:
        raise CaptchaDetected("CAPTCHA_DETECTED_RETRY")

def convert_timestamp_to_vn_time(timestamp: int) -> str:
    # Khởi tạo timezone
    vn_tz = pytz.timezone("Asia/Ho_Chi_Minh")
    
    # Dùng timezone-aware UTC datetime (chuẩn mới)
    dt_utc = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    
    # Chuyển sang Asia/Ho_Chi_Minh
    dt_vn = dt_utc.astimezone(vn_tz)
    
    return dt_vn.strftime("%Y-%m-%d %H:%M:%S")


router = Router[PlaywrightCrawlingContext]()

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
    
# --- Cấu hình chung ---
MAX_COMMENTS = 30
SCROLL_PAUSE_MS = 1000

# --- Handler xử lý từng video riêng lẻ ---
@router.handler(label='video')
async def video_handler(context: PlaywrightCrawlingContext) -> None:
    url = context.request.user_data.get('url') or context.request.url
    max_comments = context.request.user_data.get('max_comments', MAX_COMMENTS)
    context.log.info(f'Start video crawl: {url}')
    await context.page.wait_for_load_state("networkidle", timeout=30000)
    # Lấy dữ liệu JSON từ trang
    elem = await context.page.query_selector('#__UNIVERSAL_DATA_FOR_REHYDRATION__')
    if not elem:
        raise RuntimeError('No JSON data element found on video page')
    
    await _guard_captcha_or_retry(context.page, context.log)
    
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
    
    try:
        skip_btn = context.page.locator("div.TUXButton-label:has-text('Skip')").first
        # Đợi tối đa 5s cho đến khi nút hiển thị
        await skip_btn.wait_for(timeout=5000)
        await skip_btn.click(timeout=1500)
    except Exception:
        pass
    await _guard_captcha_or_retry(context.page, context.log)
    
    num_comments = item_struct['stats']['commentCount']
    
    if num_comments > 0:
        seen = set()
        # await context.page.wait_for_timeout(20000)
        previous = 0
        retries = 0
        count_all = await context.page.locator("div.css-zjz0t7-5e6d46e3--DivCommentObjectWrapper.e16z10169").count()
        locator = context.page.locator("div.css-zjz0t7-5e6d46e3--DivCommentObjectWrapper.e16z10169").first  # <-- bỏ await
        await locator.scroll_into_view_if_needed(timeout=3000)

        COMMENT_SEL = "div.css-zjz0t7-5e6d46e3--DivCommentObjectWrapper.e16z10169"
        VIEW_MORE_INNER_SEL = (
            "div.css-1ey35vz-5e6d46e3--DivViewRepliesContainer.e1cx7wx92 "
            "span:has-text('Xem'), "
            "div.css-1ey35vz-5e6d46e3--DivViewRepliesContainer.e1cx7wx92 "
            "span:has-text('View')"
        )
        
        await _guard_captcha_or_retry(context.page, context.log)
        # Yêu cầu: MAX_COMMENTS, SCROLL_PAUSE_MS đã khai báo
        await context.page.wait_for_selector(COMMENT_SEL, timeout=3000)
        comments_loc = context.page.locator(COMMENT_SEL)

        vp = context.page.viewport_size or {"height": 800}

        previous = 0
        retries = 0

        async def expand_view_more_in_top_n(page, wrappers_loc, top_n, per_wrapper_click_limit=10) -> tuple[bool, bool]:
            """
            Trả về (changed, any_left):
            - changed: có mở thêm ít nhất 1 reply không
            - any_left: sau khi click, còn nút Xem nào trong top_n không
            """
            changed = False
            total_left = 0

            n_wrappers = await wrappers_loc.count()
            limit = min(top_n, n_wrappers)

            for i in range(limit):
                await _guard_captcha_or_retry(context.page, context.log)
                wrap = wrappers_loc.nth(i)
                # click tối đa per_wrapper_click_limit lần / wrapper để tránh kẹt
                clicks = 0
                while clicks < per_wrapper_click_limit:
                    btns = wrap.locator(VIEW_MORE_INNER_SEL)
                    n_btn = await btns.count()
                    if n_btn == 0:
                        break
                    # luôn lấy cái đầu vì sau click DOM thay đổi
                    btn = btns.first
                    if await btn.is_visible():
                        try:
                            await btn.scroll_into_view_if_needed(timeout=1500)
                        except Exception:
                            pass
                        try:
                            await btn.click(timeout=2000)
                            changed = True
                            clicks += 1
                            # cho UI cập nhật
                            await page.wait_for_timeout(2000)
                        except Exception:
                            # nếu click fail, thoát vòng while để tránh kẹt
                            break
                    else:
                        break

                # đếm còn lại ở wrapper này sau khi đã click
                total_left += await wrap.locator(VIEW_MORE_INNER_SEL).count()

            any_left = total_left > 0
            return changed, any_left

        while True:
            await _guard_captcha_or_retry(context.page, context.log)
                        # Mở các nút "Xem..." CHỈ trong top N = max_comments
            changed, any_left_in_top_n = await expand_view_more_in_top_n(
                context.page, comments_loc, max_comments, per_wrapper_click_limit=10
            )

            count_all = await comments_loc.count()
            if count_all >= max_comments:
                break


            # Đợi lazy-load
            await context.page.wait_for_timeout(SCROLL_PAUSE_MS)

            new_count = await comments_loc.count()
            if new_count == previous and not changed:
                retries += 1
            else:
                retries = 0
                previous = new_count

            # Điều kiện dừng theo đúng yêu cầu:
            # - đủ max_comments, hoặc
            # - retries > 2 và KHÔNG còn nút Xem trong top N wrappers
            if new_count >= max_comments or (retries > 2 and not any_left_in_top_n):
                break

            # --- helper: kéo VƯỢT QUA target ---
            async def _scroll_past(page, target_locator, overshoot_px: int) -> None:
                # 1) thử tìm container cuộn gần nhất rồi kéo quá target
                try:
                    await target_locator.scroll_into_view_if_needed(timeout=300)
                    await page.wait_for_timeout(50)
                    await target_locator.evaluate("""
                    (el, extra) => {
                        const isScrollable = (n) => {
                            if (!n || !n.ownerDocument) return false;
                            const cs = n.ownerDocument.defaultView.getComputedStyle(n);
                            return ['auto','scroll'].includes(cs.overflowY) && n.scrollHeight > n.clientHeight;
                        };
                        // tìm ancestor có overflow-y cuộn
                        let node = el.parentElement;
                        while (node) {
                            if (isScrollable(node)) {
                                // cuộn sao cho điểm bottom của el VƯỢT quá viewport của container
                                const elBottom = el.offsetTop + el.offsetHeight;
                                const targetTop = elBottom - node.clientHeight + extra; // vượt quá một đoạn
                                node.scrollTop = Math.max(0, targetTop);
                                return true;
                            }
                            node = node.parentElement;
                        }
                        // fallback: cuộn window vượt quá
                        const rect = el.getBoundingClientRect();
                        const absBottom = rect.bottom + window.scrollY;
                        window.scrollTo({ top: absBottom + extra, behavior: 'instant' });
                        return true;
                    }
                    """, overshoot_px)
                    return
                except Exception:
                    pass

                # 2) fallback cuối: lăn chuột
                try:
                    await page.mouse.wheel(0, overshoot_px)
                except Exception:
                    # fallback nữa: trang xuống 1 phát lớn
                    await page.evaluate("(y)=>window.scrollBy(0,y)", overshoot_px)

            # --- trong vòng lặp của bạn ---
            vp = context.page.viewport_size or {"height": 800}
            half_screen   = max(200, int(vp["height"] * 0.5))
            overshoot_px  = max(400, int(vp["height"] * 0.75))  # vượt ~3/4 màn hình

            boundary_index = min(max_comments, new_count) - 1
            if boundary_index >= 0:
                try:
                    last = comments_loc.nth(boundary_index)
                    await _scroll_past(context.page, last, overshoot_px=overshoot_px)
                except Exception:
                    await context.page.mouse.wheel(0, overshoot_px)
            else:
                await context.page.mouse.wheel(0, overshoot_px)

            await context.page.wait_for_timeout(SCROLL_PAUSE_MS)

            # mẹo nhỏ: nếu vẫn không tăng count, thử overshoot “mạnh” 1 lần trước khi tăng retries
            if (await comments_loc.count()) == new_count:
                try:
                    if boundary_index >= 0:
                        last = comments_loc.nth(boundary_index)
                        await _scroll_past(context.page, last, overshoot_px=vp["height"] * 2)  # mạnh tay
                        await context.page.wait_for_timeout(int(SCROLL_PAUSE_MS * 1.2))
                except Exception:
                    pass

        import re

        COMMENT_WRAPPER_SEL = 'div.css-zjz0t7-5e6d46e3--DivCommentObjectWrapper.e16z10169'
        LV1_USER_SEL       = 'div[data-e2e="comment-username-1"] a.link-a11y-focus'
        LV2_USER_SEL       = 'div[data-e2e="comment-username-2"] a.link-a11y-focus'
        LV1_TEXT_SEL       = 'span[data-e2e="comment-level-1"]'
        LV2_TEXT_SEL       = 'span[data-e2e="comment-level-2"]'
        LIKE_CONTAINER_SEL = 'div[role="button"][aria-pressed]'
        LIKE_COUNT_INNER   = 'span.TUXText'

        def _parse_int(text: str) -> int:
            import re
            t = (text or "").strip()
            m = re.search(r'([\d\.,]+)\s*([kKmM]?)', t)
            if not m: return 0
            num, unit = m.group(1), m.group(2).lower()
            num = num.replace('.', '').replace(',', '')
            if not num.isdigit():
                d = re.findall(r'\d+', t)
                return int(d[0]) if d else 0
            val = int(num)
            if unit == 'k': val *= 1000
            elif unit == 'm': val *= 1_000_000
            return val

        async def _get_like_from(scope_el) -> int:
            try:
                like_box = await scope_el.query_selector(LIKE_CONTAINER_SEL)
                if like_box:
                    span_num = await like_box.query_selector(LIKE_COUNT_INNER)
                    if span_num:
                        return _parse_int((await span_num.inner_text()) or "")
            except Exception:
                pass
            return 0

        # Thu thập threads (cmt lvl-1 + replies) + user href + likes
        comment_divs = await context.page.query_selector_all(COMMENT_WRAPPER_SEL)
        threads = []
        seen = set()

        for wrap in comment_divs:
            # ===== LV1 trong wrapper =====
            lv1_text_el = await wrap.query_selector(LV1_TEXT_SEL)
            if not lv1_text_el:
                continue
            lv1_text = (await lv1_text_el.inner_text() or "").strip()
            if not lv1_text:
                continue

            u1 = await wrap.query_selector(LV1_USER_SEL)
            lv1_user = {"name": "", "href": ""}
            if u1:
                try:
                    lv1_user["href"] = await u1.get_attribute("href") or ""
                    lv1_user["name"] = (await u1.inner_text() or "").strip()
                except Exception:
                    pass

            lv1_likes = await _get_like_from(wrap)  # like của item cha (scope ngay trong wrapper)

            thread = {
                "cmt_1": {
                    "user": lv1_user,
                    "text": lv1_text,
                    "likes": lv1_likes,
                    "replies": []
                }
            }

            # ===== LV2 trong wrapper (không dùng ancestor) =====
            reply_text_nodes = await wrap.query_selector_all(LV2_TEXT_SEL)
            reply_user_nodes = await wrap.query_selector_all(LV2_USER_SEL)
            print(f"Found {len(reply_text_nodes)} replies under this comment")
            
            # Đồng bộ theo index: tên/href thường align với text theo thứ tự DOM
            for i, rs in enumerate(reply_text_nodes):
                t = (await rs.inner_text() or "").strip()
                if not t:
                    continue

                user = {"name": "", "href": ""}
                if i < len(reply_user_nodes) and reply_user_nodes[i]:
                    try:
                        user["href"] = await reply_user_nodes[i].get_attribute("href") or ""
                        user["name"] = (await reply_user_nodes[i].inner_text() or "").strip()
                    except Exception:
                        pass

                # Like cho từng reply: lấy like container gần nhất *bên trong wrapper*,
                # ưu tiên node cha gần reply bằng evaluate(closest) để vẫn giữ scope tương đối.
                likes = 0
                try:
                    anc = await rs.evaluate_handle(
                        """el => el.closest('div')""")  # đủ dùng: wrapper item nhỏ nhất chứa reply
                    if anc:
                        # Tìm like container bắt đầu từ anc, fallback: wrap
                        likes = await _get_like_from(anc) or await _get_like_from(wrap)
                except Exception:
                    likes = await _get_like_from(wrap)

                thread["cmt_1"]["replies"].append({
                    "user":  user,
                    "text":  t,
                    "likes": likes
                })

            # ===== Dedupe theo (lv1_href, lv1_text, reply tuples) =====
            key = (
                thread["cmt_1"]["user"].get("href", ""),
                thread["cmt_1"]["text"],
                tuple((r["user"].get("href",""), r["text"]) for r in thread["cmt_1"]["replies"])
            )
            if key not in seen:
                seen.add(key)
                threads.append(thread)

        item['comments_content'] = threads[:max_comments]

        context.log.info(f'Collected {len(item["comments_content"])} threads')


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