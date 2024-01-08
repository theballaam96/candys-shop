const fs = require('fs');
const path = require('path');
const axios = require('axios');

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

    // Extract the PR message
    const prMessage = response.data.body;
    const rawPRData = prMessage.split("\r\n")
    let json_output = {}
    rawPRData.forEach(item => {
        spl = item.split(/:(.*)/s)
        json_output[spl[0].trim()] = spl[1].trim()
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


    // Read the existing JSON file
    const filePath = path.join(__dirname, './mapping.json');
    const existingData = fs.existsSync(filePath) ? require(filePath) : [];

    // Append the PR message to the JSON file
    existingData.push(json_output);

    console.log(existingData)

    // Write the updated JSON file
    fs.writeFileSync(filePath, JSON.stringify(existingData, null, 2));

    console.log('PR message appended to JSON file successfully.');

    // Commit the changes back to the repository
    const commitMessage = `Update JSON file with PR message for #${prNumber}`;
    const commitContent = fs.readFileSync(filePath, 'utf8');

    await axios.post(`https://api.github.com/repos/${repo}/git/commits`, {
      message: commitMessage,
      content: Buffer.from(commitContent).toString('base64'),
    }, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    console.log('Changes committed back to the repository.');
  } catch (error) {
    console.error('Error:', error.message || error);
    process.exit(1);
  }
}

run();