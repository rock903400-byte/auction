import pandas as pd
import json
import re

# Load Excel
excel_file = "49518.xls"
df = pd.read_excel(excel_file)


def parse_excel_row(row):
    case_raw = str(row["字號\n股別"])
    case_match = re.search(r"(\d+)[\s\S]*?([^\d\s]+)[\s\S]*?第(\d+)號", case_raw)
    yy, id_str, no = "", "", ""
    if case_match:
        yy = case_match.group(1)
        id_str = case_match.group(2)
        no = str(int(case_match.group(3)))  # clean leading zeros
    batch = str(row["標別"]).strip() if pd.notnull(row["標別"]) else ""
    if batch == "nan":
        batch = ""
    return yy, no, batch


# Load JSON
with open("fetched_data.json", "r", encoding="utf-8") as f:
    json_data = json.load(f)

excel_keys = set()
for idx, row in df.iterrows():
    excel_keys.add(parse_excel_row(row))

# Find items in GAS (1,2,3,4,6拍) that are NOT in Excel
only_in_gas = []
gas_logic_keys = set()
for item in json_data:
    saleno = str(item.get("saleno"))
    rrange = str(item.get("rrange", "")).strip()
    if rrange in ["全部", "1分之1"]:
        yy = str(item.get("crmyy"))
        no = str(int(item.get("crmno")))
        batch = str(item.get("batchno", "")).strip()
        key = (yy, no, batch)
        gas_logic_keys.add(key)
        if key not in excel_keys:
            only_in_gas.append(item)

print(f"Total Unique Keys in GAS Logic: {len(gas_logic_keys)}")
print(f"Items in GAS Logic but NOT in Excel: {len(only_in_gas)}")

# Check items in Excel but NOT in GAS
only_in_excel = []
for k in excel_keys:
    if k not in gas_logic_keys:
        only_in_excel.append(k)

print(f"Items in Excel but NOT in GAS: {len(only_in_excel)}")
if only_in_excel:
    print("Sample items ONLY in Excel:")
    print(only_in_excel[:10])
