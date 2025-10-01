# main.py

from datetime import timedelta
import os
import json
from typing import List
# /app/


from crawlee import ConcurrencySettings, Request
from crawlee.crawlers import PlaywrightCrawler

from routes import router

async def crawl_links_tiktok(url: str, browser_type: str, label: str, max_items: int, max_comments: int) -> None:
    """The crawler entry point."""

    # Create a crawler with the necessary settings
    concurrency_settings = ConcurrencySettings(
        max_concurrency=5,
        desired_concurrency=5,   # 👈 phải ≤ max_concurrency
        # min_concurrency=1,     # (tuỳ chọn)
    )

    crawler = PlaywrightCrawler(
        concurrency_settings=concurrency_settings,
        request_handler=router,
        headless=False,
        max_requests_per_crawl=50,
        request_handler_timeout=timedelta(seconds=1500),
        browser_type=browser_type,  # 'chromium' | 'firefox' | 'webkit'
        browser_launch_options={
            "args": ["--no-sandbox"]
        },
        browser_new_context_options={
            "permissions": [],
            "viewport": {"width": 1080, "height": 720},
        }
    )
    
    # Run the crawler to collect data from several user pages
    await crawler.run(
            [Request.from_url(url, user_data={'limit': max_items, 'max_comments': max_comments}, label=label)]
    )
    
import sys
import asyncio
import json
if __name__ == '__main__':
    if len(sys.argv) < 4:
        sys.exit("Usage: python get_tiktok_video_links_and_metadata.py <browser_type> <label> <max_items> <TikTok_URL>")
    
    tiktok_url = sys.argv[5].strip()
    web = sys.argv[1].strip() if len(sys.argv) > 2 else "firefox"
    label = sys.argv[2].strip() if len(sys.argv) > 3 else "newest"
    max_items = int(sys.argv[3].strip()) if len(sys.argv) > 4 else 30
    get_comments = sys.argv[4]
    max_comments = int(sys.argv[6]) if len(sys.argv) > 5 else 100
    asyncio.run(crawl_links_tiktok(tiktok_url, web, label, max_items, max_comments))
        
    
        