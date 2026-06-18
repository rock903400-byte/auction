import pandas as pd
import json
import re

# Load Excel
excel_file = "49518.xls"
df = pd.read_excel(excel_file)


def parse_excel_row(row):
    # Case No: 110司執字第012521號 -> 110, 司執, 012521
    case_raw = str(row["字號\n股別"])
    case_match = re.search(r"(\d+)[\s\S]*?([^\d\s]+)[\s\S]*?第(\d+)號", case_raw)
    yy, id_str, no = "", "", ""
    if case_match:
        yy = case_match.group(1)
        id_str = case_match.group(2)
        no = case_match.group(3)

    batch = str(row["標別"]).strip() if pd.notnull(row["標別"]) else ""
    if batch == "nan":
        batch = ""

    auction_raw = str(row["拍賣日期\n拍賣次數"])
    auction_match = re.search(r"第(\d+)拍", auction_raw)
    saleno = auction_match.group(1) if auction_match else ""

    return yy, id_str, no, batch, saleno


# Load JSON
with open("fetched_data.json", "r", encoding="utf-8") as f:
    json_data = json.load(f)

# Group JSON items by (yy, no, batch) for faster lookup
json_lookup = {}
for item in json_data:
    yy = str(item.get("crmyy"))
    no = str(item.get("crmno")).lstrip("0")
    batch = str(item.get("batchno", "")).strip()
    key = (yy, no, batch)
    if key not in json_lookup:
        json_lookup[key] = []
    json_lookup[key].append(item)

missing_details = []
matched_count = 0

for idx, row in df.iterrows():
    yy, id_str, no, batch, saleno = parse_excel_row(row)
    # Remove leading zeros from no for matching
    clean_no = no.lstrip("0")
    key = (yy, clean_no, batch)

    matches = json_lookup.get(key, [])

    if not matches:
        missing_details.append(
            {
                "row": idx + 2,
                "case": f"{yy}{id_str}{no}",
                "batch": batch,
                "saleno": saleno,
                "reason": "Not found in raw API data (JSON)",
                "excel_val": row["字號\n股別"].replace("\n", " "),
            }
        )
        continue

    # Logic Check: saleno and rrange
    # Filter matches by saleno and rrange
    logic_pass = False
    for m in matches:
        m_saleno = str(m.get("saleno"))
        m_rrange = str(m.get("rrange", "")).strip()

        # Current GAS criteria
        s_ok = m_saleno in ["1", "2", "3"]
        r_ok = m_rrange in ["全部", "1分之1"]

        if s_ok and r_ok:
            logic_pass = True
            break

    if logic_pass:
        matched_count += 1
    else:
        # Why it failed logic
        m = matches[0]  # Just check the first one
        reason = ""
        if str(m.get("saleno")) not in ["1", "2", "3"]:
            reason = f"Saleno is {m.get('saleno')} (Excel says {saleno})"
        elif str(m.get("rrange", "")).strip() not in ["全部", "1分之1"]:
            reason = f"Rrange is '{m.get('rrange')}' (Partial share)"

        missing_details.append(
            {
                "row": idx + 2,
                "case": f"{yy}{id_str}{no}",
                "batch": batch,
                "saleno": saleno,
                "reason": reason,
                "excel_val": row["字號\n股別"].replace("\n", " "),
            }
        )

print(f"Total Excel Rows: {len(df)}")
print(f"Matched by current GAS logic: {matched_count}")
print(f"Missing/Excluded: {len(missing_details)}")

print("\nTop 20 Missing/Excluded reasons:")
for m in missing_details[:20]:
    print(
        f"Row {m['row']}: {m['case']} {m['batch']} | Reason: {m['reason']} | Excel: {m['excel_val']}"
    )

# Summary of reasons
reasons = {}
for m in missing_details:
    r = m["reason"].split(" (")[0]  # Simplify
    reasons[r] = reasons.get(r, 0) + 1

print("\nReason Summary:")
for r, count in reasons.items():
    print(f"  {r}: {count}")
