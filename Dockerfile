FROM python:3.12

# Thiết lập thư mục làm việc
WORKDIR /app
COPY . /app
# Cập nhật pip và setuptools
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Cài thêm Crawlee và Playwright
RUN python -m pip install 'crawlee[all]'
RUN playwright install

ENV PORT=8000
# Lệnh chạy ứng dụng (dùng uvicorn)
CMD ["uvicorn", "video_fast_api:app", "--host", "0.0.0.0", "--port", "8000"]
