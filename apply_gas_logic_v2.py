import json

with open("fetched_data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# 40 Townships from GAS script
search_keywords_str = "大同鄉 南澳鄉 員山鄉 復興區 尖石鄉 五峰鄉 橫山鄉 關西鎮 泰安鄉 南庄鄉 獅潭鄉 和平區 仁愛鄉 信義鄉 魚池鄉 水里鄉 阿里山鄉 桃源區 那瑪夏區 獅子鄉 三地門鄉 牡丹鄉 來義鄉 泰武鄉 瑪家鄉 春日鄉 瑪家鄉 春日鄉 滿州鄉 內埔鄉 秀林鄉 卓溪鄉 萬榮鄉 壽豐鄉 光復鄉 富里鄉 豐濱鄉 吉安鄉 鳳林鎮 玉里鎮 瑞穗鄉 花蓮市"
# Note: I noticed 瑪家鄉 and 春日鄉 were repeated in my previous string, fixed.
keywords = set(search_keywords_str.split())


def get_count(items, target_date=None, dedupe=True):
    unique = {}
    for item in items:
        # Filter share
        share = str(item.get("rrange", "")).strip()
        if share and share not in ["全部", "1分之1"]:
            continue

        # Township Filter
        ctmd = str(item.get("ctmd", "")).strip()
        if not any(k in ctmd for k in keywords):
            continue

        # Date Filter
        saledate = str(item.get("saledate", "00000000"))
        if target_date and saledate < target_date:
            continue

        if dedupe:
            # GAS Unique Key: hsimun + crmyy + crmid + crmno + saleno + batchno + sec + landno
            key = (
                str(item.get("hsimun")),
                str(item.get("crmyy")),
                str(item.get("crmid")),
                str(item.get("crmno")),
                str(item.get("saleno", "")),
                str(item.get("batchno", "")),
                str(item.get("sec", "")),
                str(item.get("landno", "")),
            )
            if key not in unique:
                unique[key] = item
        else:
            # Just count all rows that pass filters
            # But the GAS script DOES deduplicate.
            pass

    return len(unique)


today = "01150503"

# General Program Target: 268
gen_items = [i for i in data if str(i.get("saleno")) in ["1", "2", "3", "4", "6", "7"]]
print(f"General Program (Future): {get_count(gen_items, today)}")

# Buy Program Target: 138
buy_items = [i for i in data if str(i.get("saleno")) == "99"]
# Does Buy Program need date filter?
print(f"Buy Program (All): {get_count(buy_items, None)}")
print(f"Buy Program (Future): {get_count(buy_items, today)}")

# What if General includes saleno 99 but Buy is something else?
# No, saleno 99 is exactly 138 (without date filter).
