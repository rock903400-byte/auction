import json

with open(
    "C:\\Users\\user\\Desktop\\法拍\\fetched_data.json", "r", encoding="utf-8"
) as f:
    data = json.load(f)

unique_data = data[0:638]

# GAS De-duplication logic
# const uniqueKey = item.hsimun + item.crmyy + item.crmid + item.crmno + (item.saleno || "0");
gas_unique = {}
for item in unique_data:
    # saletype check (no-op as saletype is missing)
    # shre check (no-op as shre is missing)

    key = (
        str(item.get("hsimun"))
        + str(item.get("crmyy"))
        + str(item.get("crmid"))
        + str(item.get("crmno"))
        + str(item.get("saleno", "0"))
    )

    if key not in gas_unique:
        gas_unique[key] = item
    else:
        # GAS logic for overwriting:
        # if (item.proptype && item.proptype.includes("C") && (!existing.proptype || !existing.proptype.includes("C")))
        # But here proptype is C51 for all.
        pass

print(f"Total Unique Keys (GAS Logic): {len(gas_unique)}")

# Let's check for "持分" in any field
partial_shares = []
for item in unique_data:
    is_partial = False
    for val in item.values():
        if isinstance(val, str) and ("持分" in val or "分之" in val):
            if "1分之1" not in val and "全部" not in val:
                is_partial = True
                break
    if is_partial:
        partial_shares.append(item)

print(f"Records that look like partial shares: {len(partial_shares)}")

# Check for "應買" or saletype 4 equivalent
# In our JSON, saleno was 4 for some.
# But Excel has those too.
# saletype 4 usually means "特別變賣" (Buying period)
# Let's check the saletitle or saletype if we can find it.
# Wait, I don't have saletitle in JSON.
