import pandas as pd

df = pd.read_excel("49518.xls")


def parse_case(row):
    case_raw = str(row["字號\n股別"])
    batch = str(row["標別"]).strip()
    return case_raw, batch


unique_batches = set()
for _, row in df.iterrows():
    unique_batches.add(parse_case(row))

print(f"Total Rows in Excel: {len(df)}")
print(f"Unique Batches in Excel: {len(unique_batches)}")
