import pandas as pd
import json
import re

# Load Excel
excel_file = "49518.xls"
df = pd.read_excel(excel_file)


def parse_excel_row(row):
    # Case No: 110司執字第012521號 -> 110, 司執, 012521
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

    auction_raw = str(row["拍賣日期\n拍賣次數"])
    auction_match = re.search(r"第(\d+)拍", auction_raw)
    saleno = auction_match.group(1) if auction_match else ""

    return yy, id_str, no, batch, saleno


# Load JSON
with open("fetched_data.json", "r", encoding="utf-8") as f:
    json_data = json.load(f)

# Group JSON items by (yy, no, batch) for faster lookup
json_lookup = {}
for item in json_data:
    yy = str(item.get("crmyy"))
    no = str(item.get("crmno")).lstrip("0")
    batch = str(item.get("batchno", "")).strip()
    key = (yy, no, batch)
    if key not in json_lookup:
        json_lookup[key] = []
    json_lookup[key].append(item)

# 1. Identify rows that are correctly in saleno 1, 2, 3 but GAS still didn't count them all?
# Wait, Matched by current GAS logic: 237.
# Total GAS Processed Items: 260.
# This means there are 260 - 237 = 23 items in GAS that are NOT in the Excel.
# And 268 - 237 = 31 items in Excel that are NOT in GAS.

gas_processed_keys = set()
for item in json_data:
    saleno = str(item.get("saleno"))
    rrange = str(item.get("rrange", "")).strip()
    if saleno in ["1", "2", "3"] and rrange in ["全部", "1分之1"]:
        yy = str(item.get("crmyy"))
        no = str(item.get("crmno")).lstrip("0")
        batch = str(item.get("batchno", "")).strip()
        gas_processed_keys.add((yy, no, batch))

excel_keys = set()
for idx, row in df.iterrows():
    yy, id_str, no, batch, saleno = parse_excel_row(row)
    excel_keys.add((yy, no.lstrip("0"), batch))

only_in_gas = gas_processed_keys - excel_keys
print(f"Items in GAS but NOT in Excel: {len(only_in_gas)}")
if only_in_gas:
    print("Sample items only in GAS (first 5):")
    for k in list(only_in_gas)[:5]:
        print(f"  {k}")

only_in_excel = excel_keys - gas_processed_keys
print(f"Items in Excel but NOT in GAS: {len(only_in_excel)}")
# We already know these 31 are mostly saleno 4 or 6.
# Let's double check if any are saleno 1, 2, 3.
missing_low_saleno = []
for k in only_in_excel:
    # Find saleno from Excel for this key
    rows = df[
        df.apply(
            lambda r: parse_excel_row(r)[0:3] == (k[0], "", k[1].zfill(6))
            or parse_excel_row(r)[0:3] == (k[0], "", k[1]),
            axis=1,
        )
    ]  # simplified check
    # Let's just use the previous logic
    pass

# Re-run logic for clarity
missing_low_saleno_count = 0
for idx, row in df.iterrows():
    yy, id_str, no, batch, saleno = parse_excel_row(row)
    if saleno in ["1", "2", "3"]:
        key = (yy, no.lstrip("0"), batch)
        if key not in gas_processed_keys:
            missing_low_saleno_count += 1
            print(
                f"Row {idx+2}: {yy}{id_str}{no} {batch} is saleno {saleno} in Excel but missing in GAS logic!"
            )

print(f"Excel items with saleno 1-3 missing in GAS: {missing_low_saleno_count}")
