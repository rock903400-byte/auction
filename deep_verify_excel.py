import pandas as pd
import json
import re
from collections import Counter

# 1. Load Excel and Extract Unique Keys
df = pd.read_excel("49518.xls")
excel_items = []


def parse_excel_row(row):
    case_raw = str(row["字號\n股別"])
    case_match = re.search(r"(\d+)[\s\S]*?([^\d\s]+)[\s\S]*?第(\d+)號", case_raw)
    yy, no = "", ""
    if case_match:
        yy = case_match.group(1)
        no = str(int(case_match.group(3)))

    batch = str(row["標別"]).strip()
    if batch == "nan":
        batch = ""

    location = str(row["縣市"])
    county = location.split("\n")[0]

    land_info = str(row["土地坐落/面積"])
    land_match = re.search(r"小段\s+(\d+(?:-\d+)?)\s*號", land_info)
    landno = land_match.group(1) if land_match else ""

    auction_raw = str(row["拍賣日期\n拍賣次數"])
    date_match = re.search(r"(\d+/\d+/\d+)", auction_raw)
    saledate = date_match.group(1).replace("/", "") if date_match else ""
    saleno_match = re.search(r"第(\d+)拍", auction_raw)
    saleno = saleno_match.group(1) if saleno_match else ""

    return {
        "yy": yy,
        "no": no,
        "batch": batch,
        "landno": landno,
        "county": county,
        "saledate": saledate,
        "saleno": saleno,
    }


excel_keys = {}
for idx, row in df.iterrows():
    info = parse_excel_row(row)
    key = (info["yy"], info["no"], info["batch"], info["landno"], info["county"])
    excel_keys[key] = info

print(f"Excel Unique Records: {len(excel_keys)}")

# 2. Load JSON and Filter
with open("fetched_data.json", "r", encoding="utf-8") as f:
    json_data = json.load(f)

json_filtered = {}
for item in json_data:
    # Basic filters matching updated GAS logic
    share = str(item.get("rrange", "")).strip()
    if share and share not in ["全部", "1分之1"]:
        continue

    saleno = str(item.get("saleno"))
    if saleno not in ["1", "2", "3", "4", "6"]:
        continue

    yy = str(item.get("crmyy"))
    no = str(int(item.get("crmno")))
    batch = str(item.get("batchno", "")).strip()
    landno = str(item.get("landno", "")).strip()

    # County mapping
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
    hsimun = str(item.get("hsimun", ""))
    county = next((v for k, v in court_to_county.items() if k in hsimun), hsimun)

    key = (yy, no, batch, landno, county)

    # Use saledate to decide which version to keep if multiple auctions exist for same parcel (unlikely in filtered set but safe)
    saledate = str(item.get("saledate", "0")).zfill(8)

    if key in excel_keys:
        if key not in json_filtered:
            json_filtered[key] = item
        else:
            # If duplicates in JSON, keep the one matching Excel date or the latest
            if saledate == excel_keys[key]["saledate"]:
                json_filtered[key] = item

# 3. Final Verification
matched = 0
missing = []
for key in excel_keys:
    if key in json_filtered:
        matched += 1
    else:
        missing.append(key)

print("\nVerification Results:")
print(f"Matched with Excel: {matched} / {len(excel_keys)}")
print(f"Missing from JSON: {len(missing)}")

if missing:
    print("\nSample missing records (first 5):")
    for m in missing[:5]:
        print(
            f"  {m} | Excel Saledate: {excel_keys[m]['saledate']} | Saleno: {excel_keys[m]['saleno']}"
        )

# Check if missing ones are because of date (e.g., they were before 1150503)
if missing:
    past_dates = [
        excel_keys[m]["saledate"]
        for m in missing
        if excel_keys[m]["saledate"] < "01150503"
    ]
    print(f"\nMissing records with saledate < 1150503: {len(past_dates)}")

# Analyze saleno of matched items
saleno_counts = Counter([str(json_filtered[k].get("saleno")) for k in json_filtered])
print(f"\nSaleno distribution of matched items: {saleno_counts}")
