import os
import time
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv

from data_manager import (
    load_list, save_list, list_exists, delete_list,
    get_all_list_names, get_all_gen_list_names,
    save_dashboard_id, get_dashboard_id
)
from timers import setup as setup_timers
from gen_timers import setup as setup_gen_timers, build_gen_embed as build_gen_dashboard_embed

load_dotenv()
TOKEN     = os.getenv("DISCORD_TOKEN")
CLIENT_ID = int(os.getenv("CLIENT_ID"))

intents = discord.Intents.default()
intents.guilds = True
bot = commands.Bot(command_prefix="!", intents=intents, application_id=CLIENT_ID)

# ━━━━━━ Categories ━━━━━━━━━━
CATEGORY_EMOJIS = {
    "Owner": "👑", "Enemy": "🔴", "Friend": "🟢",
    "Ally":  "🔵",  "Beta":  "🟡",  "Item":  "⚫", "Timer":"⏳"
}

# ━━━━━━ Embeds & Updates ━━━━━━━━━━
async def push_list_update(list_name: str):
    dash = get_dashboard_id(list_name)
    if dash:
        channel_id, message_id = dash
        ch = bot.get_channel(channel_id)
        if ch:
            try:
                msg = await ch.fetch_message(message_id)
                await msg.edit(embed=build_embed(list_name))
            except Exception as e:
                print(f"[List Update] {e}")

def build_embed(list_name: str) -> discord.Embed:
    data = load_list(list_name)
    embed = discord.Embed(title=f"{list_name} List", color=0x808080)
    embed.add_field(name="\u200b", value="\u200b", inline=False)  # padding

    now = time.time()
    # Sort: Header first, then normal/text (3), others (2)
    data.sort(key=lambda x: 1 if x.get("category") == "Header"
                           else 3 if x.get("category") == "Text"
                           else 2)

    for item in data:
        cat = item["category"]
        if cat == "Header":
            embed.add_field(name="\u200b", value=f"**{item['name']}**", inline=False)

        elif cat == "Text":
            embed.add_field(name=f"• {item['name']}", value="\u200b", inline=False)

        elif cat == "Timer":
            # inline timer uses absolute end timestamp
            end = item.get("timer_end", 0)
            rem = max(0, int(end - now))
            d, rem_hr = divmod(rem, 86400)
            h, r      = divmod(rem_hr, 3600)
            m, s      = divmod(r, 60)
            if d:
                timestr = f"{d}d {h:02d}h {m:02d}m {s:02d}s"
            else:
                timestr = f"{h:02d}h {m:02d}m {s:02d}s"
            name_fld = f"⏳   {item['name']} — {timestr}"
            embed.add_field(name=name_fld, value="\u200b", inline=False)

        else:
            # normal categories (Owner, Enemy, Friend, Ally, Beta, Item)
            name_fld = f"{CATEGORY_EMOJIS.get(cat,'')}   {item['name']}"
            embed.add_field(name=name_fld, value="\u200b", inline=False)
            # optional comment below
            if item.get("comment"):
                embed.add_field(name="\u200b", value=f"*{item['comment']}*", inline=False)

    return embed

# ━━━━━━ Bot Startup ━━━━━━━━━━
@bot.event
async def on_ready():
    # run setup only once to avoid duplicate registration errors
    if not getattr(bot, "_startup_done", False):
        await setup_timers(bot)
        await setup_gen_timers(bot)
        await bot.tree.sync()
        print(f"Bot ready. Commands synced for {bot.user}")
        bot._startup_done = True
    else:
        print(f"Bot reconnected: {bot.user}")

# ━━━━━━ List Commands ━━━━━━━━━━
@bot.tree.command(name="create_list", description="Create a new list")
@app_commands.describe(name="Name of the new list")
async def create_list(interaction: discord.Interaction, name: str):
    if list_exists(name):
        return await interaction.response.send_message(f"⚠️ List '{name}' already exists.", ephemeral=True)
    save_list(name, [])
    await interaction.response.send_message(f"✅ Created list '{name}'.", ephemeral=True)

@bot.tree.command(name="add_name", description="Add an entry to a list")
@app_commands.describe(
    list_name="Which list",
    name="Entry name",
    category="Category emoji",
    comment="Optional comment below the entry"
)
@app_commands.choices(category=[
    app_commands.Choice(name=k, value=k)
    for k in CATEGORY_EMOJIS if k != "Timer"
])
async def add_name(
    interaction: discord.Interaction,
    list_name: str,
    name: str,
    category: app_commands.Choice[str],
    comment: str = None
):
    if not list_exists(list_name):
        return await interaction.response.send_message(f"❌ List '{list_name}' not found.", ephemeral=True)
    entry = {"name": name, "category": category.value}
    if comment:
        entry["comment"] = comment
    data = load_list(list_name)
    data.append(entry)
    save_list(list_name, data)
    await interaction.response.send_message(f"✅ Added '{name}' to '{list_name}'.", ephemeral=True)
    await push_list_update(list_name)

@bot.tree.command(name="remove_name", description="Remove an entry from a list")
@app_commands.describe(list_name="Which list", name="Entry to remove")
async def remove_name(interaction: discord.Interaction, list_name: str, name: str):
    if not list_exists(list_name):
        return await interaction.response.send_message(f"❌ List '{list_name}' not found.", ephemeral=True)
    data = [e for e in load_list(list_name) if e["name"].lower() != name.lower()]
    save_list(list_name, data)
    await interaction.response.send_message(f"🗑️ Removed '{name}' from '{list_name}'.", ephemeral=True)
    await push_list_update(list_name)

@bot.tree.command(name="edit_name", description="Edit an entry in a list")
@app_commands.describe(
    list_name="Which list",
    old_name="Existing entry",
    new_name="New entry name",
    new_category="New category",
    new_comment="Optional new comment (blank to clear)"
)
@app_commands.choices(new_category=[
    app_commands.Choice(name=k, value=k)
    for k in CATEGORY_EMOJIS if k != "Timer"
])
async def edit_name(
    interaction: discord.Interaction,
    list_name: str,
    old_name: str,
    new_name: str,
    new_category: app_commands.Choice[str],
    new_comment: str = None
):
    if not list_exists(list_name):
        return await interaction.response.send_message(f"❌ List '{list_name}' not found.", ephemeral=True)
    data = load_list(list_name)
    for e in data:
        if e["name"].lower() == old_name.lower():
            e["name"] = new_name
            e["category"] = new_category.value
            if new_comment is not None:
                if new_comment.strip() == "":
                    e.pop("comment", None)
                else:
                    e["comment"] = new_comment
            break
    save_list(list_name, data)
    await interaction.response.send_message(f"✏️ Updated '{old_name}'.", ephemeral=True)
    await push_list_update(list_name)

@bot.tree.command(name="delete_list", description="Delete an entire list")
@app_commands.describe(name="Name of the list to delete")
async def delete_list_cmd(interaction: discord.Interaction, name: str):
    if not list_exists(name):
        return await interaction.response.send_message(f"⚠️ List '{name}' not found.", ephemeral=True)
    delete_list(name)
    await interaction.response.send_message(f"🗑️ Deleted list '{name}'.", ephemeral=True)

# ━━━━━━ Inline Timer in List ━━━━━━━━━━
@bot.tree.command(name="add_timer_to_list", description="Add a timer entry into a regular list")
@app_commands.describe(
    list_name="Which list",
    name="Timer name",
    hours="Hours",
    minutes="Minutes"
)
async def add_timer_to_list(
    interaction: discord.Interaction,
    list_name: str,
    name: str,
    hours: int,
    minutes: int
):
    if not list_exists(list_name):
        return await interaction.response.send_message(f"❌ List '{list_name}' not found.", ephemeral=True)
    total = hours*3600 + minutes*60
    entry = {
        "name": name,
        "category": "Timer",
        "timer_end": time.time() + total
    }
    data = load_list(list_name)
    data.append(entry)
    save_list(list_name, data)
    await interaction.response.send_message(f"⏳ Timer '{name}' added to '{list_name}'.", ephemeral=True)
    await push_list_update(list_name)

# ━━━━━━ Text & Header Commands ━━━━━━━━━━
@bot.tree.command(name="add_text", description="Add a bullet note at bottom of a list")
@app_commands.describe(list_name="Which list", text="Text comment")
async def add_text(interaction: discord.Interaction, list_name: str, text: str):
    if not list_exists(list_name):
        return await interaction.response.send_message(f"❌ List '{list_name}' not found.", ephemeral=True)
    data = load_list(list_name)
    data.append({"name": text, "category": "Text"})
    save_list(list_name, data)
    await interaction.response.send_message(f"📝 Added text to '{list_name}'.", ephemeral=True)
    await push_list_update(list_name)

@bot.tree.command(name="add_header", description="Add/update centered header at top of a list")
@app_commands.describe(list_name="Which list", header="Header text")
async def add_header(interaction: discord.Interaction, list_name: str, header: str):
    if not list_exists(list_name):
        return await interaction.response.send_message(f"❌ List '{list_name}' not found.", ephemeral=True)
    data = [e for e in load_list(list_name) if e.get("category") != "Header"]
    data.insert(0, {"name": header, "category": "Header"})
    save_list(list_name, data)
    await interaction.response.send_message(f"🏷️ Set header for '{list_name}'.", ephemeral=True)
    await push_list_update(list_name)

# ━━━━━━ Dashboards ━━━━━━━━━━
@bot.tree.command(name="lists", description="Show or update any list dashboard")
@app_commands.describe(name="List name")
async def lists(interaction: discord.Interaction, name: str):
    # Regular lists
    if list_exists(name):
        embed = build_embed(name)
        dash  = get_dashboard_id(name)
        if dash:
            ch_id, msg_id = dash
            ch = interaction.guild.get_channel(ch_id)
            if ch:
                try:
                    msg = await ch.fetch_message(msg_id)
                    await msg.edit(embed=embed)
                    return await interaction.response.send_message(f"✅ Refreshed '{name}'.", ephemeral=True)
                except:
                    pass
        await interaction.response.send_message(embed=embed)
        msg = await interaction.original_response()
        save_dashboard_id(name, msg.channel.id, msg.id)
        return

    # Generator lists
    if name in get_all_list_names():
        # safe fallback—shouldn’t happen
        pass

    if name in get_all_gen_list_names():
        embed = build_gen_dashboard_embed(name)
        from data_manager import get_gen_dashboard_id, save_gen_dashboard_id
        dash = get_gen_dashboard_id(name)
        if dash:
            ch_id, msg_id = dash
            ch = interaction.guild.get_channel(ch_id)
            if ch:
                try:
                    msg = await ch.fetch_message(msg_id)
                    await interaction.response.send_message(f"✅ Refreshed generator '{name}'.", embed=embed, ephemeral=True)
                    return
                except:
                    pass
        await interaction.response.send_message(embed=embed)
        msg = await interaction.original_response()
        save_gen_dashboard_id(name, msg.channel.id, msg.id)
        return

    await interaction.response.send_message(f"❌ '{name}' not found.", ephemeral=True)

# ━━━━━━ Overview & Help ━━━━━━━━━━
@bot.tree.command(name="list_all", description="List all regular & generator lists")
async def list_all(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ Admin only.", ephemeral=True)
    regs = get_all_list_names()
    gens = get_all_gen_list_names()
    lines = [f"• {r} (List)" for r in regs] + [f"• {g} (Gen List)" for g in gens]
    desc = "\n".join(lines) if lines else "No lists found."
    embed = discord.Embed(title="All Lists", description=desc, color=0x808080)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="resync_timers", description="Force-refresh all list dashboards (admin only)")
async def resync_timers(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ Admin only.", ephemeral=True)
    for name in get_all_list_names():
        await push_list_update(name)
    await interaction.response.send_message("✅ All list dashboards re‑synced.", ephemeral=True)

@bot.tree.command(name="help", description="Show usage instructions")
async def help_command(interaction: discord.Interaction):
    help_text = (
        "**Gravity List Bot v3.2 Commands**\n\n"
        "/create_list name:<list>\n"
        "/add_name list_name:<list> name:<entry> category:<cat> comment:<optional>\n"
        "/remove_name list_name:<list> name:<entry>\n"
        "/edit_name list_name:<list> old_name:<old> new_name:<new> new_category:<cat> new_comment:<optional>\n"
        "/delete_list name:<list>\n\n"
        "/add_timer_to_list list_name:<list> name:<timer> hours:<int> minutes:<int>\n\n"
        "/add_text list_name:<list> text:<note>\n"
        "/add_header list_name:<list> header:<text>\n\n"
        "/lists name:<list>        - show/update any dashboard\n"
        "/list_all                - (Admin) list all lists\n"
        "/resync_timers           - (Admin) force-refresh list dashboards\n"
    )
    await interaction.response.send_message(help_text, ephemeral=True)

bot.run(TOKEN)
