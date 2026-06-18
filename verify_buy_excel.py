import pandas as pd
import json
import re

# 1. Load Excel and Extract Unique Keys for Buy Program
excel_file = "78560.xls"
df = pd.read_excel(excel_file)
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
    # In Buy program, some formats might differ, but looking for land number
    land_match = re.search(r"小段\s+(\d+(?:-\d+)?)\s*號", land_info)
    landno = land_match.group(1) if land_match else ""

    return {"yy": yy, "no": no, "batch": batch, "landno": landno, "county": county}


excel_keys = set()
for idx, row in df.iterrows():
    info = parse_excel_row(row)
    key = (info["yy"], info["no"], info["batch"], info["landno"], info["county"])
    excel_keys.add(key)

print(f"Excel Unique Records (78560.xls): {len(excel_keys)}")

# 2. Load JSON and Filter for Buy Program (saleno 99)
with open("fetched_data.json", "r", encoding="utf-8") as f:
    json_data = json.load(f)

json_filtered = {}
for item in json_data:
    # Buy Program Filter
    if str(item.get("saleno")) != "99":
        continue

    share = str(item.get("rrange", "")).strip()
    if share and share not in ["全部", "1分之1"]:
        continue

    yy = str(item.get("crmyy"))
    no = str(int(item.get("crmno")))
    batch = str(item.get("batchno", "")).strip()
    landno = str(item.get("landno", "")).strip()

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
    json_filtered[key] = item

print(f"JSON Unique Records (saleno 99): {len(json_filtered)}")

# 3. Final Verification
matched = 0
missing_in_json = []
for key in excel_keys:
    if key in json_filtered:
        matched += 1
    else:
        missing_in_json.append(key)

extra_in_json = []
for key in json_filtered:
    if key not in excel_keys:
        extra_in_json.append(key)

print("\nVerification Results:")
print(f"Matched with Excel: {matched} / {len(excel_keys)}")
print(f"Missing from JSON: {len(missing_in_json)}")
print(f"Extra in JSON (Not in Excel): {len(extra_in_json)}")

if missing_in_json:
    print("\nSample missing from JSON (first 5):")
    for m in missing_in_json[:5]:
        print(f"  {m}")

if extra_in_json:
    print("\nSample extra in JSON (first 5):")
    for e in extra_in_json[:5]:
        item = json_filtered[e]
        print(f"  {e} | ctmd: {item.get('ctmd')}")
