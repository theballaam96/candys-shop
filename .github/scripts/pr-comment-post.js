const axios = require('axios');
const fs = require("fs");
const path = require("path");

async function run() {
    try {
      // PR Data
      const prNumber = process.env.PR_NUMBER;
      const repo = "theballaam96/candys-shop";
      const token = process.env.GITHUB_TOKEN;
      const commentUser = process.env.COMMENT_USER;
      console.log(commentUser)
      const response = await axios.get(`https://api.github.com/repos/${repo}/pulls/${prNumber}`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
  
      // Extract the PR message
      let user = "Unknown";
      let userID = null;
      const file = "discord_mapping.json"
      const filePath = path.join(__dirname, `../../${file}`);
      const existingData = fs.existsSync(filePath) ? require(filePath) : {};
      if (response.data.user) {
          user = response.data.user.login;
          if (Object.keys(existingData).includes(user)) {
            userID = existingData[user]
          }
      }
      let mention = userID == null ? "" : `<@${userID}> `
      let content = `${mention}New PR Comment: ${process.env.PR_URL}`;
      const webhookUrl = process.env.DISCORD_WEBHOOK_PRCOMMENT;
      const options = {
          method: "POST",
          url: webhookUrl,
          headers: { "Content-Type": "application/json" },
          data: {
              content: content,
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