
# Gravity List Bot

**Gravity List Bot** is a Discord bot that helps server communities track categorized member names (tribes, alliances, friends/enemies) in visually styled, auto‑updating dashboards—and now also provides flexible countdown timers with pause, resume, and delete controls.

---

## 📦 Features

- **List management:** Create, edit, and delete named lists of entries with categories and emojis:
  - 👑 **Owner**
  - 🔴 **Enemy**
  - 🟢 **Friend**
  - 🔵 **Ally**
  - 🟡 **Bob**
- **Auto‑updating dashboards:** Static embeds that refresh:
  - Instantly when you add, remove, or edit an entry via `/add_name`, `/remove_name`, `/edit_name`.
  - Periodically in the background (every minute) for any external changes.
- **Persistent JSON storage:** All list data and dashboard message IDs are saved under `lists/` and survive redeploys via a mounted volume in Railway.
- **Real‑time countdown timers:** `/create_timer`, `/pause_timer`, `/resume_timer`, `/delete_timer` with per‑second updates.
- **Railway‑deployable:** Dockerfile and environment variable setup for easy hosting.

---

## ✨ Commands

### List Commands

| Command                                                                 | Description                                          |
|-------------------------------------------------------------------------|------------------------------------------------------|
| `/create_list name:<list>`                                              | Create a new list                                    |
| `/add_name list_name:<list> name:<entry> category:<cat>`               | Add an entry with category emoji to a list           |
| `/remove_name list_name:<list> name:<entry>`                           | Remove an entry from a list                          |
| `/edit_name list_name:<list> old_name:<old> new_name:<new> new_category:<cat>` | Edit an entry’s name and/or category               |
| `/delete_list list_name:<list>`                                         | Delete an entire list                                |
| `/list list_name:<list>`                                                | Show or refresh the dashboard embed for a list       |
| `/help`                                                                 | Show usage instructions                              |

### Timer Commands

| Command                                                      | Description                                   |
|--------------------------------------------------------------|-----------------------------------------------|
| `/create_timer name:<timer> hours:<int> minutes:<int>`       | Start a new countdown timer                   |
| `/pause_timer name:<timer>`                                  | Pause a running timer                         |
| `/resume_timer name:<timer>`                                 | Resume a paused timer                         |
| `/delete_timer name:<timer>`                                 | Delete a timer (running or paused)            |

Timers update **every second**, and remain visible as expired timers until deleted.

---

## 🛠️ Setup

### 1. Clone the Repo

```bash
git clone https://github.com/YOUR_USERNAME/Gravity-List-Bot.git
cd Gravity-List-Bot
```

### 2. Configure Environment Variables

Copy the example and fill in your values:

```bash
cp .env.example .env
```

```
DISCORD_TOKEN=your_discord_bot_token
CLIENT_ID=your_discord_app_client_id
DATABASE_PATH=lists/data.json
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 🚀 Run the Bot Locally

```bash
python bot.py
```

---

## ☁️ Deploy on Railway

1. Connect your GitHub repo to Railway.
2. In **Settings → Variables**, add:
   - `DISCORD_TOKEN`
   - `CLIENT_ID`
   - `DATABASE_PATH=lists/data.json`
3. Under **Settings → Volumes**, mount a volume at **/app/lists** for persistence.
4. **Disable Serverless** so background loops remain active.
5. Railway will detect the `Dockerfile` and run:

   ```dockerfile
   FROM python:3.11-slim
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   COPY . .
   CMD ["python", "bot.py"]
   ```

---

## ✅ Permissions & Scope

When inviting your bot, grant these OAuth2 scopes:

- `applications.commands`
- `bot`

Under **Bot Permissions**, enable:

- Send Messages
- Embed Links
- Read Message History
- Use Application Commands

---

## 🤝 Contributing

PRs and issues are welcome! Feel free to add features like pagination, role‑based controls, or integrations.

---

## 📜 License

MIT License

---

## Legal

- **Terms of Service:** https://github.com/AZX-215/Gravity-List-Legal/blob/main/Docs/TERMS.md
- **Privacy Policy:** https://github.com/AZX-215/Gravity-List-Legal/blob/main/Docs/PRIVACY.md
