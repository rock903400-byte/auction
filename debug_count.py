import json

with open("fetched_data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print(f"Total raw records: {len(data)}")


# Current GAS logic (simulated)
def count_with_current_logic(data):
    unique_data = {}
    for item in data:
        # Filter saleno 4 and 5
        saleno = str(item.get("saleno", ""))
        if saleno in ["4", "5"]:
            continue

        # Filter shares (shre) - BUG: shre is missing, rrange should be used
        shre = str(item.get("shre", "")).strip()
        if shre and shre not in ["全部", "1分之1"]:
            continue

        key = (
            str(item.get("hsimun"))
            + str(item.get("crmyy"))
            + str(item.get("crmid"))
            + str(item.get("crmno"))
            + str(item.get("batchno", "0"))
        )
        unique_data[key] = item
    return len(unique_data)


# Improved logic
def count_with_improved_logic(data):
    unique_data = {}
    for item in data:
        saleno = str(item.get("saleno", ""))
        # Usually 1, 2, 3 are general. 4 is Buying. 5+ are special?
        # User might want to exclude 99 too.
        if saleno not in ["1", "2", "3"]:
            continue

        # Use rrange for share filtering
        rrange = str(item.get("rrange", "")).strip()
        # In some cases rrange might be "全部" or something else
        if rrange and rrange not in ["全部", "1分之1"]:
            continue

        key = (
            str(item.get("hsimun"))
            + str(item.get("crmyy"))
            + str(item.get("crmid"))
            + str(item.get("crmno"))
            + str(item.get("batchno", "0"))
        )
        unique_data[key] = item
    return len(unique_data)


print(f"Count with current (buggy) logic: {count_with_current_logic(data)}")
print(
    f"Count with saleno in [1,2,3] and rrange filter: {count_with_improved_logic(data)}"
)

# Check unique saleno values that are NOT 4 or 5
other_saleno = set()
for item in data:
    s = str(item.get("saleno", ""))
    if s not in ["4", "5"]:
        other_saleno.add(s)
print(f"Other saleno values found: {sorted(list(other_saleno))}")

# Check rrange values
rranges = {}
for item in data:
    r = str(item.get("rrange", ""))
    rranges[r] = rranges.get(r, 0) + 1
print("Rrange distribution (first 20):")
for r, count in list(rranges.items())[:20]:
    print(f"  {r}: {count}")
