from pathlib import Path
import argparse
import tempfile
import os
from playwright.sync_api import sync_playwright

def parse_size(s: str):
    # "1080x1350" -> (1080, 1350)
    try:
        w, h = s.lower().split("x")
        return int(w), int(h)
    except Exception:
        raise argparse.ArgumentTypeError("Kích thước phải dạng WxH, ví dụ: 1080x1350")

def html_string_to_image(
    html_content: str,
    output_path: Path,
    size=(1080, 1350),
    scale=2,
    full_page=False,
    wait="networkidle",
    transparent=False,
    image_type="png",
    quality=None,  # JPEG quality 0-100, chỉ dùng khi image_type="jpeg"
):
    """
    Chuyển HTML string thành ảnh
    
    Args:
        html_content (str): Nội dung HTML dưới dạng string
        output_path (Path): Đường dẫn file ảnh xuất
        size (tuple): Kích thước viewport (width, height)
        scale (int): Device scale factor để tăng độ nét
        full_page (bool): Chụp full page hay chỉ viewport
        wait (str): Chiến lược chờ tải trang
        transparent (bool): Nền trong suốt
        image_type (str): Định dạng ảnh ("png" hoặc "jpeg")
        quality (int): Chất lượng JPEG (0-100)
    """
    
    output_path = Path(output_path).resolve()
    
    # Tạo file HTML tạm thời
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as temp_file:
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
                "full_page": full_page,
                "type": image_type,
            }
            if image_type == "jpeg" and quality is not None:
                screenshot_kwargs["quality"] = int(quality)

            page.screenshot(**screenshot_kwargs)

            context.close()
            browser.close()

        print(f"Đã xuất ảnh: {output_path}")
        
    finally:
        # Xóa file tạm thời
        try:
            os.unlink(temp_html_path)
        except OSError:
            pass

def html_file_to_image(
    input_html: Path,
    output_path: Path = None,
    size=(1080, 1350),
    scale=2,
    full_page=False,
    wait="networkidle",
    transparent=False,
    image_type="png",
    quality=None,
):
    """Giữ lại function cũ để tương thích ngược"""
    input_html = input_html.resolve()
    if not input_html.exists():
        raise FileNotFoundError(f"Không tìm thấy file: {input_html}")

    if output_path is None:
        ext = ".png" if image_type == "png" else ".jpg"
        output_path = input_html.with_suffix(ext)
    
    # Đọc HTML content từ file
    with open(input_html, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    html_string_to_image(
        html_content=html_content,
        output_path=output_path,
        size=size,
        scale=scale,
        full_page=full_page,
        wait=wait,
        transparent=transparent,
        image_type=image_type,
        quality=quality,
    )

def main():
    parser = argparse.ArgumentParser(description="Convert HTML to image using Playwright")
    parser.add_argument("html", type=Path, help="Đường dẫn file HTML")
    parser.add_argument("-o", "--out", type=Path, help="Đường dẫn file ảnh xuất")
    parser.add_argument("--size", type=parse_size, default="1080x1350",
                        help="Kích thước viewport WxH, mặc định 1080x1350")
    parser.add_argument("--scale", type=int, default=2, help="device scale factor (mặc định 2)")
    parser.add_argument("--full", action="store_true", help="Chụp full page (cuộn trang dài)")
    parser.add_argument("--wait", choices=["load", "domcontentloaded", "networkidle", "commit"],
                        default="networkidle", help="Chiến lược chờ tải trang")
    parser.add_argument("--transparent", action="store_true", help="Nền trong suốt (PNG)")
    parser.add_argument("--type", choices=["png", "jpeg"], default="png", help="Định dạng ảnh xuất")
    parser.add_argument("--quality", type=int, default=None,
                        help="Chỉ dùng cho JPEG (0-100)")
    parser.add_argument("html")
    args = parser.parse_args()

    html_file_to_image(
        input_html=args.html,
        output_path=args.out,
        size=args.size,
        scale=args.scale,
        full_page=args.full,
        wait=args.wait,
        transparent=args.transparent,
        image_type=args.type,
        quality=args.quality,
    )

# Example usage:
if __name__ == "__main__":
    # Có thể dùng như CLI hoặc import function
    
    # Ví dụ sử dụng html_string_to_image:
    html_example = """<!DOCTYPE html>\n<html lang="en">\n<head>\n    <meta charset="UTF-8">\n    <meta name="viewport" content="width=device-width, initial-scale=1.0">\n    <title>6 Products Poster - TikTok Safe</title>\n    <style>\n        @import url('https://fonts.googleapis.com/css2?family=Dancing+Script:wght@400;500;600;700&display=swap');\n        \n        * {\n            margin: 0;\n            padding: 0;\n            box-sizing: border-box;\n        }\n        \n        .poster {\n            width: 1080px;\n            height: 1350px;\n            background: #f7f7f7;\n            position: relative;\n            font-family: 'Arial', sans-serif;\n        }\n        \n        .safe-area {\n            width: 100%;\n            height: 100%;\n            position: relative;\n        }\n        \n        .grid-container {\n            width: 100%;\n            height: calc(100% - 200px);\n            padding: 30px 30px 20px 30px;\n            display: grid;\n            grid-template-columns: 1fr 2fr;\n            grid-template-rows: 1fr 1fr 1fr;\n            gap: 20px;\n        }\n        \n        .text-area {\n            height: 180px;\n            display: flex;\n            align-items: center;\n            justify-content: center;\n            padding: 0 40px;\n        }\n        \n        .image-container {\n            position: relative;\n            overflow: hidden;\n            border-radius: 15px;\n            box-shadow: 0 8px 25px rgba(0,0,0,0.1);\n            background: white;\n            padding: 12px;\n        }\n        \n        .image-container img {\n            width: 100%;\n            height: 100%;\n            object-fit: cover;\n            object-position: center;\n            border-radius: 8px;\n        }\n        \n        .img-4 img,\n        .img-5 .sub-image img {\n            background: #f7f7f7;\n        }\n        \n        .img-1 { grid-column: 1; grid-row: 1; }\n        .img-2 { grid-column: 2; grid-row: 1 / 3; }\n        .img-3 { grid-column: 1; grid-row: 2; }\n        .img-4 { grid-column: 1; grid-row: 3; }\n        .img-5 {\n            grid-column: 2;\n            grid-row: 3;\n            display: grid;\n            grid-template-columns: 1fr 1fr;\n            gap: 15px;\n            background: none;\n            box-shadow: none;\n            border-radius: 0;\n        }\n        \n        .img-5 .sub-image {\n            border-radius: 15px;\n            overflow: hidden;\n            box-shadow: 0 8px 25px rgba(0,0,0,0.1);\n            background: white;\n            padding: 12px;\n        }\n        \n        .img-5 .sub-image img {\n            width: 100%;\n            height: 100%;\n            object-fit: cover;\n            object-position: center;\n            border-radius: 8px;\n        }\n        \n        .aesthetic-text {\n            font-family: 'Dancing Script', cursive;\n            font-weight: 600;\n            font-size: 47px;\n            color: #333;\n            text-align: center;\n            letter-spacing: 1px;\n            line-height: 1.1;\n            word-wrap: break-word;\n            hyphens: auto;\n            max-width: 100%;\n        }\n    </style>\n</head>\n<body>\n    <div class="poster">\n        <div class="safe-area">\n            <div class="grid-container">\n                <div class="image-container img-1">\n                    <img src="https://cdn.pnj.io/images/detailed/252/on-gnnpxmw000036-nhan-vang-10k-dinh-da-peridot-pnj-1.jpg" alt="Product 1">\n                </div>\n                <div class="image-container img-2">\n                    <img src="https://cdn.pnj.io/images/detailed/252/on-gnnpxmw000036-nhan-vang-10k-dinh-da-peridot-pnj-2.jpg" alt="Product 2">\n                </div>\n                <div class="image-container img-3">\n                    <img src="https://cdn.pnj.io/images/detailed/252/on-gnnpxmw000036-nhan-vang-10k-dinh-da-peridot-pnj-3.jpg" alt="Product 3">\n                </div>\n                <div class="image-container img-4">\n                    <img src="https://cdn.pnj.io/images/detailed/252/sp-gnnpxmw000036-nhan-vang-10k-dinh-da-peridot-pnj-1.png" alt="Product 4">\n                </div>\n                <div class="img-5">\n                    <div class="sub-image">\n                        <img src="https://cdn.pnj.io/images/detailed/252/sp-gnnpxmw000036-nhan-vang-10k-dinh-da-peridot-pnj-2.png" alt="Product 5">\n                    </div>\n                    <div class="sub-image">\n                        <img src="https://cdn.pnj.io/images/detailed/252/sp-gnnpxmw000036-nhan-vang-10k-dinh-da-peridot-pnj-3.png" alt="Product 6">\n                    </div>\n                </div>\n            </div>\n            \n            <div class="text-area">\n                <div class="aesthetic-text">Mời đoàn mình xem Nhẫn Peridot PNJ! Đẹp sang chảnh, Gen Z mê tít!</div>\n            </div>\n        </div>\n    </div>\n</body>\n</html>"""
    html_example = 
    # Uncomment để test:
    html_string_to_image(html_example, "test_output.png")
    
    main()