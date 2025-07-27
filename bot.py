import os
import time
import discord
from discord.ext import commands, tasks
from discord import app_commands
from dotenv import load_dotenv

from data_manager import (
    load_list, save_list, list_exists, delete_list,
    get_all_list_names, get_all_gen_list_names,
    save_dashboard_id, get_dashboard_id,
    save_gen_dashboard_id, get_gen_dashboard_id,
    gen_list_exists
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
    now = time.time()
    # ensure proper ordering
    data.sort(key=lambda x: 1 if isinstance(x, dict) and x.get("category")=="Header"
                         else 3 if isinstance(x, dict) and x.get("category")=="Text"
                         else 2)
    for item in data:
        if not isinstance(item, dict):
            continue
        cat = item.get("category")
        if cat == "Header":
            embed.add_field(name="\u200b", value=f"**{item['name']}**", inline=False)
        elif cat == "Text":
            embed.add_field(name=f"• {item['name']}", value="\u200b", inline=False)
        elif cat == "Timer":
            end_ts = item.get("timer_end") or (item.get("timer_start",0)+item.get("timer_duration",0))
            rem = max(0, int(end_ts - now))
            d, rem_hr = divmod(rem,86400); h,r = divmod(rem_hr,3600); m,s=divmod(r,60)
            timestr = f"{d}d {h:02d}h {m:02d}m {s:02d}s" if d else f"{h:02d}h {m:02d}m {s:02d}s"
            embed.add_field(name=f"⏳   {item['name']} — {timestr}", value="\u200b", inline=False)
        else:
            prefix = CATEGORY_EMOJIS.get(cat,"")
            embed.add_field(name=f"{prefix}   {item['name']}", value="\u200b", inline=False)
            if item.get("comment"):
                embed.add_field(name="\u200b", value=f"*{item['comment']}*", inline=False)
    return embed

# ━━━━━━ Bot Setup ━━━━━━━━━━
@bot.event
async def on_ready():
    if not getattr(bot, "_setup_done", False):
        await setup_timers(bot)
        await setup_gen_timers(bot)
        list_dashboard_loop.start()
        await bot.tree.sync()
        bot._setup_done = True
        print(f"Bot ready. Commands synced for {bot.user}")
    else:
        print(f"Bot reconnected: {bot.user}")

# ━━━━━━ Periodic Inline-Timer Refresh ━━━━━━━━━━
@tasks.loop(seconds=3)
async def list_dashboard_loop():
    for name in get_all_list_names():
        data = load_list(name)
        if any(isinstance(i, dict) and i.get("category")=="Timer" for i in data):
            await push_list_update(name)

# ━━━━━━ Slash Commands ━━━━━━━━━━
@bot.tree.command(name="create_list", description="Create a new list")
@app_commands.describe(name="Name of the new list")
async def create_list(interaction: discord.Interaction, name: str):
    if list_exists(name):
        return await interaction.response.send_message(f"⚠️ List '{name}' exists.", ephemeral=True)
    save_list(name, [])
    await interaction.response.send_message(f"✅ Created list '{name}'.", ephemeral=True)

@bot.tree.command(name="add_name", description="Add an entry to a regular list")
@app_commands.describe(list_name="List name", name="Entry name", category="Category", comment="Optional comment")
@app_commands.choices(category=[app_commands.Choice(name=k, value=k) for k in CATEGORY_EMOJIS.keys()]+[app_commands.Choice(name="Text",value="Text"),app_commands.Choice(name="Header",value="Header"),app_commands.Choice(name="Timer",value="Timer")])
async def add_name(interaction, list_name: str, name: str, category: app_commands.Choice[str], comment: str=None):
    if not list_exists(list_name):
        return await interaction.response.send_message(f"❌ List '{list_name}' not found.", ephemeral=True)
    data = load_list(list_name)
    entry = {"name":name, "category":category.value}
    if category.value=="Timer":
        entry.update({"timer_start":time.time(),"timer_duration":3600})  # default 1h, user should use /add_timer_to_list
    if comment:
        entry["comment"]=comment
    data.append(entry); save_list(list_name,data)
    await interaction.response.send_message(f"✅ Added '{name}' to '{list_name}'.", ephemeral=True)
    await push_list_update(list_name)

@bot.tree.command(name="edit_name", description="Edit an entry in a regular list")
@app_commands.describe(list_name="List name", old_name="Current name", new_name="New name", new_category="New category", new_comment="New comment")
async def edit_name(interaction, list_name: str, old_name: str, new_name: str=None, new_category: str=None, new_comment: str=None):
    if not list_exists(list_name):
        return await interaction.response.send_message(f"❌ List '{list_name}' not found.", ephemeral=True)
    data=load_list(list_name)
    for item in data:
        if isinstance(item, dict) and item.get("name").lower()==old_name.lower():
            if new_name: item["name"]=new_name
            if new_category: item["category"]=new_category
            if new_comment is not None: item["comment"]=new_comment
            save_list(list_name,data)
            await interaction.response.send_message(f"✏️ Edited '{old_name}'.", ephemeral=True)
            await push_list_update(list_name)
            return
    await interaction.response.send_message(f"❌ Entry '{old_name}' not found.", ephemeral=True)

@bot.tree.command(name="remove_name", description="Remove an entry from a regular list")
@app_commands.describe(list_name="List name", name="Entry name")
async def remove_name(interaction, list_name: str, name: str):
    if not list_exists(list_name):
        return await interaction.response.send_message(f"❌ List '{list_name}' not found.", ephemeral=True)
    data=[i for i in load_list(list_name) if not(isinstance(i, dict) and i.get("name").lower()==name.lower())]
    save_list(list_name,data)
    await interaction.response.send_message(f"🗑️ Removed '{name}'.", ephemeral=True)
    await push_list_update(list_name)

@bot.tree.command(name="delete_list", description="Delete an entire regular list")
@app_commands.describe(name="List name")
async def delete_list_cmd(interaction, name: str):
    if not list_exists(name):
        return await interaction.response.send_message(f"❌ List '{name}' not found.", ephemeral=True)
    delete_list(name)
    await interaction.response.send_message(f"🗑️ Deleted list '{name}'.", ephemeral=True)

@bot.tree.command(name="add_text", description="Add a bullet note to a list")
@app_commands.describe(list_name="List name", text="Note text")
async def add_text(interaction, list_name: str, text: str):
    if not list_exists(list_name):
        return await interaction.response.send_message(f"❌ List '{list_name}' not found.", ephemeral=True)
    data=load_list(list_name)
    data.append({"name":text,"category":"Text"})
    save_list(list_name,data)
    await interaction.response.send_message(f"✅ Added note.", ephemeral=True)
    await push_list_update(list_name)

@bot.tree.command(name="add_header", description="Add a header to a list")
@app_commands.describe(list_name="List name", header="Header text")
async def add_header(interaction, list_name: str, header: str):
    if not list_exists(list_name):
        return await interaction.response.send_message(f"❌ List '{list_name}' not found.", ephemeral=True)
    data=load_list(list_name)
    data.append({"name":header,"category":"Header"})
    save_list(list_name,data)
    await interaction.response.send_message(f"✅ Added header.", ephemeral=True)
    await push_list_update(list_name)

@bot.tree.command(name="add_timer_to_list", description="Add a timer entry into a list")
@app_commands.describe(list_name="List name", name="Timer name", hours="Hours", minutes="Minutes")
async def add_timer_to_list(interaction, list_name: str, name: str, hours: int, minutes: int):
    if not list_exists(list_name):
        return await interaction.response.send_message(f"❌ List '{list_name}' not found.", ephemeral=True)
    duration = hours*3600 + minutes*60
    data=load_list(list_name)
    data.append({"name":name,"category":"Timer","timer_start":time.time(),"timer_duration":duration})
    save_list(list_name,data)
    await interaction.response.send_message(f"✅ Added timer to '{list_name}'.", ephemeral=True)
    await push_list_update(list_name)

@bot.tree.command(name="create_timer", description="Create a standalone timer")
@app_commands.describe(name="Timer name", hours="Hours", minutes="Minutes", role="Optional ping role")
async def create_timer(interaction, name: str, hours: int, minutes: int, role: discord.Role=None):
    await interaction.response.send_message("✅ Timer created (not implemented).", ephemeral=True)

# ... pause_timer, resume_timer, delete_timer, resync_timers left as is in timers.py ...

@bot.tree.command(name="lists", description="Show or deploy a list or generator dashboard")
@app_commands.describe(name="Name of the list")
async def lists_cmd(interaction, name: str):
    # Generator lists
    if gen_list_exists(name):
        embed = build_gen_dashboard_embed(name)
        await interaction.response.send_message(embed=embed)
        sent = await interaction.original_response()
        save_gen_dashboard_id(name, sent.channel.id, sent.id)
        return
    # Regular lists
    if list_exists(name):
        embed = build_embed(name)
        await interaction.response.send_message(embed=embed)
        sent = await interaction.original_response()
        save_dashboard_id(name, sent.channel.id, sent.id)
        return
    await interaction.response.send_message(f"❌ No list named '{name}'.", ephemeral=True)

@bot.tree.command(name="list_all", description="List all regular & generator lists (admin)")
async def list_all(interaction):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ Admin only.", ephemeral=True)
    regular = get_all_list_names()
    gen = get_all_gen_list_names()
    text = "**Regular lists:** " + (", ".join(regular) or "none") + "\n" + "**Generator lists:** " + (", ".join(gen) or "none")
    await interaction.response.send_message(text, ephemeral=True)

@bot.tree.command(name="help", description="Show usage instructions")
async def help_cmd(interaction):
    help_text = (
        "**Gravity List Bot**\n"
        "Use `/lists name:<list>` to deploy or update any list.\n"
        "For full commands see README.md."
    )
    await interaction.response.send_message(help_text, ephemeral=True)

bot.run(TOKEN)
