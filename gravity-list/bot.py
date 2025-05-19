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
    delete_list as dm_delete_list,
    list_exists
)
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
CLIENT_ID = int(os.getenv('CLIENT_ID'))
GUILD_ID = int(os.getenv('GUILD_ID'))

intents = discord.Intents.default()
intents.guilds = True

bot = commands.Bot(command_prefix='!', intents=intents, application_id=CLIENT_ID)

CATEGORY_EMOJIS = {
    "Enemy": "🔴",
    "Friend": "🟢",
    "Ally": "🔵",
    "Bob": "🟡"
}

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    # Clear global commands to avoid duplicates
    bot.tree.clear_commands()  
    # Sync commands to guild only
    guild = discord.Object(id=GUILD_ID)
    synced = await bot.tree.sync(guild=guild)
    print(f"Synced {len(synced)} commands to guild {GUILD_ID}")

# (Rest of your command definitions remain unchanged)
