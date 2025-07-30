from playwright.sync_api import sync_playwright
import time
# Provided cookies


def get_alerts_list(cookies):
    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        print(f"Normalized cookies: {json.dumps(cookies)})")
        # Set cookies
        context.add_cookies(cookies)
        print("Cookies have been set.")

        # Open a new page
        page = context.new_page()

        # Navigate to Google Alerts
        url = "https://www.google.com.vn/alerts"
        page.goto(url)

        # Wait for the page to load
        page.wait_for_load_state("domcontentloaded")
        print(f"Navigated to {url}")
        
        try:
            page.wait_for_selector("div.show_all_alerts", timeout=5000)
            show_all_alert = page.query_selector("div.show_all_alerts")
            if show_all_alert:
                show_all_alert.click()
                print("Clicked on 'Show all alerts'.")
        except Exception as e:
            print(f"Error clicking 'Show all alerts': {e}")
        page.wait_for_timeout(2000)
        alerts = page.query_selector_all("#manage-alerts-div > ul > li > div.delivery_settings > div > div.query_div > span")
        alerts_list = [alert.inner_text() for alert in alerts]
        print(f"Found {len(alerts_list)} alerts.")
        print(alerts_list)
        # Wait for a few seconds to observe the page
        page.wait_for_timeout(5000)
        # Close the browser
        browser.close()
        
def normalize_cookies(cookies: list) -> list:
    """Chỉ giữ lại cookies có tên trong danh sách cho phép, và chuẩn hóa định dạng."""
    ALLOWED_COOKIE_NAMES = [
        "SAPISID",
        "NID",
        "__Secure-1PAPISID",
        "__Secure-3PAPISID",
        "__Secure-1PSID",
        "__Secure-3PSID",
        "SSID"
    ]

    valid_samesite = {
        "lax": "Lax",
        "strict": "Strict",
        "none": "None",
        "no_restriction": "None",
        None: "None"
    }

    cleaned = []
    for c in cookies:
        if c.get("name") not in ALLOWED_COOKIE_NAMES:
            continue

        cookie = {
            "name": c["name"],
            "value": c["value"],
            "domain": c["domain"],
            "path": c.get("path", "/"),
            "expires": float(c.get("expirationDate")),
            "httpOnly": bool(c.get("httpOnly")),
            "secure": bool(c.get("secure")),
            "sameSite": valid_samesite.get(str(c.get("sameSite")).lower(), "Lax")
        }
        cleaned.append(cookie)

    return cleaned

import json
if __name__ == "__main__":
    with open('gg_cookies.json', 'r', encoding='utf-8') as f:
        cookies = json.load(f)
    cookies = normalize_cookies(cookies)
    get_alerts_list(cookies)



