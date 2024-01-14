const fs = require("fs");
const path = require("path");
const axios = require("axios");

const invalid_chars = [
  ":", "/", "\'", "\"", "?", "#", "%", "&", "{", "}", "\\", "<", ">", "*", "$",
  "!", "@", "+", "`", "|", "=", "."
];

function filterFilename(name) {
  invalid_chars.forEach((c) => {
    name = name.split("").filter((i) => i !== c).join("");
  });
  return name;
}

async function run() {
  try {
    // Get the PR number
    const prNumber = process.env.PR_NUMBER;
    const repo = process.env.GITHUB_REPOSITORY;
    const token = process.env.GITHUB_TOKEN;
    // Get the repository owner and name
    console.log(`Fetching details for PR ${prNumber} in repository ${repo}`);

    // Get the PR details using the GitHub API
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
    console.log(response_files.data);
    // Set file variables
    let bin_file = null;
    let midi_file = null;
    let preview_file = null;
    let preview_extension = null;
    const preview_extensions = ["wav", "mp3"];
    for (i = 0; i < response_files.data.length; i++) {
      const f = response_files.data[i];
      console.log(f)
      const extension_sep = f.filename.split(".");
      const extension = extension_sep[extension_sep.length - 1];
      if (extension == "bin") {
        bin_file = f.filename;
      } else if (extension == "mid") {
        midi_file = f.filename;
      } else if (preview_extensions.includes(extension)) {
        preview_file = f.filename;
        preview_extension = extension;
      }
    }
    console.log(bin_file, midi_file, preview_file, preview_extension)

    // Extract the PR message
    const prMessage = response.data.body;
    const rawPRData = prMessage.split("\r\n")
    const REQ_STRING = "IS SONG - DO NOT DELETE THIS LINE"
    if (rawPRData[0] != REQ_STRING) {
        console.log("Skipping Pull Request, missing key line.");
        return;
    }
    let json_output = {}
    rawPRData.forEach((item, index) => {
        if (index > 0) {
            if (item.split("").includes(":")) {
              spl = item.split(/:(.*)/s)
              json_output[spl[0].trim()] = spl[1].trim()
            }
        }
    })
    console.log(json_output)
    const number_vars = ["Tracks", "Duration"]
    number_vars.forEach((v) => {
        if (Object.keys(json_output).includes(v)) {
            if (!isNaN(json_output[v])) {
                json_output[v] = Number(json_output[v])
            }
        }
    })
    const arr_vars = ["Categories"]
    arr_vars.forEach((v) => {
        if (Object.keys(json_output).includes(v)) {
            json_output[v] = json_output[v].split(",").map((item) => item.trim())
        }
    })
    json_output["Verified"] = true;
    dt = new Date();
    json_output["Date"] = dt.toString();
    // Read the existing JSON file
    console.log(__dirname)
    const file = "mapping.json"
    const filePath = path.join(__dirname, `../../${file}`);
    const existingData = fs.existsSync(filePath) ? require(filePath) : [];
    // Get new file name
    let revisions = existingData.filter((entry) => ((entry["Game"] == json_output["Game"]) && (entry["Song"] == json_output["Song"]))).length;
    const rev_string = revisions == 0 ? "" : ` (REV ${revisions})`;
    const sub_file = `${filterFilename(json_output["Game"])}/${filterFilename(json_output["Song"])}${rev_string}`
    let binary_link = null;
    if (preview_file) {
      json_output["Audio"] = encodeURI(`https://github.com/theballaam96/candys-shop/raw/main/previews/${sub_file}.${preview_extension}`)
    }
    if (bin_file) {
      json_output["Binary"] = `binaries/${sub_file}.bin`
      binary_link = encodeURI(`https://github.com/theballaam96/candys-shop/raw/main/binaries/${sub_file}.bin`)
    }
    console.log(sub_file)

    
    // Read existing file for PR
    console.log("Starting file transfer")
    file_data = {
      "binaries": [bin_file, "bin", true],
      "previews": [preview_file, preview_extension, true],
      "midi": [midi_file, "mid", false],
    }
    let preview_file_bytes = null;
    Object.keys(file_data).forEach((k) => {
      k_file = file_data[k][0];
      k_ext = file_data[k][1];
      k_keep = file_data[k][2];
      if (k_file != null) {
        const binFilePath = path.join(__dirname, `../../${k_file}`);
        if (k_keep) {
          const newBinFile = `${k}/${sub_file}.${k_ext}`
          const rootDir = `${k}`
          const gameDir = `${k}/${filterFilename(json_output["Game"])}`
          if (!fs.existsSync(rootDir)) {
            fs.mkdirSync(rootDir)
          }
          if (!fs.existsSync(gameDir)) {
            fs.mkdirSync(gameDir)
          }
          const binNewFilePath = path.join(__dirname, `../../${newBinFile}`);
          const binFileData = fs.existsSync(binFilePath) ? fs.readFileSync(binFilePath) : null;
          if (k == "previews") {
            preview_file_bytes = binFileData;
          }
          if (binFileData != null) {
            fs.writeFileSync(binNewFilePath, binFileData);
          }
        }
        fs.unlinkSync(binFilePath);
      }
    })
    console.log("File Transfer Done")

    // Append the PR message to the JSON file
    existingData.push(json_output);

    // Write the updated JSON file
    fs.writeFileSync(filePath, JSON.stringify(existingData, null, 2));

    console.log("PR message appended to JSON file successfully.");

    // Post to discord
    const shorthand_to_long = {
      "bgm": "BGM",
      "events": "Event",
      "majoritems": "Major Item",
      "minoritems": "Minor Item"
    };
    let suggested_type = "Not Provided";
    if (Object.keys(json_output).includes("Group")) {
      suggested_type = json_output["Group"];
      if (Object.keys(shorthand_to_long).includes(suggested_type)) {
        suggested_type = shorthand_to_long[json_output["Group"]];
      }
    }
    const song_name = Object.keys(json_output).includes("Song") ? json_output["Song"] : "Not Provided"
    let desc_information = {
      "Game": Object.keys(json_output).includes("Game") ? json_output["Game"] : "Not Provided",
      "Song Name": Object.keys(json_output).includes("Song") ? json_output["Song"] : "Not Provided",
      "Type": suggested_type,
      "Tags": Object.keys(json_output).includes("Categories") ? json_output["Categories"] : "Not Provided",
    }
    if (Object.keys(json_output).includes("Update Notes")) {
      desc_information["Additional Notes"] = json_output["Update Notes"];
    }
    let desc_strings = []
    Object.keys(desc_information).forEach(k => {
      desc_strings.push(`**${k}**: ${desc_information[k]}`)
    })
    let update_string = ""
    if (revisions > 0) {
      update_string = ":watermelon: This song is an update\n"
    }
    let desc = desc_strings.join("\n")
    const binary_dl_link = binary_link ? binary_link : "???";
    const has_audio_file = preview_file_bytes != null;
    let audio_string = "No Preview";
    if (has_audio_file) {
      audio_string = "*(Attached)*";
    } else if (Object.keys(json_output).includes("Audio")) {
      audio_string = json_output["Audio"];
    }
    const embeds_arr = [{
      title: song_name,
      description: `${update_string}${desc}`,
      fields: [
        {
          name: "Composer(s)",
          value: Object.keys(json_output).includes("Composers") ? json_output["Composers"] : "Not Provided",
          inline: true,
        },
        {
          name: "Converted By",
          value: Object.keys(json_output).includes("Converters") ? json_output["Converters"] : "Not Provided",
          inline: true,
        },
        {
          name: "",
          value: `Download: ${binary_dl_link}`
        },
        {
          name: "",
          value: `Listen: ${audio_string}`
        }
      ],
      timestamp: new Date().toISOString(),
    }]

    const webhookUrl = process.env.DISCORD_WEBHOOK_PUBLICFILE;
    const options = {
        method: "POST",
        url: webhookUrl,
        headers: { "Content-Type": "application/json" },
        data: {
            content: "A new song has been uploaded",
            embeds: embeds_arr,
        },
    }
    axios(options)
        .then(whresp => {
            console.log('Message sent successfully:', whresp.data);
            if (has_audio_file) {
              const metadata = {}
              const boundary = "xxxxxxxx"
              let data = "";
              for (let i in metadata) {
                data += `--${boundary}\r\n`;
                data += `Content-Disposition: form-data; name=\"${i}\"; \r\n\r\n${metadata[i]}\r\n`;
              }
              data += "--" + boundary + "\r\n";
              const new_song_name = `${song_name.replaceAll(' ','').replaceAll("\"","")}.${preview_extension}`
              data += "Content-Disposition: form-data; name=\"file\"; filename=\"" + new_song_name + "\"\r\n";
              data += "Content-Type:" + "audio/mpeg" + "\r\n\r\n";
              binary_buffer = Buffer.from(preview_file_bytes, "binary");
              let payload_data = Utilities.newBlob(data).getBytes()
                .concat(binary_buffer)
                .concat(binary_buffer);
              options = {
                method: "post",
                url: webhookUrl,
                headers: {
                  "Content-Type": "multipart/form-data; boundary=" + boundary
                },
                data: payload_data
              }
              axios(options).then(whresp2 => {
                console.log('Preview posted successfully:', whresp2.data);
              }).catch(error => {
                console.log(error.message);
                process.exit(1);
              });
            }
        })
        .catch(error => {
            console.log(error.message);
            process.exit(1);
        });
  } catch (error) {
    console.error("Error:", error.response ? error.response.data : error.message || error);
    process.exit(1);
  }
}

run();