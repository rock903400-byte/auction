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

    # County/Township
    location = str(row["縣市"])
    county = location.split("\n")[0]

    # Parcel
    land_info = str(row["土地坐落/面積"])
    land_match = re.search(r"小段\s+(\d+(?:-\d+)?)\s*號", land_info)
    landno = land_match.group(1) if land_match else ""

    return yy, no, batch, landno, county


excel_keys = set()
for idx, row in df.iterrows():
    excel_keys.add(parse_excel_row(row))

print(f"Excel unique keys (yy, no, batch, landno, county): {len(excel_keys)}")

# Load JSON
with open("fetched_data.json", "r", encoding="utf-8") as f:
    json_data = json.load(f)

json_items = []
for item in json_data:
    share = str(item.get("rrange", "")).strip()
    if share and share not in ["全部", "1分之1"]:
        continue

    yy = str(item.get("crmyy"))
    no = str(int(item.get("crmno")))
    batch = str(item.get("batchno", "")).strip()
    landno = str(item.get("landno", "")).strip()
    county = str(item.get("hsimun", "")).replace(
        "地方法院", ""
    )  # Wait, hsimun is court name usually

    # Better county from hsimun
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
    json_items.append({"key": key, "item": item})

# Find items in JSON that are NOT in Excel
extra_in_json = []
for entry in json_items:
    if entry["key"] not in excel_keys:
        extra_in_json.append(entry)

print(f"Items in JSON but NOT in Excel: {len(extra_in_json)}")

if extra_in_json:
    print("\nSample extra items in JSON (first 10):")
    for e in extra_in_json[:10]:
        item = e["item"]
        print(
            f"  {e['key']} | saleno: {item.get('saleno')} | saledate: {item.get('saledate')} | ctmd: {item.get('ctmd')}"
        )

# Find items in Excel that are NOT in JSON
missing_in_json = []
json_keys = set(e["key"] for e in json_items)
for ek in excel_keys:
    if ek not in json_keys:
        missing_in_json.append(ek)

print(f"\nItems in Excel but NOT in JSON: {len(missing_in_json)}")
if missing_in_json:
    print("Sample missing items in JSON:")
    print(missing_in_json[:5])
