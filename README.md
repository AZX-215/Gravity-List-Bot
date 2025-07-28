# Gravity List Bot

**Gravity List Bot** 🎮 is a feature-rich Discord bot for Ark Survival Ascended communities (and more):

---

## 📋 Categorized Lists  
Create & manage lists with visual flair:  
- 👑 Owner, 🔴 Enemy, 🟢 Friend, 🔵 Ally, 🟡 Beta, ⚫ Item  
- **Headers & Notes:**  
  - `/add_header list_name:<list> header:<text>`  
  - `/remove_header list_name:<list> index:<#>`  
  - `/add_text list_name:<list> text:<note>`  
  - `/edit_text list_name:<list> index:<#> new_text:<text>`  
  - `/remove_text list_name:<list> index:<#>`  
- **Items & Ordering:**  
  - `/add_name list_name:<list> category:<…> item_name:<name>`  
  - `/remove_name list_name:<list> item_name:<name>`  
  - `/edit_name list_name:<list> old_name:<name> new_name:<name>`  
  - `/move_name list_name:<list> item_name:<name> position:<#>`  
  - `/sort_list list_name:<list>`  

---

## 💬 Comments on List Items  
Attach notes to specific items:  
- `/add_comment list_name:<list> item_name:<name> comment:<text>`  
- `/edit_comment list_name:<list> item_name:<name> new_comment:<text>`  
- `/remove_comment list_name:<list> item_name:<name>`  

---

## 📄 Viewing Lists  
- `/view_lists` — List all existing lists  
- `/view_gen_lists` — List all existing generator lists  

---

## 🚀 Deploying Lists & Dashboards  
- `/deploy_list name:<list>` — Deploy or update a regular list  
- `/deploy_gen_list name:<gen_list>` — Deploy or update a generator dashboard  

---

## ⌛ Standalone Countdown Timers  
- `/create_timer name:<timer> hours:<int> minutes:<int> [role:<@role>]`  
- `/pause_timer name:<timer>`  
- `/resume_timer name:<timer>`  
- `/edit_timer name:<timer> hours:<int> minutes:<int>`  
- `/delete_timer name:<timer>`  
- **Expiry pings:** Checked every minute (no per-second edits)  

---

## ⚡ Generator Dashboards  
- `/create_gen_list name:<list>`  
- `/delete_gen_list name:<list>`  
- `/add_gen tek list_name:<list> entry_name:<name> element:<int> shards:<int>`  
- `/add_gen electrical list_name:<list> entry_name:<name> gas:<int> imbued:<int>`  
- `/edit_gen list_name:<list> gen_name:<name> property:<…> new_value:<…>`  
- `/remove_gen list_name:<list> gen_name:<name>`  
- `/set_gen_role list_name:<list> role:<@role>`  

Auto-refresh every 5 minutes with staggered updates for rate-limit safety.

---

## 🛡️ Logging & Debug

### A. Internal Bot Logging  
- **Errors & warnings** are posted to a private channel of your choice (buffered & posted every minute).  
- Enable via `.env`:  
  ```env
  LOG_CHANNEL_ID=your-discord-channel-id
Or set at runtime: /set_log_channel #channel (admin only)

B. Railway Service Logs (Optional)
Stream all container logs (stdout/stderr, builds, crashes) to a Discord channel with a Discord webhook.

Create a webhook in your target Discord channel.

In Railway, add a Custom Webhook integration, paste your Discord webhook URL, and enable Service Logs and/or Deployments.

Use both logging methods for complete visibility!

🛠️ Local Setup
Clone & enter directory:

bash
Copy
Edit
git clone https://github.com/AZX-215/Gravity-List-Bot.git
cd Gravity-List-Bot
Configure environment:

bash
Copy
Edit
cp .env.example .env
Edit .env and fill in:

ini
Copy
Edit
DISCORD_TOKEN=your-bot-token
CLIENT_ID=your-client-id
GUILD_ID=optional_guild_id_for_channel-sync
LOG_CHANNEL_ID=optional-logs-channel-id
DATABASE_PATH=lists/data.json    # omit to use default
Never commit your .env! It’s git-ignored by default.

Install dependencies:

bash
Copy
Edit
pip install -r requirements.txt
Run the bot:

bash
Copy
Edit
python bot.py
🚀 Railway Deployment

Add your .env keys as Railway Environment Variables.

Use a Railswebhook for service logs/deployments as above.

Set “Teardown Overlap” to 10–30 s for seamless updates.

🤝 Contributing
PRs & issues welcome!
MIT License

Gravity List Bot is your Ark/Discord utility for smooth, stylish, organized PvP/PvE coordination. Enjoy!
