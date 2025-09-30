from playwright.sync_api import sync_playwright
import json
import gc
import time
import sys

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process"
        ]
    )

    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
        viewport={"width": 1280, "height": 720},
        bypass_csp=True,
        java_script_enabled=True
    )
    page = context.new_page()
    url = "https://www.tiktok.com/@cotuyenhoala/video/7527196260919512328"
    

    page.goto(url)
    page.wait_for_load_state("networkidle")
    page.evaluate('window.scrollBy(0, window.innerHeight);')
    time.sleep(10)
    page.evaluate('window.scrollBy(0, window.innerHeight);')
    time.sleep(10)