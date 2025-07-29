# Gravity List Bot

**Gravity List Bot** 🎮 is a feature-rich Discord bot for Ark Survival Ascended communities (and more):

---

## 📋 Categorized Lists
Create & manage lists with visual flair:
- 👑 Owner, 🔴 Enemy, 🟢 Friend, 🔵 Ally, 🟡 Beta, ⚫ Item

- **Categories:**
  - `/add_list_category list_name:<list> title:<text>`
  - `/edit_list_category list_name:<list> index:<#> new_title:<text>`
  - `/remove_list_category list_name:<list> index:<#>`
  - `/assign_to_category list_name:<list> category_index:<#> entry_type:<Text|Bullet|Name> entry_index:<#>`

- **Plain Text Notes:**
  - `/add_text list_name:<list> text:<note>`
  - `/edit_text list_name:<list> index:<#> new_text:<text>`
  - `/remove_text list_name:<list> index:<#>`

- **Bullets:**
  - `/add_bullet list_name:<list> bullet:<text>`
  - `/edit_bullet list_name:<list> index:<#> new_bullet:<text>`
  - `/remove_bullet list_name:<list> index:<#>`

- **Items & Ordering:**
  - `/add_name list_name:<list> category:<Owner|Friend|Ally|Beta|Enemy|Item> item_name:<name>`
  - `/remove_name list_name:<list> item_name:<name>`
  - `/edit_name list_name:<list> old_name:<name> new_name:<name> category:<…>`
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
- `/create_timer name:<timer> hours:<int> minutes:<int>`
- `/pause_timer name:<timer>`
- `/resume_timer name:<timer>`
- `/edit_timer name:<timer> hours:<int> minutes:<int>`
- `/delete_timer name:<timer>`
- **Expiry pings:** Checked every minute (no per-second edits)

---

## ⚡ Generator Dashboards
- `/create_gen_list name:<list>`
- `/delete_gen_list name:<list>`

- **Tek Generators:**
  - `/add_gen_tek list_name:<list> gen_name:<name> element:<int> shards:<int>`
  - `/edit_gen_tek list_name:<list> gen_name:<name> element:<int> shards:<int>`

- **Electrical Generators:**
  - `/add_gen_electrical list_name:<list> gen_name:<name> gas:<int> imbued:<int>`
  - `/edit_gen_electrical list_name:<list> gen_name:<name> gas:<int> imbued:<int>`

- **Common Actions:**
  - `/remove_gen list_name:<list> gen_name:<name>`
  - `/reorder_gen list_name:<list> from_index:<#> to_index:<#>`
  - `/set_gen_role list_name:<list> role:<@role>`

Auto-refresh every **90 seconds** (with 1 s staggers) and 10 min rate-limit back-off.

---

## 🛡️ Logging & Debug

### Internal Bot Logging
- **Errors & warnings** are posted to a private channel of your choice (buffered & posted every 10 s).
- Enable via `.env`:
  ```env
  LOG_CHANNEL_ID=your-discord-channel-id
  ```

Or at runtime:
```
/set_log_channel #channel (admin only)
```

---

## 🛠️ Local Setup
Clone & enter directory:

```bash
git clone https://github.com/AZX-215/Gravity-List-Bot.git
cd Gravity-List-Bot
```

Configure environment:

```bash
cp .env.example .env
# Edit .env with your values:
DISCORD_TOKEN=your-bot-token
CLIENT_ID=your-client-id
GUILD_ID=optional_guild_id_for_channel-sync
LOG_CHANNEL_ID=optional-logs-channel-id
DATABASE_PATH=lists/data.json # omit for default
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the bot:

```bash
python bot.py
```

---

## 🚀 Deployment on Railway
Add your `.env` keys as Railway Environment Variables.
Use a webhook for service logs/deployments if desired.
Set “Teardown Overlap” to 10–30 s for seamless restarts.

---

## 🤝 Contributing
PRs & issues welcome!
**MIT License**

Gravity List Bot is your Ark/Discord utility for smooth, stylish, organized PvP/PvE coordination. Enjoy!
