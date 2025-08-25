import os
import json
import psycopg2
from dotenv import load_dotenv
from urllib.parse import urlparse

# Load .env
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# Kết nối DB
conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

# Đọc JSON
with open("trend_videos.json", "r", encoding="utf-8") as f:
    data = json.load(f)

cur.execute(
    """
    UPDATE public.genz_trend 
    SET ranking = NULL
    """
)
# Insert video_id + ranking
for rank, item in enumerate(data, start=1):
    cur.execute(
        """
        INSERT INTO public.genz_trend (video_id, ranking)
        VALUES (%s, %s)
        ON CONFLICT (video_id) DO UPDATE SET ranking = EXCLUDED.ranking
        """,
        (item["video_id"], rank)
    )

conn.commit()
cur.close()
conn.close()
print("✅ Done!")
