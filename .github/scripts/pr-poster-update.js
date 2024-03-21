const fs = require("fs");
const path = require("path");
const axios = require('axios');
const parseMidi = require("midi-file").parseMidi;
const { Midi } = require("@tonejs/midi");

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
    let midi_raw_url = null;
    let preview_file = null;
    let preview_extension = null;
    const preview_extensions = ["wav", "mp3"];
    for (i = 0; i < response_files.data.length; i++) {
      const f = response_files.data[i];
      if (f.filename) {
        const extension_sep = f.filename.split(".");
        const extension = extension_sep[extension_sep.length - 1];
        if (extension == "bin") {
            bin_file = f.raw_url;
        } else if (extension == "mid") {
            midi_file = f.raw_url;
            midi_raw_file = f.raw_url;
        } else if (preview_extensions.includes(extension)) {
            preview_file = f.raw_url;
            preview_extension = extension;
        }
      }
    }

    // Extract the PR message
    const triggerAction = process.env.TRIGGERED_ACTION;
    const prMessage = response.data.body;
    const rawPRData = prMessage ? prMessage.split("\r\n") : []
    const REQ_STRING = "IS SONG - DO NOT DELETE THIS LINE"
    if (rawPRData[0] != REQ_STRING) {
        return;
    }
    song_upload = true;
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
            json_output[v] = json_output[v].split(",").map(item => item.trim())
        }
    })
    json_output["Verified"] = true;
    dt = new Date();
    json_output["Date"] = dt.toString();

    if (midi_file) {
      const midiURL = adjustRawURL(midi_raw_file);
      const midiParsed = await Midi.fromUrl(midiURL);
      if (midiParsed.duration) {
      	json_output["Duration"] = midiParsed.duration;
      }
    }

    let user = "Unknown";
    if (response.data.user) {
        user = response.data.user.login;
    }
    let embeds_arr = [];
    let content = "";
    let head = "";
    if ((triggerAction == "synchronize") || (triggerAction == "edited")) {
        // Need to repost the entire data again
        const information = {
            "Game": Object.keys(json_output).includes("Game") ? json_output["Game"] : "Not Provided",
            "Song Name": Object.keys(json_output).includes("Song") ? json_output["Song"] : "Not Provided",
            "Original Composer": Object.keys(json_output).includes("Composers") ? json_output["Composers"] : "Not Provided",
            "Converted By": Object.keys(json_output).includes("Converters") ? json_output["Converters"] : "Not Provided",
            "Type": Object.keys(json_output).includes("Category") ? json_output["Category"] : "Not Provided",
            "Tags": Object.keys(json_output).includes("Tags") ? json_output["Tags"] : "Not Provided",
            "Pull Request Link": `https://github.com/${repo}/pull/${prNumber}`,
            "Binary File": bin_file ? bin_file : "Not Provided",
            "Audio File": preview_file ? preview_file : Object.keys(json_output).includes("Audio") ? json_output["Audio"] : "Not Provided",
            "Midi File": midi_file ? midi_file : "Not Provided",
            "Duration": Object.keys(json_output).includes("Duration") ? json_output["Duration"] : "Not Provided",
            "Update Notes": Object.keys(json_output).includes("Update Notes") ? json_output["Update Notes"] : "Not Provided",
            "Additional Notes": Object.keys(json_output).includes("Additional Notes") ? json_output["Additional Notes"] : "Not Provided",
        }
        Object.keys(information).forEach(header => {
            content += `**${header}**: ${information[header]}\n`;
        })
        head = "New major update to pull request"
        embeds_arr.push(
            {
                title: "Pull Request Information",
                color: 0xFCCA03,
                description: content,
                timestamp: new Date().toISOString(),
            }
        );
    } else {
        const header_text = {
            "closed": "A pull request was closed",
            "ready_for_review": "A pull request was marked as ready for review",
            "reopened": "A pull request was reopened",
        }
        if (Object.keys(header_text).includes(triggerAction)) {
            const information = {
                "Pull Request Link": `https://github.com/${repo}/pull/${prNumber}`,
            }
            Object.keys(information).forEach(header => {
                content += `**${header}**: ${information[header]}\n`;
            })
            head = header_text[triggerAction];
            embeds_arr.push(
                {
                    title: "Pull Request Information",
                    color: 0xFCCA03,
                    description: content,
                    timestamp: new Date().toISOString(),
                }
            )
        }
    }
    const webhookUrl = process.env.DISCORD_WEBHOOK_SUBMISSIONS;
    const options = {
        method: "POST",
        url: webhookUrl,
        headers: { "Content-Type": "application/json" },
        data: {
            content: `${head} from ${user}`,
            embeds: embeds_arr,
        },
    }
    axios(options)
        .then(whresp => {
            console.log('Message sent successfully:', whresp.data);
        })
        .catch(error => {
            console.log(error.message);
            process.exit(1);
        });
  } catch (error) {
    console.error('Error:', error.response ? error.response.data : error.message || error);
    process.exit(1);
  }
}

run();
