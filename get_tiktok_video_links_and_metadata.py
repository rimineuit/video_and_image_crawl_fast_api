# main.py

from datetime import timedelta
import os
import json

def load_all_json_data(folder_path="/app/storage/datasets/default") -> list[dict]:
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

async def crawl_links_tiktok(url: str) -> None:
    """The crawler entry point."""

    max_items = 5

    # Create a crawler with the necessary settings
    crawler = PlaywrightCrawler(
        # Limit scraping intensity by setting a limit on requests per minute
        concurrency_settings=ConcurrencySettings(max_concurrency=1),
        # We'll configure the `router` in the next step
        request_handler=router,
        # You can use `False` during development. But for production, it's always `True`
        headless=True,
        max_requests_per_crawl=50,
        # Increase the timeout for the request handling pipeline
        request_handler_timeout=timedelta(seconds=50),
        browser_type='firefox',  # or 'chromium' or 'webkit'
        # Limit any permissions to device data
        browser_new_context_options={'permissions': [],
                                     'viewport': {'width': 1280, 'height': 800},},
    )
    
    # Run the crawler to collect data from several user pages
    await crawler.run(
        [
            Request.from_url(url, user_data={'limit': max_items}),
        ]
    )
    
import sys
import asyncio

if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit("Usage: python get_tiktok_video_links_and_metadata.py <TikTok_URL>")
         
    tiktok_url = sys.argv[1].strip()
    asyncio.run(crawl_links_tiktok(tiktok_url))
    result = load_all_json_data()
    # Print the result in a pretty JSON format
    print("Result:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
