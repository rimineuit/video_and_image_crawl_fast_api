#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
poster_generator.py
-------------------
Nhận đầu vào là danh sách file/URL ảnh (1–6) và một tiêu đề,
tạo HTML poster cố định kích thước 1080x1350 theo layout linh hoạt (3/4/5/6 sản phẩm).
Có thể tùy chọn render ra ảnh PNG/JPEG bằng Playwright.

Ví dụ:
  python poster_generator.py images/a.jpg images/b.jpg images/c.jpg -t "BST mới" -o out.html --png out.png
  python poster_generator.py https://example.com/1.jpg -t "Ưu đãi đặc biệt" --jpeg out.jpg --quality 90

Yêu cầu render ảnh: pip install playwright && playwright install chromium
"""

from __future__ import annotations

import argparse
import html as _html
import sys
from pathlib import Path
from typing import List, Sequence

# ==== (Tuỳ chọn) Render sang ảnh bằng Playwright ====
def html_string_to_image(
    html_content: str,
    output_path: Path,
    size=(1080, 1350),
    scale=2,
    wait="networkidle",
    transparent=False,
    image_type="png",
    quality: int | None = None,  # JPEG quality 0-100, chỉ dùng khi image_type="jpeg"
) -> None:
    """
    Chuyển HTML string thành ảnh bằng Playwright (Chromium).
    Lưu ý: cần cài playwright và data browser trước khi dùng.
    """
    # Import lazy để không bắt buộc người dùng cài playwright nếu chỉ cần HTML
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        raise RuntimeError(
            "Thiếu playwright. Cài bằng: pip install playwright && playwright install chromium"
        ) from e

    import tempfile, os

    output_path = Path(output_path).resolve()

    # Tạo file HTML tạm thời
    with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False, encoding="utf-8") as temp_file:
        temp_file.write(html_content)
        temp_html_path = temp_file.name

    try:
        url = Path(temp_html_path).as_uri()

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": size[0], "height": size[1]},
                device_scale_factor=scale,
            )
            page = context.new_page()
            page.set_default_timeout(60_000)

            page.goto(url, wait_until=wait)

            # Optional: ép nền trong suốt
            if transparent:
                page.evaluate("document.body.style.background = 'transparent'")

            # Chụp ảnh
            screenshot_kwargs = {
                "path": str(output_path),
                "full_page": False,  # cố định viewport 1080x1350
                "type": image_type,
            }
            if image_type == "jpeg" and quality is not None:
                screenshot_kwargs["quality"] = int(quality)

            page.screenshot(**screenshot_kwargs)

            context.close()
            browser.close()

    finally:
        # Xóa file tạm thời
        try:
            os.unlink(temp_html_path)
        except OSError:
            pass


# ==== Utilities ====
PLACEHOLDER = "https://via.placeholder.com/400x300/f0f0f0/888?text=No+Image"


def path_to_src(s: str) -> str:
    """Chuyển path local thành file:// URI; nếu đã là http(s) thì giữ nguyên."""
    s = s.strip()
    if not s:
        return PLACEHOLDER
    lower = s.lower()
    if lower.startswith("http://") or lower.startswith("https://") or lower.startswith("file://"):
        return s
    return Path(s).resolve().as_uri()


def sanitize_images(images: Sequence[str], target_len: int) -> List[str]:
    urls = [path_to_src(u) for u in images[:target_len]]
    while len(urls) < target_len:
        urls.append(PLACEHOLDER)
    return urls


def calculate_font_size(text: str) -> int:
    """
    Port từ JS:
    - baseSize=52, maxSize=120, minSize=32
    - Quy mô theo chiều dài chuỗi
    """
    container_width = 1000
    container_height = 180
    padding = 80
    available_width = container_width - padding  # chưa dùng đo pixel thật, ta giữ heuristic theo length

    base_size = 52
    max_size = 120
    min_size = 32

    text_length = len(text or "")
    if text_length <= 20:
        font_size = max_size
    elif text_length <= 50:
        font_size = max(base_size + (20 - text_length) * 1.5, min_size)
    elif text_length <= 80:
        font_size = max(base_size - (text_length - 50) * 0.3, min_size)
    else:
        # clamp tối đa 120 ký tự
        font_size = max(min_size + (120 - min(text_length, 120)) * 0.4, min_size)

    return int(font_size)


# ==== HTML Builders (1080x1350 cố định) ====
COMMON_HEAD = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{TITLE}</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Dancing+Script:wght@400;500;600;700&display=swap');

    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    .poster {{
      width: 1080px;
      height: 1350px;
      background: #f7f7f7;
      position: relative;
      font-family: 'Arial', sans-serif;
    }}
    .safe-area {{ width: 100%; height: 100%; position: relative; }}

    .text-area {{
      height: 180px;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 0 40px;
    }}
    .aesthetic-text {{
      font-family: 'Dancing Script', cursive;
      font-weight: 600;
      font-size: {FONT_SIZE}px;
      color: #333;
      text-align: center;
      letter-spacing: 1px;
      line-height: 1.1;
      word-wrap: break-word;
      hyphens: auto;
      max-width: 100%;
    }}

    .grid-container {{
      width: 100%;
      height: calc(100% - 200px);
      padding: 30px;
      display: grid;
      gap: 25px;
    }}
    .image-container {{
      position: relative;
      overflow: hidden;
      border-radius: 15px;
      box-shadow: 0 8px 25px rgba(0,0,0,0.1);
      background: white;
      padding: 12px;
    }}
    .image-container img {{
      width: 100%;
      height: 100%;
      object-fit: cover;
      object-position: center;
      border-radius: 8px;
      background: #f7f7f7;
    }}
  </style>
</head>
<body>
  <div class="poster">
    <div class="safe-area">
      {GRID}
      <div class="text-area">
        <div class="aesthetic-text">{TITLE_TEXT}</div>
      </div>
    </div>
  </div>
</body>
</html>
"""


def grid_for_3(img0: str, img1: str, img2: str) -> str:
    css = """
    <style>
      .grid-container {
        grid-template-columns: 1fr 1fr;
        grid-template-rows: 1fr 1fr;
      }
      .img-1 { grid-column: 1 / 3; grid-row: 1; }
      .img-2 { grid-column: 1; grid-row: 2; }
      .img-3 { grid-column: 2; grid-row: 2; }
    </style>
    """
    grid = f"""
    {css}
    <div class="grid-container">
      <div class="image-container img-1"><img src="{img0}" alt="Product 1" /></div>
      <div class="image-container img-2"><img src="{img1}" alt="Product 2" /></div>
      <div class="image-container img-3"><img src="{img2}" alt="Product 3" /></div>
    </div>
    """
    return grid


def grid_for_4(img0: str, img1: str, img2: str, img3: str) -> str:
    css = """
    <style>
      .grid-container {
        grid-template-columns: 1fr 1fr;
        grid-template-rows: 1fr 1fr;
      }
      .img-1 { grid-column: 1; grid-row: 1; }
      .img-2 { grid-column: 2; grid-row: 1; }
      .img-3 { grid-column: 1; grid-row: 2; }
      .img-4 { grid-column: 2; grid-row: 2; }
    </style>
    """
    grid = f"""
    {css}
    <div class="grid-container">
      <div class="image-container img-1"><img src="{img0}" alt="Product 1" /></div>
      <div class="image-container img-2"><img src="{img1}" alt="Product 2" /></div>
      <div class="image-container img-3"><img src="{img2}" alt="Product 3" /></div>
      <div class="image-container img-4"><img src="{img3}" alt="Product 4" /></div>
    </div>
    """
    return grid


def grid_for_5(img0: str, img1: str, img2: str, img3: str, img4: str) -> str:
    css = """
    <style>
      .grid-container {
        grid-template-columns: 1fr 2fr;
        grid-template-rows: 1fr 1fr;
      }
      .img-1 { grid-column: 1; grid-row: 1; }
      .img-2 { grid-column: 2; grid-row: 1; }
      .img-3 { grid-column: 1; grid-row: 2; }
      .img-4 {
        grid-column: 2;
        grid-row: 2;
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 15px;
        background: none;
        box-shadow: none;
        border-radius: 0;
        padding: 0;
      }
      .img-4 .sub-image {
        border-radius: 15px;
        overflow: hidden;
        box-shadow: 0 8px 25px rgba(0,0,0,0.1);
        background: white;
        padding: 12px;
      }
      .img-4 .sub-image img {
        width: 100%; height: 100%;
        object-fit: cover; object-position: center;
        border-radius: 8px; background: #f7f7f7;
      }
    </style>
    """
    grid = f"""
    {css}
    <div class="grid-container">
      <div class="image-container img-1"><img src="{img0}" alt="Product 1" /></div>
      <div class="image-container img-2"><img src="{img1}" alt="Product 2" /></div>
      <div class="image-container img-3"><img src="{img2}" alt="Product 3" /></div>
      <div class="img-4">
        <div class="sub-image"><img src="{img3}" alt="Product 4" /></div>
        <div class="sub-image"><img src="{img4}" alt="Product 5" /></div>
      </div>
    </div>
    """
    return grid


def grid_for_6(img0: str, img1: str, img2: str, img3: str, img4: str, img5: str) -> str:
    css = """
    <style>
      .grid-container {
        grid-template-columns: 1fr 2fr;
        grid-template-rows: 1fr 1fr 1fr;
        gap: 20px;
        padding: 30px 30px 20px 30px;
      }
      .img-1 { grid-column: 1; grid-row: 1; }
      .img-2 { grid-column: 2; grid-row: 1 / 3; }
      .img-3 { grid-column: 1; grid-row: 2; }
      .img-4 { grid-column: 1; grid-row: 3; }
      .img-5 {
        grid-column: 2;
        grid-row: 3;
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 15px;
        background: none;
        box-shadow: none;
        border-radius: 0;
        padding: 0;
      }
      .img-5 .sub-image {
        border-radius: 15px;
        overflow: hidden;
        box-shadow: 0 8px 25px rgba(0,0,0,0.1);
        background: white;
        padding: 12px;
      }
      .img-5 .sub-image img {
        width: 100%; height: 100%;
        object-fit: cover; object-position: center;
        border-radius: 8px; background: #f7f7f7;
      }
    </style>
    """
    grid = f"""
    {css}
    <div class="grid-container">
      <div class="image-container img-1"><img src="{img0}" alt="Product 1" /></div>
      <div class="image-container img-2"><img src="{img1}" alt="Product 2" /></div>
      <div class="image-container img-3"><img src="{img2}" alt="Product 3" /></div>
      <div class="image-container img-4"><img src="{img3}" alt="Product 4" /></div>
      <div class="img-5">
        <div class="sub-image"><img src="{img4}" alt="Product 5" /></div>
        <div class="sub-image"><img src="{img5}" alt="Product 6" /></div>
      </div>
    </div>
    """
    return grid


def build_html(image_urls: Sequence[str], title_text: str) -> str:
    """
    Chọn layout theo số ảnh (1-3 → layout 3; 4 → layout 4; 5 → layout 5; >=6 → layout 6).
    Luôn cố định poster 1080x1350.
    """
    # sanitize + đếm ảnh hợp lệ (không rỗng)
    non_empty = [u for u in (image_urls or []) if isinstance(u, str) and u.strip()]
    count = len(non_empty)

    # Chọn layout & số slot
    if count <= 3:
        urls = sanitize_images(non_empty, 3)
        grid = grid_for_3(*urls[:3])
        title = "3 Products Poster - TikTok Safe"
    elif count == 4:
        urls = sanitize_images(non_empty, 4)
        grid = grid_for_4(*urls[:4])
        title = "4 Products Poster - TikTok Safe"
    elif count == 5:
        urls = sanitize_images(non_empty, 5)
        grid = grid_for_5(*urls[:5])
        title = "5 Products Poster - TikTok Safe"
    else:
        urls = sanitize_images(non_empty, 6)
        grid = grid_for_6(*urls[:6])
        title = "6 Products Poster - TikTok Safe"

    safe_title_text = _html.escape(title_text or "Aesthetic")
    font_size = calculate_font_size(safe_title_text)

    html = COMMON_HEAD.format(
        TITLE=title,
        FONT_SIZE=font_size,
        GRID=grid,
        TITLE_TEXT=safe_title_text,
    )
    return html


# ==== CLI ====
def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Sinh HTML poster 1080x1350 từ danh sách ảnh (URL/path). "
                    "Có thể render ra PNG/JPEG bằng Playwright."
    )
    p.add_argument("images", nargs="+", help="Đường dẫn/URL ảnh (1–6 dùng, dư sẽ bỏ)")
    p.add_argument("-t", "--text", default="Aesthetic", help="Tiêu đề/overlay text")
    p.add_argument("-o", "--out-html", type=Path, default=Path("poster.html"),
                   help="File HTML xuất (mặc định: poster.html)")

    # Render ảnh (tuỳ chọn)
    out_group = p.add_mutually_exclusive_group()
    out_group.add_argument("--png", type=Path, help="Xuất PNG ra đường dẫn này")
    out_group.add_argument("--jpeg", type=Path, help="Xuất JPEG ra đường dẫn này")
    p.add_argument("--quality", type=int, default=None, help="JPEG quality 0–100")
    p.add_argument("--scale", type=int, default=2, help="Device scale factor khi render ảnh (mặc định 2)")
    p.add_argument("--wait", choices=["load", "domcontentloaded", "networkidle", "commit"],
                   default="networkidle", help="Chiến lược chờ tải trang khi render")

    return p.parse_args(list(argv))


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(sys.argv[1:] if argv is None else argv)

    html = build_html(args.images, args.text)

    # Ghi file HTML
    out_html: Path = args.out_html
    out_html.write_text(html, encoding="utf-8")
    print(f"Đã ghi HTML: {out_html.resolve()}")

    # Render ảnh nếu được yêu cầu
    if args.png or args.jpeg:
        out_img = args.png or args.jpeg
        img_type = "png" if args.png else "jpeg"
        html_string_to_image(
            html_content=html,
            output_path=out_img,
            size=(1080, 1350),   # cố định
            scale=args.scale,
            wait=args.wait,
            transparent=False,
            image_type=img_type,
            quality=args.quality if img_type == "jpeg" else None,
        )
        print(f"Đã xuất ảnh: {Path(out_img).resolve()}")


if __name__ == "__main__":
    main()
