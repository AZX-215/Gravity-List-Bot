import os
import time
import discord
from discord.ext import commands, tasks
from discord import app_commands
from dotenv import load_dotenv

from data_manager import (
    load_list, save_list, list_exists, delete_list,
    get_all_list_names, get_all_gen_list_names,
    save_dashboard_id, get_dashboard_id, get_gen_dashboard_id,
    save_gen_dashboard_id
)

from timers import setup as setup_timers
from gen_timers import setup as setup_gen_timers, build_gen_embed as build_gen_dashboard_embed

load_dotenv()
TOKEN     = os.getenv("DISCORD_TOKEN")
CLIENT_ID = int(os.getenv("CLIENT_ID"))

intents = discord.Intents.default()
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents, application_id=CLIENT_ID)

# ━━━━━━ Categories ━━━━━━━━━━
CATEGORY_EMOJIS = {
    "Owner": "👑", "Enemy": "🔴", "Friend": "🟢",
    "Ally":   "🔵", "Beta":   "🟡", "Item":  "⚫", "Timer":"⏳"
}

# ━━━━━━ Embed & Dashboard Helpers ━━━━━━━━━━
async def push_list_update(list_name: str):
    dash = get_dashboard_id(list_name)
    if not dash:
        return
    ch_id, msg_id = dash
    ch = bot.get_channel(ch_id)
    if not ch:
        return
    try:
        msg = await ch.fetch_message(msg_id)
        await msg.edit(embed=build_embed(list_name))
    except Exception as e:
        print(f"[List Update] {e}")

def build_embed(list_name: str) -> discord.Embed:
    data = load_list(list_name)
    embed = discord.Embed(title=f"{list_name} List", color=0x808080)
    embed.add_field(name="\u200b", value="\u200b", inline=False)

    now = time.time()
    data.sort(key=lambda x: 1 if x.get("category") == "Header"
                         else 3 if x.get("category") == "Text"
                         else 2)

    for item in data:
        cat = item.get("category")
        if cat == "Header":
            embed.add_field(name="\u200b", value=f"**{item['name']}**", inline=False)
        elif cat == "Text":
            embed.add_field(name=f"• {item['name']}", value="\u200b", inline=False)
        elif cat == "Timer":
            end_ts = item.get("timer_end") or (item.get("timer_start",0) + item.get("timer_duration",0))
            rem = max(0, int(end_ts - now))
            d, rem_hr = divmod(rem, 86400)
            h, r = divmod(rem_hr, 3600)
            m, s = divmod(r, 60)
            timestr = f"{d}d {h:02d}h {m:02d}m {s:02d}s" if d else f"{h:02d}h {m:02d}m {s:02d}s"
            embed.add_field(name=f"⏳   {item['name']} — {timestr}", value="\u200b", inline=False)
        else:
            name_fld = f"{CATEGORY_EMOJIS.get(cat,'')}   {item['name']}"
            embed.add_field(name=name_fld, value="\u200b", inline=False)
            if item.get("comment"):
                embed.add_field(name="\u200b", value=f"*{item['comment']}*", inline=False)

    return embed

# ━━━━━━ On Ready Guarded ━━━━━━━━━━
@bot.event
async def on_ready():
    if not getattr(bot, "_startup_done", False):
        try:
            await setup_timers(bot)
            await setup_gen_timers(bot)
            list_dashboard_loop.start()
            await bot.tree.sync()
            print(f"Bot ready. Commands synced for {bot.user}")
        except app_commands.errors.CommandAlreadyRegistered as e:
            print(f"[Startup] Commands already registered: {e}")
        finally:
            bot._startup_done = True
    else:
        print(f"Bot reconnected: {bot.user}")

# ━━━━━━ Periodic List Dashboard Refresh ━━━━━━━━━━
@tasks.loop(seconds=3)
async def list_dashboard_loop():
    for name in get_all_list_names():
        data = load_list(name)
        if any(item.get("category") == "Timer" for item in data):
            try:
                await push_list_update(name)
            except Exception as e:
                print(f"[List Loop] Error updating {name}: {e}")

# ━━━━━━ Slash Commands ━━━━━━━━━━
@bot.tree.command(name="create_list", description="Create a new list")
@app_commands.describe(name="Name of the new list")
async def create_list(interaction: discord.Interaction, name: str):
    if list_exists(name):
        return await interaction.response.send_message(f"⚠️ List '{name}' exists.", ephemeral=True)
    save_list(name, [])
    await interaction.response.send_message(f"✅ Created list '{name}'.", ephemeral=True)

# ... other existing commands unchanged ...

@bot.tree.command(name="help", description="Show usage instructions")
async def help_command(interaction: discord.Interaction):
    help_text = (
        "**Gravity List Bot Commands**\n\n"
        "**Regular Lists**\n"
        "/create_list name:<list>\n"
        "/add_name list_name:<list> name:<entry> category:<cat> comment:<optional>\n"
        "/remove_name list_name:<list> name:<entry>\n"
        "/edit_name list_name:<list> old_name:<old> new_name:<new> new_category:<cat> new_comment:<optional>\n"
        "/delete_list name:<list>\n"
        "/add_text list_name:<list> text:<note>\n"
        "/add_header list_name:<list> header:<text>\n"
        "/lists name:<list>\n\n"
        "**Inline Timers**\n"
        "/add_timer_to_list list_name:<list> name:<timer> hours:<int> minutes:<int>\n\n"
        "**Standalone Timers**\n"
        "/create_timer name:<timer> hours:<int> minutes:<int> [role:<@role>]\n"
        "/pause_timer name:<timer>\n"
        "/resume_timer name:<timer>\n"
        "/delete_timer name:<timer>\n"
        "/resync_timers (admin) – force‑refresh all timer messages\n\n"
        "**Generator Timers**\n"
        "/create_gen_list name:<list>\n"
        "/add_gen tek list_name:<list> entry_name:<name> element:<int> shards:<int>\n"
        "/add_gen electrical list_name:<list> entry_name:<name> gas:<int> imbued:<int>\n"
        "/edit_gen list_name:<list> old_name:<old> [--new_name:<new>] [--gen_type:<Tek|Electrical>] "
        "[--element:<int>] [--shards:<int>] [--gas:<int>] [--imbued:<int>]\n"
        "/remove_gen list_name:<list> name:<entry>\n"
        "/delete_gen_list name:<list>\n"
        "/set_gen_role list_name:<list> role:<@role>\n"
        "/list_gen_lists (admin)\n"
        "/resync_gens (admin) – force‑refresh all generator dashboards\n\n"
        "**Utilities**\n"
        "/list_all (admin) – lists all regular & generator lists\n"
        "/help – shows this message"
    )
    await interaction.response.send_message(help_text, ephemeral=True)

bot.run(TOKEN)
