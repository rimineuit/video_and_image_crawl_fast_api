import asyncio
from crawl4ai import *
import sys
import json

async def main(url):
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(
            url=url,
        )
        return result

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else None
    type_output = sys.argv[2] if len(sys.argv) > 2 else "markdown"
    
    result = asyncio.run(main(url))
    
    # Lấy thuộc tính từ type_output nếu tồn tại, ngược lại trả về toàn bộ object
    output_value = getattr(result, type_output, None)
    if output_value is None:
        print(f"[WARN] Output type '{type_output}' không tồn tại. In toàn bộ result object:")
        print(json.dumps({"response": str(result)}, ensure_ascii=False))
    else:
        print(json.dumps({"response": output_value}, ensure_ascii=False))
