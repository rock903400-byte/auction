import json

with open("fetched_data.json", "r", encoding="utf-8") as f:
    data = json.load(f)


def get_unique_count(items):
    unique = {}
    for item in items:
        # Key: County + Year + ID + No + Batch
        key = f"{item.get('hsimun')}{item.get('crmyy')}{item.get('crmid')}{item.get('crmno')}{item.get('batchno', '')}"
        if key not in unique:
            unique[key] = item
    return len(unique), unique


# Filter by share first as it's a common requirement
filtered_data = [
    item
    for item in data
    if str(item.get("rrange", "")).strip() in ["全部", "1分之1", ""]
]

print(f"Total records after share filter: {len(filtered_data)}")

# 1. Try to find 138 for Buy Program (Usually saleno '4')
buy_candidates = [item for item in filtered_data if str(item.get("saleno")) == "4"]
buy_count, buy_unique = get_unique_count(buy_candidates)
print(f"Buy Program (saleno '4') Unique Count: {buy_count}")

# 2. Try to find 268 for General Program
# Let's try saleno 1, 2, 3, 6, 99 (99 is sometimes used for special cases or '公告')
general_candidates = [
    item
    for item in filtered_data
    if str(item.get("saleno")) in ["1", "2", "3", "6", "99"]
]
gen_count, gen_unique = get_unique_count(general_candidates)
print(f"General Program (saleno 1,2,3,6,99) Unique Count: {gen_count}")

# 3. What if General is anything NOT '4'?
gen_candidates_v2 = [item for item in filtered_data if str(item.get("saleno")) != "4"]
gen_count_v2, gen_unique_v2 = get_unique_count(gen_candidates_v2)
print(f"General Program (saleno != '4') Unique Count: {gen_count_v2}")

# 4. Check saleno '99' specifically
s99 = [item for item in filtered_data if str(item.get("saleno")) == "99"]
print(f"saleno '99' Unique Count: {get_unique_count(s99)[0]}")

# 5. Check if there are overlaps
buy_keys = set(buy_unique.keys())
gen_keys = set(gen_unique.keys())
overlap = buy_keys.intersection(gen_keys)
print(f"Overlap between Buy and General (1,2,3,6,99): {len(overlap)}")
