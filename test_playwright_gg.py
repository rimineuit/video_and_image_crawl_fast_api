from playwright.sync_api import sync_playwright
import time
# Provided cookies
cookies = [
    {
        "name": "SAPISID",
        "value": "Xzvvm-XEA2Thmz5c/AEKR9rl66HFxwzhfG",
        "domain": ".google.com.vn",
        "path": "/",
        "expires": 1787627391.825662,
        "httpOnly": False,
        "secure": True,
        "sameSite": "None"
    },
    {
        "name": "NID",
        "value": "525=f45g1FRtIM8im85DfAe8dzNKNTxUok3m8-MkkEWMiEGPd_H8Tp31TBEepxl9lz-MCb1GZwj4oKektRzXDtF1QtNGrzbFId_OaBKqasPbfNmDCvtnlze04V0DQbS3B-wHvW5mYrZpPHrzN4ADbJXIl_kFbKujKI1RALxK6l5VP_QMDyT7I428YA45qcUQZL8l_O99jrbXSL6h4oJrLPZlUxtAlo7FusM-7JefDAwTCBI9q6cpXnA8a40xhBuS9tPdEf6I_Lrs81mLaf8HSN4tZTJYQtzZ0njUxSEdt3khBklzn3OWKXi1mBTerCkwc6redbRg6AaVkNtAm0WTYCRcsMHSNRDYA0p3C5zoJJVLnqF0JJyIQ-aYDoPa4RDPN6gQBzi_ApRTCwmf5hKSyY8qT5lCDqFij__LavCdkYQuWMUYN9bJPY_4eZ9rwxzMp5quuuJHjBsKCVZriAHB1Xol1XHujvM9D3h330PRn1HJi9xy8kES9nIl6IpY13fk7zRKHRxkiDL48THi2YRjEsDRusBZVbDz2hOcTHoC5Od-DfFYVlng2xvWfY9WcHddBih9g9d7VG02lNyMHLo3t4WCgKPaVfb71ELcFMUHmxGasswoV6ZPx80gMNjEUWPKbgD0Uce3YmI3Hb6VNvDm93gCnG43jwLs_35116XymddDAtLzZdEtBtjlHk59C4F5WlGaaMXLW1hGow5Vvg4x89FMhaWo3NyypJFyBfpaP8s",
        "domain": ".google.com.vn",
        "path": "/",
        "expires": 1768977094.677567,
        "httpOnly": True,
        "secure": True,
        "sameSite": "None"
    },
    {
        "name": "__Secure-1PAPISID",
        "value": "Xzvvm-XEA2Thmz5c/AEKR9rl66HFxwzhfG",
        "domain": ".google.com.vn",
        "path": "/",
        "expires": 1787627391.825698,
        "httpOnly": False,
        "secure": True,
        "sameSite": "None"
    },
    {
        "name": "__Secure-3PAPISID",
        "value": "Xzvvm-XEA2Thmz5c/AEKR9rl66HFxwzhfG",
        "domain": ".google.com.vn",
        "path": "/",
        "expires": 1787627391.825749,
        "httpOnly": False,
        "secure": True,
        "sameSite": "None"
    },
    {
        "name": "__Secure-1PSID",
        "value": "g.a000zQhx5KlXL0XqfQ66xW-zvxggOqo7oGycYl7ycDLy3wwV34R3HZKNMtZCWObgZKwFs2Fv_wACgYKAT0SARYSFQHGX2Mis-vMDIRSczdZfF987FH0ZBoVAUF8yKrx5N-m-TPo3MTPz85FB5oH0076",
        "domain": ".google.com.vn",
        "path": "/",
        "expires": 1787627391.825889,
        "httpOnly": True,
        "secure": True,
        "sameSite": "None"
    },
    {
        "name": "__Secure-3PSID",
        "value": "g.a000zQhx5KlXL0XqfQ66xW-zvxggOqo7oGycYl7ycDLy3wwV34R3kwt9XybBpN4UN_7g1-7UqgACgYKAasSARYSFQHGX2MiWxJePD_Lb6A0KDXDsS2Y4RoVAUF8yKqLvWGd-zQkENA9ql1IETcr0076",
        "domain": ".google.com.vn",
        "path": "/",
        "expires": 1787627391.825927,
        "httpOnly": True,
        "secure": True,
        "sameSite": "None"
    },
    {
        "name": "SSID",
        "value": "AuRRGo7-hEcSCFwrZ",
        "domain": ".google.com.vn",
        "path": "/",
        "expires": 1787627391.825567,
        "httpOnly": True,
        "secure": True,
        "sameSite": "None"
    }
]

def main():
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
        time.sleep(100)
        # Optional: Take a screenshot for debugging
        page.screenshot(path="google_alerts.png")
        print("Screenshot saved as google_alerts.png")

        # Wait for a few seconds to observe the page
        page.wait_for_timeout(5000)

        # Close the browser
        browser.close()

if __name__ == "__main__":
    main()