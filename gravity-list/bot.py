import os
import discord
from discord import app_commands
from discord.app_commands import check, CheckFailure
from discord.ext import commands
from data_manager import DataManager
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
CLIENT_ID = int(os.getenv('CLIENT_ID'))
DATA_PATH = os.getenv('DATABASE_PATH', 'lists/data.json')

# Configure intents: only guilds intent needed for slash commands
intents = discord.Intents.default()
intents.guilds = True

# Initialize bot
bot = commands.Bot(command_prefix='!', intents=intents, application_id=CLIENT_ID)
data = DataManager(DATA_PATH)

# Category configuration: emoji and embed color
CATEGORY_CONFIG = {
    'enemy': ('🔴', discord.Color.red()),
    'friend': ('🟢', discord.Color.green()),
    'ally': ('🔵', discord.Color.blue()),
    'bob': ('🟡', discord.Color.gold()),
}

def get_category_style(category: str):
    # Return (emoji, color) for the given category, with defaults.
    key = category.lower()
    return CATEGORY_CONFIG.get(key, ('⚪', discord.Color.light_grey()))

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')

# Admin-only create_list
@bot.tree.command(name='create_list', description='Create a new list category')
@check(lambda inter: inter.user.guild_permissions.manage_guild)
@app_commands.describe(name='Name of the list category to create')
async def slash_create_list(interaction: discord.Interaction, name: str):
    guild_id = str(interaction.guild.id)
    if not data.initialize_guild(guild_id):
        return await interaction.response.send_message(
            'List already exists or bot not initialized.', ephemeral=True)
    data.db[guild_id].setdefault('lists', {})[name] = []
    data._save()
    await interaction.response.send_message(
        f'✅ Created category **{name}**.', ephemeral=True)

@slash_create_list.error
async def slash_create_list_error(interaction: discord.Interaction, error):
    if isinstance(error, CheckFailure):
        await interaction.response.send_message(
            '❌ You need Manage Server permission to use this.', ephemeral=True)

# Add entry to list with emoji prefix
@bot.tree.command(name='add', description='Add an entry to a category list')
@app_commands.describe(category='Category name', entry='Entry to add')
async def slash_add(interaction: discord.Interaction, category: str, entry: str):
    guild_id = str(interaction.guild.id)
    if not data.guild_exists(guild_id):
        return await interaction.response.send_message(
            'Please run /create_list first.', ephemeral=True)
    lists = data.db[guild_id].get('lists', {})
    if category not in lists:
        return await interaction.response.send_message(
            f'Category **{category}** does not exist.', ephemeral=True)
    lists[category].append(entry)
    data._save()
    emoji, color = get_category_style(category)
    embed = discord.Embed(
        title=f"Added to {category}",
        description=f"{emoji} {entry}",
        color=color
    )
    await interaction.response.send_message(embed=embed)

# Show entries in list with embed and emojis
@bot.tree.command(name='list', description='Show entries in a category')
@app_commands.describe(category='Category name')
async def slash_list(interaction: discord.Interaction, category: str):
    guild_id = str(interaction.guild.id)
    if not data.guild_exists(guild_id):
        return await interaction.response.send_message(
            'Please run /create_list first.', ephemeral=True)
    entries = data.db[guild_id].get('lists', {}).get(category, [])
    if not entries:
        return await interaction.response.send_message(
            f'No entries in **{category}**.', ephemeral=True)
    emoji, color = get_category_style(category)
    formatted = '\n'.join(f"{emoji} {e}" for e in entries)
    embed = discord.Embed(
        title=f"{category.capitalize()} List",
        description=formatted,
        color=color
    )
    embed.set_footer(text=f"{len(entries)} entries")
    await interaction.response.send_message(embed=embed)

if __name__ == '__main__':
    bot.run(TOKEN)
