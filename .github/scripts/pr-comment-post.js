const axios = require('axios');

async function run() {
    try {
      // PR Data
      const prNumber = process.env.PR_NUMBER;
      const repo = "theballaam96/candys-shop";
      const token = process.env.GITHUB_TOKEN;
      const response = await axios.get(`https://api.github.com/repos/${repo}/pulls/${prNumber}`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
  
      // Extract the PR message
      let user = "Unknown";
      let userID = null;
      if (response.data.user) {
          user = response.data.user.login;
          await axios.get("https://raw.githubusercontent.com/theballaam96/candys-shop/main/discord_mapping.json")
            .then(jsonresp => {
                if (Object.keys(jsonresp.data).includes(user)) {
                    userID = jsonresp.data[user]
                }
            })
      }
      let mention = userID == null ? "" : `<@${userID}> `
      let content = `${mention}New PR Comment: ${process.env.PR_URL}`;
      const webhookUrl = process.env.DISCORD_WEBHOOK_PRCOMMENT;
      const options = {
          method: "POST",
          url: webhookUrl,
          headers: { "Content-Type": "application/json" },
          data: {
              content: content
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