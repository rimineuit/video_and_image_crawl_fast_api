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
    html_example = """<!DOCTYPE html>\n<html lang="en">\n<head>\n    <meta charset="UTF-8">\n    <meta name="viewport" content="width=device-width, initial-scale=1.0">\n    <title>Jewelry Collection Poster</title>\n    <style>\n        @import url('https://fonts.googleapis.com/css2?family=Dancing+Script:wght@400;500;600;700&family=Playfair+Display:wght@400;500;600;700;800;900&display=swap');\n        \n        * {\n            margin: 0;\n            padding: 0;\n            box-sizing: border-box;\n        }\n        \n        .poster {\n            width: 1080px;\n            height: 1350px;\n            background: linear-gradient(135deg, #e8e6f0 0%, #d8d4e8 50%, #c8c2dc 100%);\n            position: relative;\n            font-family: 'Playfair Display', serif;\n            display: flex;\n            flex-direction: column;\n            padding: 50px 40px;\n            /* Sparkle pattern overlay */\n            background-image: \n                radial-gradient(circle at 20% 80%, rgba(255,255,255,0.4) 1px, transparent 1px),\n                radial-gradient(circle at 80% 20%, rgba(255,255,255,0.3) 1px, transparent 1px),\n                radial-gradient(circle at 40% 40%, rgba(255,255,255,0.2) 0.5px, transparent 0.5px),\n                radial-gradient(circle at 60% 60%, rgba(255,255,255,0.3) 0.5px, transparent 0.5px),\n                radial-gradient(circle at 90% 70%, rgba(255,255,255,0.2) 1px, transparent 1px),\n                radial-gradient(circle at 10% 30%, rgba(255,255,255,0.3) 0.5px, transparent 0.5px);\n            background-size: 200px 200px, 150px 150px, 100px 100px, 120px 120px, 180px 180px, 90px 90px;\n        }\n        \n        .header-section {\n            height: 160px;\n            display: flex;\n            flex-direction: column;\n            align-items: center;\n            justify-content: center;\n            text-align: center;\n            margin-bottom: 30px;\n        }\n        \n        .title-text {\n            font-family: 'Dancing Script', cursive;\n            font-weight: 600;\n            font-size: 38px;\n            color: #4a4a4a;\n            margin-bottom: 10px;\n            font-style: italic;\n        }\n        \n        .main-text {\n            font-family: 'Playfair Display', serif;\n            font-weight: 900;\n            font-size: 95px;\n            color: #2c2c2c;\n            letter-spacing: 4px;\n            text-transform: uppercase;\n            line-height: 0.9;\n        }\n        \n        .images-section {\n            flex: 1;\n            display: flex;\n            align-items: center;\n            justify-content: center;\n            gap: 25px;\n            margin: 40px 0;\n        }\n        \n        .image-container {\n            position: relative;\n            background: white;\n            padding: 15px;\n            box-shadow: 0 12px 35px rgba(0,0,0,0.15);\n            transition: transform 0.3s ease, box-shadow 0.3s ease;\n        }\n        \n        .image-container:hover {\n            transform: translateY(-8px);\n            box-shadow: 0 18px 45px rgba(0,0,0,0.2);\n        }\n        \n        .image-container img {\n            width: 240px;\n            height: 300px;\n            object-fit: cover;\n            object-position: center;\n            display: block;\n        }\n        \n        /* Middle image slightly larger */\n        .img-2 {\n            transform: scale(1.1);\n        }\n        \n        .img-2 img {\n            width: 260px;\n            height: 320px;\n        }\n        \n        .promo-section {\n            height: 120px;\n            display: flex;\n            flex-direction: column;\n            align-items: center;\n            justify-content: center;\n            text-align: center;\n            margin: 30px 0;\n        }\n        \n        .promo-text {\n            font-family: 'Playfair Display', serif;\n            font-weight: 700;\n            font-size: 32px;\n            color: #2c2c2c;\n            letter-spacing: 2px;\n            text-transform: uppercase;\n            margin-bottom: 8px;\n        }\n        \n        .sub-promo-text {\n            font-family: 'Playfair Display', serif;\n            font-weight: 400;\n            font-size: 24px;\n            color: #4a4a4a;\n            letter-spacing: 1.5px;\n            text-transform: uppercase;\n        }\n        \n        .website-section {\n            height: 80px;\n            display: flex;\n            align-items: center;\n            justify-content: center;\n        }\n        \n        .website-text {\n            font-family: 'Playfair Display', serif;\n            font-weight: 500;\n            font-size: 24px;\n            color: #2c2c2c;\n            text-align: center;\n            letter-spacing: 2px;\n            text-transform: uppercase;\n        }\n        \n        /* Decorative elements */\n        .header-section::after {\n            content: '✦';\n            font-size: 20px;\n            color: #8a7ca8;\n            margin-top: 15px;\n        }\n        \n        .promo-section::before {\n            content: '◊';\n            font-size: 16px;\n            color: #8a7ca8;\n            margin-bottom: 15px;\n        }\n    </style>\n</head>\n<body>\n    <div class="poster">\n        <div class="header-section">\n            <div class="title-text">New Collection</div>\n            <div class="main-text">JEWELRY</div>\n        </div>\n        \n        <div class="images-section">\n            <div class="image-container img-1">\n                <img src="https://cdn.pnj.io/images/detailed/264/sp-sixm00y000023-hat-charm-bac-dinh-da-style-by-pnj-1.png" alt="Jewelry 1">\n            </div>\n            <div class="image-container img-2">\n                <img src="https://cdn.pnj.io/images/detailed/264/sp-sixm00y000023-hat-charm-bac-dinh-da-style-by-pnj-2.png" alt="Jewelry 2">\n            </div>\n            <div class="image-container img-3">\n                <img src="https://cdn.pnj.io/images/detailed/264/sp-sixm00y000023-hat-charm-bac-dinh-da-style-by-pnj-3.png" alt="Jewelry 3">\n            </div>\n        </div>\n        \n        <div class="promo-section">\n            <div class="promo-text">UP TO 50% OFF</div>\n            <div class="sub-promo-text">ON SELECTED ITEMS</div>\n        </div>\n        \n        <div class="website-section">\n            <div class="website-text">YOURWEBSITE.COM</div>\n        </div>\n    </div>\n</body>\n</html>"""
    
    # Uncomment để test:
    html_string_to_image(html_example, "test_output.png")
    
    main()