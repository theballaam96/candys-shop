import mido
import io
import os
import sys
import requests
import json
from datetime import datetime

INVALID_CHARS = [
    ":", "/", "'", '"', "?", "#", "%", "&", "{", "}", "\\", "<", ">", "*", "$",
    "!", "@", "+", "`", "|", "=", "."
]

REQ_STRING = "IS SONG - DO NOT DELETE THIS LINE"
REPO = "theballaam96/candys-shop"
PREVIEW_EXTENSIONS = ["wav", "mp3"]

def compute_midi_duration_from_bytes(midi_bytes: bytes) -> float:
    """
    Uses mido to try to get MidiFile.length. If that attribute isn't accurate for some file,
    fall back to calculating the time from ticks and tempo changes.
    """
    mf = mido.MidiFile(file=io.BytesIO(midi_bytes))
    # mido.MidiFile has .length property which attempts to compute length in seconds
    try:
        length = mf.length
        if length and length > 0:
            return float(length)
    except Exception:
        # fallback below
        pass

    # Fallback: compute by walking messages and converting ticks to seconds, handling tempo changes.
    ticks_per_beat = mf.ticks_per_beat
    # Default tempo 500000 microseconds per beat (120bpm)
    current_tempo = 500000
    # We need to walk all messages in time order across tracks.
    # mido provides MidiFile.tracks but times are per-track. We will merge tracks
    # to get a proper timeline using mido.merge_tracks().
    merged = mido.merge_tracks(mf.tracks)
    current_tick = 0
    total_seconds = 0.0
    for msg in merged:
        # msg.time is delta ticks
        if msg.time:
            # convert delta ticks to seconds using current_tempo
            seconds = mido.tick2second(msg.time, ticks_per_beat, current_tempo)
            total_seconds += seconds
            current_tick += msg.time
        # handle tempo changes
        if msg.type == "set_tempo":
            current_tempo = msg.tempo
    return float(total_seconds)

def getHeaders():
    token = os.getenv("PAT_TOKEN")
    return {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json"}

def pull_pr_data(pr_number):
    headers = getHeaders()

    print(f"Fetching details for PR {pr_number} in repository {REPO}")

    pr_url = f"https://api.github.com/repos/{REPO}/pulls/{pr_number}"
    pr_files_url = f"{pr_url}/files"

    response = requests.get(pr_url, headers=headers)
    response.raise_for_status()
    pr_json = response.json()

    response_files = requests.get(pr_files_url, headers=headers)
    response_files.raise_for_status()
    files_json = response_files.json()
    # Debug print the file list (like the Node script)
    print(json.dumps(files_json, indent=2))

    # Identify files
    bin_file = None
    midi_file = None
    midi_raw_file = None
    preview_file = None
    preview_extension = None

    for f in files_json:
        filename = f.get("filename")
        if not filename:
            continue
        extension = filename.split(".")[-1].lower() if "." in filename else ""
        if extension == "bin":
            bin_file = filename
        elif extension == "mid":
            midi_file = filename
            # GitHub API file objects include raw_url
            midi_raw_file = f.get("raw_url")
        elif extension in PREVIEW_EXTENSIONS:
            preview_file = filename
            preview_extension = extension

    print("Identified:", bin_file, midi_file, preview_file, preview_extension)

    # Parse PR body lines
    pr_message = pr_json.get("body", "")
    raw_pr_data = pr_message.splitlines() if pr_message else []
    if not raw_pr_data or (raw_pr_data[0].strip() != REQ_STRING):
        print("Skipping Pull Request, missing key line.")
        return

    json_output = {}
    for idx, item in enumerate(raw_pr_data):
        if idx == 0:
            continue
        if not item:
            continue
        if ":" in item:
            # split on first colon to match original: item.split(/:(.*)/s)
            key, _, value = item.partition(":")
            json_output[key.strip()] = value.strip()

    print("Parsed PR metadata:", json_output)

    # Convert numeric fields
    number_vars = ["Tracks", "Duration"]
    for v in number_vars:
        if v in json_output:
            val = json_output[v]
            try:
                # Accept integer or float
                if "." in val:
                    json_output[v] = float(val)
                else:
                    json_output[v] = int(val)
            except Exception:
                pass

    # Convert array fields
    arr_vars = ["Tags"]
    for v in arr_vars:
        if v in json_output and json_output[v]:
            json_output[v] = [item.strip() for item in json_output[v].split(",") if item.strip()]

    json_output["Verified"] = True
    json_output["Date"] = datetime.now().isoformat()

    return {
        "output": json_output,
        "midi_raw": midi_raw_file,
        "midi": midi_file,
        "bin": bin_file,
        "preview": preview_file,
        "preview_ext": preview_extension,
    }

def filter_filename(name: str) -> str:
    if not name:
        return ""
    # Remove all invalid characters
    out = "".join(ch for ch in name if ch not in INVALID_CHARS)
    return out


def adjust_raw_url(input_url: str) -> str:
    if not input_url:
        return input_url
    return input_url.replace("github.com", "raw.githubusercontent.com").replace("raw/", "")


def safe_get_json(url: str, headers: dict):
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    return r.json()