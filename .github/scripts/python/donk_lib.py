import mido
import io
import os
import requests
import json
import sys
from pathlib import Path
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

def getPath(file_path: str):
    SCRIPT_DIR = Path(__file__).resolve().parent
    ROOT_UP_TWO = SCRIPT_DIR.joinpath("../../../").resolve()
    return ROOT_UP_TWO.joinpath(file_path)

def get_pr_labels(pr_number):
    issue_url = f"https://api.github.com/repos/{REPO}/issues/{pr_number}"
    response = requests.get(issue_url, headers=getHeaders())
    response.raise_for_status()
    issue_json = response.json()

    labels = [label["name"] for label in issue_json.get("labels", [])]
    return labels


def pull_pr_data(pr_number):
    headers = getHeaders()

    print(f"Fetching details for PR {pr_number} in repository {REPO}")

    pr_url = f"https://api.github.com/repos/{REPO}/pulls/{pr_number}"
    pr_files_url = f"{pr_url}/files"
    func_output = {
        "pull_request": f"https://github.com/theballaam96/candys-shop/pull/{pr_number}",
        "labels": get_pr_labels(pr_number),
    }

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
    bin_file_url = None
    prev_file_url = None
    for f in files_json:
        filename = f.get("filename")
        if not filename:
            continue
        extension = filename.split(".")[-1].lower() if "." in filename else ""
        if extension == "bin":
            bin_file = filename
            bin_file_url = f.get("raw_url")
        elif extension == "mid":
            midi_file = filename
            # GitHub API file objects include raw_url
            midi_raw_file = f.get("raw_url")
        elif extension in PREVIEW_EXTENSIONS:
            preview_file = filename
            preview_extension = extension
            prev_file_url = f.get("raw_url")

    print("Identified:", bin_file, midi_file, preview_file, preview_extension)

    # Parse PR body lines
    pr_message = pr_json.get("body", "")
    func_output["submitter"] = pr_json.get("user", {}).get("login", "Unknown")
    raw_pr_data = pr_message.splitlines() if pr_message else []
    if not raw_pr_data or (raw_pr_data[0].strip() != REQ_STRING):
        func_output["is_song"] = False
        return func_output

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

    if midi_raw_file is not None:
        midi_resp = requests.get(midi_raw_file)
        midi_resp.raise_for_status()
        json_output["Duration"] = compute_midi_duration_from_bytes(midi_resp.content)

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

    new_game = False
    if "Game" in json_output:
        file_path = getPath("images.json")
        image_data = json.load(open(file_path)) if os.path.exists(file_path) else {}
        if json_output["Game"] not in image_data:
            new_game = True

    # Compose remaining output
    func_output["is_song"] = True
    func_output["output"] = json_output
    func_output["midi_raw"] = midi_raw_file
    func_output["midi"] = midi_file
    func_output["bin"] = bin_file
    func_output["bin_raw"] = bin_file_url
    func_output["preview"] = preview_file
    func_output["preview_raw"] = prev_file_url
    func_output["preview_ext"] = preview_extension
    func_output["new_game"] = new_game

    return func_output

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

def string_compare(source: str, comparison: str) -> float:
    arr_a = list(source.lower())
    arr_b = list(comparison.lower())
    arr_a_copy = arr_a[:]
    arr_b_copy = arr_b[:]
    matching_a = 0
    matching_b = 0

    # A -> B
    for ch in arr_a:
        if ch in arr_b:
            arr_b.remove(ch)
            matching_a += 1

    # B -> A
    arr_a = arr_a_copy[:]
    arr_b = arr_b_copy[:]
    for ch in arr_b:
        if ch in arr_a:
            arr_a.remove(ch)
            matching_b += 1

    a_score = matching_a / len(source) if source else 0
    b_score = matching_b / len(comparison) if comparison else 0
    return (a_score + b_score) / 2

def postAudio(song_name, preview_extension, preview_file, webhook_url):
    bad_song_file_chars = [" ", '"']
    filtered_song_name = "".join(ch for ch in song_name if ch not in bad_song_file_chars)
    new_song_name = f"{filtered_song_name}.{preview_extension or 'mp3'}"
    boundary = b"xxxxxxxx"
    body = b""
    body += b"--" + boundary + b"\r\n"
    body += f'Content-Disposition: form-data; name="file"; filename="{new_song_name}"\r\n'.encode("utf-8")
    body += b"Content-Type: audio/mpeg\r\n\r\n"
    body += preview_file
    body += b"\r\n--" + boundary + b"--\r\n"
    headers = {
        "Content-Type": f"multipart/form-data; boundary={boundary.decode()}"
    }
    try:
        whresp2 = requests.post(webhook_url, data=body, headers=headers)
        whresp2.raise_for_status()
        print("Preview posted successfully:", whresp2.text)
    except Exception as e:
        print("Error posting preview file:", e)
        sys.exit(1)