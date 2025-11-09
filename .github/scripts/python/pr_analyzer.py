import os
import sys
import json
import requests
from datetime import datetime
from github import Github, Auth
from dotenv import load_dotenv
from donk_lib import pull_pr_data, getPath, postAudio, adjust_raw_url

load_dotenv()

POST_COMMENT = True

def message(pr_data):
    webhook_url = os.getenv("DISCORD_WEBHOOK_SUBMISSIONS")
    triggered_action = os.getenv("TRIGGERED_ACTION")
    header_text = {
        "closed": {
            "text": "A pull request was closed",
            "color": 0xFF0000,
        },
        "ready_for_review": {
            "text": "A pull request was marked as ready for review",
            "color": 0xD700A7,
        },
        "reopened": {
            "text": "A pull request was reopened",
            "color": 0x9FD700,
        },
        "edited": {
            "text": "A pull request was edited",
            "color": 0xFCCA03,
        },
        "synchronize": {
            "text": "A pull request was synchronized",
            "color": 0xFCCA03,
        },
        "opened": {
            "text": "New Pull Request",
            "color": 0x03FC0F,
        },
    }
    default_text = f"A pull request action ({triggered_action})"
    title = f"{header_text.get(triggered_action, {'text': default_text})['text']} from {pr_data['submitter']}"
    components = [
        {
            "type": 1,  # Action row
            "components": [],
        }
    ]
    has_component = False
    has_embed = False
    audio_file = None
    if pr_data["is_song"]:
        json_output = pr_data["output"]
        color = header_text.get(triggered_action, {'color': 0x03FC0F})['color']
        # Set up description
        desc_information = {
            "Game": json_output.get("Game", "Not Provided"),
            "Song Name": json_output.get("Song", "Not Provided"),
            "Original Composer": json_output.get("Composers", "Not Provided"),
            "Converted By": json_output.get("Converters", "Not Provided"),
            "Type": json_output.get("Category", "Not Provided"),
            "Tags": ", ".join(json_output.get("Tags", ["Not Provided"])),
            "Needs a logo": pr_data.get("new_game", False),
            "Duration": json_output.get("Duration", 0),
            "Update Notes": json_output.get("Update Notes", "Not Provided"),
            "Additional Notes": json_output.get("Additional Notes", "Not Provided"),
        }

        desc_strings = [f"**{k}**: {v}" for k, v in desc_information.items()]
        desc = '\n'.join(desc_strings)
        # Set up embeds
        embed = {
            "title": "New Song Pull Request",
            "color": color,
            "description": desc,
            "timestamp": datetime.utcnow().isoformat(),
        }

        buttons = {
            "Pull Request": pr_data.get("pull_request"),
            "Binary File": pr_data.get("bin_raw"),
            "MIDI File": pr_data.get("midi_raw"),
            "YouTube": json_output.get("Audio"),
        }
        if pr_data.get("preview_raw") is not None:
            url_to_pull = adjust_raw_url(pr_data["preview_raw"])
            audio_resp = requests.get(url_to_pull)
            audio_resp.raise_for_status()
            audio_file = audio_resp.content
        for but_title, prop in buttons.items():
            if prop is None:
                continue
            components[0]["components"].append({
                "type": 2,  # Button
                "style": 5,  # Link button
                "label": but_title,
                "url": prop,
            })
        has_component = True
        has_embed = True
    else:
        components[0]["components"].append({
            "type": 2,  # Button
            "style": 5,  # Link button
            "label": "Pull Request",
            "url": pr_data["pull_request"],
        })
        has_component = True

    payload = {
        "content": title,
    }
    if has_embed:
        payload["embeds"] = [embed]
    if has_component:
        webhook_url = f"{webhook_url}?wait=true&with_components=true"
        payload["components"] = components

    # Post the embed
    try:
        whresp = requests.post(webhook_url, json=payload, headers={"Content-Type": "application/json"})
        whresp.raise_for_status()
        print("Message sent successfully:", whresp.text)
    except Exception as e:
        print("Error sending webhook embed:", e)
        sys.exit(1)
    if audio_file is not None:
        json_output = pr_data["output"]
        postAudio(json_output.get("Song", "Not Provided"), pr_data["preview_ext"], audio_file, webhook_url)
    return

def run():
    try:
        needs_changing = False
        new_game = False
        pr_number = os.getenv("PR_NUMBER")
        token = os.getenv("PAT_TOKEN")
        repo_full = "theballaam96/candys-shop"
                
        data = pull_pr_data(pr_number)
        song_upload = data["is_song"]
        if song_upload:
            json_output = data["output"]
            print(json_output)

            # Load image/mapping JSONs (optional)
            file_path = getPath("images.json")
            image_data = json.load(open(file_path)) if os.path.exists(file_path) else {}

            # Placeholder for MIDI duration (skip actual parsing)

            if song_upload:
                needs_changing = (not data.get("bin")) or ((not json_output.get("Audio")) and (not data.get("preview")))

            # Check for new game similarity
            game_name = json_output.get("Game")
            if game_name and isinstance(image_data, dict):
                if game_name not in image_data:
                    new_game = True

        # Compose message
        segments = [
            "Mornin'",
            "",
            "I've analyzed your pull request and ascertained the following information from it. This will help the verifiers handle your request faster:",
            f"> Is Song Upload: {'Yes' if song_upload else 'No'}",
        ]
        if song_upload:
            segments.append(f"> Has Binary File: {'Yes' if 'Binary' in json_output else 'No'}")
            segments.append(f"> Has Preview: {'Yes' if 'Audio' in json_output else 'No'}")
            segments.append(f"> Is new game: {'Yes' if new_game else 'No'}")
        segments.append(f"> Something needs changing: {'YES!!! (PLEASE FIX ERRORS)' if needs_changing else 'No'}")
        if song_upload:
            segments.append("")
            segments.append("Here's what the output will look like:")
            segments.append("```")
            segments.append(json.dumps(json_output, indent=4))
            segments.append("```")

        prMessage = "\n".join(segments)

        # Comment on PR
        if POST_COMMENT:
            auth = Auth.Token(token)
            g = Github(auth=auth)
            repo = g.get_repo(repo_full)
            issue = repo.get_issue(int(pr_number))
            issue.create_comment(prMessage)
        else:
            print(prMessage)

        if needs_changing:
            print("::error::Something needs changing in order to make this PR valid.")
            exit(1)

        message(data)

    except Exception as e:
        print(f"::error::{str(e)}")
        exit(1)


if __name__ == "__main__":
    run()
