const axios = require('axios');

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
    const arr_vars = ["Categories"];
    const data_headers = [
        new UploadHeader("Game", true),
        new UploadHeader("Song", true),
        new UploadHeader("Group", true),
        new UploadHeader("Composers", false),
        new UploadHeader("Converters", false),
        new UploadHeader("Audio", false),
        new UploadHeader("Duration", true),
        new UploadHeader("Tracks", true),
        new UploadHeader("Categories", true),
        new UploadHeader("Update Notes", false),
        new UploadHeader("Additional Notes", false),
        /* Automatically generated headers */
        // new UploadHeader("Date", true),
        // new UploadHeader("Verified", true),
        // new UploadHeader("Binary", true),
    ]


    // PR Data
    const prNumber = process.env.PR_NUMBER;
    const repo = process.env.GITHUB_REPOSITORY;
    const token = process.env.GITHUB_TOKEN;
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
    let preview_file = null;
    let preview_extension = null;
    const preview_extensions = ["wav", "mp3"];
    for (i = 0; i < response_files.data.length; i++) {
      const f = response_files.data[i];
      const extension_sep = f.filename.split(".");
      const extension = extension_sep[extension_sep.length - 1];
      if (extension == "bin") {
        bin_file = f.raw_url;
      } else if (extension == "mid") {
        midi_file = f.raw_url;
      } else if (preview_extensions.includes(extension)) {
        preview_file = f.raw_url;
        preview_extension = extension;
      }
    }

    // Extract the PR message
    const prMessage = response.data.body;
    const rawPRData = prMessage.split("\r\n")
    const REQ_STRING = "IS SONG - DO NOT DELETE THIS LINE"
    if (rawPRData[0] == REQ_STRING) {
        song_upload = true;
    }
    let json_output = {}
    rawPRData.forEach((item, index) => {
        if (index > 0) {
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

    let user = "Unknown";
    if (response.data.user) {
        user = response.data.user.login;
    }
    let embeds_arr = [];
    if (song_upload) {
        let content = "";
        const information = {
            "Game": Object.keys(json_output).includes("Game") ? json_output["Game"] : "Not Provided",
            "Song Name": Object.keys(json_output).includes("Song") ? json_output["Song"] : "Not Provided",
            "Original Composer": Object.keys(json_output).includes("Composers") ? json_output["Composers"] : "Not Provided",
            "Converted By": Object.keys(json_output).includes("Converters") ? json_output["Converters"] : "Not Provided",
            "Type": Object.keys(json_output).includes("Group") ? json_output["Group"] : "Not Provided",
            "Categories": Object.keys(json_output).includes("Categories") ? json_output["Categories"] : "Not Provided",
            "Pull Request Link": `https://github.com/${repo}/pull/${prNumber}`,
            "Binary File": bin_file ? bin_file : "Not Provided",
            "Audio File": preview_file ? preview_file : Object.keys(json_output).includes("Audio") ? json_output["Audio"] : "Not Provided",
            "Midi File": midi_file ? midi_file : "Not Provided",
            "Update Notes": Object.keys(json_output).includes("Update Notes") ? json_output["Update Notes"] : "Not Provided",
            "Additional Notes": Object.keys(json_output).includes("Additional Notes") ? json_output["Additional Notes"] : "Not Provided",
        }
        Object.keys(information).forEach(header => {
            content += `**${header}**: ${information[header]}\n`;
        })
        embeds_arr.push(
            {
                title: "New Song Pull Request",
                description: content,
                timestamp: new Date().toISOString(),
            }
        );
    } else {
        
        const information = {
            "Pull Request Link": `https://github.com/${repo}/pull/${prNumber}`,
        }
        Object.keys(information).forEach(header => {
            content += `**${header}**: ${information[header]}\n`;
        })
        embeds_arr.push(
            {
                title: "New Code Pull Request",
                description: content,
                timestamp: new Date().toISOString(),
            }
        )
    }
    const webhookUrl = process.env.DISCORD_WEBHOOK;
    const options = {
        method: "POST",
        url: webhookUrl,
        headers: { "Content-Type": "application/json" },
        content: `New Pull Request from ${user}`,
        data: JSON.stringify({embeds_arr}),
    }
    axios.post(options)
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