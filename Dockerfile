FROM python:3.12

# Thiết lập thư mục làm việc
WORKDIR /app
COPY . /app
# Cập nhật pip và setuptools
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Cài thêm Crawlee và Playwright
RUN python -m pip install 'crawlee[all]'
RUN playwright install --with-deps
# Cài các gói hệ thống mà Playwright cần
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libdbus-1-3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libxkbcommon0 \
    libatspi2.0-0 \
    libx11-xcb1 \
    libxcursor1 \
    libxi6 \
    libgtk-3-0 \
    libgdk-3-0 \
    && rm -rf /var/lib/apt/lists/*


ENV PORT=8000
# Lệnh chạy ứng dụng (dùng uvicorn)
CMD ["uvicorn", "video_fast_api:app", "--host", "0.0.0.0", "--port", "8000"]
