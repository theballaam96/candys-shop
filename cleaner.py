import json
import os
import shutil
from urllib.parse import unquote

invalid_chars = [
    ":", "/", "\'", "\"", "?", "#", "%", "&", "{", "}", "\\", "<", ">", "*", "$",
    "!", "@", "+", "`", "|", "=", "."
]
def filterFilename(name: str) -> str:
    for char in invalid_chars:
        name = name.replace(char, "")
    return name

preview_vacant = []
previews_referenced = []

with open("mapping.json", "r", encoding="utf-8") as fh:
    data = json.loads(fh.read())
    games_total = []
    for index, song in enumerate(data):
        if "Binary" not in song:
            print(f"No binary for {song['Game']}: {song['Song']} ({index})")
        else:
            if not os.path.exists(song["Binary"]):
                print(f"Binary not found for {song['Game']}: {song['Song']} ({index})")
        # Preview Check
        if "Audio" in song:
            preview_path = song["Audio"]
            found_preview = True
            if "github.com" in preview_path:
                preview_path_no_gh = unquote(preview_path.replace("https://github.com/theballaam96/candys-shop/raw/main/",""))
                if not os.path.exists(preview_path_no_gh):
                    preview_vacant.append({
                        "Game": song["Game"],
                        "Song": song["Song"],
                        "Index": index,
                    })
                    found_preview = False
                if found_preview:
                    previews_referenced.append(f"./{preview_path_no_gh}")
            if found_preview:
                del_index = None
                preview_vacant = [v for v in preview_vacant if v["Game"] != song["Game"] or v["Song"] != song["Song"]]
    for item in preview_vacant:
        print(f"Warning: Preview does not exist for {item['Game']}: {item['Song']} ({item['Index']})")
all_previews = []
PREVIEW_PATH = "./previews"
for root, dirs, files in os.walk(PREVIEW_PATH):
    for file in files:
        all_previews.append(os.path.join(root, file).replace("\\","/"))
for preview in all_previews:
    if preview not in previews_referenced:
        os.remove(preview)
for root, dirs, files in os.walk(PREVIEW_PATH):
    if len(files) == 0 and root != PREVIEW_PATH:
        folder = root.replace("\\","/")
        shutil.rmtree(folder)