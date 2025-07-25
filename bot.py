
import os
import discord
from discord.ext import commands
from discord import app_commands
from data_manager import (
    load_list, save_list, add_to_list, edit_entry, remove_entry,
    delete_list, list_exists, save_dashboard_id, get_dashboard_id,
    get_all_dashboards, get_list_hash
)
from dotenv import load_dotenv
import asyncio

# Import setup from timers
from timers import setup as setup_timers

print("🔧 bot.py v10 (await add_cog) loading…")
load_dotenv()

TOKEN     = os.getenv("DISCORD_TOKEN")
CLIENT_ID = int(os.getenv("CLIENT_ID"))
print("🔑 TOKEN loaded?", bool(TOKEN), "CLIENT_ID loaded?", bool(CLIENT_ID))

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
    if not dash: return
    channel_id, message_id = dash
    channel = interaction.guild.get_channel(channel_id)
    if not channel: return
    try:
        msg = await channel.fetch_message(message_id)
        await msg.edit(embed=build_embed(list_name))
    except (discord.NotFound, discord.Forbidden):
        pass

async def background_updater():
    last_hashes = {}
    await bot.wait_until_ready()
    while not bot.is_closed():
        for list_name, dash in get_all_dashboards().items():
            current = get_list_hash(list_name)
            if last_hashes.get(list_name) != current:
                last_hashes[list_name] = current
                channel = bot.get_channel(dash["channel_id"])
                if channel:
                    try:
                        msg = await channel.fetch_message(dash["message_id"])
                        await msg.edit(embed=build_embed(list_name))
                    except (discord.NotFound, discord.Forbidden):
                        pass
        await asyncio.sleep(60)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"🔄 Synced {len(bot.tree.get_commands())} commands")
    print(f"✅ Bot is ready as {bot.user}")
    bot.loop.create_task(background_updater())
    # Await adding the TimerCog properly
    await setup_timers(bot)

# ---- List commands ----
@bot.tree.command(name="create_list", description="Create a new list")
@app_commands.describe(name="Name")
async def create_list(interaction: discord.Interaction, name: str):
    if list_exists(name):
        return await interaction.response.send_message(f"⚠️ List '{name}' exists", ephemeral=True)
    save_list(name, [])
    await interaction.response.send_message(f"✅ List '{name}' created.", ephemeral=True)

# ... rest of list commands identical ...

@bot.tree.command(name="help", description="Show usage instructions")
async def help_command(interaction: discord.Interaction):
    help_text = ("**Help**\n"
                 "/create_list name:<list>\n"
                 "/add_name list_name:<list> name:<entry> category:<cat>\n"
                 "/create_timer name:<timer> hours:<int> minutes:<int>\n"
                 "/help\n")
    await interaction.response.send_message(help_text, ephemeral=True)

bot.run(TOKEN)
