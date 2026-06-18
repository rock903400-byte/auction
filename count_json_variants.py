import json

with open("fetched_data.json", "r", encoding="utf-8") as f:
    json_data = json.load(f)


# Count unique items in JSON (all saleno, all rrange)
def get_unique_count(data, allow_saleno=None, saletype_filter=None):
    unique_data = {}
    for item in data:
        # Simulate API filtering if possible
        # But fetched_data.json only has saletype="" results

        saleno = str(item.get("saleno"))
        if allow_saleno and saleno not in allow_saleno:
            continue

        rrange = str(item.get("rrange", "")).strip()
        if rrange not in ["全部", "1分之1"]:
            continue

        # Key: Court + Year + ID + No + Batch
        key = f"{item.get('hsimun')}{item.get('crmyy')}{item.get('crmid')}{item.get('crmno')}{item.get('batchno', '')}"

        if key not in unique_data:
            unique_data[key] = item
    return len(unique_data)


print(f"Total Unique in JSON (1-99): {get_unique_count(json_data)}")
print(
    f"Unique (1,2,3,4,6): {get_unique_count(json_data, allow_saleno=['1','2','3','4','6'])}"
)
print(f"Unique (1,2,3): {get_unique_count(json_data, allow_saleno=['1','2','3'])}")
print(f"Unique (4,6): {get_unique_count(json_data, allow_saleno=['4','6'])}")
