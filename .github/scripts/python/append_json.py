#!/usr/bin/env python3
"""
pr_to_mapping.py

Converted from the original Node.js script to Python for running in GitHub Actions.

Environment variables required:
- PR_NUMBER
- PAT_TOKEN
- DISCORD_WEBHOOK_PUBLICFILE

Dependencies (install in your action environment):
pip install requests mido

Notes:
- This script expects the uploaded files (bin/mid/wav/mp3) to be present at ../../<filename>
  relative to the script directory, matching the original Node.js behavior.
- mapping.json is expected (or will be created) at ../../mapping.json relative to script.
"""

import os
import sys
import json
from datetime import datetime
import requests
from dotenv import load_dotenv
from donk_lib import (
    compute_midi_duration_from_bytes,
    REPO,
    pull_pr_data,
    getHeaders,
    filter_filename,
    adjust_raw_url,
    getPath,
    postAudio,
)
from yt_post import uploadVideoWrapper

# ---------------------------
# Utility / configuration
# ---------------------------

load_dotenv()

# Paths: match the Node behavior of using __dirname and ../../
MAPPING_FILE = getPath("mapping.json")
MOVE_FILES = False
SHORTHAND_TO_LONGHAND = {
    "bgm": "BGM",
    "events": "Event",
    "majoritems": "Major Item",
    "minoritems": "Minor Item",
}


def message(json_output, binary_link, preview_file_bytes, is_update, preview_extension, preview_path):
    # Initial information
    webhook_url = os.getenv("DISCORD_WEBHOOK_PUBLICFILE")
    song_name = json_output.get("Song", "Not Provided")
    binary_dl_link = binary_link if binary_link else "???"
    has_audio_file = preview_file_bytes is not None
    update_string = ":watermelon: This song is an update\n" if is_update else ""
    if has_audio_file and (json_output["Category"] != "bgm"):
        # mimic Node Buffer length check: bytes length < (25 * 1024 * 1024)
        has_audio_file = len(preview_file_bytes) < (25 * 1024 * 1024)
    audio_string = "No Preview"
    game_name = json_output.get("Game", "Not Provided")
    composers = json_output.get("Composers", "Not Provided")
    converters = json_output.get("Converters", "Not Provided")
    add_yt = False
    if has_audio_file:
        if json_output["Category"] == "bgm":
            attempted_link = uploadVideoWrapper(game_name, song_name, converters, composers, preview_file_bytes)
            if attempted_link is not None:
                json_output["Audio"] = attempted_link
                audio_string = attempted_link
                if preview_path is not None and os.path.exists(preview_path):
                    os.remove(preview_path)
                add_yt = True
            else:
                audio_string = "*(Attached)*"
        else:
            audio_string = "*(Attached)*"
    elif "Audio" in json_output:
        audio_string = json_output["Audio"]
        add_yt = True
    suggested_type = "Not Provided"
    if "Category" in json_output:
        suggested_type = SHORTHAND_TO_LONGHAND.get(json_output["Category"], json_output["Category"])

    desc_information = {
        "Game": game_name,
        "Song Name": song_name,
        "Type": suggested_type,
        "Tags": ", ".join(json_output.get("Tags", ["Not Provided"])),
    }
    if "Update Notes" in json_output:
        desc_information["Additional Notes"] = json_output["Update Notes"]

    desc_strings = [f"**{k}**: {v}" for k, v in desc_information.items()]
    desc = '\n'.join(desc_strings)
    # Set up embeds
    embed = {
        "title": song_name,
        "description": f"{update_string}{desc}",
        "fields": [
            {"name": "Composer(s)", "value": composers, "inline": True},
            {"name": "Converted By", "value": converters, "inline": True},
        ],
        "timestamp": datetime.utcnow().isoformat(),
    }

    components = [
        {
            "type": 1,  # Action row
            "components": [
                {
                    "type": 2,  # Button
                    "style": 5,  # Link button
                    "label": "Binary File",
                    "url": binary_dl_link,
                },
            ],
        }
    ]
    if add_yt:
        components[0]["components"].append({
            "type": 2,
            "style": 5,
            "label": "YouTube",
            "url": audio_string,
        })

    payload = {
        "content": "A new song has been uploaded",
        "embeds": [embed],
        "components": components,  # Attach the buttons
    }

    # Post the embed
    try:
        whresp = requests.post(f"{webhook_url}?wait=true&with_components=true", json=payload, headers={"Content-Type": "application/json"})
        whresp.raise_for_status()
        print("Message sent successfully:", whresp.text)
    except Exception as e:
        print("Error sending webhook embed:", e)
        sys.exit(1)

    # If we have audio bytes and it is small enough, post as a multipart file
    if has_audio_file:
        postAudio(song_name, preview_extension, preview_file_bytes)

def handlePR(pr_number, check_labels = True):
    try:
        data = pull_pr_data(pr_number)
        if not data["is_song"]:
            return
        if "batch-merge-ignore" in data["labels"] and check_labels:
            return
        json_output = data["output"]

        # Read existing mapping.json
        if MAPPING_FILE.exists():
            try:
                with open(MAPPING_FILE, "r", encoding="utf-8") as fh:
                    existing_data = json.load(fh)
                if not isinstance(existing_data, list):
                    existing_data = []
            except Exception:
                existing_data = []
        else:
            existing_data = []

        # compute revisions
        revisions = 0
        for entry in existing_data:
            if (
                entry.get("Game") == json_output.get("Game")
                and entry.get("Song") == json_output.get("Song")
            ):
                revisions += 1
        rev_string = "" if revisions == 0 else f" (REV {revisions})"
        sub_file = f"{filter_filename(json_output.get('Game'))}/{filter_filename(json_output.get('Song'))}{rev_string}"

        binary_link = None
        if data["preview"]:
            json_output["Audio"] = requests.utils.requote_uri(
                f"https://github.com/{REPO}/raw/main/previews/{sub_file}.{data['preview_ext']}"
            )
        if data["bin"]:
            json_output["Binary"] = f"binaries/{sub_file}.bin"
            binary_link = requests.utils.requote_uri(
                f"https://github.com/{REPO}/raw/main/binaries/{sub_file}.bin"
            )
        print("sub_file:", sub_file)

        # File transfer (move/copy and cleanup)
        print("Starting file transfer")
        file_data = {
            "binaries": [data["bin"], "bin", True],
            "previews": [data["preview"], data["preview_ext"], True],
            "midi": [data["midi"], "mid", False],
        }

        preview_file_bytes = None
        preview_path = None

        for k, v in file_data.items():
            k_file, k_ext, k_keep = v
            if not k_file:
                continue
            bin_file_path = getPath(k_file)
            if k_keep:
                new_bin_file = f"{k}/{sub_file}.{k_ext}"
                root_dir = getPath(k)
                game_dir = getPath(k, filter_filename(json_output.get("Game") or ""))
                # ensure directories
                root_dir.mkdir(parents=True, exist_ok=True)
                game_dir.mkdir(parents=True, exist_ok=True)
                bin_new_file_path = getPath(new_bin_file)
                bin_file_data = None
                if bin_file_path.exists():
                    bin_file_data = bin_file_path.read_bytes()
                # If preview, keep bytes for Discord post
                if k == "previews":
                    preview_file_bytes = bin_file_data
                    preview_path = bin_new_file_path
                if bin_file_data is not None:
                    bin_new_file_path.parent.mkdir(parents=True, exist_ok=True)
                    bin_new_file_path.write_bytes(bin_file_data)
            # Remove original file if exists
            if bin_file_path.exists() and MOVE_FILES:
                try:
                    bin_file_path.unlink()
                except Exception as e:
                    print("Warning: could not remove original file:", bin_file_path, e)

        print("File Transfer Done")

        # Parse midi duration if midi_file provided
        if data["midi"] and data["midi_raw"]:
            midi_url = adjust_raw_url(data["midi_raw"])
            try:
                r = requests.get(midi_url, headers=getHeaders())
                r.raise_for_status()
                midi_bytes = r.content
                duration = compute_midi_duration_from_bytes(midi_bytes)
                if duration:
                    json_output["Duration"] = duration
            except Exception as e:
                print("Warning: could not fetch/parse midi:", e)


        # Prepare Discord embed payload
        message(json_output, binary_link, preview_file_bytes, revisions > 0, data["preview_ext"], preview_path)
        
        # Append and save mapping.json
        existing_data.append(json_output)
        try:
            MAPPING_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(MAPPING_FILE, "w", encoding="utf-8") as fh:
                json.dump(existing_data, fh, indent=2, ensure_ascii=False)
            print("PR message appended to JSON file successfully.")
        except Exception as e:
            print("Error writing mapping.json:", e)
            sys.exit(1)

    except requests.HTTPError as he:
        resp = he.response
        try:
            print("HTTP Error:", resp.status_code, resp.text)
        except Exception:
            print("HTTP Error:", he)
        sys.exit(1)
    except Exception as ex:
        print("Error:", ex)
        sys.exit(1)


if __name__ == "__main__":
    pr_number = os.getenv("PR_NUMBER")
    handlePR(pr_number)