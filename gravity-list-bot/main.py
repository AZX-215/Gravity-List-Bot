import os
import discord
from discord.ext import commands
from data_manager import DataManager
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN not set in environment")

# Configure intents
intents = discord.Intents.default()
intents.guilds = True
intents.message_content = True  # only if needed

# Initialize bot
bot = commands.Bot(command_prefix='/', intents=intents)
data = DataManager(os.getenv('DATABASE_PATH', 'data.json'))

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')

@bot.command(name='setup')
@commands.has_guild_permissions(administrator=True)
async def setup(ctx):
    guild_id = str(ctx.guild.id)
    if data.initialize_guild(guild_id):
        await ctx.send('✅ Gravity List initialized for this server.')
    else:
        await ctx.send('⚠️ Gravity List is already initialized here.')

@bot.command(name='add')
async def add_name(ctx, category: str, *, name: str):
    guild_id = str(ctx.guild.id)
    if not data.guild_exists(guild_id):
        await ctx.send('Please run `/setup` first.', ephemeral=True)
        return
    data.add_name(guild_id, category, name)
    await ctx.send(f'Added **{name}** to category **{category}**.')

@bot.command(name='list')
async def list_names(ctx, category: str):
    guild_id = str(ctx.guild.id)
    if not data.guild_exists(guild_id):
        await ctx.send('Please run `/setup` first.', ephemeral=True)
        return
    names = data.get_names(guild_id, category)
    if names:
        formatted = '\n'.join(f'- {n}' for n in names)
        await ctx.send(f'**{category.capitalize()}**:\n{formatted}')
    else:
        await ctx.send(f'No entries found in **{category}**.')

@setup.error
async def setup_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send('❌ You need Administrator permission to run this.', ephemeral=True)

if __name__ == '__main__':
    bot.run(TOKEN)
