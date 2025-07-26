# Gravity List Bot

**Gravity List Bot** is a Discord bot designed to help your community:

- **Track categorized lists** (Member roles, alliances, enemies, owners, and inline timers)
- **Run real‑time countdown timers** as standalone or embedded in lists
- **Manage Ark Ascended generator timers** (Tek & Electrical) with auto‑updating dashboards
- **Persist all data** via JSON files in a mounted volume (`lists/` directory)

---

## 📦 Key Features

1. **Categorized Lists**  
   - Create, add, edit, remove, delete entries with emojis: 👑 Owner | 🔴 Enemy | 🟢 Friend | 🔵 Ally | 🟡 Beta  
   - Inline timers in lists: ⏳ entries count down live

2. **Standalone Countdown Timers**  
   - `/create_timer`, `/pause_timer`, `/resume_timer`, `/delete_timer`  
   - Updates every second in your channel  

3. **Inline Timers in Lists**  
   - `/add_timer_to_list` adds a ⏳ timer entry to any existing list  
   - Timers auto‑update every 5 seconds in the background

4. **Generator Timers (Ark Ascended)**  
   - `/create_generator_list` to start a fresh generator list  
   - `/add_generator`, `/edit_generator`, `/remove_generator`, `/delete_generator_list`  
   - Tracks Tek and Electrical fuel durations with live countdown  

5. **Unified Dashboards**  
   - `/lists <name>` shows or refreshes any regular or generator list embed  
   - Auto‑refreshes on changes and every 5 seconds in the background

6. **Overview of All Lists**  
   - `/list_all` (Admin only) lists all regular & generator list names

7. **Help & Utility**  
   - `/help` displays the full command list and usage  

8. **JSON‑backed Persistence**  
   - Data lives under `lists/` (including `generator_lists/`)  
   - Volume mount (`/app/lists`) ensures data survives redeploys

---

## 🛠️ Local Setup

1. **Clone the Repo**
   ```bash
   git clone https://github.com/AZX-215/Gravity-List-Bot.git
   cd Gravity-List-Bot
   ```

2. **Create `.env`**
   ```
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
