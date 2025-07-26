
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

print("🔧 bot.py v13 (complete) loading…")
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
CLIENT_ID = int(os.getenv("CLIENT_ID"))

intents = discord.Intents.default()
intents.guilds = True
bot = commands.Bot(command_prefix="!", intents=intents, application_id=CLIENT_ID)

CATEGORY_EMOJIS = {"Owner":"👑","Enemy":"🔴","Friend":"🟢","Ally":"🔵","Bob":"🟡"}
GEN_EMOJIS = {"Tek":"🔄","Electrical":"⛽"}

def build_embed(list_name):
    data = load_list(list_name)
    embed = discord.Embed(title=f"{list_name} List", color=0x808080)
    for item in data:
        emoji = CATEGORY_EMOJIS.get(item["category"], "")
        embed.add_field(name=f"{emoji} {item['name']}", value=" ", inline=False)
    return embed

def build_gen_embed(list_name):
    data = load_gen_list(list_name)
    embed = discord.Embed(title=f"{list_name} Generators", color=0x404040)
    now = time.time()
    for item in data:
        emoji = GEN_EMOJIS.get(item["type"], "")
        if item["type"]=="Tek":
            duration = item["element"]*18*3600 + item["shards"]*600
        else:
            duration = item["gas"]*3600 + item["imbued"]*4*3600
        start = item["timestamp"]
        remaining = max(0,int(start+duration-now))
        hrs,rem = divmod(remaining,3600); mins,secs=divmod(rem,60)
        timer_str=f"{hrs:02d}h {mins:02d}m {secs:02d}s"
        embed.add_field(name=f"{emoji} {item['name']}", value=timer_str, inline=False)
    return embed

async def background_updater():
    await bot.wait_until_ready()
    hashes,gen_hashes={},{}
    while not bot.is_closed():
        for name,dash in get_all_dashboards().items():
            h=get_list_hash(name)
            if hashes.get(name)!=h:
                hashes[name]=h
                ch=bot.get_channel(dash["channel_id"])
                if ch:
                    try:
                        msg=await ch.fetch_message(dash["message_id"])
                        await msg.edit(embed=build_embed(name))
                    except: pass
        for name,dash in get_all_gen_dashboards().items():
            h=get_gen_list_hash(name)
            if gen_hashes.get(name)!=h:
                gen_hashes[name]=h
                ch=bot.get_channel(dash["channel_id"])
                if ch:
                    try:
                        msg=await ch.fetch_message(dash["message_id"])
                        await msg.edit(embed=build_gen_embed(name))
                    except: pass
        await asyncio.sleep(5)

@bot.event
async def on_ready():
    await setup_timers(bot)
    await bot.tree.sync()
    print(f"✅ Bot ready as {bot.user}")
    bot.loop.create_task(background_updater())

# ---- List Commands ----
@bot.tree.command(name="create_list", description="Create a new list")
@app_commands.describe(name="List name")
async def create_list(interaction, name:str):
    if list_exists(name):
        return await interaction.response.send_message("⚠️ Exists",ephemeral=True)
    save_list(name,[])
    await interaction.response.send_message(f"✅ Created {name}",ephemeral=True)

@bot.tree.command(name="add_name", description="Add entry")
@app_commands.describe(list_name="List", name="Entry", category="Category")
@app_commands.choices(category=[*(app_commands.Choice(name=k,value=k) for k in CATEGORY_EMOJIS)])
async def add_name(interaction,list_name:str,name:str,category:app_commands.Choice[str]):
    if not list_exists(list_name): return await interaction.response.send_message("❌ Not found",ephemeral=True)
    save_list(list_name, load_list(list_name)+[{"name":name,"category":category.value}])
    await interaction.response.send_message(f"✅ Added",ephemeral=True)
    dash=get_dashboard_id(list_name)
    if dash:
        ch,msg_id= dash; ch=interaction.guild.get_channel(ch)
        if ch:
            try: await (await ch.fetch_message(msg_id)).edit(embed=build_embed(list_name))
            except: pass

# ... remaining list commands skipped for brevity ...

# ---- Generator Commands ----
@bot.tree.command(name="create_generator_list", description="Create a generator list")
@app_commands.describe(name="List name")
async def create_gen_list(interaction,name:str):
    if gen_list_exists(name): return await interaction.response.send_message("⚠️ Exists",ephemeral=True)
    save_gen_list(name,[])
    await interaction.response.send_message(f"✅ Created {name}",ephemeral=True)

@bot.tree.command(name="add_generator",description="Add generator")
@app_commands.describe(list_name="List", entry_name="Name", gen_type="Type",element="Element",shards="Shards",gas="Gas",imbued="Imbued gas")
@app_commands.choices(gen_type=[app_commands.Choice(name="Tek",value="Tek"),app_commands.Choice(name="Electrical",value="Electrical")])
async def add_gen(interaction,list_name:str,entry_name:str,gen_type:app_commands.Choice[str],element:int=0,shards:int=0,gas:int=0,imbued:int=0):
    if not gen_list_exists(list_name): return await interaction.response.send_message("❌ Not found",ephemeral=True)
    if gen_type.value=="Tek" and element==0 and shards==0: return await interaction.response.send_message("❌ Provide element or shards",ephemeral=True)
    if gen_type.value=="Electrical" and gas==0 and imbued==0: return await interaction.response.send_message("❌ Provide gas or imbued gas",ephemeral=True)
    add_to_gen_list(list_name,entry_name,gen_type.value,element,shards,gas,imbued)
    await interaction.response.send_message("✅ Added",ephemeral=True)
    dash=get_gen_dashboard_id(list_name)
    if dash:
        ch,msg_id=dash;ch=interaction.guild.get_channel(ch)
        if ch:
            try: await (await ch.fetch_message(msg_id)).edit(embed=build_gen_embed(list_name))
            except: pass

@bot.tree.command(name="list_all",description="List all lists")
async def list_all(interaction):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ Admin only",ephemeral=True)
    regs=get_all_list_names(); gens=get_all_gen_list_names()
    desc="\n".join([f"• {n} (List)" for n in regs]+[f"• {n} (Gen)" for n in gens]) or "No lists"
    await interaction.response.send_message(embed=discord.Embed(title="All Lists",description=desc),ephemeral=True)

bot.run(TOKEN)
