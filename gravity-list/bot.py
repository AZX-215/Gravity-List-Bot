help_text = """**Gravity List Bot – Help**

Gravity List Bot lets you organize and display static, categorized lists in your Discord server.

---

**🧾 Core Commands**
- `/create_list name:<list_name>`  
  Create a new list for categorized names.

- `/add_name list_name:<list> name:<entry>`  
  Add a name to a list. You'll select a category after.

- `/edit_name list_name:<list> old_name:<current> new_name:<new>`  
  Rename an entry and change its category.

- `/remove_name list_name:<list> name:<entry>`  
  Remove a specific name from a list.

- `/delete_list list_name:<list>`  
  Permanently delete a list and its dashboard (admin only).

- `/list list_name:<list>`  
  Re-post the dashboard embed for a list.

---

**📋 Categories**
Each name gets a colored emoji and category:
- 🔴 Enemy
- 🟢 Friend
- 🔵 Ally
- 🟡 Bob

The dashboard updates automatically with colors and counts.

---

**ℹ️ Notes**
- Only one dashboard per list is tracked.
- Lists are saved persistently per server.
"""

import os
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Select
from data_manager import DataManager
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
CLIENT_ID = int(os.getenv('CLIENT_ID'))
GUILD_ID = int(os.getenv('GUILD_ID'))  # Add your guild ID in .env
DATA_PATH = os.getenv('DATABASE_PATH', 'lists/data.json')

intents = discord.Intents.default()
intents.guilds = True

bot = commands.Bot(command_prefix='!', intents=intents, application_id=CLIENT_ID)
data = DataManager(DATA_PATH)

CATEGORY_EMOJI_COLOR = {
    'Enemy': ('🔴', discord.Color.red()),
    'Friend': ('🟢', discord.Color.green()),
    'Ally': ('🔵', discord.Color.blue()),
    'Bob': ('🟡', discord.Color.gold()),
}
GRAY = discord.Color.light_grey()

class CategorySelect(Select):
    def __init__(self, list_name, entry, old_entry=None):
        options = [
            discord.SelectOption(label=cat, description=f"Choose {cat}", emoji=emoji)
            for cat, (emoji, _) in CATEGORY_EMOJI_COLOR.items()
        ]
        super().__init__(placeholder="Select category...", min_values=1, max_values=1, options=options)
        self.list_name = list_name
        self.entry = entry
        self.old_entry = old_entry

    async def callback(self, interaction: discord.Interaction):
        category = self.values[0]
        guild_id = str(interaction.guild.id)
        if self.old_entry:
            data.edit_entry(guild_id, self.list_name, self.old_entry, self.entry, category)
        else:
            data.add_entry(guild_id, self.list_name, self.entry, category)
        list_obj = data.get_list(guild_id, self.list_name)
        entries = list_obj['entries']
        unique_cats = {e['category'] for e in entries}
        if len(unique_cats) == 1 and unique_cats.pop() in CATEGORY_EMOJI_COLOR:
            _, embed_color = CATEGORY_EMOJI_COLOR[entries[0]['category']]
        else:
            embed_color = GRAY
        formatted = "\n".join(f"{CATEGORY_EMOJI_COLOR[e['category']][0]} {e['entry']}" for e in entries)
        embed = discord.Embed(title=f"{self.list_name} List", description=formatted, color=embed_color)
        embed.set_footer(text=f"{len(entries)} entries")
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
        action = "Edited" if self.old_entry else "Added"
        await interaction.response.send_message(f"✅ {action} **{self.entry}** as **{category}** in **{self.list_name}**.", ephemeral=True)
        self.view.stop()

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    await bot.tree.sync(guild=discord.Object(id=GUILD_ID))  # Force re-sync

@bot.tree.command(name='create_list', description='Create a new list')

async def slash_create_list(interaction: discord.Interaction, name: str):
    guild_id = str(interaction.guild.id)
    if not data.create_list(guild_id, name):
        return await interaction.response.send_message('List exists or bot not initialized.', ephemeral=True)
    await interaction.response.send_message(f'✅ Created list **{name}**.', ephemeral=True)

@bot.tree.command(name='delete_list', description='Delete an entire list')

async def slash_delete_list(interaction: discord.Interaction, list_name: str):
    guild_id = str(interaction.guild.id)
    list_obj = data.get_list(guild_id, list_name)
    if not list_obj:
        return await interaction.response.send_message('List not found.', ephemeral=True)
    if list_obj['message_id'] and list_obj['channel_id']:
        channel = bot.get_channel(list_obj['channel_id'])
        try:
            msg = await channel.fetch_message(list_obj['message_id'])
            await msg.delete()
        except:
            pass
    data.delete_list(guild_id, list_name)
    await interaction.response.send_message(f'🗑️ Deleted list **{list_name}**.', ephemeral=True)

@bot.tree.command(name='add_name', description='Add a name to a list and categorize')
@app_commands.describe(list_name='List to add to', name='Name to add')
async def slash_add_name(interaction: discord.Interaction, list_name: str, name: str):
    guild_id = str(interaction.guild.id)
    if not data.get_list(guild_id, list_name):
        return await interaction.response.send_message('List not found. Create with /create_list.', ephemeral=True)
    view = View(timeout=60)
    view.add_item(CategorySelect(list_name, name))
    await interaction.response.send_message(f'Choose category for **{name}** in **{list_name}**:', view=view, ephemeral=True)

@bot.tree.command(name='edit_name', description='Edit a name and its category in a list')
@app_commands.describe(list_name='List name', old_name='Existing entry', new_name='New entry')
async def slash_edit_name(interaction: discord.Interaction, list_name: str, old_name: str, new_name: str):
    guild_id = str(interaction.guild.id)
    list_obj = data.get_list(guild_id, list_name)
    if not list_obj:
        return await interaction.response.send_message('List not found.', ephemeral=True)
    if not any(e['entry'] == old_name for e in list_obj['entries']):
        return await interaction.response.send_message(f'Entry **{old_name}** not found.', ephemeral=True)
    view = View(timeout=60)
    view.add_item(CategorySelect(list_name, new_name, old_entry=old_name))
    await interaction.response.send_message(f'Choose category for **{new_name}** (replacing **{old_name}**):', view=view, ephemeral=True)

@bot.tree.command(name='list', description='Show or create dashboard for a list')
@app_commands.describe(list_name='Which list to show')
async def slash_list(interaction: discord.Interaction, list_name: str):
    guild_id = str(interaction.guild.id)
    list_obj = data.get_list(guild_id, list_name)
    if not list_obj:
        return await interaction.response.send_message('List not found.', ephemeral=True)
    entries = list_obj['entries']
    formatted = "\n".join(f"{CATEGORY_EMOJI_COLOR[e['category']][0]} {e['entry']}" for e in entries) or 'No entries yet.'
    unique_cats = {e['category'] for e in entries}
    if len(unique_cats) == 1 and entries and unique_cats.pop() in CATEGORY_EMOJI_COLOR:
        _, embed_color = CATEGORY_EMOJI_COLOR[entries[0]['category']]
    else:
        embed_color = GRAY
    embed = discord.Embed(title=f"{list_name} List", description=formatted, color=embed_color)
    embed.set_footer(text=f"{len(entries)} entries")
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


@bot.tree.command(name='help', description='How to use Gravity List Bot')
async def slash_help(interaction: discord.Interaction):
    await interaction.response.send_message(help_text, ephemeral=True)

@bot.tree.command(name='remove_name', description='Remove a name from a list')
@app_commands.describe(list_name='List name', name='Name to remove')
async def slash_remove_name(interaction: discord.Interaction, list_name: str, name: str):
    guild_id = str(interaction.guild.id)
    list_obj = data.get_list(guild_id, list_name)
    if not list_obj:
        return await interaction.response.send_message('List not found.', ephemeral=True)
    original_len = len(list_obj['entries'])
    list_obj['entries'] = [e for e in list_obj['entries'] if e['entry'] != name]
    if len(list_obj['entries']) == original_len:
        return await interaction.response.send_message(f'**{name}** not found in **{list_name}**.', ephemeral=True)
    data._save()

    entries = list_obj['entries']
    formatted = "\n".join(f"{CATEGORY_EMOJI_COLOR[e['category']][0]} {e['entry']}" for e in entries) or 'No entries yet.'
    unique_cats = {e['category'] for e in entries}
    if len(unique_cats) == 1 and entries and unique_cats.pop() in CATEGORY_EMOJI_COLOR:
        _, embed_color = CATEGORY_EMOJI_COLOR[entries[0]['category']]
    else:
        embed_color = GRAY
    embed = discord.Embed(title=f"{list_name} List", description=formatted, color=embed_color)
    embed.set_footer(text=f"{len(entries)} entries")

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

    await interaction.response.send_message(f'❌ Removed **{name}** from **{list_name}**.', ephemeral=True)

if __name__ == '__main__':
    bot.run(TOKEN)
