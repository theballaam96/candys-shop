const fs = require('fs');
const path = require('path');
const axios = require('axios');

const invalid_chars = [
  ":", "/", "\'", "\"", "?", "#", "%", "&", "{", "}", "\\", "<", ">", "*", "$",
  "!", "@", "+", "`", "|", "=", "."
]
function filterFilename(name) {
  invalid_chars.forEach(c => {
    name = name.split("").filter(i => i != c).join("");
  })
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
    // Set file variables
    let bin_file = null;
    let midi_file = null;
    let preview_file = null;
    let preview_extension = null;
    const preview_extensions = ["wav", "mp3"];
    response_files.data.forEach(f => {
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
    })

    // Extract the PR message
    const prMessage = response.data.body;
    const rawPRData = prMessage.split("\r\n")
    const REQ_STRING = "IS SONG - DO NOT DELETE THIS LINE"
    if (rawPRData[0] != REQ_STRING) {
        console.log('Skipping Pull Request, missing key line.');
        return;
    }
    let json_output = {}
    rawPRData.forEach((item, index) => {
        if (index > 0) {
            spl = item.split(/:(.*)/s)
            json_output[spl[0].trim()] = spl[1].trim()
        }
    })
    const number_vars = ["Tracks", "Duration"]
    number_vars.forEach(v => {
        if (Object.keys(json_output).includes(v)) {
            if (!isNaN(json_output[v])) {
                json_output[v] = Number(json_output[v])
            }
        }
    })
    const arr_vars = ["Categories"]
    arr_vars.forEach(v => {
        if (Object.keys(json_output).includes(v)) {
            json_output[v] = json_output[v].split(",").map(item => item.trim())
        }
    })
    json_output["Verified"] = true;
    dt = new Date();
    json_output["Date"] = dt.toString();
    const sub_file = `${filterFilename(json_output['Game'])}/${filterFilename(json_output['Song'])}`

    // Read the existing JSON file
    console.log(__dirname)
    const file = "mapping.json"
    const filePath = path.join(__dirname, `../../${file}`);
    const existingData = fs.existsSync(filePath) ? require(filePath) : [];
    // Read existing file for PR
    file_data = {
      "binaries": [bin_file, "bin", true],
      "previews": [preview_file, preview_extension, true],
      "midi": [midi_file, "mid", false],
    }
    Object.keys(file_data).forEach(k => {
      k_file = file_data[k][0];
      k_ext = file_data[k][1];
      k_keep = file_data[k][2];
      if (k_file != null) {
        const binFilePath = path.join(__dirname, `../../${k_file}`);
        if (k_keep) {
          const newBinFile = `${k}/${sub_file}.${k_ext}`
          const binNewFilePath = path.join(__dirname, `../../${newBinFile}`);
          const binFileData = fs.existsSync(binFilePath) ? require(binFilePath) : null;
          fs.writeFileSync(binNewFilePath, binFileData);
        }
        fs.unlinkSync(binFilePath);
      }
    })

    // Append the PR message to the JSON file
    existingData.push(json_output);

    // Write the updated JSON file
    fs.writeFileSync(filePath, JSON.stringify(existingData, null, 2));

    console.log('PR message appended to JSON file successfully.');
  } catch (error) {
    console.error('Error:', error.response ? error.response.data : error.message || error);
    process.exit(1);
  }
}

run();