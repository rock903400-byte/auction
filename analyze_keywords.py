import pandas as pd
import re

# Load Excel
excel_file = "49518.xls"
df = pd.read_excel(excel_file)

# Extract towns from "縣市" and "土地坐落/面積"
# Row example: 縣市: 花蓮縣, 土地坐落: 秀林鄉...
towns = set()
for idx, row in df.iterrows():
    # Try to find town in the address string
    addr = str(row["土地坐落/面積"])
    # Towns are usually 3 chars: XX鄉, XX區, XX鎮, XX市
    match = re.search(r"([^\s\d]+?[鄉區鎮市])", addr)
    if match:
        towns.add(match.group(1))

print(f"Towns found in Excel ({len(towns)}):")
print(sorted(list(towns)))

# Check if there are any towns in my script's keywords that are NOT in the Excel
script_keywords = "大同鄉 南澳鄉 員山鄉 烏來區 復興區 尖石鄉 五峰鄉 橫山鄉 關西鎮 泰安鄉 南庄鄉 獅潭鄉 和平區 仁愛鄉 信義鄉 魚池鄉 水里鄉 阿里山鄉 桃源區 那瑪夏區 茂林區 六龜區 獅子鄉 三地門鄉 牡丹鄉 來義鄉 泰武鄉 瑪家鄉 春日鄉 霧臺鄉 滿州鄉 車城鄉 內埔鄉 新埤鄉 秀林鄉 卓溪鄉 萬榮鄉 壽豐鄉 光復鄉 富里鄉 豐濱鄉 吉安鄉 鳳林鎮 玉里鎮 瑞穗鄉 花蓮市 新城鄉"
script_towns = set(script_keywords.split())

missing_in_excel = script_towns - towns
print(f"\nTowns in script but NOT in Excel ({len(missing_in_excel)}):")
print(sorted(list(missing_in_excel)))

missing_in_script = towns - script_towns
print(f"\nTowns in Excel but NOT in script ({len(missing_in_script)}):")
print(sorted(list(missing_in_script)))
