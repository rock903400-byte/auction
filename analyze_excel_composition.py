import pandas as pd
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
    return f"{yy}{id_str}{no}", batch


print(f"Total rows in Excel: {len(df)}")

# Check for duplicates by Case+Lot
keys = [parse_excel_row(row) for _, row in df.iterrows()]
unique_keys = set(keys)
print(f"Unique Case+Lot combinations in Excel: {len(unique_keys)}")

if len(keys) != len(unique_keys):
    print(f"Found {len(keys) - len(unique_keys)} duplicate Case+Lot rows in Excel.")
    # Show some duplicates
    from collections import Counter

    counts = Counter(keys)
    for k, c in counts.items():
        if c > 1:
            print(f"  Duplicate: {k} appears {c} times")


# Check saleno distribution again
def get_saleno(row):
    auction_raw = str(row["拍賣日期\n拍賣次數"])
    match = re.search(r"第(\d+)拍", auction_raw)
    return match.group(1) if match else "Other"


salenos = [get_saleno(row) for _, row in df.iterrows()]
from collections import Counter

print("\nSaleno distribution in Excel:")
print(Counter(salenos))
