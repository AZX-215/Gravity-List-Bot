import os
import discord
from discord import app_commands
from discord.ext import commands
from tribe_manager import TribeManager

# Load from env
TOKEN = os.getenv('DISCORD_TOKEN')
ALLOWED_ROLE_IDS = [int(x) for x in os.getenv('ALLOWED_ROLE_IDS', '').split(',') if x]

# Setup bot
intents = discord.Intents.default()
intents.guilds = True
intents.guild_messages = True
bot = commands.Bot(command_prefix='!', intents=intents)
tribe_manager = TribeManager()

# Mapping categories to diff prefixes and emojis
CATEGORY_DATA = {
    'friend': {'emoji': '🟢', 'prefix': '+'},
    'enemy':  {'emoji': '🔴', 'prefix': '-'},
    'ally':   {'emoji': '🔵', 'prefix': ' '},  # default white
    'bob':    {'emoji': '🟡', 'prefix': '!'},  # orange-ish via diff '!' hack
    None:     {'emoji': '▫️', 'prefix': ' '}   # uncolored
}

def has_allowed_role(interaction: discord.Interaction):
    return any(role.id in ALLOWED_ROLE_IDS for role in interaction.user.roles)

async def update_view_message(channel: discord.TextChannel):
    items = tribe_manager.get_items(channel.id, channel.name)
    lines = []
    for item in items:
        cat = item['category']
        data = CATEGORY_DATA.get(cat, CATEGORY_DATA[None])
        emoji = data['emoji']
        prefix = data['prefix']
        name = item['name']
        if item['struck']:
            name = f'~~{name}~~'
        # build diff line: prefix, space, emoji, space, name
        lines.append(f"{prefix} {emoji} {name}")
    formatted = '\n'.join(lines) or '(empty)'
    # wrap in diff code block for colored prefixes
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
    await bot.tree.sync()

# ... slash commands remain unchanged ...
# (create_list, add_name, edit_name, remove_name, strike_name, categorize_name, view_list, delete_list)

bot.run(TOKEN)
