import subprocess
import sys
import time

# ===== Config =====
periods = [7]
type_filters = ['thịnh hành']
limit = 500  # chỉnh nếu cần
max_retries = 3  # số lần retry tối đa

# ===== Runner =====
for tf in type_filters:
    for pd in periods:
        print(f"=== Running: type_filter='{tf}', period={pd} days (limit={limit}) ===", flush=True)
        
        # Retry mechanism
        retry_count = 0
        success = False
        
        while retry_count <= max_retries and not success:
            try:
                if retry_count > 0:
                    print(f"[RETRY] Attempt {retry_count}/{max_retries} for type_filter='{tf}', period={pd}", flush=True)
                
                subprocess.run(
                    [sys.executable, "playwright_tiktok_ads.py", str(limit), tf, str(pd)],
                    check=True
                )
                success = True
                print(f"[SUCCESS] Completed: type_filter='{tf}', period={pd}", flush=True)
                
            except subprocess.CalledProcessError as e:
                retry_count += 1
                print(f"[ERROR] Run failed for type_filter='{tf}', period={pd} (attempt {retry_count}): {e}", flush=True)
                
                if retry_count <= max_retries:
                    wait_time = retry_count * 2  # tăng dần thời gian chờ: 2s, 4s, 6s
                    print(f"[WAIT] Waiting {wait_time}s before retry...", flush=True)
                    time.sleep(wait_time)
                else:
                    print(f"[FAILED] Max retries ({max_retries}) reached for type_filter='{tf}', period={pd}. Moving to next task.", flush=True)
        
        # Nghỉ 1s giữa các lần chạy cho nhẹ máy (tuỳ chọn)
        if success:
            time.sleep(5)