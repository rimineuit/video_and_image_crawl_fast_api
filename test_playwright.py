from playwright.sync_api import sync_playwright
import time

# Essential cookies formatted for Playwright with corrected sameSite values
cookies = [
    {
        "name": "sessionid",
        "value": "ef68dca6ba98f942132c6ea158654200",
        "domain": ".tiktok.com",
        "path": "/",
        "expires": 1766817945.66888,
        "httpOnly": True,
        "secure": True,
        "sameSite": "None"  # Corrected from "none" (case-insensitive, but standardized)
    },
    {
        "name": "sid_guard",
        "value": "ef68dca6ba98f942132c6ea158654200%7C1751265963%7C15551982%7CSat%2C+27-Dec-2025+06%3A45%3A45+GMT",
        "domain": ".tiktok.com",
        "path": "/",
        "expires": 1782369963.66873,
        "httpOnly": True,
        "secure": True,
        "sameSite": "None"  # Standardized
    },
    {
        "name": "uid_tt",
        "value": "c3878d3d742f64731a705df809d04d8c7cfe63814d5f4478da9430c6f2b0821e",
        "domain": ".tiktok.com",
        "path": "/",
        "expires": 1766817945.668775,
        "httpOnly": True,
        "secure": True,
        "sameSite": "None"  # Standardized
    },
    {
        "name": "ttwid",
        "value": "1%7CB74m9kXqUjxeKeQ0piiXRDk3GP3ZX_kyqxsSuEzQDB8%7C1753151283%7C43bf86c7f87706f4c0d30e53c4df59f11bf22f07de21aa28b7943edf63b3e54b",
        "domain": ".tiktok.com",
        "path": "/",
        "expires": 1784687283.111174,
        "httpOnly": True,
        "secure": True,
        "sameSite": "None"  # Corrected from "no_restriction"
    },
    {
        "name": "passport_csrf_token",
        "value": "70e3fdf23a31bf45b62c591b9ccca966",
        "domain": ".tiktok.com",
        "path": "/",
        "expires": 1756091058.4893,
        "httpOnly": False,
        "secure": True,
        "sameSite": "None"  # Corrected from "no_restriction"
    },
    {
        "name": "store-country-code",
        "value": "vn",
        "domain": ".tiktok.com",
        "path": "/",
        "expires": 1766817945.348112,
        "httpOnly": True,
        "secure": False,
        "sameSite": "None"  # Standardized
    }
]

def main():
    # Initialize Playwright
    with sync_playwright() as p:
        # Launch browser (Chromium, can also use firefox or webkit)
        browser = p.chromium.launch(headless=False)  # Set headless=True for no UI
        context = browser.new_context()

        # Set cookies in the browser context
        context.add_cookies(cookies)
        print("Cookies have been set.")

        # Open a new page
        page = context.new_page()

        # Navigate to the TikTok search URL
        url = "https://www.tiktok.com/explore"
        page.goto(url)

        # Wait for the page to load (adjust selector based on TikTok's structure)
        page.wait_for_load_state("domcontentloaded")
        print(f"Navigated to {url}")

        # Scroll down half the screen every second
        for _ in range(10000):  # Adjust the range for the number of scrolls
            page.evaluate("window.scrollBy(0, window.innerHeight / 2);")
            time.sleep(1)  # Wait for 1 second between scrolls

        # Optional: Verify session state (e.g., check for logged-in elements)
        try:
            profile_element = page.query_selector("a[href*='/@']")  # Example selector for user profile link
            if profile_element:
                print("User appears to be logged in (profile link found).")
            else:
                print("User may not be logged in or page structure has changed.")
        except Exception as e:
            print(f"Error checking session state: {e}")

        # Optional: Take a screenshot for debugging
        page.screenshot(path="tiktok_search.png")
        print("Screenshot saved as tiktok_search.png")

        # Wait for a few seconds to observe the page (optional, for non-headless mode)
        time.sleep(5)

        # Close the browser
        browser.close()

if __name__ == "__main__":
    main()