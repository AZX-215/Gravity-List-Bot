# Gravity List Bot

**Gravity List Bot** 🎮 is a Discord bot built for Ark Survival Ascended communities and beyond, offering:

- 📋 **Categorized Lists** with custom emojis  
- ⏳ **Inline & Standalone Timers** for countdowns  
- ⚡ **Generator Dashboards** (Tek & Electrical) with auto-refresh & expiry pings  
- 💾 **JSON Persistence** via a mounted `lists/` volume  

---

## 📦 Key Features

### 1. 📋 Categorized Lists  
- **Create** & **Manage** entries with emojis:  
  - 👑 Owner  
  - 🔴 Enemy  
  - 🟢 Friend  
  - 🔵 Ally  
  - 🟡 Beta  
  - ⚫ Item  
- **Headers & Notes**:  
  - `/add_header list_name:<list> header:<text>`  
  - `/add_text   list_name:<list> text:<note>`

### 2. ⏳ Inline Timers in Lists  
- `/add_timer_to_list list_name:<list> name:<timer> hours:<int> minutes:<int>`  
- 🔄 **Auto-refresh**: lists containing timers update every **3 seconds**  
- 🔧 **Force-resync**: `/resync_timers` (admin) re-syncs all inline and standalone timers

### 3. ⌛ Standalone Countdown Timers  
- `/create_timer  name:<timer> hours:<int> minutes:<int> [role:<@role>]`  
- `/pause_timer   name:<timer>`  
- `/resume_timer  name:<timer>`  
- `/delete_timer  name:<timer>`  
- **Force-resync**: `/resync_timers` also refreshes standalone timers

### 4. ⚡ Generator Timers (Ark Ascended)  
- `/create_gen_list           name:<list>`  
- `/add_gen tek               list_name:<list> entry_name:<name> element:<int> shards:<int>`  
- `/add_gen electrical        list_name:<list> entry_name:<name> gas:<int> imbued:<int>`  
- `/edit_gen                  list_name:<list> old_name:<old> [--new_name:<new>] [--gen_type:<Tek|Electrical>] [--element:<int>] [--shards:<int>] [--gas:<int>] [--imbued:<int>]`  
- `/remove_gen                list_name:<list> name:<entry>`  
- `/delete_gen_list           name:<list>`  
- `/set_gen_role              list_name:<list> role:<@role>`  
- `/list_gen_lists            (admin)`  
- **Force-resync**: `/resync_gens` (admin)  
- 🔄 **Auto-refresh**: dashboards update every **5 minutes**; expiry pings summon roles when fuel runs out  

### 5. 🔗 Unified Dashboards  
- `/lists name:<list>` deploys or updates **any** list or generator dashboard  
- Background tasks handle efficient refresh.

### 6. ⚙️ Utilities & Help  
- `/list_all` (admin) — lists **all** regular & generator lists  
- `/help` — displays usage instructions  

---

## 🛠️ Local Setup

1. **Clone the Repo**  
   ```bash
   git clone https://github.com/AZX-215/Gravity-List-Bot.git
   cd Gravity-List-Bot
   ```

2. **Configure Environment**  
   ```bash
   cp .env.example .env
   DISCORD_TOKEN=YOUR_DISCORD_TOKEN
   CLIENT_ID=YOUR_CLIENT_ID
   DATABASE_PATH=lists/data.json
   ```

3. **Install Dependencies**  
   ```bash
   pip install -r requirements.txt
   ```

4. **Run**  
   ```bash
   python bot.py
   ```

---

## ☁️ Deployment Notes

- 🔄 Inline-timer lists: update every **3s**  
- ⚡ Generator dashboards: update every **5min**  
- 🔧 **Manual Resync**: `/resync_timers` & `/resync_gens`  
- 📂 Ensure volume mount at `/app/lists`  

---

## 🤝 Contributing

PRs & issues welcome! Add features like pagination, permissions controls, or custom dashboard embeds.

## 📜 License

MIT License
