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
    console.log(__dirname)
    const filePath = path.join(__dirname, '../../mapping.json');
    const existingData = fs.existsSync(filePath) ? require(filePath) : [];

    // Append the PR message to the JSON file
    existingData.push(json_output);

    // Write the updated JSON file
    fs.writeFileSync(filePath, JSON.stringify(existingData, null, 2));

    console.log('PR message appended to JSON file successfully.');

    // Get the default branch of the repository
    const { data: repoData } = await axios.get(`https://api.github.com/repos/${repo}`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    const defaultBranch = repoData.default_branch;

    // Get the latest commit SHA of the default branch
    const { data: branchData } = await axios.get(`https://api.github.com/repos/${repo}/git/ref/heads/${defaultBranch}`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    const latestCommitSHA = branchData.object.sha;

    // Get the content of the existing file
    const existingFile = await axios.get(`https://api.github.com/repos/${repo}/contents/${filePath}`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    // Commit the changes back to the repository
    const commitMessage = `Update JSON file with PR message for #${prNumber}`;
    const commitContent = fs.readFileSync(filePath, 'utf8');
    const base64Content = Buffer.from(commitContent).toString('base64');

    await axios.post(`https://api.github.com/repos/${repo}/contents/${filePath}`, {
      message: commitMessage,
      content: base64Content,
      sha: existingFile.data.sha,
      branch: defaultBranch,
    }, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    console.log('Changes committed back to the repository.');

    console.log('Changes committed back to the repository.');
  } catch (error) {
    console.error('Error:', error.response ? error.response.data : error.message || error);
    process.exit(1);
  }
}

run();