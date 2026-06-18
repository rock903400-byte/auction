import json

with open("fetched_data.json", "r", encoding="utf-8") as f:
    json_data = json.load(f)


def get_counts_refined(data):
    # Using a key that identifies unique LAND PLOTS
    # Key: Court + Case No + Sale No + Lot + Section + Land No
    def get_plot_key(item):
        return f"{item.get('hsimun')}{item.get('crmyy')}{item.get('crmid')}{item.get('crmno')}{item.get('saleno')}{item.get('batchno', '')}{item.get('sec', '')}{item.get('landno', '')}"

    general_unique = {}

    for item in data:
        # Filter share
        rrange = str(item.get("rrange", "")).strip()
        if rrange not in ["全部", "1分之1"]:
            continue

        key = get_plot_key(item)

        # In this JSON (General search), we just take everything
        if key not in general_unique:
            general_unique[key] = item

    return len(general_unique)


total_gen = get_counts_refined(json_data)
print(f"Total Unique Land Plots in General Search: {total_gen}")

# If this is 268, we found the winning logic!
