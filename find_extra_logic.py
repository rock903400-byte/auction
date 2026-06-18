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
    return (yy, no, batch, landno, county)


excel_keys = set()
for idx, row in df.iterrows():
    excel_keys.add(parse_excel_row(row))

# Load JSON
with open("fetched_data.json", "r", encoding="utf-8") as f:
    json_data = json.load(f)

keywords = "大同鄉 南澳鄉 員山鄉 復興區 尖石鄉 五峰鄉 橫山鄉 關西鎮 泰安鄉 南庄鄉 獅潭鄉 和平區 仁愛鄉 信義鄉 魚池鄉 水里鄉 阿里山鄉 桃源區 那瑪夏區 獅子鄉 三地門鄉 牡丹鄉 來義鄉 泰武鄉 瑪家鄉 春日鄉 滿州鄉 內埔鄉 秀林鄉 卓溪鄉 萬榮鄉 壽豐鄉 光復鄉 富里鄉 豐濱鄉 吉安鄉 鳳林鎮 玉里鎮 瑞穗鄉 花蓮市".split()

# Candidate items for General
candidates = []
for item in json_data:
    if str(item.get("saleno")) not in ["1", "2", "3", "4", "6"]:
        continue
    if str(item.get("rrange", "")).strip() not in ["", "全部", "1分之1"]:
        continue
    if str(item.get("saledate", "00000000")) < "01150428":
        continue
    if not any(k in str(item.get("ctmd", "")) for k in keywords):
        continue

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

    candidates.append({"key": key, "item": item})

# Deduplicate candidates by key + saleno
unique_candidates = {}
for c in candidates:
    k = c["key"] + (c["item"].get("saleno"),)
    if k not in unique_candidates:
        unique_candidates[k] = c

print(f"Total Unique Candidates: {len(unique_candidates)}")

# Extra in candidates (not in excel)
extra = []
for k, c in unique_candidates.items():
    if k[:5] not in excel_keys:
        extra.append(c)

print(f"Extra items: {len(extra)}")
if extra:
    print("\nSample extra item properties:")
    for e in extra[:5]:
        item = e["item"]
        print(
            f"  Key: {e['key']} | saleno: {item.get('saleno')} | saledate: {item.get('saledate')} | ctmd: {item.get('ctmd')} | rrange: {item.get('rrange')}"
        )
