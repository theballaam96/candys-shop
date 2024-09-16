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
      let content = null;
      let webhookUrl = null;
      const embed = [
        {
          "type": "rich",
          "title": "",
          "description": process.env.COMMENT_TEXT,
          "color": 0x016464,
          "author": {
            "name": commentUser
          },
          "url": process.env.PR_URL,
          "timestamp": new Date().toISOString(),
        }
      ]
      if (user == commentUser) {
        // Post to verification team
        content = `New PR Comment on ${user}'s PR "${response.data.title}": ${process.env.PR_URL}`
        webhookUrl = process.env.DISCORD_WEBHOOK_SUBMISSION;
      } else {
        return
        // Post to submission comments channel
        let mention = userID == null ? "" : `<@${userID}> `
        content = `${mention}New PR Comment on "${response.data.title}": ${process.env.PR_URL}`;
        webhookUrl = process.env.DISCORD_WEBHOOK_PRCOMMENT;
      }
      const options = {
          method: "POST",
          url: webhookUrl,
          headers: { "Content-Type": "application/json" },
          data: {
              content: content,
              embeds: embed,
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
