import zipfile
import json
import io
with open("images.json") as f:
    images = json.load(f)
# Load mapping.json and load it into a dictionary
with open('mapping.json') as f:
    mapping = json.load(f)
    # Reverse the list
    mapping = mapping[::-1]
# Open the zip file
added_songs = {}
with zipfile.ZipFile('full_pack.zip', 'w') as z:
    # Create a zip file using the data in mapping.json to create it,
    for map_data in mapping:
        if map_data['Song'] in added_songs:
            print("Skipping duplicate song: " + map_data['Song'])
            continue
        category = map_data['Category']
        song = map_data['Song']
        song = song.replace('/', '_')
        binary = map_data['Binary']
        image_data = images.get(map_data['Game'])
        if image_data.get("short_name"):
            game_short = image_data["short_name"]
        else:
            game_short = map_data['Game']
        game_config = {
            "song": map_data['Song'],
            "song_short": map_data['Song'],
            "game": map_data['Game'],
            "game_short": game_short,
            "group": map_data['Category'],
            "length":map_data.get('Duration', 0),
            "logo": "",
            "composer": map_data['Composers'],
            "converter": map_data['Converters'],
            "audio": map_data.get('Audio', ''),
            "tags": map_data.get('Tags', [])
        }
        if image_data is not None:
            game_config["logo"] = image_data["icon"]
        
        with io.BytesIO() as zip_buffer:
            with zipfile.ZipFile(zip_buffer, 'w') as z2:
                with open(binary, "rb") as f:
                    data = f.read()
                    z2.writestr("song.bin", data)
                    z2.writestr('data.json', json.dumps(game_config))
            
            # Add the sub zip file to the main zip
            z.writestr(category + '/' + song + '.candy', zip_buffer.getvalue())
        added_songs[map_data['Song']] = True
