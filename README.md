# Gravity List Bot

**Gravity List Bot** is a Discord bot designed to help your community:

- **Track categorized lists** (headers, bullet notes, alliances, enemies, owners)
- **Run real‑time countdown timers** as standalone or embedded in lists
- **Manage Ark Ascended generator timers** (Tek & Electrical) with auto‑updating dashboards
- **Persist all data** via JSON files in a mounted volume (`lists/` directory)

---

## 📦 Key Features

1. **Categorized Lists**  
   - Create, add, edit, remove, delete entries with emojis: 👑 Owner | 🔴 Enemy | 🟢 Friend | 🔵 Ally | 🟡 Beta | ⚫ Item  
   - **Headers & Bullet Notes**: `/add_header list_name:<list> header:<text>` places a centered title; `/add_text list_name:<list> text:<note>` adds bullet points

2. **Inline Timers in Lists**  
   - `/add_timer_to_list list_name:<list> name:<timer> hours:<int> minutes:<int>` adds a ⏳ timer entry  
   - **Auto‑refresh**: Only lists that contain timers are refreshed every 3 seconds  
   - **Force‑resync**: `/resync_timers` (admin) re‑syncs all dashboards on demand

3. **Standalone Countdown Timers**  
   - `/create_timer name:<timer> hours:<int> minutes:<int> [role:<@role>]`  
   - `/pause_timer name:<timer>`  
   - `/resume_timer name:<timer>`  
   - `/delete_timer name:<timer>`  
   - **Force‑resync**: `/resync_timers` (admin) also refreshes all timer messages

4. **Generator Timers (Ark Ascended)**  
   - `/create_gen_list name:<list>` to start a new generator list  
   - `/add_gen tek list_name:<list> entry_name:<name> element:<int> shards:<int>`  
   - `/add_gen electrical list_name:<list> entry_name:<name> gas:<int> imbued:<int>`  
   - `/edit_gen list_name:<list> old_name:<old> [--new_name:<new>] [--gen_type:<Tek|Electrical>] [--element:<int>] [--shards:<int>] [--gas:<int>] [--imbued:<int>]`  
   - `/remove_gen list_name:<list> name:<entry>`  
   - `/delete_gen_list name:<list>`  
   - `/set_gen_role list_name:<list> role:<@role>` to set ping role  
   - `/list_gen_lists` lists all generator lists (admin)  
   - **Force‑resync**: `/resync_gens` (admin) force‑refreshes all generator dashboards  
   - **Auto‑refresh**: Dashboards update every 5 minutes with expiry pings

5. **Unified Dashboards**  
   - `/lists name:<list>` shows or updates any regular, inline‑timer, or generator list embed  
   - Background tasks handle updates efficiently

6. **Overview & Help**  
   - `/list_all` (admin only) lists all regular & generator list names  
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

- **Frequency Tweaks**: Inline‐timer lists update every 3 seconds; generator dashboards update every 5 minutes.  
- **Commands to Monitor**: Check `/resync_timers` for manual timer refresh and `/resync_gens` for generator dashboards.  
- **Railway Deployment**: Ensure volume mount at `/app/lists`.

---

## 🤝 Contributing

PRs & issues welcome! Feel free to add features like pagination, role‑based controls, etc.

## 📜 License

MIT License
