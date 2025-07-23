import json
import requests
from bs4 import BeautifulSoup

def calc_eer(hearts, comments, shares, saves, plays):
    if plays == 0:
        return 0
    return ((hearts * 1 + comments * 5 + shares * 7 + saves * 10) / plays) * 100

def fetch_tiktok_video_data(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
    }

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise RuntimeError(f"Failed to fetch video page: {response.status_code}")

    soup = BeautifulSoup(response.text, 'html.parser')
    elem = soup.find('script', id='__UNIVERSAL_DATA_FOR_REHYDRATION__')
    if not elem:
        raise RuntimeError('No JSON data element found on video page')

    raw = elem.string
    data_json = json.loads(raw)
    item_struct = data_json['__DEFAULT_SCOPE__']['webapp.video-detail']['itemInfo']['itemStruct']

    music_info = item_struct.get('music', {})
    music = {
        'id': music_info.get('id'),
        'title': music_info.get('title'),
        'play_url': music_info.get('playUrl'),
        'author_name': music_info.get('authorName'),
        'cover_large': music_info.get('coverLarge'),
        'duration': music_info.get('duration')
    }

    stats = item_struct['stats']
    hearts = stats['diggCount']
    comments = stats['commentCount']
    shares = stats['shareCount']
    saves = int(stats['collectCount'])
    plays = stats['playCount']

    eer_score = calc_eer(hearts, comments, shares, saves, plays)

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
        'hearts': hearts,
        'shares': shares,
        'comments': comments,
        'plays': plays,
        'saves': saves,
        'eer_score': round(eer_score, 2),
        'video_url': url,
        'thumbnail': item_struct['video']['cover'],
        'publishedAt': convert_timestamp_to_vn_time(int(item_struct['createTime'])),
        'music': music
    }

    return item

def convert_timestamp_to_vn_time(timestamp):
    from datetime import datetime, timezone, timedelta
    vn_timezone = timezone(timedelta(hours=7))  # Vietnam timezone (UTC+7)
    return datetime.fromtimestamp(timestamp, tz=vn_timezone).strftime('%Y-%m-%d %H:%M:%S')

def fetch_video_list(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def main():
    input_file = "tiktok_videos.json"
    output_file = "tiktok_video_data.json"

    video_list = fetch_video_list(input_file)
    all_video_data = []

    for video in video_list:
        try:
            video_data = fetch_tiktok_video_data(video['url'])
            all_video_data.append(video_data)
            print(f"Fetched data for {video['url']}")
        except Exception as e:
            print(f"Failed to fetch data for {video['url']}: {e}")

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_video_data, f, ensure_ascii=False, indent=4)
    print(f"Data saved to {output_file}")

if __name__ == "__main__":
    main()
