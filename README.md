# Gravity List Bot

Slash-only Discord bot for Ark: Survival Ascended groups: smart lists, generator dashboards, timers, optional server status dashboards, and structured logging.

<p align="center">
  <img alt="Discord" src="https://img.shields.io/badge/Discord.py-2.x-blue">
  <img alt="Python"  src="https://img.shields.io/badge/Python-3.11+-yellow">
  <img alt="Style"   src="https://img.shields.io/badge/Code-black%20%26%20ruff-brightgreen">
</p>

---

## What it does

### 📋 Smart Lists
Structured lists with categories, named entries, bullets, and free-text sections. Deploy a list to a channel as a single rendered message/embed.

### ⛽ Generator dashboards
Track Tek/Gas/Electrical generator burn time and deploy/update a live dashboard message.

### ⏱️ Timers
Create, pause/resume, edit, and delete timers.

### 🧹 AutoPrune (keep last N)
Automatically deletes the **oldest** messages in a channel while always keeping the newest **N**.

- Runs every **2 hours**
- Deletes oldest first; does nothing if the channel has ≤ `keep_last`
- Bulk-deletes recent messages when possible (Discord bulk-delete limit is ~14 days)
- Falls back to slow 1-by-1 deletes for older messages
- Designed to be gentle on rate limits (configurable delays)

### 🧾 Logging
- Console logging goes to **stdout** (Railway-friendly)
- Optional **Discord ops log channel** (buffered)
- Optional **command-usage log channel** (recommended)

> This bot does **not** run a screenshots ingest HTTP server. Screenshot ingest/processing should live in your separate **Gravity Capture** stack.

---

## Command catalog

### Lists
- `/create_list` · `/delete_list`
- `/add_list_category` · `/edit_list_category` · `/remove_list_category`
- `/assign_to_category`
- `/add_text` · `/edit_text` · `/remove_text`
- `/add_bullet` · `/edit_bullet` · `/remove_bullet`
- `/add_name` · `/edit_name` · `/remove_name` · `/move_name` · `/sort_list`
- `/add_comment` · `/edit_comment` · `/remove_comment`
- `/view_lists`
- `/deploy_list`

### Generator dashboards
- `/create_gen_list` · `/delete_gen_list`
- `/add_gen_tek` · `/edit_gen_tek`
- `/add_gen_electrical` · `/edit_gen_electrical`
- `/remove_gen` · `/reorder_gen`
- `/set_gen_role`
- `/view_gen_lists`
- `/deploy_gen_list`
- `/mute_gen_alerts` · `/unmute_gen_alerts`
- `/update_all_gens_tek` · `/update_all_gens_electrical`

### Timers
- `/create_timer`
- `/pause_timer` · `/resume_timer`
- `/edit_timer`
- `/delete_timer`

### AutoPrune
- `/autoprune_enable`
- `/autoprune_disable`
- `/autoprune_list`
- `/autoprune_run_now`

### Optional dashboards (if enabled)
BattleMetrics:
- `/bm_asa_server_query`
- `/bm_asa_dashboard_start` · `/bm_asa_dashboard_stop` · `/bm_asa_dashboard_refresh`

ArkStatus:
- `/as_server_query`
- `/as_dashboard_start` · `/as_dashboard_stop` · `/as_dashboard_refresh`

### Debug / maintenance (optional)
- `/debug_storage`
- `/migrate_regular_lists_to_subdir`
- `/migrate_gen_lists_to_volume`

---

## Setup (local)

### Requirements
- Python 3.11+
- A Discord application + bot token

### Install
```bash
pip install -r requirements.txt
```

### Configure
Copy `env.example` to `.env` and fill in values (or set env vars in your shell/host).

Minimum:
- `DISCORD_TOKEN`

Run:
```bash
python bot.py
```

---

## Railway deployment

### Required Railway variables
- `DISCORD_TOKEN`

### Recommended (persistence)
Mount a Railway volume (example mount: `/data`) and set:
- `DATABASE_PATH=/data/lists/data.json`

This causes all bot JSON data to live under `/data/` (lists, generator lists, timers, autoprune config, etc.).

### Recommended (log sanity)
- `LOG_LEVEL=INFO`
- `QUIET_DISCORD_LOGS=1` (default; suppresses high-frequency `discord.gateway` INFO like “RESUMED session”)

---

## Environment variables

### Core
- `DISCORD_TOKEN` (required)
- `GUILD_ID` (optional; `0` = global slash sync, faster dev sync if set)
- `BRAND_NAME` (optional; used in some dashboard output)

### Storage
- `DATABASE_PATH` (default: `./data.json`)
- `DASHBOARDS_PATH` (default: alongside DATABASE_PATH)
- `GEN_DASHBOARDS_PATH` (default: alongside DATABASE_PATH)
- `AUTOPRUNE_PATH` (default: alongside DATABASE_PATH)

> Tip: On Railway, setting `DATABASE_PATH` inside your volume is usually enough; the rest default into the same directory.

### Logging (console)
- `LOG_LEVEL` (default `INFO`)

### Logging (Discord channel posting)
If these are unset, nothing is posted to Discord and logs remain in Railway/stdout.

Ops log channel:
- `LOG_CHANNEL_ID`
- `LOG_CHANNEL_LEVEL` (default `WARNING`)
- `LOG_CHANNEL_FLUSH_SEC` (default `10`)
- `LOG_CHANNEL_MAX_LINES` (default `200`)

Command usage channel (recommended):
- `COMMAND_LOG_CHANNEL_ID`
- `COMMAND_LOG_CHANNEL_LEVEL` (default `INFO`)
- `COMMAND_LOG_FLUSH_SEC` (default: `LOG_CHANNEL_FLUSH_SEC`)
- `COMMAND_LOG_MAX_LINES` (default: `LOG_CHANNEL_MAX_LINES`)

Noise suppression:
- `QUIET_DISCORD_LOGS` (default `1`)
- `SUPPRESS_HTTP_RATELIMIT_WARNINGS` (default `1`; prevents frequent `discord.http` 429 warnings from being posted to Discord log channels)

### AutoPrune tuning (optional)
- `AUTOPRUNE_USE_BULK_DELETE` (default `1`)
- `AUTOPRUNE_BULK_SAFE_DAYS` (default `13.5`)
- `AUTOPRUNE_BULK_DELAY_SECONDS` (default `0.80`)
- `AUTOPRUNE_DELETE_DELAY_SECONDS` (default `1.10`)
- `AUTOPRUNE_INTERVAL_MINUTES` (default `120`; checks every 2 hours)
- `AUTOPRUNE_LOG_TICKS` (default `1`; logs each scheduled tick to Railway stdout)
- `AUTOPRUNE_LOG_NOOP` (default `1`; logs no-op runs where nothing needed deleting)
- `AUTOPRUNE_LOG_SKIPS` (default `1`; logs skips due to missing perms or invalid channel)

### Optional: BattleMetrics module
Enable:
- `ENABLE_BATTLEMETRICS=1`

Required:
- `BM_API_KEY`
- `BM_SERVER_IDS` (comma-separated)

Optional:
- `BM_CHANNEL_ID`
- `BM_REFRESH_SEC`
- `BM_BACKOFF_SEC`

### Optional: ArkStatus module
Required:
- `AS_API_KEY`
- `AS_TARGETS` (comma-separated)

Optional:
- `AS_CHANNEL_ID`
- `AS_REFRESH_SEC`
- `AS_BACKOFF_SEC`
- `AS_TIER`

---

## Discord intents & permissions

### Intents
- Message Content intent: **Off** (slash-only)
- Presence intent: **Off**
- Server Members intent: **Off** (unless you add member-aware features)

### Permissions
Recommended:
- Send Messages
- Embed Links
- Read Message History

Additional permissions if you enable specific features:
- Manage Messages (AutoPrune)
