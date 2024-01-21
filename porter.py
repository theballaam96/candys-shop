import typing
import requests
from bs4 import BeautifulSoup
import zipfile
import os
import shutil
import json
import urllib.parse

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
    "Category",
    "Composers",
    "Converters",
    "Binary",
    "Audio",
    "Duration",
    "Tracks",
    "Tags",
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
file_dirs = ["binaries", "previews"]
for d in file_dirs:
    if os.path.exists(f"./{d}"):
        shutil.rmtree(f"./{d}")
    os.mkdir(f"./{d}")
    for game in game_list:
        if os.path.exists(f"./{d}/{filterFilename(game)}"):
            shutil.rmtree(f"./{d}/{filterFilename(game)}")
# Generate files
new_json = []
made_files = {}
with zipfile.ZipFile("pack.zip", 'r') as zip_ref:
    for index, new_data in enumerate(parsed_data):
        if len(new_data["Binary"].strip()) > 0:
            game_name = new_data["Game"]
            song_name = new_data["Song"]
            converters = new_data["Converters"]
            new_file_name_raw = f"binaries/{filterFilename(game_name)}/{filterFilename(song_name)} by {filterFilename(converters)}"
            new_audio_name_raw = f"previews/{filterFilename(game_name)}/{filterFilename(song_name)} by {filterFilename(converters)}"
            if new_file_name_raw in made_files:
                new_file_name = f"{new_file_name_raw} (REV {made_files[new_file_name_raw]}).bin"
                new_audio_name_raw = f"{new_audio_name_raw} (REV {made_files[new_file_name_raw]})"
                made_files[new_file_name_raw] += 1
            else:
                new_file_name = f"{new_file_name_raw}.bin"
                new_audio_name_raw = f"{new_audio_name_raw}"
                made_files[new_file_name_raw] = 1
            for d in file_dirs:
                if not os.path.exists(f"./{d}/{filterFilename(game_name)}"):
                    os.mkdir(f"./{d}/{filterFilename(game_name)}")
            bin_file_name = f"{new_data['Binary']}.bin"
            if bin_file_name in zip_ref.namelist():
                with zip_ref.open(bin_file_name) as binary:
                    with open(new_file_name, "wb") as fh:
                        fh.write(binary.read())
            new_data["Binary"] = new_file_name
            new_data["Verified"] = True
            if "Tracks" in new_data:
                new_data["Tracks"] = int(new_data["Tracks"])
            if "Duration" in new_data:
                new_data["Duration"] = float(new_data["Duration"])
            if "Categories" in new_data:
                new_data["Categories"] = new_data["Categories"].split(", ")
            if "Notes" in new_data:
                note_keys = ("Additional Notes", "Update Notes")
                for ki, k in enumerate(note_keys):
                    arr = new_data["Notes"].split("|")
                    new_data[k] = "" if len(arr) <= ki else arr[ki]
                    if len(new_data[k]) == 0:
                        del new_data[k]
                del new_data["Notes"]
            if "Audio" in new_data:
                audio_f = new_data["Audio"]
                if "cdn.discordapp.com" in audio_f or "drive.google.com" in audio_f:
                    audio_ext = None
                    accepted_exts = [".mp3", ".wav"]
                    for ext in accepted_exts:
                        if ext in audio_f:
                            audio_ext = ext
                    audio_response = requests.get(audio_f)
                    with open(f"./{new_audio_name_raw}{audio_ext}", "wb") as af:
                        af.write(audio_response.content)
                    new_data["Audio"] = "https://" + urllib.parse.quote(f"github.com/theballaam96/candys-shop/raw/main/{new_audio_name_raw}{audio_ext}")
            new_json.append(new_data)
with open("mapping.json", "w", encoding="utf-8") as output_data:
    output_data.write(json.dumps(new_json, indent=4))
            