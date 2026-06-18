import pandas as pd
import json
import re

# Load Excel
df = pd.read_excel("49518.xls")


def parse_excel_row(row):
    case_raw = str(row["字號\n股別"])
    case_match = re.search(r"(\d+)[\s\S]*?([^\d\s]+)[\s\S]*?第(\d+)號", case_raw)
    yy, id_str, no = "", "", ""
    if case_match:
        yy = case_match.group(1)
        id_str = case_match.group(2)
        no = str(int(case_match.group(3)))
    batch = str(row["標別"]).strip()
    if batch == "nan":
        batch = ""

    location = str(row["縣市"])
    county = location.split("\n")[0]

    land_info = str(row["土地坐落/面積"])
    land_match = re.search(r"小段\s+(\d+(?:-\d+)?)\s*號", land_info)
    landno = land_match.group(1) if land_match else ""

    return yy, no, batch, landno, county


excel_keys = {}
for idx, row in df.iterrows():
    key = parse_excel_row(row)
    excel_keys[key] = idx

# Load JSON
with open("fetched_data.json", "r", encoding="utf-8") as f:
    json_data = json.load(f)

# Find JSON items matching Excel keys
matched_items = []
seen_keys = set()
for item in json_data:
    yy = str(item.get("crmyy"))
    no = str(int(item.get("crmno")))
    batch = str(item.get("batchno", "")).strip()
    landno = str(item.get("landno", "")).strip()
    county = str(item.get("hsimun", "")).replace("地方法院", "")
    court_to_county = {
        "花蓮": "花蓮縣",
        "新竹": "新竹縣",
        "南投": "南投縣",
        "宜蘭": "宜蘭縣",
        "高雄": "高雄市",
        "屏東": "屏東縣",
        "嘉義": "嘉義縣",
        "苗栗": "苗栗縣",
        "臺中": "臺中市",
        "桃園": "桃園市",
    }
    county_clean = next((v for k, v in court_to_county.items() if k in county), county)

    key = (yy, no, batch, landno, county_clean)
    if key in excel_keys:
        matched_items.append(item)
        seen_keys.add(key)

print(f"Total Excel Keys: {len(excel_keys)}")
print(f"Matched JSON items: {len(matched_items)}")
print(f"Unique matched keys: {len(seen_keys)}")

# Analyze saleno of matched items
from collections import Counter

salenos = [str(i.get("saleno")) for i in matched_items]
print("\nSaleno distribution of matched items:")
print(Counter(salenos))

# Analyze saledate of matched items
saledates = [str(i.get("saledate")) for i in matched_items]
print(f"\nSaledate range: {min(saledates)} to {max(saledates)}")
