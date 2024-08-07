(async () => {
    const axios = require('axios');
    const { Octokit } = await import("@octokit/rest");
    const fs = require('fs');
    const path = require('path');
    const parseMidi = require("midi-file").parseMidi;
    const { Midi } = require("@tonejs/midi");
    
    const invalid_chars = [
        ":", "/", "\'", "\"", "?", "#", "%", "&", "{", "}", "\\", "<", ">", "*", "$",
        "!", "@", "+", "`", "|", "=", "."
    ];
    
    function filterFilename(name) {
        if (!name) {
            return ""
        }
        invalid_chars.forEach((c) => {
            name = name.split("").filter((i) => i !== c).join("");
        });
        return name;
    }
    
    function stringCompare(source, comparison) {
        // Returns a similarity score between two strings;
        let arr_a = source.toLowerCase().split("")
        let arr_b = comparison.toLowerCase().split("")
        const arr_a_copy = arr_a.slice()
        const arr_b_copy = arr_b.slice()
        let matching_characters_a = 0;
        let matching_characters_b = 0;
        // Check similarity for A->B
        arr_a.forEach(source_character => {
            const found_index = arr_b.indexOf(source_character)
            if (found_index > -1) {
                matching_characters_a += 1;
            }
            arr_b = arr_b.filter((item, index) => index != found_index);
        })
        // Check similarity for B->A
        arr_a = arr_a_copy.slice()
        arr_b = arr_b_copy.slice()
        arr_b.forEach(comparison_character => {
            const found_index = arr_a.indexOf(comparison_character)
            if (found_index > -1) {
                matching_characters_b += 1;
            }
            arr_a = arr_a.filter((item, index) => index != found_index);
        })
        // Determine score
        const a_score = matching_characters_a / source.length;
        const b_score = matching_characters_b / comparison.length;
        return (a_score + b_score) / 2;
    }
    
    function adjustRawURL(input_url) {
        return input_url.replace("github.com","raw.githubusercontent.com").replace("raw/","")
    }
    
    async function run() {
      try {
        class UploadHeader {
            constructor (name, mandatory) {
                this.name = name
                this.mandatory = mandatory
            }
        }
    
        // Response Flags
        let song_upload = false;
        let mandatory_headers_included = [];
        let unlisted_headers = [];
        let needs_changing = false;
        let new_game = false;
        let similar_game_name = "";
        let similar_game_score = 0;
        const number_vars = ["Tracks", "Duration"];
        const arr_vars = ["Tags"];
        const data_headers = [
            new UploadHeader("Game", true),
            new UploadHeader("Song", true),
            new UploadHeader("Category", true),
            new UploadHeader("Composers", false),
            new UploadHeader("Converters", false),
            new UploadHeader("Audio", false),
            new UploadHeader("Tags", false),
            new UploadHeader("Update Notes", false),
            new UploadHeader("Additional Notes", false),
            /* Automatically generated headers */
            // new UploadHeader("Date", true),
            // new UploadHeader("Verified", true),
            // new UploadHeader("Binary", true),
            // new UploadHeader("Duration", true),
            // new UploadHeader("Tracks", true),
        ]
    
    
        // PR Data
        const prNumber = process.env.PR_NUMBER;
        const repo = "theballaam96/candys-shop";
        const token = process.env.PAT_TOKEN;
        const response = await axios.get(`https://api.github.com/repos/${repo}/pulls/${prNumber}`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });
        const response_files = await axios.get(`https://api.github.com/repos/${repo}/pulls/${prNumber}/files`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });
        // Set file variables
        let bin_file = null;
        let midi_file = null;
        let midi_raw_file = null;
        let preview_file = null;
        let preview_extension = null;
        const preview_extensions = ["wav", "mp3"];
        for (i = 0; i < response_files.data.length; i++) {
          const f = response_files.data[i];
          if (f.filename) {
              const extension_sep = f.filename.split(".");
              const extension = extension_sep[extension_sep.length - 1];
              if (extension == "bin") {
                bin_file = f.filename;
              } else if (extension == "mid") {
                midi_file = f.filename;
                midi_raw_file = f.raw_url;
              } else if (preview_extensions.includes(extension)) {
                preview_file = f.filename;
                preview_extension = extension;
              }
          }
        }
        const octokit = new Octokit({auth: token})
    
        // Extract the PR message
        const prMessage = response.data.body;
        const rawPRData = prMessage ? prMessage.split("\r\n") : []
        const REQ_STRING = "IS SONG - DO NOT DELETE THIS LINE"
        if (rawPRData[0] == REQ_STRING) {
            song_upload = true;
        }
        let json_output = {}
        rawPRData.forEach((item, index) => {
            if ((index > 0) && (item)) {
                spl = item.split(/:(.*)/s)
                if (item.split("").includes(":")) {
                    key = spl[0].trim()
                    header_data = data_headers.filter(h => h.name == key)
                    if (header_data.length == 0) {
                        // Uses header not listed in the array
                        unlisted_headers.push(key)
                    } else {
                        if (header_data[0].mandatory) {
                            mandatory_headers_included.push(key)
                        }
                    }
                    json_output[key] = spl[1].trim()
                }
            }
        })
        number_vars.forEach(v => {
            if (Object.keys(json_output).includes(v)) {
                if (!isNaN(json_output[v])) {
                    json_output[v] = Number(json_output[v])
                }
            }
        })
        arr_vars.forEach(v => {
            if (Object.keys(json_output).includes(v)) {
                if (json_output[v]) {
                    json_output[v] = json_output[v].split(",").map(item => item.trim())
                }
            }
        })
        json_output["Verified"] = true;
        dt = new Date();
        json_output["Date"] = dt.toString();
    
        // Check headers
        let missing_mandatory_headers = [];
        data_headers.forEach(h => {
            if (h.mandatory) {
                if (!mandatory_headers_included.includes(h.name)) {
                    missing_mandatory_headers.push(h.name)
                }
            }
        })
        
    
        // Check game list
        const file = "images.json"
        const mappingFile = "mapping.json"
        const filePath = path.join(__dirname, `../../${file}`);
        const mappingPath = path.join(__dirname, `../../${mappingFile}`);
        const imageData = fs.existsSync(filePath) ? require(filePath) : [];
        const mappingData = fs.existsSync(mappingPath) ? require(mappingPath) : [];
        // Get new file name
        let revisions = mappingData.filter((entry) => ((entry["Game"] == json_output["Game"]) && (entry["Song"] == json_output["Song"]))).length;
        const rev_string = revisions == 0 ? "" : ` (REV ${revisions})`;
        const sub_file = `${filterFilename(json_output["Game"])}/${filterFilename(json_output["Song"])}${rev_string}`
        if (preview_file) {
          json_output["Audio"] = encodeURI(`https://github.com/theballaam96/candys-shop/raw/main/previews/${sub_file}.${preview_extension}`)
        }
        if (bin_file) {
          json_output["Binary"] = `binaries/${sub_file}.bin`
        }
        if (midi_file) {
            const midiURL = adjustRawURL(midi_raw_file);
            const midiParsed = await Midi.fromUrl(midiURL);
            if (midiParsed.duration) {
                json_output["Duration"] = midiParsed.duration;
            }
        }
    
        if (song_upload) {
            needs_changing = missing_mandatory_headers.length > 0 || unlisted_headers.length > 0 || !Object.keys(json_output).includes("Binary") || !Object.keys(json_output).includes("Audio");
        }
    
        const game_name = Object.keys(json_output).includes("Game") ? json_output["Game"] : null;
        const similarity_threshold = 0.75
        if (game_name != null) {
            if (!Object.keys(imageData).includes(game_name)) {
                new_game = true;
                let max_score = 0;
                let max_score_name = "";
                Object.keys(imageData).forEach(gn => {
                    new_score = stringCompare(game_name, gn);
                    if (new_score > max_score) {
                        max_score = new_score
                        max_score_name = gn
                    }
                })
                if (max_score >= similarity_threshold) {
                    similar_game_name = max_score_name;
                    similar_game_score = max_score;
                }
            }
        }
    
        // Compose Message
        let segments = [
            "Mornin'",
            "",
            "I've analyzed your pull request and ascertained the following information from it. This will help the verifiers handle your request faster:",
            `> Is Song Upload: ${song_upload ? "Yes": "No"}`
        ]
        if (song_upload) {
            segments.push(`> Has Binary File: ${Object.keys(json_output).includes("Binary") ? "Yes" : "No"}`)
            segments.push(`> Has Preview: ${Object.keys(json_output).includes("Audio") ? "Yes" : "No"}`)
            segments.push(`> Missing Mandatory Information: ${missing_mandatory_headers.length == 0 ? "None" : missing_mandatory_headers.join(", ")}`)
            segments.push(`> Headers which I don't understand: ${unlisted_headers.length == 0 ? "None": unlisted_headers.join(", ")}`)
            segments.push(`> Is new game: ${new_game ? "Yes": "No"}`)
            if (new_game) {
                if (similar_game_score > 0) {
                    segments.push(`> Detected as Similar to: ${similar_game_name} (Similarity Score: ${parseInt(similar_game_score * 100, 10)}%)`)
                }
            }
        }
        segments.push(`> Something needs changing: ${needs_changing ? "YES!!! (PLEASE ENSURE YOU FIX ANY ERRORS SO THIS SAYS NO BEFORE MERGING)": "No"}`)
        segments.push("") // Prevent following messges getting indented
        if (song_upload) {
            segments.push("Here's what the output will look like:")
            segments.push("\`\`\`")
            segments.push(JSON.stringify(json_output, undefined, 4))
            segments.push("\`\`\`")
        }
    
    
        const message = segments.join("\n");
        await octokit.issues.createComment({
            owner: repo.split("/")[0],
            repo: repo.split("/")[1],
            issue_number: parseInt(prNumber, 10), // Ensure prNumber is parsed as an integer
            body: message,
        });
    
        if (needs_changing) {
            console.error("Something needs changing in order to make this PR valid.")
            process.exit(1);
        }
      } catch (error) {
        console.error('Error:', error.response ? error.response.data : error.message || error);
        process.exit(1);
      }
    }
    
    run();
})();
