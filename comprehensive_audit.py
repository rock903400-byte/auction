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
        no = str(int(case_match.group(3)))
    batch = str(row["標別"]).strip() if pd.notnull(row["標別"]) else ""
    if batch == "nan":
        batch = ""

    auction_raw = str(row["拍賣日期\n拍賣次數"])
    auction_match = re.search(r"第(\d+)拍", auction_raw)
    saleno = auction_match.group(1) if auction_match else ""

    return yy, no, batch, saleno


excel_items = []
for idx, row in df.iterrows():
    yy, no, batch, saleno = parse_excel_row(row)
    excel_items.append(
        {"yy": yy, "no": no, "batch": batch, "saleno": saleno, "row_idx": idx + 2}
    )

# Load JSON
with open("fetched_data.json", "r", encoding="utf-8") as f:
    json_data = json.load(f)

# Deduplicate JSON by the same logic as GAS
gas_unique = {}
for item in json_data:
    saleno = str(item.get("saleno"))
    rrange = str(item.get("rrange", "")).strip()
    # Broaden filter to see if we are missing items due to strict filtering
    if rrange in ["全部", "1分之1", ""]:  # added empty string
        yy = str(item.get("crmyy"))
        no = str(int(item.get("crmno")))
        batch = str(item.get("batchno", "")).strip()
        key = (yy, no, batch)

        if saleno in ["1", "2", "3"]:
            if key not in gas_unique:
                gas_unique[key] = item
            else:
                # Prefer items with more info if needed
                pass

print(f"Excel Total Rows: {len(excel_items)}")
print(f"GAS Deduplicated (saleno 1-3): {len(gas_unique)}")

# Cross check
excel_keys = set((i["yy"], i["no"], i["batch"]) for i in excel_items)
gas_keys = set(gas_unique.keys())

missing_in_gas = [
    i for i in excel_items if (i["yy"], i["no"], i["batch"]) not in gas_keys
]
extra_in_gas = [k for k in gas_keys if k not in excel_keys]

print(f"\nMissing in GAS (Present in Excel): {len(missing_in_gas)}")
for i in missing_in_gas[:10]:
    print(
        f"  Excel Row {i['row_idx']}: {i['yy']}年 {i['no']}號 {i['batch']} (Excel saleno: {i['saleno']})"
    )

print(f"\nExtra in GAS (Not in Excel): {len(extra_in_gas)}")
for k in extra_in_gas[:10]:
    print(f"  {k}")
