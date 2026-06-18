import requests
import re
import json


def fetch_data():
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://aomp109.judicial.gov.tw/judbp/wkw/WHD1A02/V2.htm",
    }

    # Get CSRF and Token
    res = session.get(
        "https://aomp109.judicial.gov.tw/judbp/wkw/WHD1A02/V2.htm", headers=headers
    )
    content = res.text

    csrf_match = re.search(r'name="_csrf"\s+value="([^"]+)"', content)
    token_match = re.search(
        r'var\s+token\s*=\s*[\'"]([^\'"]+)[\'"]', content
    ) or re.search(r'name="token"\s+value="([^"]+)"', content)

    csrf = csrf_match.group(1) if csrf_match else ""
    token = token_match.group(1) if token_match else ""

    print(f"CSRF: {csrf}")
    print(f"Token: {token}")

    if not csrf or not token:
        print("Failed to get CSRF or Token")
        return []

    searchKeywords = "大同鄉 南澳鄉 員山鄉 烏來區 復興區 尖石鄉 五峰鄉 橫山鄉 關西鎮 泰安鄉 南庄鄉 獅潭鄉 和平區 仁愛鄉 信義鄉 魚池鄉 水里鄉 阿里山鄉 桃源區 那瑪夏區 茂林區 六龜區 獅子鄉 三地門鄉 牡丹鄉 來義鄉 泰武鄉 瑪家鄉 春日鄉 霧臺鄉 滿州鄉 車城鄉 內埔鄉 新埤鄉 秀林鄉 卓溪鄉 萬榮鄉 壽豐鄉 光復鄉 富里鄉 豐濱鄉 吉安鄉 鳳林鎮 玉里鎮 瑞穗鄉 花蓮市 新城鄉"
    url = "https://aomp109.judicial.gov.tw/judbp/wkw/WHD1A02/QUERY.htm"
    all_data = []
    page = 1

    while page <= 10:
        print(f"Fetching page {page}...")
        payload = {
            "proptype": "C51",
            "saletype": "",
            "keyword": searchKeywords,
            "rrange": "ALL",
            "pageSize": "100",
            "page": str(page),
            "token": token,
            "_csrf": csrf,
            "sorted_column": "A.CRMYY, A.CRMID, A.CRMNO, A.SALENO, A.ROWID",
            "sorted_type": "ASC",
            "is_search": "Y",
        }

        res = session.post(url, data=payload, headers=headers)
        try:
            data = res.json()
            if "data" in data and data["data"]:
                all_data.extend(data["data"])
                print(f"  Received {len(data['data'])} items (Total: {len(all_data)})")
                if len(data["data"]) < 100:
                    break
            else:
                print("  No more data or error in response")
                break
        except Exception as e:
            print(f"  Error parsing JSON: {e}")
            break
        page += 1

    return all_data


if __name__ == "__main__":
    data = fetch_data()
    with open("fetched_data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Done. Total items: {len(data)}")
