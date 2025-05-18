import os
import discord
from discord import app_commands
from discord.app_commands import check, CheckFailure
from discord.ext import commands
from discord.ui import View, Select
from data_manager import DataManager
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
CLIENT_ID = int(os.getenv('CLIENT_ID'))
DATA_PATH = os.getenv('DATABASE_PATH', 'lists/data.json')

intents = discord.Intents.default()
intents.guilds = True

bot = commands.Bot(command_prefix='!', intents=intents, application_id=CLIENT_ID)
data = DataManager(DATA_PATH)

# Category config: emoji and embed color
CATEGORY_EMOJI_COLOR = {
    'Enemy': ('🔴', discord.Color.red()),
    'Friend': ('🟢', discord.Color.green()),
    'Ally':  ('🔵', discord.Color.blue()),
    'Bob':   ('🟡', discord.Color.gold()),
}

class CategorySelect(Select):
    def __init__(self, list_name, entry):
        options = [
            discord.SelectOption(label=cat, description=f"Add as {cat}", emoji=emoji)
            for cat, (emoji, _) in CATEGORY_EMOJI_COLOR.items()
        ]
        super().__init__(placeholder="Pick a category...", min_values=1, max_values=1, options=options)
        self.list_name = list_name
        self.entry = entry

    async def callback(self, interaction: discord.Interaction):
        category = self.values[0]
        guild_id = str(interaction.guild.id)
        # Save entry
        data.add_entry(guild_id, self.list_name, self.entry, category)
        # Update static dashboard
        list_obj = data.get_list(guild_id, self.list_name)
        entries = list_obj['entries']
        emoji, color = CATEGORY_EMOJI_COLOR.get(category, ('⚪', discord.Color.light_grey()))
        formatted = "\n".join(f"{CATEGORY_EMOJI_COLOR[e['category']][0]} {e['entry']}" for e in entries)
        embed = discord.Embed(title=f"{self.list_name} List", description=formatted, color=color)
        embed.set_footer(text=f"{len(entries)} entries")
        # Send or edit dashboard message
        if list_obj['message_id'] and list_obj['channel_id']:
            channel = bot.get_channel(list_obj['channel_id'])
            try:
                msg = await channel.fetch_message(list_obj['message_id'])
                await msg.edit(embed=embed)
            except:
                msg = await interaction.channel.send(embed=embed)
                data.set_message_metadata(guild_id, self.list_name, interaction.channel.id, msg.id)
        else:
            msg = await interaction.channel.send(embed=embed)
            data.set_message_metadata(guild_id, self.list_name, interaction.channel.id, msg.id)
        await interaction.response.send_message(f"Added **{self.entry}** as **{category}**.", ephemeral=True)
        self.view.stop()

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")

@bot.tree.command(name='create_list', description='Create a new list')
@check(lambda inter: inter.user.guild_permissions.manage_guild)
async def slash_create_list(interaction: discord.Interaction, name: str):
    guild_id = str(interaction.guild.id)
    if not data.create_list(guild_id, name):
        return await interaction.response.send_message('List exists or bot not initialized.', ephemeral=True)
    await interaction.response.send_message(f'✅ Created list **{name}**.', ephemeral=True)

@slash_create_list.error
async def on_create_error(interaction, error):
    if isinstance(error, CheckFailure):
        await interaction.response.send_message('❌ Manage Server permission required.', ephemeral=True)

@bot.tree.command(name='add_name', description='Add a name and categorize')
async def slash_add_name(interaction: discord.Interaction, list_name: str, entry: str):
    guild_id = str(interaction.guild.id)
    if not data.get_list(guild_id, list_name):
        return await interaction.response.send_message('List not found. Create with /create_list.', ephemeral=True)
    view = View(timeout=60)
    view.add_item(CategorySelect(list_name, entry))
    await interaction.response.send_message(f'Choose category for **{entry}**:', view=view, ephemeral=True)

@bot.tree.command(name='list', description='Show or create dashboard for a list')
async def slash_list(interaction: discord.Interaction, list_name: str):
    guild_id = str(interaction.guild.id)
    list_obj = data.get_list(guild_id, list_name)
    if not list_obj:
        return await interaction.response.send_message('List not found. Create with /create_list.', ephemeral=True)
    entries = list_obj['entries']
    # Determine embed color based on first category or default
    # If list contains mixed categories, default to grey
    unique_cats = {e['category'] for e in entries}
    if len(unique_cats) == 1 and unique_cats.pop() in CATEGORY_EMOJI_COLOR:
        _, color = CATEGORY_EMOJI_COLOR[entries[0]['category']]
    else:
        color = discord.Color.light_grey()
    formatted = "\n".join(f"{CATEGORY_EMOJI_COLOR[e['category']][0]} {e['entry']}" for e in entries) or 'No entries yet.'
    embed = discord.Embed(title=f"{list_name} List", description=formatted, color=color)
    embed.set_footer(text=f"{len(entries)} entries")
    # Static dashboard behavior
    if list_obj['message_id'] and list_obj['channel_id']:
        channel = bot.get_channel(list_obj['channel_id'])
        try:
            msg = await channel.fetch_message(list_obj['message_id'])
            await msg.edit(embed=embed)
        except:
            msg = await interaction.channel.send(embed=embed)
            data.set_message_metadata(guild_id, list_name, interaction.channel.id, msg.id)
    else:
        msg = await interaction.channel.send(embed=embed)
        data.set_message_metadata(guild_id, list_name, interaction.channel.id, msg.id)
    await interaction.response.send_message('Dashboard updated!', ephemeral=True)

if __name__ == '__main__':
    bot.run(TOKEN)
