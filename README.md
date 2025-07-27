# Gravity List Bot

**Gravity List Bot** is a Discord bot designed to help your community:

- **Track categorized lists** (headers, bullet notes, alliances, enemies, owners)
- **Run real‑time countdown timers** as standalone or embedded in lists
- **Manage Ark Ascended generator timers** (Tek & Electrical) with auto‑updating dashboards
- **Persist all data** via JSON files in a mounted volume (`lists/` directory)

---

## 📦 Key Features

1. **Categorized Lists**  
   - Create, add, edit, remove, delete entries with emojis: 👑 Owner | 🔴 Enemy | 🟢 Friend | 🔵 Ally | 🟡 Beta
   - **Headers & Bullet Notes**: `/add_header` places a centered title; `/add_text` adds bullet points

2. **Inline Timers in Lists**  
   - `/add_timer_to_list list_name name hours minutes` adds a ⏳ timer entry
   - **Auto‑refresh**: Only lists that contain inline timers are refreshed every 3 seconds in the background
   - **Force‑resync**: A background loop every 1 minute ensures accuracy; `/resync_timers` (admin) re‑syncs all list dashboards on demand

3. **Standalone Countdown Timers**  
   - `/create_timer`, `/pause_timer`, `/resume_timer`, `/delete_timer`  
   - Updates every second in your channel  
   - `/resync_timers` command also refreshes these embeds in lists dashboards

4. **Generator Timers (Ark Ascended)**  
   - `/create_generator_list` to start a fresh generator list  
   - `/add_generator`, `/edit_generator`, `/remove_generator`, `/delete_generator_list`
   - Tracks Tek and Electrical fuel durations with live countdown  
   - **Dashboards** auto‑refresh every 2 minutes with expiry pings

5. **Unified Dashboards**  
   - `/lists <name>` shows or refreshes any regular, inline‑timer, or generator list embed  
   - Background tasks handle updates with minimal overhead (only timers lists)

6. **Overview & Help**  
   - `/list_all` (Admin only) lists all regular & generator list names
   - `/help` displays the full command list and usage

7. **JSON‑backed Persistence**  
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

## ☁️ Deployment Notes

- **Frequency Tweaks**: Inline‐timer lists update every 3 seconds; force‑resync loop runs every minute.
- **Commands to Monitor**: Check `/resync_timers` for manual dashboard refreshes.
- **Railway Deployment**: Same as before, ensure volume mount at `/app/lists`.

---

## 🤝 Contributing

PRs & issues welcome! Feel free to add features like pagination, role‑based controls, etc.

## 📜 License

MIT License
