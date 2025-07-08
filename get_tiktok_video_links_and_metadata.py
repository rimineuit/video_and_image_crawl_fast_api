# main.py

from datetime import timedelta
import os
import json
from typing import List
# /app/
def load_all_json_data(folder_path="storage/datasets/default") -> list[dict]:
    data_list = []

    for filename in os.listdir(folder_path):
        if filename.endswith(".json") and filename != "__metadata__.json":
            file_path = os.path.join(folder_path, filename)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    data_list.append(data)
            except Exception as e:
                print(f"Lỗi khi đọc file {filename}: {e}")

    return data_list

from crawlee import ConcurrencySettings, Request
from crawlee.crawlers import PlaywrightCrawler

from routes import router

async def crawl_links_tiktok(urls: List, browser_type: str, label: str) -> None:
    """The crawler entry point."""

    max_items = 30

    # Create a crawler with the necessary settings
    crawler = PlaywrightCrawler(
        concurrency_settings=ConcurrencySettings(max_concurrency=1),
        request_handler=router,
        headless=True,
        max_requests_per_crawl=50,
        request_handler_timeout=timedelta(seconds=90),
        browser_type=browser_type,  # 'chromium' hoặc 'firefox' hoặc 'webkit'
        browser_launch_options={
            "args": ["--no-sandbox"]
        },
        browser_new_context_options={
            'permissions': [],
            'viewport': {'width': 1280, 'height': 800},
        },
    )
    
    # Run the crawler to collect data from several user pages
    print(urls)
    await crawler.run(
        [
            Request.from_url(url, user_data={'limit': max_items}, label=label) for url in urls
        ]
    )
    
import sys
import asyncio
import json
if __name__ == '__main__':
    if len(sys.argv) < 3:
        sys.exit("Usage: python get_tiktok_video_links_and_metadata.py <browser_type> <label> <TikTok_URLs>")
         
    tiktok_urls = sys.argv[3:]
    web = sys.argv[1].strip() if len(sys.argv) > 2 else "firefox"
    label = sys.argv[2].strip() if len(sys.argv) > 3 else "newest"
    asyncio.run(crawl_links_tiktok(tiktok_urls, web, label))
    
    result = load_all_json_data()
    # Print the result in a pretty JSON format
    print("Result:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
        