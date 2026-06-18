import json

with open("fetched_data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

if data:
    keys = set()
    for item in data:
        keys.update(item.keys())
    print("All keys in the first item:", list(data[0].keys()))
    print("All unique keys in the whole dataset:", sorted(list(keys)))

    # Look for items where saleno might be related to auction type
    # (though we think it's target no)

    # Let's see if there are any fields we missed
    for key in sorted(list(keys)):
        if "sale" in key.lower() or "type" in key.lower() or "title" in key.lower():
            print(f"Potential field: {key}")
