import pandas as pd
import re

df = pd.read_excel("49518.xls")
salenos = []
for _, row in df.iterrows():
    val = str(row["拍賣日期\n拍賣次數"])
    match = re.search(r"第(\d+)拍", val)
    if match:
        salenos.append(match.group(1))
    else:
        salenos.append("None")

from collections import Counter

print(Counter(salenos))
