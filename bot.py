
import os
import time
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import asyncio

from data_manager import (
    load_list, save_list, list_exists, delete_list, get_all_list_names,
    load_gen_list, save_gen_list, gen_list_exists, delete_gen_list, get_all_gen_list_names,
    add_to_gen_list,
    save_dashboard_id, get_dashboard_id, get_all_dashboards, get_list_hash,
    save_gen_dashboard_id, get_gen_dashboard_id, get_all_gen_dashboards, get_gen_list_hash
)
from timers import setup as setup_timers

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
CLIENT_ID = int(os.getenv("CLIENT_ID"))

intents = discord.Intents.default()
intents.guilds = True
bot = commands.Bot(command_prefix="!", intents=intents, application_id=CLIENT_ID)

CATEGORY_EMOJIS = {"Owner":"👑","Enemy":"🔴","Friend":"🟢","Ally":"🔵","Bob":"🟡","Timer":"⏳"}
GEN_EMOJIS = {"Tek":"🔄","Electrical":"⛽"}

def build_embed(list_name: str) -> discord.Embed:
    data = load_list(list_name)
    embed = discord.Embed(title=f"{list_name} List", color=0x808080)
    now = time.time()
    for item in data:
        if item.get("category") == "Timer":
            start = item.get("timer_start", now)
            duration = item.get("timer_duration", 0)
            remaining = max(0, int(start + duration - now))
            hrs, rem = divmod(remaining, 3600)
            mins, secs = divmod(rem, 60)
            timer_str = f"{hrs:02d}h {mins:02d}m {secs:02d}s"
            name_field = f"⏳ {item['name']} — {timer_str}"
        else:
            emoji = CATEGORY_EMOJIS.get(item["category"], "")
            name_field = f"{emoji} {item['name']}"
        embed.add_field(name=name_field, value=" ", inline=False)
    return embed

def build_gen_embed(list_name: str) -> discord.Embed:
    data = load_gen_list(list_name)
    embed = discord.Embed(title=f"{list_name} Generators", color=0x404040)
    now = time.time()
    for item in data:
        emoji = GEN_EMOJIS.get(item["type"], "")
        if item["type"] == "Tek":
            duration = item["element"] * 18 * 3600 + item["shards"] * 600
        else:
            duration = item["gas"] * 3600 + item["imbued"] * 4 * 3600
        remaining = max(0, int(item["timestamp"] + duration - now))
        hrs, rem = divmod(remaining, 3600)
        mins, secs = divmod(rem, 60)
        timer_str = f"{hrs:02d}h {mins:02d}m {secs:02d}s"
        embed.add_field(name=f"{emoji} {item['name']}", value=timer_str, inline=False)
    return embed

async def background_updater():
    await bot.wait_until_ready()
    std_hashes, gen_hashes = {}, {}
    while not bot.is_closed():
        for name, dash in get_all_dashboards().items():
            h = get_list_hash(name)
            if std_hashes.get(name) != h:
                std_hashes[name] = h
                ch = bot.get_channel(dash["channel_id"])
                if ch:
                    try:
                        msg = await ch.fetch_message(dash["message_id"])
                        await msg.edit(embed=build_embed(name))
                    except:
                        pass
        for name, dash in get_all_gen_dashboards().items():
            h = get_gen_list_hash(name)
            if gen_hashes.get(name) != h:
                gen_hashes[name] = h
                ch = bot.get_channel(dash["channel_id"])
                if ch:
                    try:
                        msg = await ch.fetch_message(dash["message_id"])
                        await msg.edit(embed=build_gen_embed(name))
                    except:
                        pass
        await asyncio.sleep(5)

@bot.event
async def on_ready():
    await setup_timers(bot)
    await bot.tree.sync()
    print(f"Bot ready. Commands synced for {bot.user}")
    bot.loop.create_task(background_updater())

# Regular list commands
@bot.tree.command(name="create_list", description="Create a new list")
@app_commands.describe(name="Name of the new list")
async def create_list(interaction: discord.Interaction, name: str):
    if list_exists(name):
        return await interaction.response.send_message(f"⚠️ List '{name}' exists.", ephemeral=True)
    save_list(name, [])
    await interaction.response.send_message(f"✅ Created '{name}'.", ephemeral=True)

@bot.tree.command(name="add_name", description="Add entry to a list")
@app_commands.describe(list_name="Which list", name="Entry name", category="Category")
@app_commands.choices(category=[app_commands.Choice(name=k,value=k) for k in CATEGORY_EMOJIS if k!="Timer"])
async def add_name(interaction: discord.Interaction, list_name: str, name: str, category: app_commands.Choice[str]):
    if not list_exists(list_name):
        return await interaction.response.send_message(f"❌ List '{list_name}' not found.", ephemeral=True)
    data = load_list(list_name)
    data.append({"name":name,"category":category.value})
    save_list(list_name,data)
    await interaction.response.send_message(f"✅ Added '{name}'", ephemeral=True)

@bot.tree.command(name="remove_name", description="Remove entry from a list")
@app_commands.describe(list_name="Which list", name="Entry to remove")
async def remove_name(interaction: discord.Interaction, list_name: str, name: str):
    if not list_exists(list_name):
        return await interaction.response.send_message(f"❌ List '{list_name}' not found.", ephemeral=True)
    data=[e for e in load_list(list_name) if e["name"].lower()!=name.lower()]
    save_list(list_name,data)
    await interaction.response.send_message(f"🗑️ Removed '{name}'", ephemeral=True)

@bot.tree.command(name="edit_name", description="Edit an entry")
@app_commands.describe(list_name="Which list", old_name="Old entry", new_name="New entry", new_category="New category")
@app_commands.choices(new_category=[app_commands.Choice(name=k,value=k) for k in CATEGORY_EMOJIS if k!="Timer"])
async def edit_name(interaction: discord.Interaction, list_name: str, old_name: str, new_name: str, new_category: app_commands.Choice[str]):
    if not list_exists(list_name):
        return await interaction.response.send_message(f"❌ List '{list_name}' not found.", ephemeral=True)
    for e in load_list(list_name):
        if e["name"].lower()==old_name.lower():
            e["name"]=new_name; e["category"]=new_category.value; break
    save_list(list_name, load_list(list_name))
    await interaction.response.send_message(f"✏️ Updated '{old_name}' to '{new_name}'", ephemeral=True)

@bot.tree.command(name="delete_list", description="Delete a list")
@app_commands.describe(name="Name of list")
async def delete_list_cmd(interaction: discord.Interaction, name: str):
    if not list_exists(name):
        return await interaction.response.send_message(f"⚠️ '{name}' not found", ephemeral=True)
    delete_list(name)
    await interaction.response.send_message(f"🗑️ Deleted '{name}'", ephemeral=True)

# Unified list display
@bot.tree.command(name="lists", description="Show or update a list (regular or generator)")
@app_commands.describe(name="List name")
async def lists(interaction: discord.Interaction, name: str):
    if list_exists(name):
        embed=build_embed(name)
        dash=get_dashboard_id(name)
        if dash:
            ch=interaction.guild.get_channel(dash["channel_id"])
            try: msg=await ch.fetch_message(dash["message_id"]); await msg.edit(embed=embed); await interaction.response.send_message(f"✅ Updated '{name}'",ephemeral=True)
            except: await interaction.response.send_message(embed=embed); msg=await interaction.original_response(); save_dashboard_id(name, msg.channel.id, msg.id)
        else:
            await interaction.response.send_message(embed=embed); msg=await interaction.original_response(); save_dashboard_id(name, msg.channel.id, msg.id)
    elif gen_list_exists(name):
        # same logic for generator
        embed=build_gen_embed(name)
        dash=get_gen_dashboard_id(name)
        if dash:
            ch=interaction.guild.get_channel(dash["channel_id"])
            try: msg=await ch.fetch_message(dash["message_id"]); await msg.edit(embed=embed); await interaction.response.send_message(f"✅ Updated gen '{name}'",ephemeral=True)
            except: await interaction.response.send_message(embed=embed); msg=await interaction.original_response(); save_gen_dashboard_id(name,msg.channel.id,msg.id)
        else:
            await interaction.response.send_message(embed=embed); msg=await interaction.original_response(); save_gen_dashboard_id(name,msg.channel.id,msg.id)
    else:
        await interaction.response.send_message(f"❌ '{name}' not found", ephemeral=True)

# ... (rest of generator/timer commands unchanged) ...

bot.run(TOKEN)
