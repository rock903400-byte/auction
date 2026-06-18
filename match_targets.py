import json

with open("fetched_data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Filter share
data = [
    item for item in data if str(item.get("rrange", "")).strip() in ["全部", "1分之1"]
]


def get_unique_count(items, key_type="parcel"):
    unique = {}
    for item in items:
        if key_type == "parcel":
            key = (
                item.get("hsimun"),
                item.get("crmyy"),
                item.get("crmid"),
                item.get("crmno"),
                item.get("batchno", ""),
                item.get("landno", ""),
            )
        else:  # case/batch
            key = (
                item.get("hsimun"),
                item.get("crmyy"),
                item.get("crmid"),
                item.get("crmno"),
                item.get("batchno", ""),
            )

        if key not in unique:
            unique[key] = item
    return len(unique)


# Let's try to match 138.
# Maybe 138 is unique BATCHES in Buy Program?
# And 268 is unique PARCELS in General Program?

saleno_counts_batches = {}
saleno_counts_parcels = {}

all_salenos = sorted(list(set(str(i.get("saleno")) for i in data)))

for s in all_salenos:
    items = [i for i in data if str(i.get("saleno")) == s]
    saleno_counts_batches[s] = get_unique_count(items, "batch")
    saleno_counts_parcels[s] = get_unique_count(items, "parcel")

print("Unique Counts per saleno:")
print(f"{'saleno':<10} {'Unique Batches':<20} {'Unique Parcels':<20}")
for s in all_salenos:
    print(f"{s:<10} {saleno_counts_batches[s]:<20} {saleno_counts_parcels[s]:<20}")

# Target Buy: 138.
# Is 138 any of these?
# saleno '99' unique batches is 73. 73 * 2 = 146? No.
# saleno '4' unique batches is 91. 91? No.

# Wait, what if Buy is saleno 4 and 99 combined?
buy_items = [i for i in data if str(i.get("saleno")) in ["4", "99"]]
print(f"\nUnique Batches (saleno 4, 99): {get_unique_count(buy_items, 'batch')}")
print(f"Unique Parcels (saleno 4, 99): {get_unique_count(buy_items, 'parcel')}")

# What if General is saleno 1, 2, 3?
gen_items = [i for i in data if str(i.get("saleno")) in ["1", "2", "3"]]
print(f"\nUnique Batches (saleno 1, 2, 3): {get_unique_count(gen_items, 'batch')}")
print(f"Unique Parcels (saleno 1, 2, 3): {get_unique_count(gen_items, 'parcel')}")

# What if General includes saleno 6?
gen_items_v2 = [i for i in data if str(i.get("saleno")) in ["1", "2", "3", "6"]]
print(f"Unique Batches (saleno 1, 2, 3, 6): {get_unique_count(gen_items_v2, 'batch')}")
print(f"Unique Parcels (saleno 1, 2, 3, 6): {get_unique_count(gen_items_v2, 'parcel')}")
