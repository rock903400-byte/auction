import json

with open("fetched_data.json", "r", encoding="utf-8") as f:
    json_data = json.load(f)


def get_row_counts(data):
    general_rows = 0
    buy_rows = 0

    for item in data:
        # Filter share
        rrange = str(item.get("rrange", "")).strip()
        if rrange not in ["全部", "1分之1"]:
            continue

        saleno = str(item.get("saleno", ""))

        # If we DON'T de-duplicate:
        if saleno in ["4", "5"]:
            buy_rows += 1
        else:
            general_rows += 1

    return general_rows, buy_rows


gen_r, buy_rows = get_row_counts(json_data)

print("Total Rows in JSON (No De-duplication, Share Filtered):")
print(f"  General Program rows: {gen_r}")
print(f"  Buy Program rows: {buy_rows}")

# Check saleno counts specifically
from collections import Counter

salenos = [
    str(item.get("saleno"))
    for item in json_data
    if str(item.get("rrange", "")).strip() in ["全部", "1分之1"]
]
print("\nSaleno counts in JSON:")
print(Counter(salenos))
