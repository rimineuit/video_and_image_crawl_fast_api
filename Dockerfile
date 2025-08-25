FROM python:3.12-slim-bookworm


# Cần vài lib nền tảng chung + libgbm1 theo cảnh báo
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl gnupg ca-certificates \
    libnss3 libxss1 libasound2 libx11-xcb1 libxrandr2 \
    libxcomposite1 libxcursor1 libxdamage1 libxfixes3 libxi6 \
    libgtk-3-0 libatk1.0-0 libdbus-1-3 libgbm1 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Cài deps Python trước để tận dụng cache
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    # Cài browser + đúng bộ phụ thuộc cho bookworm
    python -m playwright install --with-deps chromium
RUN crawl4ai-setup
RUN crawl4ai-doctor 
# Copy code
COPY . /app

ENV PORT=8000
CMD ["uvicorn", "video_fast_api:app", "--host", "0.0.0.0", "--port", "8000"]
