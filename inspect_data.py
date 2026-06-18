import json

with open(
    "C:\\Users\\user\\Desktop\\法拍\\fetched_data.json", "r", encoding="utf-8"
) as f:
    data = json.load(f)

for item in data[:20]:
    crm = item.get("crm", "N/A")
    saledate = item.get("saledate", "N/A")
    saleno = item.get("saleno", "N/A")
    batchno = item.get("batchno", "N/A")
    print(f"Case: {crm}, Date: {saledate}, SaleNo: {saleno}, BatchNo: {batchno}")
