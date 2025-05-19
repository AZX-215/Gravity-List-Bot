import os
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import json

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
CLIENT_ID = int(os.getenv("CLIENT_ID"))
GUILD_ID = int(os.getenv("GUILD_ID"))
LISTS_DIR = "lists"

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents, application_id=CLIENT_ID)

CATEGORY_EMOJIS = {
    "Enemy": "🔴",
    "Friend": "🟢",
    "Ally": "🔵",
    "Bob": "🟡"
}

CATEGORY_COLORS = {
    "Enemy": 0xff0000,
    "Friend": 0x00ff00,
    "Ally": 0x0000ff,
    "Bob": 0xffff00
}

def get_list_path(guild_id, list_name):
    path = os.path.join(LISTS_DIR, str(guild_id))
    os.makedirs(path, exist_ok=True)
    return os.path.join(path, f"{list_name}.json")

def load_list(guild_id, list_name):
    path = get_list_path(guild_id, list_name)
    if not os.path.exists(path):
        return {}
    with open(path, "r") as f:
        return json.load(f)

def save_list(guild_id, list_name, data):
    path = get_list_path(guild_id, list_name)
    with open(path, "w") as f:
        json.dump(data, f, indent=4)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

@bot.tree.command(name="create_list", description="Create a new list", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(name="The name of the list")
async def create_list(interaction: discord.Interaction, name: str):
    save_list(interaction.guild_id, name, {})
    await interaction.response.send_message(f"List '{name}' created!", ephemeral=True)

@bot.tree.command(name="add_name", description="Add a name to a list", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(list_name="The list to add to", name="Name to add", category="Choose a category")
@app_commands.choices(category=[
    app_commands.Choice(name="Enemy", value="Enemy"),
    app_commands.Choice(name="Friend", value="Friend"),
    app_commands.Choice(name="Ally", value="Ally"),
    app_commands.Choice(name="Bob", value="Bob")
])
async def add_name(interaction: discord.Interaction, list_name: str, name: str, category: app_commands.Choice[str]):
    data = load_list(interaction.guild_id, list_name)
    data[name] = category.value
    save_list(interaction.guild_id, list_name, data)
    await interaction.response.send_message(f"Added {name} as {category.value} to {list_name}.", ephemeral=True)
    await update_dashboard(interaction.guild, list_name)

@bot.tree.command(name="remove_name", description="Remove a name from a list", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(list_name="The list to modify", name="Name to remove")
async def remove_name(interaction: discord.Interaction, list_name: str, name: str):
    data = load_list(interaction.guild_id, list_name)
    if name in data:
        del data[name]
        save_list(interaction.guild_id, list_name, data)
        await interaction.response.send_message(f"Removed {name} from {list_name}.", ephemeral=True)
        await update_dashboard(interaction.guild, list_name)
    else:
        await interaction.response.send_message(f"{name} not found in {list_name}.", ephemeral=True)

@bot.tree.command(name="delete_list", description="Delete an entire list", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(name="The list name to delete")
async def delete_list(interaction: discord.Interaction, name: str):
    path = get_list_path(interaction.guild_id, name)
    if os.path.exists(path):
        os.remove(path)
        await interaction.response.send_message(f"List '{name}' has been deleted.", ephemeral=True)
    else:
        await interaction.response.send_message(f"List '{name}' does not exist.", ephemeral=True)

@bot.tree.command(name="edit_name", description="Edit a name and its category", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(list_name="The list to modify", old_name="Current name", new_name="New name", new_category="New category")
@app_commands.choices(new_category=[
    app_commands.Choice(name="Enemy", value="Enemy"),
    app_commands.Choice(name="Friend", value="Friend"),
    app_commands.Choice(name="Ally", value="Ally"),
    app_commands.Choice(name="Bob", value="Bob")
])
async def edit_name(interaction: discord.Interaction, list_name: str, old_name: str, new_name: str, new_category: app_commands.Choice[str]):
    data = load_list(interaction.guild_id, list_name)
    if old_name in data:
        del data[old_name]
        data[new_name] = new_category.value
        save_list(interaction.guild_id, list_name, data)
        await interaction.response.send_message(f"Updated {old_name} to {new_name} as {new_category.value}.", ephemeral=True)
        await update_dashboard(interaction.guild, list_name)
    else:
        await interaction.response.send_message(f"{old_name} not found in {list_name}.", ephemeral=True)

@bot.tree.command(name="list", description="Show entries in a list", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(name="The list to display")
async def show_list(interaction: discord.Interaction, name: str):
    await update_dashboard(interaction.guild, name)
    await interaction.response.send_message(f"List '{name}' updated in channel.", ephemeral=True)

async def update_dashboard(guild, list_name):
    channel = discord.utils.get(guild.text_channels, name=list_name)
    if not channel:
        return
    data = load_list(guild.id, list_name)
    await channel.purge()
    if not data:
        await channel.send(embed=discord.Embed(title="Empty List", description="No entries.", color=0x808080))
        return
    for name, category in data.items():
        embed = discord.Embed(description=f"{CATEGORY_EMOJIS[category]} **{name}**", color=CATEGORY_COLORS[category])
        await channel.send(embed=embed)

bot.run(TOKEN)