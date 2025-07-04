FROM python:3.12

# Cập nhật pip và setuptools
RUN pip install -U pip setuptools

# Thiết lập thư mục làm việc
WORKDIR /app

# Cài dependencies Python
COPY requirements.txt .
RUN pip install -r requirements.txt

# Cài thêm Crawlee và Playwright
RUN pip install 'crawlee[all]'
RUN playwright install --with-deps

# Sao chép toàn bộ mã nguồn
COPY . .

# Thiết lập biến môi trường để đảm bảo stdout UTF-8
ENV PYTHONIOENCODING=utf-8
ENV PYTHONUTF8=1

# (Tuỳ chọn) Bật chế độ headless nếu cần
ENV HEADLESS=true

# Mở port (tuỳ bạn dùng bao nhiêu, thường là 8000 với FastAPI)
EXPOSE 8000
ENV PORT=8000
# Lệnh chạy ứng dụng (dùng uvicorn)
CMD ["uvicorn", "video_fast_api:app", "--host", "0.0.0.0", "--port", "8000"]
