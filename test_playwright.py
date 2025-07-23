from playwright.sync_api import sync_playwright
import time

# # Provided cookies
# cookies = [
#     {
#         "domain": ".www.tiktok.com",
#         "expirationDate": 1777259031,
#         "hostOnly": False,
#         "httpOnly": False,
#         "name": "delay_guest_mode_vid",
#         "path": "/",
#         "sameSite": "None",
#         "secure": True,
#         "session": False,
#         "storeId": None,
#         "value": "5"
#     },
#     {
#         "domain": ".tiktok.com",
#         "expirationDate": 1786764797,
#         "hostOnly": False,
#         "httpOnly": False,
#         "name": "ttcsid_C97F14JC77U63IDI7U40",
#         "path": "/",
#         "sameSite": "None",
#         "secure": False,
#         "session": False,
#         "storeId": None,
#         "value": "1753067375395::YSuHRgwK3wT89k4b0zFx.2.1753068797013"
#     },
#     {
#         "domain": ".tiktok.com",
#         "expirationDate": 1784603430.186038,
#         "hostOnly": False,
#         "httpOnly": True,
#         "name": "tt-target-idc-sign",
#         "path": "/",
#         "sameSite": "None",
#         "secure": False,
#         "session": False,
#         "storeId": None,
#         "value": "rrKS8KCvjCucx61CT42l97_GWa5H0umBWUU78suoDBHRgpNk7CwTIAakuvx_yR_2H9l8MZk8DUS6yEbrjOxOEH76SHkReOIhnBZ4hdz8GVdjPhv9rTIVBmqQHTAOBfE05CZp2ffFlpdubJA0U5KnYNHVAaFH_4wcFGDacqIy5PMCOW-bwyRyVYvjQeXkBKHEQQA7PL5nHKn0Buc5pWJ0fzs0ZbuHgD32yl2-QyYMvrNm6FDH6Ubz2mihVcSQVZ9lwQwpLpKtMXlDbXuhdCO4edJXOFAVIHvJuCvQoGCFk_CDOACELZvS3foGzPAKzka0wBcFlRmg_uYiFCabvnhoFYm5UitD2b9Zqu3FCt37UCI2FHSFIr3O2Lp8UxYU3KkUKe2mkT75Ha16DBx4POQC54vn57D93zx5DVUcKv18nwhwq53VfxmpfLYcvLscDKmDmY_EQk7oKOraKK8DdSmgX_g8mfenwT1trOJocqED3DtztNUTZjeuZjCCoGEDT1nc"
#     },
#     # Add the rest of the cookies here...
# ]

def main():
    # Initialize Playwright
    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(
            headless=False,  # Set to True for no UI
            args=[
                "--disable-blink-features=AutomationControlled",  # Prevent detection as automated browser
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process"
            ]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",  # Custom user agent
            viewport={"width": 1280, "height": 800},  # Set viewport size
            permissions=["geolocation"],  # Enable geolocation permission
            geolocation={"latitude": 40.712776, "longitude": -74.005974},  # New York City, USA
            timezone_id="America/New_York"  # Set timezone to New York
        )

        # Set cookies in the browser context
        # context.add_cookies(cookies)
        print("Cookies have been set.")

        # Open a new page
        page = context.new_page()

        # Navigate to the TikTok search URL
        url = "https://www.tiktok.com/explore"
        page.goto(url)

        # Wait for the page to load
        page.wait_for_load_state("domcontentloaded")
        print(f"Navigated to {url}")

        # Optional: Take a screenshot for debugging
        page.screenshot(path="tiktok_explore.png")
        print("Screenshot saved as tiktok_explore.png")

        # Wait for a few seconds to observe the page
        time.sleep(5)

        # Close the browser
        browser.close()

if __name__ == "__main__":
    main()