# update_transcripts.py
# !pip install sqlalchemy psycopg2-binary python-dotenv

import os
import time
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from get_transcripts import download_transcript  # import trực tiếp hàm bạn đã viết

# ===== Config =====
BATCH_SIZE = 50
SLEEP_SEC  = 0.5

# ===== DB connect =====
load_dotenv()
db_url = os.getenv("DATABASE_URL")
if not db_url:
    raise RuntimeError("Missing DATABASE_URL in .env")

if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)

engine = create_engine(db_url, pool_pre_ping=True, future=True)

# ===== SQL =====
SQL_PICK = text("""
    SELECT id, url
    FROM public.tiktok_trend_capture
    WHERE playcount IS NOT NULL
      AND transcripts IS NULL
      AND url IS NOT NULL
    ORDER BY id
    LIMIT :limit
""")

SQL_UPDATE = text("""
    UPDATE public.tiktok_trend_capture
    SET transcripts = :tx
    WHERE id = :id AND transcripts IS NULL
""")

def main():
    total_done = 0
    while True:
        # Lấy một batch
        with engine.begin() as conn:
            rows = list(conn.execute(SQL_PICK, {"limit": BATCH_SIZE}))
        if not rows:
            print("✅ Không còn bản ghi nào cần cập nhật.")
            break

        for rid, url in rows:
            try:
                print(f"\n[FETCH] id={rid} url={url}")
                tx = download_transcript(url).strip()  # có thể rỗng

                if not tx:
                    print("  -> Không lấy được transcript, sẽ lưu chuỗi rỗng.")

                # Lưu lại (kể cả rỗng)
                with engine.begin() as conn:
                    res = conn.execute(SQL_UPDATE, {"tx": tx, "id": rid})
                    if res.rowcount == 1:
                        total_done += 1
                        print(f"  -> ĐÃ LƯU ({len(tx)} chars)")
                    else:
                        print("  -> Bị thay đổi trạng thái (đã có transcripts trước khi update). Bỏ qua.")

                time.sleep(SLEEP_SEC)

            except Exception as e:
                print(f"  !! Lỗi id={rid}: {e}")
                # tiếp tục các bản ghi khác

    print(f"\n🎯 Hoàn tất. Đã cập nhật: {total_done} hàng.")

if __name__ == "__main__":
    main()
