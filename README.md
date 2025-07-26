
# Gravity List Bot

**Gravity List Bot** is a Discord bot designed to help your community:

- **Track categorized lists** (Member roles, alliances, enemies, owners, and inline timers)  
- **Run real‑time countdown timers** as standalone or embedded in lists  
- **Manage Ark Ascended generator timers** (Tek & Electrical) with auto‑updating dashboards  
- **Persist all data** via JSON files in a mounted volume (`lists/` directory)

---

## 📦 Key Features

1. **Categorized Lists**  
   - Slash commands to create, add, edit, remove, and delete entries with emojis:  
     👑 Owner | 🔴 Enemy | 🟢 Friend | 🔵 Ally | 🟡 Bob  
   - Inline timers in lists: ⏳ entries that count down in the embed

2. **Standalone Countdown Timers**  
   - `/create_timer`, `/pause_timer`, `/resume_timer`, `/delete_timer`  
   - Updates **every second** in your channel  

3. **Inset Timers in Lists**  
   - `/add_timer_to_list` adds a ⏳ timer entry to any existing list  
   - Timers auto‑update **every 5 seconds** in the background dashboard loop  

4. **Generator Timers (Ark Ascended)**  
   - Separate generator lists via `/create_generator_list`  
   - `/add_generator`, `/edit_generator`, `/remove_generator`, `/delete_generator_list`  
   - Tracks Tek and Electrical fuel durations with live countdown  

5. **Unified Dashboard Display**  
   - `/lists <name>` shows or updates any regular or generator list embed  
   - Auto‑refreshes on changes and every 5 seconds in the background  

6. **List Overview**  
   - `/list_all` (Admin only) lists **all** your list names (regular & generator) alphabetically  

7. **JSON‑backed Persistence**  
   - Data lives under `lists/` (including `generator_lists/`)  
   - Volume mount (`/app/lists`) ensures data survives redeploys  

8. **Railway Deployment Ready**  
   - Dockerfile for containerized hosting  
   - Environment variables for token, client ID, paths  
   - Instructions below for quick setup  

---

## ✨ Slash Commands

### Regular List Commands

| Command                               | Description                                               |
|---------------------------------------|-----------------------------------------------------------|
| `/create_list name:<list>`            | Create a new empty list                                    |
| `/add_name list_name:<list> name:<entry> category:<cat>` | Add an entry with category emoji to a list         |
| `/remove_name list_name:<list> name:<entry>` | Remove an entry from a list                          |
| `/edit_name list_name:<list> old_name:<old> new_name:<new> new_category:<cat>` | Rename/update category of an entry |
| `/delete_list name:<list>`            | Delete an entire list                                     |

### Countdown Timer Commands

| Command                                    | Description                             |
|--------------------------------------------|-----------------------------------------|
| `/create_timer name:<timer> hours:<int> minutes:<int>` | Start a standalone timer         |
| `/pause_timer name:<timer>`                | Pause a running standalone timer        |
| `/resume_timer name:<timer>`               | Resume a paused standalone timer        |
| `/delete_timer name:<timer>`               | Delete a standalone timer               |
| `/add_timer_to_list list_name:<list> name:<timer> hours:<int> minutes:<int>` | Add an inline timer to a list |

### Generator List Commands

| Command                                                                                                         | Description                         |
|-----------------------------------------------------------------------------------------------------------------|-------------------------------------|
| `/create_generator_list name:<list>`                                                                            | Create a new Ark generator list     |
| `/add_generator list_name:<list> entry_name:<name> gen_type:<Tek/Electrical> element:<int> shards:<int> gas:<int> imbued:<int>` | Add generator & fuel info |
| `/edit_generator list_name:<list> old_name:<old> new_name:<new> element:<int> shards:<int> gas:<int> imbued:<int>`        | Edit a generator entry |
| `/remove_generator list_name:<list> entry_name:<name>`                                                           | Remove a generator entry            |
| `/delete_generator_list name:<list>`                                                                             | Delete an entire generator list     |

### Dashboard & Overview

| Command                   | Description                                                    |
|---------------------------|----------------------------------------------------------------|
| `/lists name:<list>`      | Show or update the embed for any regular or generator list     |
| `/list_all` _(Admin only)_| Ephemeral alphabetic list of all regular + generator list names |

---

## 🛠️ Local Setup

1. **Clone the Repo**
   ```bash
   git clone https://github.com/YOUR_USERNAME/Gravity-List-Bot.git
   cd Gravity-List-Bot
   ```

2. **Environment Variables**  
   Copy and fill your values in `.env`:
   ```bash
   cp .env.example .env
   ```
   ```env
   DISCORD_TOKEN=your_token_here
   CLIENT_ID=your_app_client_id
   DATABASE_PATH=lists/data.json
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run Locally**
   ```bash
   python bot.py
   ```

---

## ☁️ Railway Deployment

1. **Connect** your GitHub repo to Railway.  
2. **Variables** → Add:
   - `DISCORD_TOKEN`
   - `CLIENT_ID`
   - `DATABASE_PATH=lists/data.json`  
3. **Volumes** → Mount path:  
   - Host volume → `/app/lists` (ensures all JSON stays)  
4. **Settings**:
   - **Disable Serverless** (to keep your bot alive)  
   - **Custom Start Command**: `python bot.py`  
5. **Deploy** & watch **Service Logs** for:
   ```
   Bot ready. Commands synced for Gravity-List...
   ```

> **Tip**: For instant command updates while testing, switch to guild‑scoped sync:
> ```python
> TEST_GUILD = discord.Object(id=YOUR_GUILD_ID)
> await bot.tree.sync(guild=TEST_GUILD)
> ```

---

## ✅ Bot Permissions & OAuth2 Scopes

**OAuth2 Scopes**:
- `applications.commands`
- `bot`

**Bot Permissions**:
- Send Messages
- Embed Links
- Read Message History
- Use Application Commands

---

## 🤝 Contributing

PRs & issues welcome! Feel free to add features like pagination, role‑based controls, or integrations.

---

## 📜 License

MIT License

---

## Legal

- **Terms:** https://github.com/AZX-215/Gravity-List-Legal/blob/main/Docs/TERMS.md  
- **Privacy:** https://github.com/AZX-215/Gravity-List-Legal/blob/main/Docs/PRIVACY.md  
