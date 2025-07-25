
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

print("🔧 bot.py v4 (with auto-update & Owner category) is loading…")
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
    except discord.NotFound:
        pass

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
                if channel:
                    try:
                        msg = await channel.fetch_message(dash["message_id"])
                        embed = build_embed(list_name)
                        await msg.edit(embed=embed)
                        print(f"🔁 Auto-updated dashboard for '{list_name}'")
                    except discord.NotFound:
                        continue
        await asyncio.sleep(60)  # Poll every minute

@bot.event
async def on_ready():
    synced = await bot.tree.sync()
    print(f"🔄 Synced {len(synced)} global commands")
    print(f"✅ Bot is ready as {bot.user}")
    bot.loop.create_task(background_updater())

@bot.tree.command(name="create_list", description="Create a new list")
@app_commands.describe(name="Name of the new list")
async def create_list(interaction: discord.Interaction, name: str):
    if list_exists(name):
        return await interaction.response.send_message(f"⚠️ List '{name}' exists", ephemeral=True)
    save_list(name, [])
    await interaction.response.send_message(f"✅ List '{name}' created.", ephemeral=True)

@bot.tree.command(name="add_name", description="Add a name to a list")
@app_commands.describe(list_name="Which list to add to", name="Name to add", category="Select category")
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
    await interaction.response.send_message(f"✅ Added '{name}' as '{category.value}' to '{list_name}'", ephemeral=True)
    await update_dashboard(list_name, interaction)

@bot.tree.command(name="remove_name", description="Remove a name from a list")
@app_commands.describe(list_name="Which list", name="Name to remove")
async def remove_name(interaction: discord.Interaction, list_name: str, name: str):
    if not list_exists(list_name):
        return await interaction.response.send_message(f"❌ List '{list_name}' not found", ephemeral=True)
    remove_entry(list_name, name)
    await interaction.response.send_message(f"🗑️ Removed '{name}' from '{list_name}'", ephemeral=True)
    await update_dashboard(list_name, interaction)

@bot.tree.command(name="edit_name", description="Edit a name and its category")
@app_commands.describe(list_name="Which list", old_name="Existing name", new_name="New name", new_category="Select new category")
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
    await interaction.response.send_message(f"✏️ Updated '{old_name}' to '{new_name}' as '{new_category.value}'", ephemeral=True)
    await update_dashboard(list_name, interaction)

@bot.tree.command(name="delete_list", description="Delete an entire list")
@app_commands.describe(name="Name of the list to delete")
async def delete_list_cmd(interaction: discord.Interaction, name: str):
    if not list_exists(name):
        return await interaction.response.send_message(f"⚠️ List '{name}' not found", ephemeral=True)
    delete_list(name)
    await interaction.response.send_message(f"🗑️ Deleted list '{name}'", ephemeral=True)

@bot.tree.command(name="list", description="Show or create dashboard for a list")
@app_commands.describe(name="Which list to display")
async def list_dashboard(interaction: discord.Interaction, name: str):
    embed = build_embed(name)
    dash = get_dashboard_id(name)
    if not dash:
        await interaction.response.send_message(embed=embed)
        msg = await interaction.original_response()
        save_dashboard_id(name, msg.channel.id, msg.id)
    else:
        channel_id, message_id = dash
        channel = interaction.guild.get_channel(channel_id)
        try:
            msg = await channel.fetch_message(message_id)
            await msg.edit(embed=embed)
            await interaction.response.send_message(f"✅ Dashboard for '{name}' updated.", ephemeral=True)
        except:
            await interaction.response.send_message(embed=embed)
            msg = await interaction.original_response()
            save_dashboard_id(name, msg.channel.id, msg.id)

@bot.tree.command(name="help", description="Show usage instructions")
async def help_command(interaction: discord.Interaction):
    help_text = ("**Gravity List Bot Help**\n\n"
                 "/create_list name:<list> – Create a list\n"
                 "/add_name list_name:<list> name:<entry> category:<cat> – Add a name\n"
                 "/remove_name list_name:<list> name:<entry> – Remove a name\n"
                 "/edit_name list_name:<list> old_name:<old> new_name:<new> new_category:<cat> – Edit a name\n"
                 "/delete_list name:<list> – Delete a list\n"
                 "/list name:<list> – Show or create dashboard\n"
                 "/help – Show this help")
    await interaction.response.send_message(help_text, ephemeral=True)

bot.run(TOKEN)
