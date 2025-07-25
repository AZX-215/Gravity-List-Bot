
import os
import discord
from discord.ext import commands
from discord import app_commands
from data_manager import (
    load_list,
    save_list,
    add_to_list,
    edit_entry,
    remove_entry,
    delete_list,
    list_exists,
    save_dashboard_id,
    get_dashboard_id,
    get_all_dashboards,
    get_list_hash
)
from dotenv import load_dotenv
import asyncio

print("🔧 bot.py v5 (with access handling & Owner category) is loading…")
load_dotenv()

TOKEN     = os.getenv("DISCORD_TOKEN")
CLIENT_ID = int(os.getenv("CLIENT_ID"))

intents = discord.Intents.default()
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents, application_id=CLIENT_ID)

CATEGORY_EMOJIS = {
    "Enemy":  "🔴",
    "Friend": "🟢",
    "Ally":   "🔵",
    "Bob":    "🟡",
    "Owner":  "👑"
}

def build_embed(list_name: str) -> discord.Embed:
    data = load_list(list_name)
    embed = discord.Embed(title=f"{list_name} List", color=0x808080)
    for item in data:
        emoji = CATEGORY_EMOJIS.get(item["category"], "")
        embed.add_field(name=f"{emoji} {item['name']}", value=" ", inline=False)
    return embed

async def update_dashboard(list_name: str, interaction: discord.Interaction):
    dash = get_dashboard_id(list_name)
    if not dash:
        return
    channel_id, message_id = dash
    channel = interaction.guild.get_channel(channel_id)
    if channel is None:
        return
    try:
        msg = await channel.fetch_message(message_id)
        embed = build_embed(list_name)
        await msg.edit(embed=embed)
    except (discord.NotFound, discord.Forbidden):
        # Cannot access or message missing; skip
        return

# Background task for auto-updating dashboards
last_hashes = {}
async def background_updater():
    await bot.wait_until_ready()
    while not bot.is_closed():
        dashboards = get_all_dashboards()
        for list_name, dash in dashboards.items():
            current_hash = get_list_hash(list_name)
            if last_hashes.get(list_name) != current_hash:
                last_hashes[list_name] = current_hash
                channel = bot.get_channel(dash["channel_id"])
                if not channel:
                    continue
                try:
                    msg = await channel.fetch_message(dash["message_id"])
                    embed = build_embed(list_name)
                    await msg.edit(embed=embed)
                    print(f"🔁 Auto-updated dashboard for '{list_name}'")
                except discord.Forbidden:
                    print(f"🚫 No access to channel {channel.id} for '{list_name}', skipping auto-update")
                except discord.NotFound:
                    # Message might have been deleted
                    continue
        await asyncio.sleep(60)

@bot.event
async def on_ready():
    synced = await bot.tree.sync()
    print(f"🔄 Synced {len(synced)} global commands")
    print(f"✅ Bot is ready as {bot.user}")
    bot.loop.create_task(background_updater())

# ... rest of commands unchanged ...
