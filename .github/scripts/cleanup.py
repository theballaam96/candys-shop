import json
import os

MAPPING_FILE = "mapping.json"
PREVIEWS_DIR = "previews"

# Load mapping.json
with open(MAPPING_FILE, "r") as f:
    data = json.load(f)

unique_dict = []
for item in data:
    contains = False
    for unique_item in unique_dict:
        if unique_item["Game"] == item["Game"]:
            if unique_item["Song"] == item["Song"]:
                contains = True
                unique_item["Audio"] = item["Audio"]
    if not contains:
        unique_dict.append({
            "Game": item["Game"],
            "Song": item["Song"],
            "Audio": item["Audio"],
        })

# Push to mapping that it the link has been pruned
for item in data:
    for unique_item in unique_dict:
        if unique_item["Game"] != item["Game"]:
            continue
        if unique_item["Song"] != item["Song"]:
            continue
        if unique_item["Audio"] == item["Audio"]:
            continue
        if isinstance(item["Audio"], str) and "github.com" in item["Audio"]:
            item["pruned"] = True

with open(MAPPING_FILE, "w") as f:
    json.dump(data, f, indent=2)

# Step 5: Cleanup unused preview files
used_audio_files = [x["Audio"] for x in unique_dict]

# Remove unused files in previews/
for root, _, files in os.walk(PREVIEWS_DIR):
    for file in files:
        full_path = os.path.join(root, file)
        rel_path = os.path.relpath(full_path, ".")
        if rel_path not in used_audio_files:
            print(f"Removing unused preview file: {rel_path}")
            # os.remove(full_path)
