# main.py

from datetime import timedelta
import os
import json
from typing import List
# /app/
def load_all_json_data(folder_path="./storage/datasets/default") -> list[dict]:
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

async def crawl_links_tiktok(url: str, browser_type: str, label: str, max_items: int) -> None:
    """The crawler entry point."""

    # Create a crawler with the necessary settings
    crawler = PlaywrightCrawler(
        concurrency_settings=ConcurrencySettings(max_concurrency=1),
        request_handler=router,
        headless=False,
        max_requests_per_crawl=50,
        request_handler_timeout=timedelta(seconds=150),
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
    await crawler.run(
            [Request.from_url(url, user_data={'limit': max_items}, label=label)]
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
    asyncio.run(crawl_links_tiktok(tiktok_url, web, label, max_items))
        
    result = load_all_json_data()
    # Print the result in a pretty JSON format
    print("Result:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
        