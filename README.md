# Gravity List Bot

> A fast, slash-only Discord bot that helps Ark: Survival Ascended groups stay organized: smart lists, generator dashboards, countdown timers, optional server status, and structured logging.

<p align="center">
  <img alt="Discord" src="https://img.shields.io/badge/Discord.py-2.x-blue">
  <img alt="Python"  src="https://img.shields.io/badge/Python-3.11+-yellow">
  <img alt="Style"   src="https://img.shields.io/badge/Code-black%20%26%20ruff-brightgreen">
</p>

---

## ✨ What it does (feature tour)

### 1) 📋 Smart Lists (with categories, notes, and comments)
Keep PvP intel and tribe coordination tidy in one place.

- **Built-in categories:** 👑 Owner · 🔴 Enemy · 🟢 Friend · 🔵 Ally · 🟡 Beta · ⚫ Item
- **Entry types:** plain text notes, bullets, and named items you can re-order and edit.
- **Per-item comments:** attach a short note to any entry (e.g., “offline 2am-8am”).
- **Deploy to a channel:** render/update a list in an embed on demand.

**Typical flow**

/add_name list_name:Scouts category:Enemy item_name:"Tribe XYZ"
/add_comment list_name:Scouts item_name:"Tribe XYZ" comment:"Seen on NE Snow"
/deploy_list name:Scouts


### 2) ⚡ Generator Dashboards (ASA base upkeep)
One glance health for Tek/Electrical generators with role-based pings.

- Track **element/shards** for Tek; **gas/imbued** for Electrical.
- Auto-refresh every 90s (staggered by 1s) with rate-limit back-off.
- Assign a **role** to ping when a dashboard requires attention.

**Example**

/create_gen_list name:MainBase
/add_gen_tek list_name:MainBase gen_name:Forge element:700 shards:0
/add_gen_electrical list_name:MainBase gen_name:Workshop gas:30 imbued:12
/set_gen_role list_name:MainBase role:@Maintenance
/deploy_gen_list name:MainBase


### 3) ⏱️ Standalone Countdown Timers
Fire-and-forget timers for raids, imprints, breeding, and chores.

- Create, pause/resume, edit, delete.
- Safe for long-running servers; checks every minute and posts when done.

/create_timer name:"Raid timer" hours:1 minutes:45


### 4) 🛰️ (Optional) Server Status / ASA Uptime
If enabled in the environment, the bot can post a single-card status for your ASA server (players, map, status). Useful for quick checks in ops channels.

> This module is off by default and gated behind an environment flag so the bot can remain minimal when you don't need it.

### 5) 🧾 Logging & Debug (private channel)
The bot can write warnings/errors and short heartbeat summaries to a private Discord channel you choose. Messages are buffered and posted in small batches (gentle on rate limits).

/set_log_channel #ops-logs # admin only

ext.

---

## 🧩 Commands (catalog)

> All commands are **slash commands**. No message content is processed.

### Lists
- `/add_list_category`
- `/edit_list_category`
- `/remove_list_category`
- `/assign_to_category`
- `/add_text` · `/edit_text` · `/remove_text`
- `/add_bullet` · `/edit_bullet` · `/remove_bullet`
- `/add_name` · `/edit_name` · `/remove_name` · `/move_name` · `/sort_list`
- `/add_comment` · `/edit_comment` · `/remove_comment`
- `/view_lists` — list all lists
- `/deploy_list name:<list>` — render/update a list in a channel

### Generator dashboards
- `/create_gen_list` · `/delete_gen_list`
- `/add_gen_tek` · `/edit_gen_tek`
- `/add_gen_electrical` · `/edit_gen_electrical`
- `/remove_gen` · `/reorder_gen`
- `/set_gen_role`
- `/view_gen_lists`
- `/deploy_gen_list name:<list>`

### Timers
- `/create_timer` · `/pause_timer` · `/resume_timer`
- `/edit_timer` · `/delete_timer`

### Ops / logging (optional)
- `/set_log_channel` (admin)

---

## 🛠️ Setup (self-hosting)

### Requirements
- Python **3.11+**
- A Discord **application + bot** (slash commands)
- Recommended: a private “ops logs” channel for errors

### 1) Get the code
```bash
git clone https://github.com/AZX-215/Gravity-List-Bot.git
cd Gravity-List-Bot

2) Configure environment

cp .env.example .env
# Edit with your values:
DISCORD_TOKEN=your-bot-token                 # required
CLIENT_ID=your-app-client-id                 # required for slash sync
GUILD_ID=optional_dev_guild_id               # optional: speeds up local command sync
LOG_CHANNEL_ID=optional_channel_id           # optional: for private logs
DATABASE_PATH=lists/data.json                # optional: custom path (default shown)
ENABLE_BATTLEMETRICS=0                       # optional: set 1 to enable server status

    Data location: lists are stored on disk (JSON). You can point DATABASE_PATH wherever you prefer on your host.

3) Install & run

pip install -r requirements.txt
python bot.py

4) Railway (quick deploy)

    Set the same .env keys in Railway → Variables.

    Give the service a 10–30s teardown overlap so timers/list refreshes bridge restarts.

    Check “Deploy Logs” after each release to confirm slash commands are synced.

🔒 Discord intents & permissions (for Trust & Safety review)

Bot style: slash-only.
Message Content Intent: Off (not required).
Presence Intent: Off (not required).
Server Members Intent: Off by default. (Turn on only if you plan to use member-aware features later.)

Requested permissions in servers

    Send Messages, Embed Links, Read Message History

    Attach Files (if using screenshots worker)

    Manage Messages (optional: if you want the bot to tidy its own posts)

    Use Slash Commands

What the bot stores

    List/dashboard content and names

    Channel/message IDs where the bot posts its own embeds (for updating)

    Optional: a destination channel ID for logs

What the bot does not do

    No DM processing, no message content reading, no member scraping

    No retention of user PII beyond Discord IDs tied to bot messages

    No third-party data sharing

Delete my data

    Remove items via slash commands or remove the whole list; the JSON entry is deleted.

    Removing the bot from a server stops all collection immediately.

Contact

    Open an issue on the GitHub repository (preferred).

    For abuse reports or takedowns, include a link to the offending message and server.

🤝 GravityCapture (companion app)

We’re building GravityCapture

alongside this bot. It’s an auxiliary service that ingests server logs and forwards structured insights to Discord.

    Status: active development (not yet feature-complete)

    Goal: become a fully-functioning log bot—alerts, searchable history, and screenshot attachments that complement Gravity List dashboards

    Integration: the Gravity List bot already includes a small screenshots worker; GravityCapture will expand on that with robust pipelines and moderation-friendly summaries.

Stay tuned on the GravityCapture repo for milestones and usage docs.
🗺️ Roadmap

    EOS player tracking (teaser): upcoming feature to track player identities across EOS, with privacy-respecting summaries surfaced in ops channels. Perfect for scouting and ban-evasion detection.

    Richer dashboard widgets (generators, turrets, fridges)

    Scheduled report posts (daily/weekly base health)

    Multi-guild separation & export/import tools

🧪 Local development

python -m venv .venv
. .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
pre-commit install
pre-commit run -a

📦 Versioning & releases

We tag releases (vX.Y.Z) and ship via GitHub Releases. Pin a specific tag for production deploys. See CHANGELOG for details.
📝 License

MIT — contributions welcome! Open issues/PRs for bugs, features, and docs.
