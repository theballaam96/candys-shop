#!/usr/bin/env python3
import http.client
import httplib2
import os
import random
import sys
import time
import requests
import json
import soundfile as sf
import pyloudnorm as pyln
import numpy as np
from io import BytesIO
from PIL import Image, ImageFilter, ImageEnhance, ImageDraw, ImageFont
from moviepy.editor import ImageClip, AudioFileClip
from donk_lib import getPath

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# Constants
httplib2.RETRIES = 1
MAX_RETRIES = 10

RETRIABLE_EXCEPTIONS = (
    httplib2.HttpLib2Error,
    IOError,
    http.client.NotConnected,
    http.client.IncompleteRead,
    http.client.ImproperConnectionState,
    http.client.CannotSendRequest,
    http.client.CannotSendHeader,
    http.client.ResponseNotReady,
    http.client.BadStatusLine,
)

RETRIABLE_STATUS_CODES = [500, 502, 503, 504]

YOUTUBE_UPLOAD_SCOPE = "https://www.googleapis.com/auth/youtube.upload"
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

VALID_PRIVACY_STATUSES = ("public", "private", "unlisted")

class UploadOptions:
    def __init__(self, file, title, description, category, keywords, privacyStatus):
        self.file = file
        self.title = title
        self.description = description
        self.category = category
        self.keywords = keywords
        self.privacyStatus = privacyStatus

def get_authenticated_service_noninteractive():
    """
    Non-interactive auth using a refresh token. Expects either:
      - Environment variables: YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN
    or
      - client_secrets.json and token.json (token.json created by interactive flow).
    """

    # prefer environment variables (best for CI)

    refresh_token = os.getenv("YT_REFRESH_TOKEN")
    client_id = os.getenv("YT_CLIENT_ID")
    client_secret = os.getenv("YT_CLIENT_SECRET")

    # client_id = os.environ.get("YT_CLIENT_ID")
    # client_secret = os.environ.get("YT_CLIENT_SECRET")
    # refresh_token = os.environ.get("YT_REFRESH_TOKEN")

    if client_id and client_secret and refresh_token:
        creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=[YOUTUBE_UPLOAD_SCOPE],
        )
        # Force refresh to get an access token now
        creds.refresh(Request())
    else:
        # fallback to token.json created by interactive flow
        token_file = "token.json"
        if os.path.exists(token_file):
            creds = Credentials.from_authorized_user_file(token_file, [YOUTUBE_UPLOAD_SCOPE])
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
        else:
            raise RuntimeError(
                "No credentials found. Set YT_CLIENT_ID/YT_CLIENT_SECRET/YT_REFRESH_TOKEN or run interactive flow to create token.json."
            )

    youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, credentials=creds, cache_discovery=False)
    return youtube


def initialize_upload(youtube, options):
    tags = options.keywords.split(",") if options.keywords else None

    body = dict(
        snippet=dict(
            title=options.title,
            description=options.description,
            tags=tags,
            categoryId=options.category,
        ),
        status=dict(privacyStatus=options.privacyStatus),
    )

    insert_request = youtube.videos().insert(
        part=",".join(body.keys()),
        body=body,
        media_body=MediaFileUpload(options.file, chunksize=-1, resumable=True),
    )

    return resumable_upload(insert_request)


def resumable_upload(insert_request):
    response = None
    error = None
    retry = 0

    while response is None:
        try:
            print("Uploading file...")
            status, response = insert_request.next_chunk()
            if response is not None:
                if "id" in response:
                    return response["id"]
                else:
                    sys.exit(f"The upload failed with an unexpected response: {response}")
        except HttpError as e:
            if e.resp.status in RETRIABLE_STATUS_CODES:
                error = f"A retriable HTTP error {e.resp.status} occurred:\n{e.content}"
            else:
                raise
        except RETRIABLE_EXCEPTIONS as e:
            error = f"A retriable error occurred: {e}"

        if error is not None:
            print(error)
            retry += 1
            if retry > MAX_RETRIES:
                sys.exit("No longer attempting to retry.")

            max_sleep = 2**retry
            sleep_seconds = random.random() * max_sleep
            print(f"Sleeping {sleep_seconds:.2f} seconds and then retrying...")
            time.sleep(sleep_seconds)
            error = None
    return None

def uploadVideo(file, title, description, category="22", keywords="", privacyStatus="unlisted"):
    options = UploadOptions(file, title, description, category, keywords, privacyStatus)

    youtube = get_authenticated_service_noninteractive()

    try:
        return initialize_upload(youtube, options)
    except HttpError as e:
        print(f"An HTTP error {e.resp.status} occurred:\n{e.content}")
    return None

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/141.0.0.0 Safari/537.36"
}

IMAGES_FILE = getPath("images.json")
UPLOAD_TO_YT = True

def normalize_youtube_audio(file_bytes):
    # Load audio
    # Load from bytes
    data, sr = sf.read(BytesIO(file_bytes))

    # Ensure float32 array
    if data.dtype != np.float32:
        data = data.astype(np.float32)

    # Convert threshold to amplitude
    silence_thresh_db = -40
    silence_thresh = 10 ** (silence_thresh_db / 20.0)

    # If stereo, average across channels
    if data.ndim > 1:
        rms = np.sqrt(np.mean(data**2, axis=1))
    else:
        rms = np.abs(data)

    # Find first frame above threshold (non-silent start)
    non_silent_idx = np.argmax(rms > silence_thresh)
    if rms[non_silent_idx] <= silence_thresh:
        non_silent_idx = 0  # file may be all silence

    # Trim leading silence
    trimmed = data[non_silent_idx:]

    # Measure loudness
    meter = pyln.Meter(sr)
    loudness = meter.integrated_loudness(trimmed)

    # Normalize to target LUFS
    normalized = pyln.normalize.loudness(trimmed, loudness, -14)

    # Export back to bytes (WAV)
    buf = BytesIO()
    sf.write(buf, normalized, sr, format='mp3')
    with open("vid_audio.mp3", "wb") as fh:
        fh.write(buf.getvalue())
    return "vid_audio.mp3"

def uploadVideoWrapper(game, song, converters, composers, audio_file_bytes):
    images_json = None
    if IMAGES_FILE.exists():
        try:
            with open(IMAGES_FILE, "r", encoding="utf-8") as fh:
                images_json = json.load(fh)
            if not isinstance(images_json, dict):
                images_json = {}
        except Exception:
            images_json = {}
    else:
        images_json = {}
    icon = None
    base_icon = "https://i.imgur.com/1CdpLMp.png"
    song_file_str = f"{game}_{song}"
    song_file_str = ''.join(ch for ch in song_file_str if ch.isalnum())
    if game in images_json:
        icon = images_json[game]["icon"]
    backdrop = Image.new(mode="RGBA", size=(1280, 720))
    try:
        response = requests.get(base_icon, headers=headers)
        response.raise_for_status()  # ensure we got a valid response

        # Load the image into PIL directly from bytes
        img = Image.open(BytesIO(response.content)).convert("RGBA")
        w, h = img.size
        wscale = 1280 / w
        hscale = 720 / h
        scale = max(wscale, hscale)
        new_w = int(w * scale)
        new_h = int(h * scale)
        cen_w = new_w / 2
        cen_h = new_h / 2
        l_w = int(cen_w - 640)
        r_w = int(cen_w + 640)
        t_h = int(cen_h - 360)
        b_h = int(cen_h + 360)
        backdrop = img.resize((new_w, new_h)).crop((l_w, t_h, r_w, b_h))
    except requests.exceptions.RequestException as e:
        print(f"Error downloading image: {e}")

    blurred = backdrop.filter(ImageFilter.GaussianBlur(radius=8))
    enhancer = ImageEnhance.Brightness(blurred)
    blurred = enhancer.enhance(0.6)

    subtitles = [
        song,
        f"Game: {game}",
        f"Composed By: {composers}",
        f"Converted By: {converters}",
    ]

    draw = ImageDraw.Draw(blurred)
    pos_y = 460
    cwd_dir = os.getcwd().split("/")[-1].split("\\")[-1]
    offset = ""
    if cwd_dir != "python":
        offset = ".github/scripts/python/"
    for index, sub in enumerate(subtitles):
        font_size = 25
        if index == 0:
            font_size = 40
            font = ImageFont.truetype(f"{offset}Roboto-Bold.ttf", size=font_size)
        else:
            font = ImageFont.truetype(f"{offset}Roboto-Medium.ttf", size=font_size)
        position = (150, pos_y)
        pos_y += (font_size + 5)
        color = (255, 255, 255)
        draw.text(position, sub, fill=color, font=font, stroke_width=2, stroke_fill=(0, 0, 0))

    icon_img = None
    if icon is not None:
        try:
            response = requests.get(icon, headers=headers)
            response.raise_for_status()  # ensure we got a valid response

            # Load the image into PIL directly from bytes
            icon_img = Image.open(BytesIO(response.content)).convert("RGBA")
        except requests.exceptions.RequestException as e:
            print(f"Error downloading image: {e}")

    box_width = 400
    if icon_img is not None:
        # tl = (150, 440 - box_width)
        # br = (150 + box_width, 440)
        # fill = (40, 40, 40)
        # draw.rectangle([tl, br], fill=fill)

        w, h = icon_img.size
        wscale = box_width / w
        hscale = box_width / h
        scale = min(wscale, hscale)
        new_w = int(w * scale)
        new_h = int(h * scale)
        cen_w = new_w / 2
        cen_h = new_h / 2
        pos_w = int(150 + (new_w / 2) - cen_w)
        pos_h = int(440 - (new_h / 2) - cen_h)
        icon_img = icon_img.resize((new_w, new_h))
        blurred.paste(icon_img, (pos_w, pos_h), icon_img)

    blurred.save("vid_thumb.png")

    audio_file = normalize_youtube_audio(audio_file_bytes)


    # Create Video
    audio_clip = AudioFileClip(audio_file)
    image_clip: ImageClip = ImageClip("vid_thumb.png")
    image_clip = image_clip.set_duration(audio_clip.duration)
    image_clip = image_clip.set_fps(24)

    video_clip = image_clip.set_audio(audio_clip)
    video_clip.write_videofile("output_video.mp4", codec="libx264", audio_codec="aac")

    if UPLOAD_TO_YT:
        title = f"{song} (DK64 Soundfont)"
        if game != "Other":
            title += f" | {game}"
        if len(title) > 100:
            title = title[:100]  # I'm looking at you, Touhou games which tell a local folktale in their title
        desc = f"Composed by: {composers}\nConverted by: {converters}\nStart your music composition journey: https://discord.dk64randomizer.com\nPack Builder: https://theballaam96.github.io/pack_builder.html"
        if len(desc) > 5000:
            desc = desc[:5000]  # We should never ever ever ever run into this, but I'm sure Touhou 50 will when it includes the entire bee movie script in it's title
        video_id = uploadVideo("output_video.mp4", title, desc, privacyStatus="unlisted")
        if video_id is None:
            raise Exception("Whoops, something went wrong with the upload of the video.")
        components = [
            "output_video.mp4",
            "vid_thumb.png",
            "vid_audio.mp3",
        ]
        for comp in components:
            if os.path.exists(comp):
                os.remove(comp)
        return f"https://youtu.be/{video_id}"
    return None