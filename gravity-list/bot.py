import os
import discord
from discord import app_commands
from discord.ext import commands
from data_manager import DataManager
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
CLIENT_ID = int(os.getenv('CLIENT_ID'))
DATA_PATH = os.getenv('DATABASE_PATH', 'lists/data.json')

# Configure intents: no Message Content needed for slash commands
intents = discord.Intents.default()
intents.guilds = True

# Provide a dummy prefix for commands.Bot even if not used
bot = commands.Bot(command_prefix='!', intents=intents, application_id=CLIENT_ID)
data = DataManager(DATA_PATH)

@bot.event
async def on_ready():
    # Sync commands globally
    await bot.tree.sync()
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')

# Admin-only create_list command visible only to Manage Server roles
@bot.tree.command(
    name='create_list',
    description='Create a new list for Gravity List',
    default_member_permissions=discord.Permissions(manage_guild=True)
)
@app_commands.describe(name='Name of the list to create')
async def slash_create_list(interaction: discord.Interaction, name: str):
    guild_id = str(interaction.guild.id)
    if not data.initialize_guild(guild_id):
        return await interaction.response.send_message('List already exists or bot not initialized.', ephemeral=True)
    # Ensure 'lists' structure exists
    data.db[guild_id].setdefault('lists', {})[name] = []
    data._save()
    await interaction.response.send_message(f'✅ Created list **{name}**.', ephemeral=False)

@bot.tree.command(name='add', description='Add an entry to a list')
@app_commands.describe(list_name='List to add to', entry='Entry to add')
async def slash_add(interaction: discord.Interaction, list_name: str, entry: str):
    guild_id = str(interaction.guild.id)
    if not data.guild_exists(guild_id):
        return await interaction.response.send_message('Please run /create_list first.', ephemeral=True)
    lists = data.db[guild_id].get('lists', {})
    if list_name not in lists:
        return await interaction.response.send_message(f'List **{list_name}** does not exist.', ephemeral=True)
    lists[list_name].append(entry)
    data._save()
    await interaction.response.send_message(f'Added **{entry}** to **{list_name}**.')

@bot.tree.command(name='list', description='Show entries in a list')
@app_commands.describe(list_name='List to display')
async def slash_list(interaction: discord.Interaction, list_name: str):
    guild_id = str(interaction.guild.id)
    if not data.guild_exists(guild_id):
        return await interaction.response.send_message('Please run /create_list first.', ephemeral=True)
    entries = data.db[guild_id].get('lists', {}).get(list_name, [])
    if entries:
        formatted = '\n'.join(f'- {e}' for e in entries)
        await interaction.response.send_message(formatted)
    else:
        await interaction.response.send_message(f'No entries in **{list_name}**.', ephemeral=True)

if __name__ == '__main__':
    bot.run(TOKEN)
