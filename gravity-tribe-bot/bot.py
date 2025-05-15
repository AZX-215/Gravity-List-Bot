import os
import discord
from discord import app_commands
from discord.ext import commands
from tribe_manager import TribeManager

# Load from environment variables
TOKEN = os.getenv('DISCORD_TOKEN')
ALLOWED_ROLE_IDS = [int(x) for x in os.getenv('ALLOWED_ROLE_IDS','').split(',') if x]
GUILD_ID = int(os.getenv('GUILD_ID', '0'))
TEST_GUILD = discord.Object(id=GUILD_ID) if GUILD_ID else None

# Setup bot
intents = discord.Intents.default()
intents.guilds = True
intents.guild_messages = True
bot = commands.Bot(command_prefix='!', intents=intents)
tribe_manager = TribeManager()

# Mapping categories to emojis and diff prefixes
CATEGORY_DATA = {
    'friend': {'emoji': '🟢', 'prefix': '+'},
    'enemy':  {'emoji': '🔴', 'prefix': '-'},
    'ally':   {'emoji': '🔵', 'prefix': ' '},
    'bob':    {'emoji': '🟡', 'prefix': '!'},
    None:     {'emoji': '▫️', 'prefix': ' '}
}

def has_allowed_role(interaction: discord.Interaction):
    return any(role.id in ALLOWED_ROLE_IDS for role in interaction.user.roles)

async def update_view_message(channel: discord.TextChannel):
    items = tribe_manager.get_items(channel.id, channel.name)
    lines = []
    for item in items:
        data = CATEGORY_DATA.get(item['category'], CATEGORY_DATA[None])
        emoji = data['emoji']
        prefix = data['prefix']
        name = item['name']
        if item['struck']:
            name = f'~~{name}~~'
        lines.append(f"{prefix} {emoji} {name}")
    formatted = '\n'.join(lines) or '(empty)'
    content = f"```diff\n{formatted}\n```"
    msg_id = tribe_manager.get_view_message(channel.id, channel.name)
    if msg_id:
        try:
            msg = await channel.fetch_message(msg_id)
            await msg.edit(content=content)
            return
        except:
            pass
    msg = await channel.send(content=content)
    tribe_manager.set_view_message(channel.id, channel.name, msg.id)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    # Sync commands to guild for instant availability
    if TEST_GUILD:
        await bot.tree.sync(guild=TEST_GUILD)
        print(f"Slash commands synced to guild {GUILD_ID}")
    else:
        await bot.tree.sync()
        print("Slash commands synced globally (may take up to 1 hour)")

# Slash commands with guild scoping
@bot.tree.command(guild=TEST_GUILD, name='create_list', description='Create tribe list for this channel')
async def create_list(interaction: discord.Interaction):
    if not has_allowed_role(interaction):
        return await interaction.response.send_message("No permission.", ephemeral=True)
    tribe_manager.create_list(interaction.channel_id, interaction.channel.name)
    await interaction.response.send_message("✅ Created list.", ephemeral=True)

@bot.tree.command(guild=TEST_GUILD, name='add_name', description='Add a name')
@app_commands.describe(name='Name to add')
async def add_name(interaction: discord.Interaction, name: str):
    if not has_allowed_role(interaction):
        return await interaction.response.send_message("No permission.", ephemeral=True)
    if not tribe_manager.list_exists(interaction.channel_id, interaction.channel.name):
        return await interaction.response.send_message("No list. Use /create_list", ephemeral=True)
    tribe_manager.add_name(interaction.channel_id, interaction.channel.name, name)
    await update_view_message(interaction.channel)
    await interaction.response.send_message(f"✅ Added `{name}`.", ephemeral=True)

@bot.tree.command(guild=TEST_GUILD, name='edit_name', description='Edit a name')
@app_commands.describe(old_name='Existing name', new_name='New name')
async def edit_name(interaction: discord.Interaction, old_name: str, new_name: str):
    if not has_allowed_role(interaction):
        return await interaction.response.send_message("No permission.", ephemeral=True)
    tribe_manager.edit_name(interaction.channel_id, interaction.channel.name, old_name, new_name)
    await update_view_message(interaction.channel)
    await interaction.response.send_message(f"✏️ `{old_name}` -> `{new_name}`.", ephemeral=True)

@bot.tree.command(guild=TEST_GUILD, name='remove_name', description='Remove a name')
@app_commands.describe(name='Name to remove')
async def remove_name(interaction: discord.Interaction, name: str):
    if not has_allowed_role(interaction):
        return await interaction.response.send_message("No permission.", ephemeral=True)
    tribe_manager.remove_name(interaction.channel_id, interaction.channel.name, name)
    await update_view_message(interaction.channel)
    await interaction.response.send_message(f"❌ Removed `{name}`.", ephemeral=True)

@bot.tree.command(guild=TEST_GUILD, name='strike_name', description='Toggle strikethrough')
@app_commands.describe(name='Name to toggle strikethrough')
async def strike_name(interaction: discord.Interaction, name: str):
    if not has_allowed_role(interaction):
        return await interaction.response.send_message("No permission.", ephemeral=True)
    tribe_manager.strike_name(interaction.channel_id, interaction.channel.name, name)
    await update_view_message(interaction.channel)
    await interaction.response.send_message(f"✅ Toggled strikethrough for `{name}`.", ephemeral=True)

@bot.tree.command(guild=TEST_GUILD, name='categorize_name', description='Categorize a name')
@app_commands.describe(name='Name to categorize', category='Category')
@app_commands.choices(category=[
    app_commands.Choice(name='Friend', value='friend'),
    app_commands.Choice(name='Enemy', value='enemy'),
    app_commands.Choice(name='Ally', value='ally'),
    app_commands.Choice(name='Bob', value='bob'),
])
async def categorize_name(interaction: discord.Interaction, name: str, category: str):
    if not has_allowed_role(interaction):
        return await interaction.response.send_message("No permission.", ephemeral=True)
    tribe_manager.categorize_name(interaction.channel_id, interaction.channel.name, name, category)
    await update_view_message(interaction.channel)
    await interaction.response.send_message(f"🏷️ `{name}` set to **{category}**.", ephemeral=True)

@bot.tree.command(guild=TEST_GUILD, name='view_list', description='View the list')
async def view_list(interaction: discord.Interaction):
    if not tribe_manager.list_exists(interaction.channel_id, interaction.channel.name):
        return await interaction.response.send_message("No list. Use /create_list", ephemeral=True)
    await update_view_message(interaction.channel)
    await interaction.response.send_message("✅ List displayed.", ephemeral=True)

@bot.tree.command(guild=TEST_GUILD, name='delete_list', description='Delete the list')
async def delete_list(interaction: discord.Interaction):
    if not has_allowed_role(interaction):
        return await interaction.response.send_message("No permission.", ephemeral=True)
    tribe_manager.delete_list(interaction.channel_id, interaction.channel.name)
    await interaction.response.send_message("🗑️ List deleted.", ephemeral=True)

bot.run(TOKEN)
