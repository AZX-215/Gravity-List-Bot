# Gravity List Bot

**Gravity List Bot** is a public Discord bot that helps server communities track categorized member names (tribes, alliances, friends/enemies) in visually styled static dashboards.

---

## 📦 Features

- Slash command interface for managing lists
- Categorized entries with emojis & colors:
  - 🔴 Enemy
  - 🟢 Friend
  - 🔵 Ally
  - 🟡 Bob
- Auto-updating static embeds (dashboard-style)
- Interactive category selection via dropdown
- JSON-backed persistent storage per server
- Minimal setup, Railway-deployable

---

## ✨ Commands

| Command | Description |
|--------|-------------|
| `/create_list name:<list>` | Create a new list |
| `/add_name list_name:<list> name:<entry>` | Add entry to list (category is prompted interactively) |
| `/edit_name list_name:<list> old_name:<old> new_name:<new>` | Rename an entry and update category |
| `/remove_name list_name:<list> name:<entry>` | Delete a specific entry from a list |
| `/delete_list list_name:<list>` | Delete the entire list (admin only) |
| `/list list_name:<list>` | Refresh or display the list's dashboard embed |
| `/help` | Show full usage help |

---

## 🛠️ Setup

### 1. Clone the Repo

```bash
git clone https://github.com/YOUR_USERNAME/Gravity-List-Bot.git
cd Gravity-List-Bot
```

### 2. Configure Environment Variables

Create a `.env` file based on the example:

```bash
cp .env.example .env
```

Then fill in:
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

## 🚀 Run the Bot (Locally)

```bash
python bot.py
```

---

## ☁️ Deploy on Railway

1. Connect the GitHub repo to [Railway](https://railway.app/)
2. Set the following environment variables:
   - `DISCORD_TOKEN`
   - `CLIENT_ID`
   - `DATABASE_PATH` (recommended: `lists/data.json`)
3. ## Deployment on Railway
-We use a standard Dockerfile to build and run the bot.

(1) **Ensure your repo root contains:**
   - `Dockerfile`
   - `bot.py`
   - `data_manager.py`
   - `requirements.txt`
   - `.env.example` (with `DISCORD_TOKEN`, `CLIENT_ID`, and optional `DATABASE_PATH`)

(2) **Set up Railway variables**  
   In your project’s **Settings → Variables**, add:
   - `DISCORD_TOKEN` – your bot token  
   - `CLIENT_ID` – your application client ID  
   - `DATABASE_PATH` – (optional) e.g. `./lists/data.json`

(3) **Deploy**  
   Railway will detect the `Dockerfile` and run:
   ```dockerfile
   FROM python:3.11-slim
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   COPY . .
   CMD ["python", "bot.py"]


---

## ✅ Permissions & Scope

You must add your bot with the following OAuth2 scopes:

- `applications.commands`
- `bot`

Minimum bot permissions:
- Send Messages
- Embed Links
- Read Message History
- Manage Messages (optional, for deleting embeds)

---

## 📚 Example Workflow

1. `/create_list name:Enemies`
2. `/add_name list_name:Enemies name:TribeX`
   - Select "Enemy" from the dropdown
3. `/list list_name:Enemies` – posts the dashboard
4. `/edit_name list_name:Enemies old_name:TribeX new_name:TribeXYZ`
   - Reassign a new category
5. `/remove_name list_name:Enemies name:TribeXYZ`
6. `/delete_list list_name:Enemies`

---

## 🤝 Contributing

PRs and forks are welcome. If you’d like to add more categories, role-based list controls, or pagination, feel free to submit an issue or fork it.

---

## 📜 License

MIT

## Legal

- **Terms of Service:**  
  https://github.com/AZX-215/Gravity-List-Legal/blob/main/Docs/TERMS.md

- **Privacy Policy:**  
  https://github.com/AZX-215/Gravity-List-Legal/blob/main/Docs/PRIVACY.md 
