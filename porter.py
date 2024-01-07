import typing
import requests
from bs4 import BeautifulSoup
import zipfile
import os
import uuid
import shutil
import json

SHEET = "https://docs.google.com/spreadsheets/d/13WWHcGiYJQD_rUqfGL17Lp0zn7MveU5xf7Fy-CNghzo/gviz/tq?tqx=out:html&tq&gid=1"

def scrapeDataFromSpreadsheet() -> typing.List[typing.List[str]]:
    html = requests.get(SHEET).text
    soup = BeautifulSoup(html, 'lxml')
    salas_cine = soup.find_all('table')[0]
    rows = [[td.text for td in row.find_all("td")] for row in salas_cine.find_all('tr')]
    return rows

invalid_chars = [
    ":", "/", "\'", "\"", "?", "#", "%", "&", "{", "}", "\\", "<", ">", "*", "$",
    "!", "@", "+", "`", "|", "=", "."
]
def filterFilename(name: str) -> str:
    for char in invalid_chars:
        name = name.replace(char, "")
    return name

headers = [
    "Date",
    "Game",
    "Song",
    "Group",
    "Composers",
    "Converters",
    "Binary",
    "Audio",
    "Duration",
    "Tracks",
    "Categories",
    "Notes",
]

# Parse Data
data = scrapeDataFromSpreadsheet()
parsed_data = []
game_list = []
for index, val in enumerate(data):
    if index >= 2:
        new_data = {}
        for header_index, header in enumerate(headers):
            substring = val[header_index]
            if substring[0] == "|":
                substring = substring[1:]
            substring = substring.replace("\xa0","")
            if len(substring) > 0:
                new_data[header] = substring
        parsed_data.append(new_data)
        game_name = new_data["Game"]
        if game_name not in game_list:
            game_list.append(game_name)
# Clear Games
if os.path.exists("./binaries"):
    shutil.rmtree("./binaries")
os.mkdir("./binaries")
for game in game_list:
    if os.path.exists(f"./binaries/{filterFilename(game)}"):
        shutil.rmtree(f"./binaries/{filterFilename(game)}")
# Generate files
new_json = []
made_files = {}
with zipfile.ZipFile("pack.zip", 'r') as zip_ref:
    for index, new_data in enumerate(parsed_data):
        if len(new_data["Binary"].strip()) > 0:
            game_name = new_data["Game"]
            song_name = new_data["Song"]
            converters = new_data["Converters"]
            new_data["UUID"] = str(uuid.uuid4())
            new_file_name_raw = f"binaries/{filterFilename(game_name)}/{filterFilename(song_name)} by {filterFilename(converters)}"
            if new_file_name_raw in made_files:
                new_file_name = f"{new_file_name_raw} (REV {made_files[new_file_name_raw]}).bin"
                made_files[new_file_name_raw] += 1
            else:
                new_file_name = f"{new_file_name_raw}.bin"
                made_files[new_file_name_raw] = 1
            if not os.path.exists(f"./binaries/{filterFilename(game_name)}"):
                os.mkdir(f"./binaries/{filterFilename(game_name)}")
            bin_file_name = f"{new_data['Binary']}.bin"
            if bin_file_name in zip_ref.namelist():
                with zip_ref.open(bin_file_name) as binary:
                    with open(new_file_name, "wb") as fh:
                        fh.write(binary.read())
            new_data["Binary"] = new_file_name
            if "Tracks" in new_data:
                new_data["Tracks"] = int(new_data["Tracks"])
            if "Duration" in new_data:
                new_data["Duration"] = float(new_data["Duration"])
            new_json.append(new_data)
with open("mapping.json", "w", encoding="utf-8") as output_data:
    output_data.write(json.dumps(new_json, indent=4))
            