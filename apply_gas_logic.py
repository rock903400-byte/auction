import json

with open("fetched_data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# 40 Townships from GAS script
search_keywords_str = "大同鄉 南澳鄉 員山鄉 復興區 尖石鄉 五峰鄉 橫山鄉 關西鎮 泰安鄉 南庄鄉 獅潭鄉 和平區 仁愛鄉 信義鄉 魚池鄉 水里鄉 阿里山鄉 桃源區 那瑪夏區 獅子鄉 三地門鄉 牡丹鄉 來義鄉 泰武鄉 瑪家鄉 春日鄉 滿州鄉 內埔鄉 秀林鄉 卓溪鄉 萬榮鄉 壽豐鄉 光復鄉 富里鄉 豐濱鄉 吉安鄉 鳳林鎮 玉里鎮 瑞穗鄉 花蓮市"
keywords = search_keywords_str.split()


def get_unique_count_gas_logic(items):
    unique = {}
    for item in items:
        # Filter share
        share = str(item.get("rrange", "")).strip()
        if share and share not in ["全部", "1分之1"]:
            continue

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

        # Check if keyword matches (this is tricky because API filter might be broader)
        # But let's check if 'ctmd' (township) is in our list
        ctmd = str(item.get("ctmd", "")).strip()
        if not any(k in ctmd for k in keywords):
            continue

        if key not in unique:
            unique[key] = item
    return len(unique)


# General Program: What saleno's?
# In GAS, saletype "" is used.
# Usually this returns saleno 1, 2, 3.
# Sometimes it returns 4 or 6 if they are part of general auctions.
gen_salenos = ["1", "2", "3", "4", "6", "7"]  # common general salenos
# Wait, if I use 1, 2, 3, 4, 6, 7 I might get too many.
# Let's try to find which combination gives 268.

possible_combinations = [
    ["1", "2", "3"],
    ["1", "2", "3", "6"],
    ["1", "2", "3", "4", "6"],
    ["1", "2", "3", "4", "6", "7"],
]

print("General Program Candidates (GAS logic + Township Filter):")
for combo in possible_combinations:
    items = [i for i in data if str(i.get("saleno")) in combo]
    count = get_unique_count_gas_logic(items)
    print(f"  saleno {combo}: {count}")

# Buy Program: saletype 4
# Usually returns saleno '99' or '4'.
buy_salenos = ["99"]
items = [i for i in data if str(i.get("saleno")) in buy_salenos]
count = get_unique_count_gas_logic(items)
print(f"\nBuy Program (saleno ['99']): {count}")

buy_salenos_v2 = ["4"]
items = [i for i in data if str(i.get("saleno")) in buy_salenos_v2]
count = get_unique_count_gas_logic(items)
print(f"Buy Program (saleno ['4']): {count}")
