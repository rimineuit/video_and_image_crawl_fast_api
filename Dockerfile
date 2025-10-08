FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Chỉ copy requirements trước để tận dụng cache
COPY requirements.txt .

# Cài runtime deps + ffmpeg + toolchain (build-essential, pkg-config) để build wheel,
# cài Python deps, cài Playwright Chromium kèm deps hệ thống,
# chạy crawl4ai setup/doctor, rồi purge toolchain để giảm size
RUN apt-get update && apt-get install -y --no-install-recommends \
      curl gnupg ca-certificates \
      libnss3 libxss1 libasound2 libx11-xcb1 libxrandr2 \
      libxcomposite1 libxcursor1 libxdamage1 libxfixes3 libxi6 \
      libgtk-3-0 libatk1.0-0 libdbus-1-3 libgbm1 \
      ffmpeg \
      build-essential pkg-config \
 && pip install --upgrade pip \
 && pip install -r requirements.txt \
 && python -m playwright install --with-deps chromium \
 && python -m pip install 'crawlee[all]' \
 && crawl4ai-setup \
 && crawl4ai-doctor \
 && apt-get purge -y build-essential pkg-config \
 && apt-get autoremove -y \
 && rm -rf /var/lib/apt/lists/*

# Copy code sau cùng để cache layer pip
COPY . /app

ENV PORT=8000
CMD ["uvicorn", "video_fast_api:app", "--host", "0.0.0.0", "--port", "8000"]
