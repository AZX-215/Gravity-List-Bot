import os
import discord
from discord import app_commands
from discord.ext import commands
from tribe_manager import TribeManager

# Load from environment variables
TOKEN = os.getenv('DISCORD_TOKEN')
ALLOWED_ROLE_IDS = [int(x) for x in os.getenv('ALLOWED_ROLE_IDS', '').split(',') if x]

# Setup bot
intents = discord.Intents.default()
intents.guilds = True
intents.guild_messages = True
bot = commands.Bot(command_prefix="!", intents=intents)

tribe_manager = TribeManager()

def has_allowed_role(interaction: discord.Interaction):
    return any(role.id in ALLOWED_ROLE_IDS for role in interaction.user.roles)

async def update_view_message(channel: discord.TextChannel):
    channel_id = channel.id
    channel_name = channel.name
    tribe_list = tribe_manager.get_list(channel_id, channel_name)
    formatted_list = '\n'.join(f"- {name}" for name in tribe_list) or "(empty)"
    content = f"```diff\n{formatted_list}\n```"

    message_id = tribe_manager.get_view_message(channel_id, channel_name)
    if message_id:
        try:
            msg = await channel.fetch_message(message_id)
            await msg.edit(content=content)
            return
        except (discord.NotFound, discord.Forbidden):
            pass

    # Send a new persistent message
    msg = await channel.send(content=content)
    tribe_manager.set_view_message(channel_id, channel_name, msg.id)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    await bot.tree.sync()

@bot.tree.command(name="create_list", description="Create the tribe list for this channel.")
async def create_list(interaction: discord.Interaction):
    if not has_allowed_role(interaction):
        await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
        return
    channel = interaction.channel
    tribe_manager.create_list(channel.id, channel.name)
    await interaction.response.send_message("✅ Tribe list created for this channel!", ephemeral=True)

@bot.tree.command(name="add_name", description="Add a name to the tribe list.")
@app_commands.describe(name="The tribe name to add.")
async def add_name(interaction: discord.Interaction, name: str):
    if not has_allowed_role(interaction):
        await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
        return
    channel = interaction.channel
    if not tribe_manager.list_exists(channel.id, channel.name):
        await interaction.response.send_message("❌ No list exists in this channel. Use /create_list first.", ephemeral=True)
        return
    tribe_manager.add_name(channel.id, channel.name, name)
    await update_view_message(channel)
    await interaction.response.send_message(f"✅ Added `{name}` to the tribe list.", ephemeral=True)

@bot.tree.command(name="edit_name", description="Edit a name in the tribe list.")
@app_commands.describe(old_name="The existing name.", new_name="The new name.")
async def edit_name(interaction: discord.Interaction, old_name: str, new_name: str):
    if not has_allowed_role(interaction):
        await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
        return
    channel = interaction.channel
    if not tribe_manager.list_exists(channel.id, channel.name):
        await interaction.response.send_message("❌ No list exists in this channel. Use /create_list first.", ephemeral=True)
        return
    tribe_manager.edit_name(channel.id, channel.name, old_name, new_name)
    await update_view_message(channel)
    await interaction.response.send_message(f"✏️ Edited `{old_name}` to `{new_name}`.", ephemeral=True)

@bot.tree.command(name="remove_name", description="Remove a name from the tribe list.")
@app_commands.describe(name="The name to remove.")
async def remove_name(interaction: discord.Interaction, name: str):
    if not has_allowed_role(interaction):
        await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
        return
    channel = interaction.channel
    if not tribe_manager.list_exists(channel.id, channel.name):
        await interaction.response.send_message("❌ No list exists in this channel. Use /create_list first.", ephemeral=True)
        return
    tribe_manager.remove_name(channel.id, channel.name, name)
    await update_view_message(channel)
    await interaction.response.send_message(f"❌ Removed `{name}` from the tribe list.", ephemeral=True)

@bot.tree.command(name="view_list", description="Display or update the tribe list.")
async def view_list(interaction: discord.Interaction):
    channel = interaction.channel
    if not tribe_manager.list_exists(channel.id, channel.name):
        await interaction.response.send_message("❌ No list exists in this channel. Use /create_list first.", ephemeral=True)
        return
    await update_view_message(channel)
    await interaction.response.send_message("✅ Tribe list displayed/updated.", ephemeral=True)

@bot.tree.command(name="delete_list", description="Delete the tribe list for this channel.")
async def delete_list(interaction: discord.Interaction):
    if not has_allowed_role(interaction):
        await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
        return
    channel = interaction.channel
    if tribe_manager.list_exists(channel.id, channel.name):
        message_id = tribe_manager.get_view_message(channel.id, channel.name)
        if message_id:
            try:
                msg = await channel.fetch_message(message_id)
                await msg.delete()
            except (discord.NotFound, discord.Forbidden):
                pass
        tribe_manager.delete_list(channel.id, channel.name)
        await interaction.response.send_message("🗑️ Tribe list deleted for this channel.", ephemeral=True)
    else:
        await interaction.response.send_message("❌ No list exists in this channel.", ephemeral=True)

bot.run(TOKEN)
