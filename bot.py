
import os
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import asyncio

from data_manager import (
    load_list, save_list, add_to_list, edit_entry, remove_entry,
    delete_list as dm_delete_list, list_exists, save_dashboard_id,
    get_dashboard_id, get_all_dashboards, get_list_hash
)
from timers import setup as setup_timers

print("🔧 bot.py v11 (descriptor fixes) loading…")
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
    if not dash:
        return
    channel_id, message_id = dash
    channel = interaction.guild.get_channel(channel_id)
    if not channel:
        return
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
    # Register timer commands first
    await setup_timers(bot)
    # Sync all commands
    synced = await bot.tree.sync()
    print(f"🔄 Synced {len(synced)} commands")
    print(f"✅ Bot is ready as {bot.user}")
    bot.loop.create_task(background_updater())

# ---- List Commands ----

@bot.tree.command(name="create_list", description="Create a new list")
@app_commands.describe(name="Name of the new list")
async def create_list(interaction: discord.Interaction, name: str):
    if list_exists(name):
        return await interaction.response.send_message(f"⚠️ List '{name}' exists", ephemeral=True)
    save_list(name, [])
    await interaction.response.send_message(f"✅ List '{name}' created.", ephemeral=True)

@bot.tree.command(name="add_name", description="Add a name to a list")
@app_commands.describe(list_name="Which list to add to", name="Entry to add", category="Category")
@app_commands.choices(category=[
    app_commands.Choice(name="Enemy", value="Enemy"),
    app_commands.Choice(name="Friend", value="Friend"),
    app_commands.Choice(name="Ally", value="Ally"),
    app_commands.Choice(name="Bob", value="Bob"),
    app_commands.Choice(name="Owner", value="Owner")
])
async def add_name(interaction: discord.Interaction, list_name: str, name: str, category: app_commands.Choice[str]):
    if not list_exists(list_name):
        return await interaction.response.send_message(f"❌ List '{list_name}' not found", ephemeral=True)
    add_to_list(list_name, name, category.value)
    await interaction.response.send_message(f"✅ Added '{name}' as '{category.value}'", ephemeral=True)
    await update_dashboard(list_name, interaction)

@bot.tree.command(name="remove_name", description="Remove an entry from a list")
@app_commands.describe(list_name="Which list", name="Entry to remove")
async def remove_name(interaction: discord.Interaction, list_name: str, name: str):
    if not list_exists(list_name):
        return await interaction.response.send_message(f"❌ List '{list_name}' not found", ephemeral=True)
    remove_entry(list_name, name)
    await interaction.response.send_message(f"🗑️ Removed '{name}'", ephemeral=True)
    await update_dashboard(list_name, interaction)

@bot.tree.command(name="edit_name", description="Edit an entry's name and category")
@app_commands.describe(list_name="Which list", old_name="Existing entry", new_name="New entry", new_category="New category")
@app_commands.choices(new_category=[
    app_commands.Choice(name="Enemy", value="Enemy"),
    app_commands.Choice(name="Friend", value="Friend"),
    app_commands.Choice(name="Ally", value="Ally"),
    app_commands.Choice(name="Bob", value="Bob"),
    app_commands.Choice(name="Owner", value="Owner")
])
async def edit_name(interaction: discord.Interaction, list_name: str, old_name: str, new_name: str, new_category: app_commands.Choice[str]):
    if not list_exists(list_name):
        return await interaction.response.send_message(f"❌ List '{list_name}' not found", ephemeral=True)
    edit_entry(list_name, old_name, new_name, new_category.value)
    await interaction.response.send_message(f"✏️ Updated '{old_name}' to '{new_name}'", ephemeral=True)
    await update_dashboard(list_name, interaction)

@bot.tree.command(name="delete_list", description="Delete an entire list")
@app_commands.describe(list_name="List to delete")
async def delete_list_cmd(interaction: discord.Interaction, list_name: str):
    if not list_exists(list_name):
        return await interaction.response.send_message(f"❌ List '{list_name}' not found", ephemeral=True)
    dm_delete_list(list_name)
    await interaction.response.send_message(f"🗑️ Deleted list '{list_name}'", ephemeral=True)

@bot.tree.command(name="list", description="Show or create dashboard for a list")
@app_commands.describe(list_name="Which list to display")
async def list_dashboard(interaction: discord.Interaction, list_name: str):
    embed = build_embed(list_name)
    dash = get_dashboard_id(list_name)
    if not dash:
        await interaction.response.send_message(embed=embed)
        msg = await interaction.original_response()
        save_dashboard_id(list_name, msg.channel.id, msg.id)
    else:
        channel_id, message_id = dash
        channel = interaction.guild.get_channel(channel_id)
        try:
            msg = await channel.fetch_message(message_id)
            await msg.edit(embed=embed)
            await interaction.response.send_message("✅ Dashboard updated.", ephemeral=True)
        except (discord.NotFound, discord.Forbidden):
            await interaction.response.send_message(embed=embed)
            msg = await interaction.original_response()
            save_dashboard_id(list_name, msg.channel.id, msg.id)

@bot.tree.command(name="help", description="Show usage instructions")
async def help_command(interaction: discord.Interaction):
    help_text = (
        "**Gravity List Bot Commands**\n"
        "/create_list name:<list>\n"
        "/add_name list_name:<list> name:<entry> category:<cat>\n"
        "/remove_name list_name:<list> name:<entry>\n"
        "/edit_name list_name:<list> old_name:<old> new_name:<new> new_category:<cat>\n"
        "/delete_list list_name:<list>\n"
        "/list list_name:<list>\n"
        "/create_timer name:<timer> hours:<int> minutes:<int>\n"
        "/help\n"
    )
    await interaction.response.send_message(help_text, ephemeral=True)

bot.run(TOKEN)
