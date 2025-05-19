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
    guild = discord.Object(id=GUILD_ID)
    await bot.tree.sync(guild=guild)
    print(f"Logged in as {bot.user} and synced commands to guild {GUILD_ID}")

@bot.tree.command(name="create_list", description="Create a new list", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(name="Name of the list")
async def create_list(interaction: discord.Interaction, name: str):
    if list_exists(name):
        return await interaction.response.send_message(f"⚠️ List `{name}` already exists.", ephemeral=True)
    save_list(name, [])
    await interaction.response.send_message(f"✅ List `{name}` created.", ephemeral=True)

@bot.tree.command(name="add_name", description="Add a name to a list", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(list_name="Which list", name="Name to add", category="Category")
@app_commands.choices(category=[
    app_commands.Choice(name="Enemy", value="Enemy"),
    app_commands.Choice(name="Friend", value="Friend"),
    app_commands.Choice(name="Ally", value="Ally"),
    app_commands.Choice(name="Bob", value="Bob")
])
async def add_name(interaction: discord.Interaction, list_name: str, name: str, category: app_commands.Choice[str]):
    if not list_exists(list_name):
        return await interaction.response.send_message(f"❌ List `{list_name}` not found.", ephemeral=True)
    add_to_list(list_name, name, category.value)
    await interaction.response.send_message(f"✅ {CATEGORY_EMOJIS[category.value]} `{name}` as `{category.value}` to `{list_name}`.", ephemeral=True)
    await show_list(interaction, list_name)

@bot.tree.command(name="remove_name", description="Remove a name from a list", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(list_name="Which list", name="Name to remove")
async def remove_name(interaction: discord.Interaction, list_name: str, name: str):
    if not list_exists(list_name):
        return await interaction.response.send_message(f"❌ List `{list_name}` not found.", ephemeral=True)
    remove_entry(list_name, name)
    await interaction.response.send_message(f"🗑️ Removed `{name}` from `{list_name}`.", ephemeral=True)
    await show_list(interaction, list_name)

@bot.tree.command(name="edit_name", description="Edit a name and its category", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(list_name="Which list", old_name="Existing name", new_name="New name", new_category="New category")
@app_commands.choices(new_category=[
    app_commands.Choice(name="Enemy", value="Enemy"),
    app_commands.Choice(name="Friend", value="Friend"),
    app_commands.Choice(name="Ally", value="Ally"),
    app_commands.Choice(name="Bob", value="Bob")
])
async def edit_name(interaction: discord.Interaction, list_name: str, old_name: str, new_name: str, new_category: app_commands.Choice[str]):
    if not list_exists(list_name):
        return await interaction.response.send_message(f"❌ List `{list_name}` not found.", ephemeral=True)
    edit_entry(list_name, old_name, new_name, new_category.value)
    await interaction.response.send_message(f"✏️ Updated `{old_name}` to `{new_name}` as `{new_category.value}`.", ephemeral=True)
    await show_list(interaction, list_name)

@bot.tree.command(name="delete_list", description="Delete an entire list", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(name="Which list")
async def delete_list_cmd(interaction: discord.Interaction, name: str):
    if not list_exists(name):
        return await interaction.response.send_message(f"⚠️ List `{name}` does not exist.", ephemeral=True)
    dm_delete_list(name)
    await interaction.response.send_message(f"🗑️ Deleted list `{name}`.", ephemeral=True)

@bot.tree.command(name="list", description="Show entries in a list", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(name="Which list")
async def show_list(interaction: discord.Interaction, name: str):
    data = load_list(name)
    if not data:
        return await interaction.response.send_message(f"📭 List `{name}` is empty or doesn't exist.", ephemeral=True)
    embed = discord.Embed(title=f"{name} List", color=0x808080)
    for item in data:
        emoji = CATEGORY_EMOJIS.get(item['category'], '')
        embed.add_field(name=f"{emoji} {item['name']}", value="‎", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="help", description="Show usage instructions", guild=discord.Object(id=GUILD_ID))
async def help_command(interaction: discord.Interaction):
    help_text = (
        "**Gravity List Bot Help**\n\n"
        "/create_list name:<list> – create a new list.\n"
        "/add_name list_name:<list> name:<entry> category:<cat> – add a name.\n"
        "/remove_name list_name:<list> name:<entry> – remove a name.\n"
        "/edit_name list_name:<list> old_name:<old> new_name:<new> new_category:<cat> – edit an entry.\n"
        "/delete_list name:<list> – delete the list.\n"
        "/list name:<list> – show or refresh dashboard.\n"
        "/help – show this message."
    )
    await interaction.response.send_message(help_text, ephemeral=True)

bot.run(TOKEN)
