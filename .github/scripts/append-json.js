const fs = require('fs');
const path = require('path');
const { Octokit } = require('@octokit/rest');

async function run() {
  try {
    const octokit = new Octokit({ auth: process.env.GITHUB_TOKEN });

    // Get the PR number
    const prNumber = process.env.GITHUB_EVENT_NUMBER;

    // Get the PR details
    const { data: pr } = await octokit.pulls.get({
      owner: process.env.GITHUB_REPOSITORY.split('/')[0],
      repo: process.env.GITHUB_REPOSITORY.split('/')[1],
      pull_number: prNumber,
    });

    // Extract the PR message
    const prMessage = pr.data.body;

    // Read the existing JSON file
    const filePath = path.join(__dirname, 'mapping.json');
    const existingData = fs.existsSync(filePath) ? require(filePath) : [];

    // Append the PR message to the JSON file
    existingData.push({ prNumber, prMessage });

    // Write the updated JSON file
    fs.writeFileSync(filePath, JSON.stringify(existingData, null, 2));

    console.log('PR message appended to JSON file successfully.');
  } catch (error) {
    console.error('Error:', error.message || error);
    process.exit(1);
  }
}

run();