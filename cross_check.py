import pandas as pd
import json

# Load the user's reference Excel file
excel_file = "49518.xls"
try:
    df = pd.read_excel(excel_file)
    print(f"Loaded Excel: {excel_file}, Total Rows: {len(df)}")
except Exception as e:
    print(f"Error loading Excel: {e}")
    exit()

# Extract key identifying information from Excel
# We need to map Excel columns to API fields.
# Based on typical judicial Excel output:
# Court name, Case number (113司執12345), Section (股), Date, Lot (標別)
# Let's inspect column names first.
print("Excel Columns:", df.columns.tolist())

# Load local JSON data
with open("fetched_data.json", "r", encoding="utf-8") as f:
    json_data = json.load(f)


# Simulation of the CURRENT GAS LOGIC
def get_gas_processed_data(data):
    processed = []
    unique_keys = set()
    for item in data:
        saleno = str(item.get("saleno", ""))
        if saleno not in ["1", "2", "3"]:
            continue
        rrange = str(item.get("rrange", "")).strip()
        if rrange and rrange not in ["全部", "1分之1"]:
            continue

        # Identity Key
        key = f"{item.get('hsimun')}{item.get('crmyy')}年{item.get('crmid')}字第{item.get('crmno')}號{item.get('batchno', '')}"
        if key not in unique_keys:
            unique_keys.add(key)
            processed.append(item)
    return processed


gas_items = get_gas_processed_data(json_data)
print(f"GAS Processed Items: {len(gas_items)}")

# Create a list of identifiers for GAS items
gas_identifiers = set()
for item in gas_items:
    # 113司執012345
    case_str = f"{item.get('crmyy')}{item.get('crmid')}{item.get('crmno')}"
    # Remove leading zeros in crmno if necessary, but API usually has padding
    gas_identifiers.add((case_str, str(item.get("batchno", ""))))

# Try to match Excel rows
missing_in_gas = []
excel_identifiers = []

# Assume Excel has "字號" and "標別" or similar
# Let's look at the first few rows to confirm column names
print("\nFirst 3 rows of Excel:")
print(df.iloc[:3])
