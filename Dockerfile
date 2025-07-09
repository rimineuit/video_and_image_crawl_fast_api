FROM python:3.12

# Cài đặt thư viện hệ thống cần thiết cho Playwright trước
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gnupg \
    libnss3 \
    libxss1 \
    libasound2 \
    libx11-xcb1 \
    libxrandr2 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxfixes3 \
    libxi6 \
    libgtk-3-0 \
    libgdk-pixbuf2.0-0 \
    libatk1.0-0 \
    libdbus-1-3 && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Tạo thư mục làm việc
WORKDIR /app
# Copy toàn bộ mã nguồn
COPY . /app

# Copy file requirements trước để tận dụng cache
COPY requirements.txt .

# Cài đặt Python packages
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install 'crawlee[playwright]'

# Cài đặt Playwright và các trình duyệt liên quan
RUN python -m playwright install && \
    python -m playwright install-deps



ENV PORT=8000

CMD ["uvicorn", "video_fast_api:app", "--host", "0.0.0.0", "--port", "8000"]
