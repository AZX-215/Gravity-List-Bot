import os
import time
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv

from data_manager import (
    load_list, save_list, list_exists, delete_list,
    get_all_list_names, get_all_gen_list_names,
    save_dashboard_id, get_dashboard_id, get_all_dashboards, get_list_hash
)
from timers import setup as setup_timers
from gen_timers import setup as setup_gen_timers, build_gen_embed

load_dotenv()
TOKEN     = os.getenv("DISCORD_TOKEN")
CLIENT_ID = int(os.getenv("CLIENT_ID"))

intents = discord.Intents.default()
intents.guilds = True
bot = commands.Bot(command_prefix="!", intents=intents, application_id=CLIENT_ID)

CATEGORY_EMOJIS = {
    "Owner": "👑", "Enemy": "🔴", "Friend": "🟢",
    "Ally":   "🔵", "Beta":   "🟡", "Timer":"⏳"
}

# Helper to push a list dashboard update if one exists
async def push_list_update(list_name):
    dash = get_dashboard_id(list_name)
    if dash:
        channel_id, message_id = dash
        ch = bot.get_channel(channel_id)
        if ch:
            try:
                msg = await ch.fetch_message(message_id)
                await msg.edit(embed=build_embed(list_name))
            except Exception as e:
                print(f"Error updating dashboard {list_name}: {e}")

def build_embed(list_name: str) -> discord.Embed:
    """Embed for regular lists, including inline timers. Improved with spacing."""
    data = load_list(list_name)
    embed = discord.Embed(title=f"{list_name} List", color=0x808080)
    # Add extra space under the title
    embed.add_field(name="\u200b", value="\u200b", inline=False)  # Blank line for breathing room

    now = time.time()
    for item in data:
        if item.get("category") == "Timer":
            start = item["timer_start"]
            dur   = item["timer_duration"]
            rem   = max(0, int(start + dur - now))
            h, r  = divmod(rem, 3600)
            m, s  = divmod(r, 60)
            # Add extra spaces after emoji for visual padding
            name_field = f"⏳   {item['name']} — {h:02d}h {m:02d}m {s:02d}s"
        else:
            # Add extra spaces after emoji for visual padding
            name_field = f"{CATEGORY_EMOJIS.get(item['category'],'')}   {item['name']}"
        embed.add_field(name=name_field, value="\u200b", inline=False)
    return embed


@bot.event
async def on_ready():
    # start standalone timers Cog (1s updates)
    await setup_timers(bot)
    # start generator Cog (2m updates, or whatever you have set)
    await setup_gen_timers(bot)
    # sync slash commands
    await bot.tree.sync()
    print(f"Bot ready. Commands synced for {bot.user}")

# ━━━ Regular List Commands ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@bot.tree.command(name="create_list", description="Create a new list")
@app_commands.describe(name="Name of the new list")
async def create_list(interaction: discord.Interaction, name: str):
    if list_exists(name):
        return await interaction.response.send_message(
            f"⚠️ List '{name}' already exists.", ephemeral=True
        )
    save_list(name, [])
    await interaction.response.send_message(
        f"✅ Created list '{name}'.", ephemeral=True
    )

@bot.tree.command(name="add_name", description="Add an entry to a list")
@app_commands.describe(
    list_name="Which list", name="Entry name", category="Category emoji"
)
@app_commands.choices(category=[
    app_commands.Choice(name=k, value=k)
    for k in CATEGORY_EMOJIS if k != "Timer"
])
async def add_name(
    interaction: discord.Interaction,
    list_name: str,
    name: str,
    category: app_commands.Choice[str]
):
    if not list_exists(list_name):
        return await interaction.response.send_message(
            f"❌ List '{list_name}' not found.", ephemeral=True
        )
    data = load_list(list_name)
    data.append({"name": name, "category": category.value})
    save_list(list_name, data)
    await interaction.response.send_message(
        f"✅ Added '{name}' to '{list_name}'.", ephemeral=True
    )
    await push_list_update(list_name)

@bot.tree.command(name="remove_name", description="Remove an entry from a list")
@app_commands.describe(list_name="Which list", name="Entry to remove")
async def remove_name(
    interaction: discord.Interaction,
    list_name: str,
    name: str
):
    if not list_exists(list_name):
        return await interaction.response.send_message(
            f"❌ List '{list_name}' not found.", ephemeral=True
        )
    data = [e for e in load_list(list_name) if e["name"].lower() != name.lower()]
    save_list(list_name, data)
    await interaction.response.send_message(
        f"🗑️ Removed '{name}' from '{list_name}'.", ephemeral=True
    )
    await push_list_update(list_name)

@bot.tree.command(name="edit_name", description="Edit an entry in a list")
@app_commands.describe(
    list_name="Which list",
    old_name="Existing entry",
    new_name="New entry name",
    new_category="New category"
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
    new_category: app_commands.Choice[str]
):
    if not list_exists(list_name):
        return await interaction.response.send_message(
            f"❌ List '{list_name}' not found.", ephemeral=True
        )
    data = load_list(list_name)
    for e in data:
        if e["name"].lower() == old_name.lower():
            e["name"] = new_name
            e["category"] = new_category.value
            break
    save_list(list_name, data)
    await interaction.response.send_message(
        f"✏️ Updated '{old_name}'.", ephemeral=True
    )
    await push_list_update(list_name)

@bot.tree.command(name="delete_list", description="Delete an entire list")
@app_commands.describe(name="Name of the list to delete")
async def delete_list_cmd(
    interaction: discord.Interaction,
    name: str
):
    if not list_exists(name):
        return await interaction.response.send_message(
            f"⚠️ List '{name}' not found.", ephemeral=True
        )
    delete_list(name)
    await interaction.response.send_message(
        f"🗑️ Deleted list '{name}'.", ephemeral=True
    )
    # No update needed—dashboard is deleted with list

# ━━━ Inline Timer in List ━━━━━━━━━━━━━━━━━━━━━━━━━━━━

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
        return await interaction.response.send_message(
            f"❌ List '{list_name}' not found.", ephemeral=True
        )
    total = hours * 3600 + minutes * 60
    entry = {
        "name": name,
        "category": "Timer",
        "timer_start": time.time(),
        "timer_duration": total
    }
    data = load_list(list_name)
    data.append(entry)
    save_list(list_name, data)
    await interaction.response.send_message(
        f"⏳ Timer '{name}' added to '{list_name}'.", ephemeral=True
    )
    await push_list_update(list_name)

# ━━━ Dashboard Display ━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@bot.tree.command(name="lists", description="Show or update any list dashboard")
@app_commands.describe(name="List name")
async def lists(interaction: discord.Interaction, name: str):
    # Regular lists
    if list_exists(name):
        embed = build_embed(name)
        dash  = get_dashboard_id(name)
        if dash:
            channel_id, message_id = dash
            ch = interaction.guild.get_channel(channel_id)
            if ch:
                try:
                    msg = await ch.fetch_message(message_id)
                    await msg.edit(embed=embed)
                    return await interaction.response.send_message(
                        f"✅ Refreshed '{name}'.", ephemeral=True
                    )
                except:
                    pass
        # no existing dashboard
        await interaction.response.send_message(embed=embed)
        msg = await interaction.original_response()
        save_dashboard_id(name, msg.channel.id, msg.id)
        return

    # Generator lists
    if name in get_all_gen_list_names():
        embed = build_gen_embed(name)
        from data_manager import get_gen_dashboard_id, save_gen_dashboard_id
        dash = get_gen_dashboard_id(name)
        if dash:
            channel_id, message_id = dash
            ch = interaction.guild.get_channel(channel_id)
            if ch:
                try:
                    msg = await ch.fetch_message(message_id)
                    return await interaction.response.send_message(
                        f"✅ Refreshed gen '{name}'.", embed=embed, ephemeral=True
                    )
                except:
                    pass
        await interaction.response.send_message(embed=embed)
        msg = await interaction.original_response()
        save_gen_dashboard_id(name, msg.channel.id, msg.id)
        return

    # Not found
    await interaction.response.send_message(
        f"❌ '{name}' not found.", ephemeral=True
    )

# ━━━ Overview & Help ━━━━━━━━━━━━━━━━━━━━━━━━━━━━

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

@bot.tree.command(name="help", description="Show usage instructions")
async def help_command(interaction: discord.Interaction):
    help_text = (
        "**Gravity List Bot Commands**\n\n"
        "/create_list name:<list>\n"
        "/add_name list_name:<list> name:<entry> category:<cat>\n"
        "/remove_name list_name:<list> name:<entry>\n"
        "/edit_name list_name:<list> old_name:<old> new_name:<new> new_category:<cat>\n"
        "/delete_list name:<list>\n\n"
        "/add_timer_to_list list_name:<list> name:<timer> hours:<int> minutes:<int>\n\n"
        "/create_timer name:<timer> hours:<int> minutes:<int>\n"
        "/pause_timer name:<timer>\n"
        "/resume_timer name:<timer>\n"
        "/delete_timer name:<timer>\n\n"
        "/create_generator_list name:<list>\n"
        "/add_generator list_name:<list> entry_name:<gen> gen_type:<Tek|Electrical> element:<int> shards:<int> gas:<int> imbued:<int>\n"
        "/edit_generator list_name:<list> old_name:<old> new_name:<new> element:<int> shards:<int> gas:<int> imbued:<int>\n"
        "/remove_generator list_name:<list> entry_name:<gen>\n"
        "/delete_generator_list name:<list>\n\n"
        "/lists name:<list>        - show or refresh any dashboard embed\n"
        "/list_all                - (Admin) list all list names\n"
    )
    await interaction.response.send_message(help_text, ephemeral=True)

bot.run(TOKEN)
