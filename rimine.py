import json
with open('gg_cookies.json', 'r', encoding='utf-8') as f:
    cookies = json.load(f)

original_cookies_list = cookies

cookies_for_playwright = []
for cookie in original_cookies_list:
    playwright_cookie = {
        'name': cookie['name'],
        'value': cookie['value'],
        'domain': '.google.com.vn',
        'path': cookie['path'],
        'expires': cookie['expirationDate'], # Renaming expirationDate to expires for Playwright
        'httpOnly': cookie['httpOnly'],
        'secure': cookie['secure'],
        'sameSite': cookie['sameSite'].replace('no_restriction', 'None').capitalize() if cookie['sameSite'] else "None" # Adjusting 'no_restriction' to 'None' and capitalizing
    }
    cookies_for_playwright.append(playwright_cookie)


print("Cookies prepared for Playwright:", cookies_for_playwright)


from playwright.sync_api import sync_playwright
import time
# Provided cookies


def get_alerts_list(cookies):
    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
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
        
get_alerts_list(cookies_for_playwright)