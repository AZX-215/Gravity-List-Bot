# Gravity List Bot

**Gravity List Bot** 🎮 is a feature-rich Discord bot for Ark Survival Ascended communities (and more):

---

## 📋 Categorized Lists
Create & manage lists with visual flair:
- 👑 Owner, 🔴 Enemy, 🟢 Friend, 🔵 Ally, 🟡 Beta, ⚫ Item  
- **Headers & Notes:**  
  - `/add_header list_name:<list> header:<text>`
  - `/add_text list_name:<list> text:<note>`

---

## ⏳ Inline Timers in Lists  
- Add timers with `/add_timer_to_list list_name:<list> name:<timer> hours:<int> minutes:<int>`
- **Live countdowns:** Powered by Discord timestamps (`<t:TIMESTAMP:R>`)  
- **No message spam**: Timers self-update; the bot only pings on expiry

---

## ⌛ Standalone Countdown Timers  
- `/create_timer name:<timer> hours:<int> minutes:<int> [role:<@role>]`
- `/pause_timer name:<timer>` / `/resume_timer name:<timer>` / `/delete_timer name:<timer>`
- **Expiry pings:** Checked every minute (no per-second edits)

---

## ⚡ Generator Dashboards  
- `/create_gen_list name:<list>`
- `/add_gen tek list_name:<list> entry_name:<name> element:<int> shards:<int>`
- `/add_gen electrical list_name:<list> entry_name:<name> gas:<int> imbued:<int>`
- `/edit_gen`, `/remove_gen`, `/delete_gen_list`, `/set_gen_role`, `/list_gen_lists`
- **Auto-refresh:** Every 5 minutes with **staggered updates** (rate-limit safe)
- **Visually enhanced embeds:** Emojis, color, bold, clear sections

---

## 🛡️ Logging & Debug

### **A. Internal Bot Logging**
- **Errors & warnings** are posted to a private channel of your choice (buffered & posted every minute).
- **How to enable:**  
  - Add to your `.env` (not tracked by git):
    ```
    LOG_CHANNEL_ID=your-discord-channel-id
    ```
  - Or set via `/set_log_channel` (admin only) in Discord.

### **B. Railway Service Logs (Optional)**
- **Stream all container logs** (stdout/stderr, builds, crashes) to a Discord channel with a [Discord webhook](https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks).
  1. Create a webhook in your target Discord channel.
  2. In Railway, add a **Custom Webhook** integration, paste your Discord webhook URL, and enable "Service Logs" and/or "Deployments".
- Use both logging methods for complete visibility!

---

## 🔗 Deploying Any Dashboard  
- `/lists name:<list>` posts or updates any **regular** list or generator dashboard.

---

## 🛠️ Local Setup

1. **Clone & enter directory:**
   ```bash
   git clone https://github.com/AZX-215/Gravity-List-Bot.git
   cd Gravity-List-Bot

    Configure environment:

cp .env.example .env

    Edit .env and fill in:

        DISCORD_TOKEN=your-bot-token

        CLIENT_ID=your-client-id

        LOG_CHANNEL_ID=optional-logs-channel-id

        DATABASE_PATH=lists/data.json (or omit for default)

    Never commit your .env! (It’s ignored by default for your safety.)

Install dependencies:

pip install -r requirements.txt

Run the bot:

    python bot.py

🚀 Railway Deployment

    Add your secrets as Railway Variables (from .env keys)

    Set up Teardown Overlap for seamless deploys (10-30s overlap recommended)

    (Optional) Set up a Railway logs webhook to a Discord channel

🤝 Contributing

    PRs & issues welcome!

    MIT License

Quick Tips

    Slash commands auto-register in Discord when you start the bot

    For questions, DM the maintainer or open a GitHub issue

    Use .env.example for local dev; never share your real secrets

Gravity List Bot is your Ark/Discord utility for smooth, stylish, organized PvP/PvE coordination. Enjoy!
