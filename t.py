import requests
from bs4 import BeautifulSoup
import json
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define headers to mimic a browser
headers = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "referer": "https://www.tiktok.com/",
}

def scrape_tiktok_video_metadata(video_url):
    try:
        # Send request to the video page
        response = requests.get(video_url, headers=headers)
        logger.info(f"Received [{response.status_code}] from: {video_url}")
        
        if response.status_code != 200:
            raise Exception(f"Failed request, Status Code {response.status_code}")

        # Parse HTML content
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Find the script tag with __UNIVERSAL_DATA_FOR_REHYDRATION__
        script_tag = soup.select_one("script[id='__UNIVERSAL_DATA_FOR_REHYDRATION__']")
        if not script_tag:
            raise Exception("Script tag not found")

        # Parse JSON data
        json_data = json.loads(script_tag.text)
        
        # Navigate to video metadata
        video_info = json_data.get("__DEFAULT_SCOPE__", {}).get("webapp.video-detail", {}).get("itemInfo", {}).get("itemStruct", {})
        
        if not video_info:
            raise Exception("Video metadata not found")

        # Extract common metadata fields
        metadata = {
            "video_id": video_info.get("id", "N/A"),
            "description": video_info.get("desc", "N/A"),
            "create_time": video_info.get("createTime", "N/A"),
            "author": video_info.get("author", {}).get("uniqueId", "N/A"),
            "author_nickname": video_info.get("author", {}).get("nickname", "N/A"),
            "stats": {
                "digg_count": video_info.get("stats", {}).get("diggCount", 0),
                "share_count": video_info.get("stats", {}).get("shareCount", 0),
                "comment_count": video_info.get("stats", {}).get("commentCount", 0),
                "play_count": video_info.get("stats", {}).get("playCount", 0),
                "collect_count": video_info.get("stats", {}).get("collectCount", 0),
            },
            "music_title": video_info.get("music", {}).get("title", "N/A"),
            "music_author": video_info.get("music", {}).get("authorName", "N/A"),
            "video_url": video_info.get("video", {}).get("playAddr", "N/A"),
            "hashtags": [tag.get("hashtagName", "") for tag in video_info.get("textExtra", []) if tag.get("hashtagName")],
            "is_ad": video_info.get("isAd", "N/A"),
        }

        return metadata

    except Exception as e:
        logger.error(f"Error scraping video metadata: {e}")
        return None

# Example usage
video_url = "https://www.tiktok.com/@username/video/7527651639302425876"
metadata = scrape_tiktok_video_metadata(video_url)

if metadata:
    print(json.dumps(metadata, indent=2))