# Gravity List Bot

**Gravity List Bot** 🎮 is a Discord bot for Ark Survival Ascended communities (and beyond):

---

## 📋 Categorized Lists
Create & manage entries with emojis:
- 👑 Owner, 🔴 Enemy, 🟢 Friend, 🔵 Ally, 🟡 Beta, ⚫ Item  
- Headers & notes:  
  `/add_header list_name:<list> header:<text>`  
  `/add_text   list_name:<list> text:<note>`

---

## ⏳ Inline Timers in Lists  
- `/add_timer_to_list list_name:<list> name:<timer> hours:<int> minutes:<int>`  
- **Self‑updating** via Discord’s native timestamps—no bot edits required!  
- Shows live countdown: `<t:TIMESTAMP:R>`

---

## ⌛ Standalone Countdown Timers  
- `/create_timer  name:<timer> hours:<int> minutes:<int> [role:<@role>]`  
- `/pause_timer   name:<timer>`  
- `/resume_timer  name:<timer>`  
- `/delete_timer  name:<timer>`  
- **Expiry pings** are checked every minute; no continuous message edits.

---

## ⚡ Generator Dashboards  
- `/create_gen_list name:<list>`  
- `/add_gen tek list_name:<list> entry_name:<name> element:<int> shards:<int>`  
- `/add_gen electrical list_name:<list> entry_name:<name> gas:<int> imbued:<int>`  
- `/edit_gen`, `/remove_gen`, `/delete_gen_list`, `/set_gen_role`, `/list_gen_lists`  
- **Auto‑refresh** every 5 minutes with **staggered updates** to avoid bursts  
- **Enhanced embeds** with color accents, section grouping, bold names, emojis, and timestamps.

---

## 🔍 Logging & Debug  
- Configure optional logging channel:  
  In your `.env`, add:  
  ```bash
  LOG_CHANNEL_ID=123456789012345678
  ```  
- Warnings & errors are buffered and posted every minute as a single log message.

---

## 🔗 Deploying Any Dashboard  
- `/lists name:<list>` shows or updates **any** regular list or generator dashboard.

---

## 🛠️ Local Setup

1. Clone & enter directory:
   ```bash
   git clone https://github.com/AZX-215/Gravity-List-Bot.git
   cd Gravity-List-Bot
   ```
2. Configure `.env`:
   ```bash
   cp .env.example .env
   DISCORD_TOKEN=YOUR_DISCORD_TOKEN
   CLIENT_ID=YOUR_CLIENT_ID
   LOG_CHANNEL_ID=OPTIONAL_LOG_CHANNEL_ID
   DATABASE_PATH=lists/data.json
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the bot:
   ```bash
   python bot.py
   ```

---

## 🤝 Contributing
PRs & issues welcome!  

MIT License
