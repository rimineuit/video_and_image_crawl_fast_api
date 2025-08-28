import os
import sys
import google.generativeai as genai

# API_KEY = os.getenv("GEMINI_API_KEY")
# if not API_KEY:
#     sys.exit("Vui lòng export GEMINI_API_KEY.")

genai.configure(api_key='AIzaSyAUeYtTRNafF4geV_eoO7JimqkLCcHhokU')

# Liệt kê & xóa
files = list(genai.list_files())  # iterator -> list
if not files:
    print("Không có file nào.")
    sys.exit(0)

deleted = 0
for f in files:
    # f.name ví dụ "files/abc123"
    print(f"Deleting {f.name} ...", end=" ")
    try:
        genai.delete_file(f.name)
        print("OK")
        deleted += 1
    except Exception as e:
        print(f"FAILED: {e}")

print(f"Xong. Đã xóa {deleted}/{len(files)} file.")
