import json

with open("fetched_data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

unique_data = {}
total_raw = len(data)
filtered_by_saleno = 0
filtered_by_share = 0

for item in data:
    # 1. saleno must be "1", "2", or "3"
    saleno = str(item.get("saleno", ""))
    if saleno not in ["1", "2", "3"]:
        continue
    filtered_by_saleno += 1

    # 2. rrange must be "全部" or "1分之1"
    rrange = str(item.get("rrange", "")).strip()
    if rrange and rrange not in ["全部", "1分之1"]:
        continue
    filtered_by_share += 1

    # 3. Deduplication Key: hsimun + crmyy + crmid + crmno + batchno
    key = (
        str(item.get("hsimun"))
        + str(item.get("crmyy"))
        + str(item.get("crmid"))
        + str(item.get("crmno"))
        + str(item.get("batchno", "0"))
    )

    if key not in unique_data:
        unique_data[key] = item
    else:
        # Overwrite logic: if current proptype has "C" and existing doesn't
        existing = unique_data[key]
        item_proptype = str(item.get("proptype", ""))
        existing_proptype = str(existing.get("proptype", ""))
        if "C" in item_proptype and "C" not in existing_proptype:
            unique_data[key] = item

print(f"Total Raw Records: {total_raw}")
print(f"Records with saleno in [1, 2, 3]: {filtered_by_saleno}")
print(f"Records after rrange filtering: {filtered_by_share}")
print(f"Final Count after Deduplication: {len(unique_data)}")

# Sample cases to verify
print("\nSample Unique Keys:")
for k in list(unique_data.keys())[:5]:
    print(f"  {k}")
