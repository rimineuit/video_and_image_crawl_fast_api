FROM python:3.12

WORKDIR /app
COPY . /app

RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    python -m pip install 'crawlee[playwright]'
RUN python -m playwright install 
RUN apt-get update && apt-get install -y \
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
    libdbus-1-3 \
    --no-install-recommends && \
    apt-get clean && rm -rf /var/lib/apt/lists/*


ENV PORT=8000

CMD ["uvicorn", "video_fast_api:app", "--host", "0.0.0.0", "--port", "8000"]
