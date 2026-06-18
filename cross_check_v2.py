import pandas as pd
import json
import re

# Load Excel
excel_file = "49518.xls"
df = pd.read_excel(excel_file)


# Function to extract case details from Excel
def parse_excel_row(row):
    # Case No: 110司執字第012521號 -> 110司執012521
    case_raw = str(row["字號\n股別"])
    case_match = re.search(r"(\d+)[\s\S]*?([^\d\s]+)[\s\S]*?第(\d+)號", case_raw)
    case_id = ""
    if case_match:
        case_id = f"{case_match.group(1)}{case_match.group(2)}{case_match.group(3)}"

    # Lot: NaN or A, B...
    batch = str(row["標別"]) if pd.notnull(row["標別"]) else ""

    # Auction times: 115/05/27\n第4拍 -> 4
    auction_raw = str(row["拍賣日期\n拍賣次數"])
    auction_match = re.search(r"第(\d+)拍", auction_raw)
    saleno = auction_match.group(1) if auction_match else ""

    return case_id, batch, saleno


# Load JSON
with open("fetched_data.json", "r", encoding="utf-8") as f:
    json_data = json.load(f)

# Identify all general auction items in JSON (saleno 1, 2, 3)
gas_logic_identifiers = set()
for item in json_data:
    if str(item.get("saleno")) in ["1", "2", "3"]:
        rrange = str(item.get("rrange", "")).strip()
        if rrange in ["全部", "1分之1"]:
            case_id = f"{item.get('crmyy')}{item.get('crmid')}{item.get('crmno')}"
            batch = str(item.get("batchno", ""))
            gas_logic_identifiers.add((case_id, batch))

print(f"Items in GAS logic (saleno 1-3, all-share): {len(gas_logic_identifiers)}")

# Compare with Excel
excel_items = []
saleno_counts = {}

for idx, row in df.iterrows():
    case_id, batch, saleno = parse_excel_row(row)
    excel_items.append(
        {
            "case": case_id,
            "batch": batch,
            "saleno": saleno,
            "raw": row["字號\n股別"].replace("\n", " "),
        }
    )
    saleno_counts[saleno] = saleno_counts.get(saleno, 0) + 1

print("\nExcel saleno distribution:")
for s, count in sorted(saleno_counts.items()):
    print(f"  第 {s} 拍: {count}")

# Check which Excel items are missing in GAS logic
missing = []
for item in excel_items:
    if (item["case"], item["batch"]) not in gas_logic_identifiers:
        missing.append(item)

print(f"\nExcel items missing in GAS logic: {len(missing)}")
if missing:
    print("Sample missing items (first 10):")
    for m in missing[:10]:
        print(
            f"  Case: {m['case']}, Batch: {m['batch']}, Saleno: {m['saleno']}, Raw: {m['raw']}"
        )

# Check why they are missing
# 1. Is it because saleno > 3?
saleno_over_3 = [m for m in missing if m["saleno"] and int(m["saleno"]) > 3]
print(f"\nMissing because Saleno > 3 (e.g., 4th, 6th auction): {len(saleno_over_3)}")

# 2. Is it because of "99" (公告)?
saleno_99 = [m for m in missing if m["saleno"] == "99"]
print(f"Missing because Saleno is 99 (公告): {len(saleno_99)}")

# 3. Check for items that ARE saleno 1-3 but still missing (maybe rrange?)
missing_low_saleno = [m for m in missing if m["saleno"] in ["1", "2", "3"]]
print(f"Missing despite Saleno 1-3: {len(missing_low_saleno)}")
for m in missing_low_saleno:
    # Look for these in raw JSON
    found_in_raw = [
        j
        for j in json_data
        if f"{j.get('crmyy')}{j.get('crmid')}{j.get('crmno')}" == m["case"]
        and str(j.get("batchno", "")) == m["batch"]
    ]
    if found_in_raw:
        print(
            f"  Found in raw JSON: {m['case']} {m['batch']}, saleno: {found_in_raw[0].get('saleno')}, rrange: '{found_in_raw[0].get('rrange')}'"
        )
    else:
        print(f"  NOT found in raw JSON at all: {m['case']} {m['batch']}")
