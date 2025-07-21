from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            geolocation={"latitude": 21.0285, "longitude": 105.8542},
            locale='vi-VN',
            timezone_id='Asia/Ho_Chi_Minh',
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) ...",
            permissions=["geolocation"],

        )
        page = await context.new_page()
        await page.goto("https://www.tiktok.com/explore")
        await page.wait_for_timeout(10000)

        await browser.close()
