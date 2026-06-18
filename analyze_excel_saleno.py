import json

with open("fetched_data.json", "r", encoding="utf-8") as f:
    data = json.load(f)


def get_unique_parcel_count(items):
    unique = {}
    for item in items:
        # Key: County + Year + ID + No + Batch + LandNo
        key = (
            item.get("hsimun"),
            item.get("crmyy"),
            item.get("crmid"),
            item.get("crmno"),
            item.get("batchno", ""),
            item.get("landno", ""),
        )
        if key not in unique:
            unique[key] = item
    return len(unique), unique


# Filter share
filtered_data = [
    item for item in data if str(item.get("rrange", "")).strip() in ["全部", "1分之1"]
]

# 1. Buy Program (saleno '4')
buy_candidates = [item for item in filtered_data if str(item.get("saleno")) == "4"]
buy_count, _ = get_unique_parcel_count(buy_candidates)
print(f"Buy Program (saleno '4') Unique Parcels: {buy_count}")

# 2. General Program (Target 268)
# Let's see what saleno's are in the Excel.
# Based on comprehensive_audit.py, Excel has 1, 2, 3, 4, 6.
# WAIT. Excel HAS saleno 4?
# Row 2: 110年 12521號 A (Excel saleno: 4)
# If saleno 4 is in Excel (General Program), then what is in Buy Program?
# Ah! In Taiwan, some "第4拍" are General and some are "公告應買".
# But wait, usually General Program is 1st, 2nd, 3rd. Then it goes to Buy (公告應買). Then it might go to 4th (減價拍賣).
# Or something like that.

# Let's check the Excel content for saleno again.
# I'll use a script to count saleno in Excel.
