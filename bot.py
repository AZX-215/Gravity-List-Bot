
import os
import time
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import asyncio

from data_manager import (
    load_list, save_list, list_exists, delete_list, get_all_list_names,
    load_gen_list, save_gen_list, gen_list_exists, delete_gen_list, get_all_gen_list_names,
    add_to_gen_list,
    save_dashboard_id, get_dashboard_id, get_all_dashboards, get_list_hash,
    save_gen_dashboard_id, get_gen_dashboard_id, get_all_gen_dashboards, get_gen_list_hash
)
from timers import setup as setup_timers

print("🔧 bot.py v14 (unified `/lists`) loading…")
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
CLIENT_ID = int(os.getenv("CLIENT_ID"))

intents = discord.Intents.default()
intents.guilds = True
bot = commands.Bot(command_prefix="!", intents=intents, application_id=CLIENT_ID)

CATEGORY_EMOJIS = {"Owner":"👑","Enemy":"🔴","Friend":"🟢","Ally":"🔵","Bob":"🟡"}
GEN_EMOJIS = {"Tek":"🔄","Electrical":"⛽"}

def build_embed(list_name: str) -> discord.Embed:
    data = load_list(list_name)
    embed = discord.Embed(title=f"{list_name} List", color=0x808080)
    for item in data:
        emoji = CATEGORY_EMOJIS.get(item["category"], "")
        embed.add_field(name=f"{emoji} {item['name']}", value=" ", inline=False)
    return embed

def build_gen_embed(list_name: str) -> discord.Embed:
    data = load_gen_list(list_name)
    embed = discord.Embed(title=f"{list_name} Generators", color=0x404040)
    now = time.time()
    for item in data:
        emoji = GEN_EMOJIS.get(item["type"], "")
        if item["type"] == "Tek":
            duration = item["element"]*18*3600 + item["shards"]*600
        else:
            duration = item["gas"]*3600 + item["imbued"]*4*3600
        start = item["timestamp"]
        remaining = max(0, int(start + duration - now))
        hrs, rem = divmod(remaining, 3600)
        mins, secs = divmod(rem, 60)
        timer_str = f"{hrs:02d}h {mins:02d}m {secs:02d}s"
        embed.add_field(name=f"{emoji} {item['name']}", value=timer_str, inline=False)
    return embed

async def background_updater():
    await bot.wait_until_ready()
    std_hashes, gen_hashes = {}, {}
    while not bot.is_closed():
        for name, dash in get_all_dashboards().items():
            h = get_list_hash(name)
            if std_hashes.get(name) != h:
                std_hashes[name] = h
                ch = bot.get_channel(dash["channel_id"])
                if ch:
                    try:
                        msg = await ch.fetch_message(dash["message_id"])
                        await msg.edit(embed=build_embed(name))
                    except:
                        pass
        for name, dash in get_all_gen_dashboards().items():
            h = get_gen_list_hash(name)
            if gen_hashes.get(name) != h:
                gen_hashes[name] = h
                ch = bot.get_channel(dash["channel_id"])
                if ch:
                    try:
                        msg = await ch.fetch_message(dash["message_id"])
                        await msg.edit(embed=build_gen_embed(name))
                    except:
                        pass
        await asyncio.sleep(5)

@bot.event
async def on_ready():
    await setup_timers(bot)
    await bot.tree.sync()
    print(f"🔄 Synced commands for {bot.user}")
    bot.loop.create_task(background_updater())

# ---- List Commands ----
@bot.tree.command(name="create_list", description="Create a new list")
@app_commands.describe(name="Name of the new list")
async def create_list(interaction: discord.Interaction, name: str):
    if list_exists(name):
        return await interaction.response.send_message(f"⚠️ '{name}' exists", ephemeral=True)
    save_list(name, [])
    await interaction.response.send_message(f"✅ Created list '{name}'", ephemeral=True)

# ... [the rest of the v14 content] ...

bot.run(TOKEN)
