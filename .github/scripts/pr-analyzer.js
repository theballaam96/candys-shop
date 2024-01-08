const axios = require('axios');
const { Octokit } = require("@octokit/rest");

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
    const number_vars = ["Tracks", "Duration"];
    const arr_vars = ["Categories"];
    const data_headers = [
        new UploadHeader("Game", true),
        new UploadHeader("Song", true),
        new UploadHeader("Group", true),
        new UploadHeader("Composers", false),
        new UploadHeader("Converters", false),
        new UploadHeader("Audio", true),
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
    const octokit = new Octokit({auth: token})

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

    let missing_mandatory_headers = [];
    data_headers.forEach(h => {
        if (h.mandatory) {
            if (!mandatory_headers_included.includes(h.name)) {
                missing_mandatory_headers.push(h.name)
            }
        }
    })
    if (song_upload) {
        needs_changing = missing_mandatory_headers.length > 0 || unlisted_headers.length > 0;
    }

    // Compose Message
    let segments = [
        "Mornin'",
        "",
        "I've analyzed your pull request and ascertained the following information from it. This will help the verifiers handle your request faster:",
        `> Is Song Upload: ${song_upload ? "Yes": "No"}`
    ]
    if (song_upload) {
        segments.push(`> Missing Mandatory Information: ${missing_mandatory_headers.length == 0 ? "None" : missing_mandatory_headers.join(", ")}`)
        segments.push(`> Headers which I don't understand: ${unlisted_headers.length == 0 ? "None": unlisted_headers.join(", ")}`)
    }
    segments.push(`> Something needs changing: ${needs_changing ? "Yes": "No"}`)
    segments.push("Here's what the output will look like:")
    segments.push("\`\`\`")
    segments.push(JSON.stringify(json_output, undefined, 4))
    segments.push("\`\`\`")


    const message = segments.join("\n");
    await octokit.issues.createComment({
        owner: repo.split("/")[0],
        repo: repo.split("/")[1],
        issue_number: parseInt(prNumber, 10), // Ensure prNumber is parsed as an integer
        body: message,
    });
  } catch (error) {
    console.error('Error:', error.response ? error.response.data : error.message || error);
    process.exit(1);
  }
}

run();