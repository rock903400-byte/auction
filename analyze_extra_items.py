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
        no = case_match.group(3)
    batch = str(row["標別"]).strip() if pd.notnull(row["標別"]) else ""
    if batch == "nan":
        batch = ""
    return yy, no.lstrip("0"), batch


# Load JSON
with open("fetched_data.json", "r", encoding="utf-8") as f:
    json_data = json.load(f)

excel_keys = set()
for idx, row in df.iterrows():
    excel_keys.add(parse_excel_row(row))

# Find items in GAS (1,2,3拍) that are NOT in Excel
only_in_gas = []
for item in json_data:
    saleno = str(item.get("saleno"))
    rrange = str(item.get("rrange", "")).strip()
    if saleno in ["1", "2", "3"] and rrange in ["全部", "1分之1"]:
        yy = str(item.get("crmyy"))
        no = str(item.get("crmno")).lstrip("0")
        batch = str(item.get("batchno", "")).strip()
        key = (yy, no, batch)
        if key not in excel_keys:
            only_in_gas.append(item)

print(f"Items in GAS (1-3) but NOT in Excel: {len(only_in_gas)}")
if only_in_gas:
    print("\nSample items ONLY in GAS:")
    for item in only_in_gas[:10]:
        print(
            f"  Case: {item.get('crmyy')}{item.get('crmid')}{item.get('crmno')}, Batch: {item.get('batchno')}, Saleno: {item.get('saleno')}, Town: {item.get('ctmd')}, Date: {item.get('saledate')}"
        )

# Check if they are from some specific town or date
towns = {}
for item in only_in_gas:
    t = item.get("ctmd")
    towns[t] = towns.get(t, 0) + 1
print("\nTown distribution of 'Only in GAS' items:")
print(towns)

dates = {}
for item in only_in_gas:
    d = item.get("saledate")
    dates[d] = dates.get(d, 0) + 1
print("\nDate distribution of 'Only in GAS' items:")
print(sorted(dates.items()))
