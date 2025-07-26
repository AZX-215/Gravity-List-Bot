
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

# ---- Regular List Commands ----

@bot.tree.command(name="create_list", description="Create a new list")
@app_commands.describe(name="Name of the new list")
async def create_list(interaction: discord.Interaction, name: str):
    if list_exists(name):
        return await interaction.response.send_message(f"⚠️ List '{name}' already exists.", ephemeral=True)
    save_list(name, [])
    await interaction.response.send_message(f"✅ Created list '{name}'.", ephemeral=True)

@bot.tree.command(name="add_name", description="Add entry to a list")
@app_commands.describe(list_name="Which list", name="Entry name", category="Category")
@app_commands.choices(category=[app_commands.Choice(name=k, value=k) for k in CATEGORY_EMOJIS if k!="Timer"])
async def add_name(interaction: discord.Interaction, list_name: str, name: str, category: app_commands.Choice[str]):
    if not list_exists(list_name):
        return await interaction.response.send_message(f"❌ List '{list_name}' not found.", ephemeral=True)
    data = load_list(list_name)
    data.append({"name": name, "category": category.value})
    save_list(list_name, data)
    await interaction.response.send_message(f"✅ Added '{name}' to '{list_name}'.", ephemeral=True)
    dash = get_dashboard_id(list_name)
    if dash:
        ch = interaction.guild.get_channel(dash["channel_id"])
        if ch:
            try:
                msg = await ch.fetch_message(dash["message_id"])
                await msg.edit(embed=build_embed(list_name))
            except:
                pass

@bot.tree.command(name="remove_name", description="Remove entry from a list")
@app_commands.describe(list_name="Which list", name="Entry to remove")
async def remove_name(interaction: discord.Interaction, list_name: str, name: str):
    if not list_exists(list_name):
        return await interaction.response.send_message(f"❌ List '{list_name}' not found.", ephemeral=True)
    data = [e for e in load_list(list_name) if e["name"].lower()!=name.lower()]
    save_list(list_name, data)
    await interaction.response.send_message(f"🗑️ Removed '{name}' from '{list_name}'.", ephemeral=True)
    dash = get_dashboard_id(list_name)
    if dash:
        ch = interaction.guild.get_channel(dash["channel_id"])
        if ch:
            try:
                msg = await ch.fetch_message(dash["message_id"])
                await msg.edit(embed=build_embed(list_name))
            except:
                pass

@bot.tree.command(name="edit_name", description="Edit entry in a list")
@app_commands.describe(list_name="Which list", old_name="Current name", new_name="New name", new_category="New category")
@app_commands.choices(new_category=[app_commands.Choice(name=k, value=k) for k in CATEGORY_EMOJIS if k!="Timer"])
async def edit_name(interaction: discord.Interaction, list_name: str, old_name: str, new_name: str, new_category: app_commands.Choice[str]):
    if not list_exists(list_name):
        return await interaction.response.send_message(f"❌ List '{list_name}' not found.", ephemeral=True)
    data = load_list(list_name)
    for e in data:
        if e["name"].lower()==old_name.lower():
            e["name"]=new_name
            e["category"]=new_category.value
            break
    save_list(list_name, data)
    await interaction.response.send_message(f"✏️ Updated '{old_name}'.", ephemeral=True)
    dash = get_dashboard_id(list_name)
    if dash:
        ch = interaction.guild.get_channel(dash["channel_id"])
        if ch:
            try:
                msg = await ch.fetch_message(dash["message_id"])
                await msg.edit(embed=build_embed(list_name))
            except:
                pass

@bot.tree.command(name="delete_list", description="Delete an entire list")
@app_commands.describe(name="Name of the list to delete")
async def delete_list_cmd(interaction: discord.Interaction, name: str):
    if not list_exists(name):
        return await interaction.response.send_message(f"⚠️ List '{name}' not found.", ephemeral=True)
    delete_list(name)
    await interaction.response.send_message(f"🗑️ Deleted list '{name}'.", ephemeral=True)

# ---- Inline Timer ----

@bot.tree.command(name="add_timer_to_list", description="Add a timer entry into a regular list")
@app_commands.describe(list_name="Which list", name="Timer name", hours="Hours", minutes="Minutes")
async def add_timer_to_list(interaction: discord.Interaction, list_name: str, name: str, hours: int, minutes: int):
    if not list_exists(list_name):
        return await interaction.response.send_message(f"❌ List '{list_name}' not found.", ephemeral=True)
    total = hours*3600 + minutes*60
    entry = {"name": name, "category":"Timer", "timer_start": time.time(), "timer_duration": total}
    data = load_list(list_name)
    data.append(entry)
    save_list(list_name, data)
    await interaction.response.send_message(f"⏳ Timer '{name}' added to '{list_name}'.", ephemeral=True)
    dash = get_dashboard_id(list_name)
    if dash:
        ch = interaction.guild.get_channel(dash["channel_id"])
        if ch:
            try:
                msg = await ch.fetch_message(dash["message_id"])
                await msg.edit(embed=build_embed(list_name))
            except:
                pass

# ---- Generator List Commands ----

@bot.tree.command(name="create_generator_list", description="Create a new generator timer list")
@app_commands.describe(name="Name of the generator list")
async def create_generator_list(interaction: discord.Interaction, name: str):
    if gen_list_exists(name):
        return await interaction.response.send_message(f"⚠️ Generator list '{name}' exists.", ephemeral=True)
    save_gen_list(name, [])
    await interaction.response.send_message(f"✅ Created generator list '{name}'.", ephemeral=True)

@bot.tree.command(name="add_generator", description="Add a generator entry to a list")
@app_commands.describe(
    list_name="Which generator list",
    entry_name="Generator name",
    gen_type="Generator type",
    element="Element amount",
    shards="Shards amount",
    gas="Gas amount",
    imbued="Element imbued gas amount"
)
@app_commands.choices(gen_type=[app_commands.Choice(name="Tek",value="Tek"), app_commands.Choice(name="Electrical",value="Electrical")])
async def add_generator(interaction: discord.Interaction, list_name: str, entry_name: str, gen_type: app_commands.Choice[str], element: int=0, shards: int=0, gas: int=0, imbued: int=0):
    if not gen_list_exists(list_name):
        return await interaction.response.send_message(f"❌ Generator list '{list_name}' not found.", ephemeral=True)
    if gen_type.value=="Tek" and element+shards==0:
        return await interaction.response.send_message("❌ Provide element or shards.", ephemeral=True)
    if gen_type.value=="Electrical" and gas+imbued==0:
        return await interaction.response.send_message("❌ Provide gas or imbued gas.", ephemeral=True)
    add_to_gen_list(list_name, entry_name, gen_type.value, element, shards, gas, imbued)
    await interaction.response.send_message(f"✅ Added '{entry_name}' to '{list_name}'.", ephemeral=True)
    dash = get_gen_dashboard_id(list_name)
    if dash:
        ch = interaction.guild.get_channel(dash["channel_id"])
        if ch:
            try:
                msg = await ch.fetch_message(dash["message_id"])
                await msg.edit(embed=build_gen_embed(list_name))
            except:
                pass

@bot.tree.command(name="edit_generator", description="Edit a generator entry")
@app_commands.describe(list_name="Which generator list", old_name="Existing entry name", new_name="New entry name", element="Element amount", shards="Shards amount", gas="Gas amount", imbued="Element imbued gas amount")
async def edit_generator(interaction: discord.Interaction, list_name: str, old_name: str, new_name: str, element: int=0, shards: int=0, gas: int=0, imbued: int=0):
    if not gen_list_exists(list_name):
        return await interaction.response.send_message(f"❌ Generator list '{list_name}' not found.", ephemeral=True)
    data = load_gen_list(list_name)
    for item in data:
        if item["name"].lower()==old_name.lower():
            item["name"]=new_name
            item["element"]=element
            item["shards"]=shards
            item["gas"]=gas
            item["imbued"]=imbued
            break
    save_gen_list(list_name, data)
    await interaction.response.send_message(f"✏️ Updated generator '{old_name}'.", ephemeral=True)
    dash = get_gen_dashboard_id(list_name)
    if dash:
        ch = interaction.guild.get_channel(dash["channel_id"])
        if ch:
            try:
                msg = await ch.fetch_message(dash["message_id"])
                await msg.edit(embed=build_gen_embed(list_name))
            except:
                pass

@bot.tree.command(name="remove_generator", description="Remove a generator entry")
@app_commands.describe(list_name="Which generator list", entry_name="Entry to remove")
async def remove_generator(interaction: discord.Interaction, list_name: str, entry_name: str):
    if not gen_list_exists(list_name):
        return await interaction.response.send_message(f"❌ Generator list '{list_name}' not found.", ephemeral=True)
    data = [e for e in load_gen_list(list_name) if e["name"].lower()!=entry_name.lower()]
    save_gen_list(list_name, data)
    await interaction.response.send_message(f"🗑️ Removed '{entry_name}' from '{list_name}'.", ephemeral=True)
    dash = get_gen_dashboard_id(list_name)
    if dash:
        ch = interaction.guild.get_channel(dash["channel_id"])
        if ch:
            try:
                msg = await ch.fetch_message(dash["message_id"])
                await msg.edit(embed=build_gen_embed(list_name))
            except:
                pass

@bot.tree.command(name="delete_generator_list", description="Delete a generator list")
@app_commands.describe(name="Name of the generator list to delete")
async def delete_generator_list(interaction: discord.Interaction, name: str):
    if not gen_list_exists(name):
        return await interaction.response.send_message(f"❌ Generator list '{name}' not found.", ephemeral=True)
    delete_gen_list(name)
    await interaction.response.send_message(f"🗑️ Deleted generator list '{name}'.", ephemeral=True)

# ---- Overview ----

@bot.tree.command(name="list_all", description="List all list names (regular & generator)")
async def list_all(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ Administrator required.", ephemeral=True)
    regs = get_all_list_names()
    gens = get_all_gen_list_names()
    lines = [f"• {r} (List)" for r in regs] + [f"• {g} (Gen List)" for g in gens]
    desc = "\n".join(lines) if lines else "No lists found."
    embed = discord.Embed(title="All Lists", description=desc, color=0x808080)
    await interaction.response.send_message(embed=embed, ephemeral=True)

bot.run(TOKEN)
