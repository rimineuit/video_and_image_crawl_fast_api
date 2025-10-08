# syntax=docker/dockerfile:1.7
FROM python:3.11-slim-bookworm AS app

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    # Đảm bảo pip cài bánh xe khi có thể (nhanh hơn)
    PIP_DEFAULT_TIMEOUT=100

WORKDIR /app

# --- System deps tối thiểu cho Chromium + ffmpeg + fonts ---
# Lưu ý: --no-install-recommends giúp giảm size
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl gnupg \
      # Playwright/Chromium runtime libs
      libnss3 libxss1 libasound2 libx11-xcb1 libxrandr2 \
      libxcomposite1 libxcursor1 libxdamage1 libxfixes3 libxi6 \
      libgtk-3-0 libatk1.0-0 libdbus-1-3 libgbm1 \
      # Fonts để render ổn định khi headless
      fonts-liberation fonts-dejavu-core \
      # Media
      ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# --- Tận dụng cache pip ---
# Sao chép requirements trước để cache layer pip
COPY requirements.txt /app/requirements.txt

# Dùng cache mount (BuildKit) để tăng tốc pip (không làm phình image)
RUN --mount=type=cache,target=/root/.cache/pip,sharing=locked \
    pip install --upgrade pip && \
    pip install -r requirements.txt


# --- Cài Chromium & deps của Playwright trong 1 lệnh ---
# --with-deps sẽ đảm bảo các system deps đủ, nhưng ta đã cài phần lớn ở trên.
# Lệnh này sẽ tải Chromium riêng của Playwright (ổn định hơn so với apt chromium)
RUN python -m playwright install --with-deps chromium

# (Tuỳ nhu cầu) Thiết lập Crawl4AI một lần trong image
# Nếu chỉ cần runtime, có thể bỏ 'doctor' để tiết kiệm thời gian build.
RUN crawl4ai-setup && crawl4ai-doctor

# Sao chép code sau cùng để giữ cache pip
COPY . /app

# Tạo user không phải root cho an toàn
RUN useradd -m -u 10001 appuser && chown -R appuser:appuser /app
USER appuser

ENV PORT=8000

# Healthcheck nhẹ (tuỳ chỉnh endpoint)
# HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
#   CMD wget -qO- http://127.0.0.1:${PORT}/health || exit 1

# Chạy Uvicorn (uvicorn[standard] giúp có uvloop/httptools)
CMD ["uvicorn", "video_fast_api:app", "--host", "0.0.0.0", "--port", "8000"]