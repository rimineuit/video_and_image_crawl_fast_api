from playwright.sync_api import sync_playwright
import json
import gc
import time
import sys

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=False,
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
    url = "https://www.google.com/maps/place/PNJ+632+Quang+Trung/@10.8360141,106.6416451,15z/data=!4m10!1m2!2m1!1zQ-G7rWEgSMOgbmcgVHJhbmcgU-G7qWMgUG5q!3m6!1s0x317529a76c3a7b25:0xa2d7488a32038f49!8m2!3d10.8360141!4d106.6606995!15sChtD4butYSBIw6BuZyBUcmFuZyBT4bupYyBQbmoiA4gBAVodIhtj4butYSBow6BuZyB0cmFuZyBz4bupYyBwbmqSAQ1qZXdlbHJ5X3N0b3JlmgEkQ2hkRFNVaE5NRzluUzBWSlEwRm5TVVF6T1hGaWFXeFJSUkFCqgF0Cg0vZy8xMWZreXlmMnJmEAEqHyIbY-G7rWEgaMOgbmcgdHJhbmcgc-G7qWMgcG5qKEIyHxABIhtVh7qHTy2Va09YOYg7ov-AaRC0ROwxjPT3HFsyHxACIhtj4butYSBow6BuZyB0cmFuZyBz4bupYyBwbmrgAQD6AQQIABAw!16s%2Fg%2F11csr560l1?entry=ttu&g_ep=EgoyMDI1MDkyMy4wIKXMDSoASAFQAw%3D%3D"
    

    page.goto(url)
    time.sleep(10)
    page.wait_for_selector("""
        document.querySelector("#QA0Szd > div > div > div.w6VYqd > div.bJzME.Hu9e2e.tTVLSc > div > div.e07Vkf.kA9KIf > div > div > div.m6QErb.DxyBCb.kA9KIf.dS8AEf.XiKgde")
                .scrollBy(0, 300)
        """)
    for i in range(10):
        # Scroll xuống 300px
        print("Scroll")
        page.evaluate("""
        document.querySelector("#QA0Szd > div > div > div.w6VYqd > div.bJzME.Hu9e2e.tTVLSc > div > div.e07Vkf.kA9KIf > div > div > div.m6QErb.DxyBCb.kA9KIf.dS8AEf.XiKgde")
                .scrollBy(0, 300)
        """)
        time.sleep(2)
    time.sleep(10)