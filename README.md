# Gravity List Bot (v3.2)

**Gravity List Bot** is a Discord bot designed to help your community:

- **Track categorized lists** with emojis: 👑 Owner, 🔴 Enemy, 🟢 Friend, 🔵 Ally, 🟡 Beta, ⚫ Item
- **Inline timers** embedded in lists (countdown to days/h/m/s)
- **Standalone countdown timers**
- **Generator timers** (Ark Ascended Tek & Electrical)
- **Custom headers & notes**
- **Unified dashboards** with auto-refresh
- **Optional comments** on list entries
- **Persistent JSON storage**

---

## 📦 Key Features

1. **Categorized Lists**  
   - `/create_list`, `/add_name`, `/edit_name`, `/remove_name`, `/delete_list`  
   - Supports categories: Owner (👑), Enemy (🔴), Friend (🟢), Ally (🔵), Beta (🟡), Item (⚫)  
   - Optional `comment` on `/add_name`, rendered italic below the entry

2. **Custom Headers & Notes**  
   - `/add_header` sets a centered header at the top of a list  
   - `/add_text` appends a freeform bullet note at the bottom

3. **Inline Timers in Lists**  
   - `/add_timer_to_list` adds a ⏳ timer entry to any existing list  
   - Countdown displays days/hours/minutes/seconds  
   - Dashboards auto-update every **3 seconds** for lists containing timers

4. **Standalone Countdown Timers**  
   - `/create_timer`, `/pause_timer`, `/resume_timer`, `/delete_timer`  
   - Embeds update every second; optional role ping on expiry

5. **Generator Timers (Ark Ascended)**  
   - `/create_generator_list`, `/add_generator`, `/edit_generator`, `/remove_generator`, `/delete_generator_list`  
   - Tracks Tek & Electrical durations with days support

6. **Unified Dashboards**  
   - `/lists <name>` shows or refreshes any regular or generator dashboard  
   - Auto-refresh on changes and via `/resync_timers` every 3 seconds for timer lists  
   - `/resync_timers` now force-refreshes **all** dashboards (regular & generator)

7. **Overview of All Lists**  
   - `/list_all` (Admin only) lists all regular & generator lists

8. **Help & Utility**  
   - `/help` displays usage instructions and all commands

9. **JSON‑Backed Persistence**  
   - All data stored as JSON under `lists/`  
   - Volume mount (`/app/lists`) ensures data survives redeploys

---

## 🛠️ Local Setup

1. **Clone the Repo**
   ```bash
   git clone https://github.com/AZX-215/Gravity-List-Bot.git
   cd Gravity-List-Bot
   ```

2. **Create `.env`**
   ```bash
   cp .env.example .env
   DISCORD_TOKEN=YOUR_DISCORD_TOKEN
   CLIENT_ID=YOUR_CLIENT_ID
   DATABASE_PATH=lists/data.json
   ```

3. **Install**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run Locally**
   ```bash
   python bot.py
   ```

---

## ☁️ Railway Deployment

1. **Connect GitHub** and select this repo.
2. **Variables** → add:
   - `DISCORD_TOKEN`
   - `CLIENT_ID`
   - `DATABASE_PATH=lists/data.json`
3. **Volumes** → mount a volume to `/app/lists`
4. **Settings**:
   - Disable **Serverless**
   - Start command: `python bot.py`
5. **Deploy** → check **Service Logs** for:
   ```
   Bot ready. Commands synced for Gravity List
   ```

---

## ✅ OAuth2 & Permissions

**Scopes**: `applications.commands` + `bot`  
**Permissions**: Send Messages, Embed Links, Read History, Use Application Commands

---

## 🤝 Contributing

PRs & issues welcome! Feel free to add features like pagination, role‑based controls, etc.

---

## 📜 License

MIT License
