import pandas as pd
import json
import re

# Load Excel
df = pd.read_excel("C:\\Users\\user\\Desktop\\法拍\\02919.xls")


# Extract case numbers from Excel
# "字號\n股別": "110司執字第012521號\n(孝股)"
def extract_case_no(s):
    if not isinstance(s, str):
        return s
    match = re.search(r"(\d+司執字第\d+號)", s)
    return match.group(1) if match else s


excel_cases = set(df["字號\n股別"].apply(extract_case_no))
print(f"Unique Case Numbers in Excel: {len(excel_cases)}")

# Load JSON
with open(
    "C:\\Users\\user\\Desktop\\法拍\\fetched_data.json", "r", encoding="utf-8"
) as f:
    data = json.load(f)

# Use only unique records (first 638)
unique_data = data[0:638]


# GAS logic for Case Number: item.crmyy + "年" + item.crmid + "字第" + item.crmno + "號"
def get_gas_case_no(item):
    return f"{item['crmyy']}年{item['crmid']}字第{item['crmno']}號"


# But Excel format is "110司執字第012521號"
# So let's convert JSON to that format for comparison
def get_comp_case_no(item):
    return f"{item['crmyy']}{item['crmid']}字第{item['crmno']}號"


gas_cases = set(get_comp_case_no(item) for item in unique_data)
print(f"Unique Case Numbers in JSON: {len(gas_cases)}")

# Intersection and Difference
common = gas_cases.intersection(excel_cases)
only_gas = gas_cases - excel_cases
only_excel = excel_cases - gas_cases

print(f"Common Cases: {len(common)}")
print(f"Only in GAS: {len(only_gas)}")
print(f"Only in Excel: {len(only_excel)}")

if only_gas:
    print("\nSample cases only in GAS:")
    for c in list(only_gas)[:10]:
        # Find item in JSON to see details
        item = next(i for i in unique_data if get_comp_case_no(i) == c)
        print(
            f"Case: {c}, Town: {item.get('ctmd')}, Date: {item.get('saledate')}, Saleno: {item.get('saleno')}"
        )

if only_excel:
    print("\nSample cases only in Excel:")
    for c in list(only_excel)[:10]:
        print(c)
