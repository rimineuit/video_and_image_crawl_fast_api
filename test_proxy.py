import json
import requests

# Giả sử file tên proxies.json
with open("proxies.json", "r") as f:
    proxy_list = json.load(f)

test_url = "https://httpbin.org/ip"

for item in proxy_list:
    ip = item["ip_address"]
    port = item["port"]
    proxy = f"http://{ip}:{port}"

    try:
        r = requests.get(test_url,
                         proxies={"http": proxy, "https": proxy},
                         timeout=5)
        print(proxy, "✅ OK", "->", r.json())
    except Exception as e:
        print(proxy, "❌ FAILED")
