import os
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv

from data_manager import (
    load_list, save_list, list_exists, delete_list,
    get_all_list_names, get_all_gen_list_names,
    save_dashboard_id, save_gen_dashboard_id,
    gen_list_exists
)
from timers import TimerCog
from gen_timers import setup_gen_timers, build_gen_timetable_embed
from logging_cog import LoggingCog

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", 0))

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

CATEGORY_EMOJIS = {
    "Owner": "👑", "Enemy": "🔴", "Friend": "🟢",
    "Ally":   "🔵", "Beta":  "🟡", "Item":  "⚫"
}


def build_embed(list_name: str) -> discord.Embed:
    data = load_list(list_name)
    embed = discord.Embed(title=f"{list_name} List", color=0x808080)

    data.sort(key=lambda x: (
        0 if x.get("category") == "Header" else
        1 if x.get("category") == "Text"   else
        2 if x.get("category") == "Timer"  else
        3
    ))

    for it in data:
        cat = it["category"]
        if cat == "Header":
            embed.add_field(name="\u200b", value=f"**{it['name']}**", inline=False)
        elif cat == "Text":
            embed.add_field(name=f"• {it['name']}", value="\u200b", inline=False)
        elif cat == "Timer":
            end_ts = int(it.get("timer_end") or (it["timer_start"] + it["timer_duration"]))
            embed.add_field(name=f"⏳   {it['name']} — <t:{end_ts}:R>",
                            value="\u200b", inline=False)
        else:
            prefix = CATEGORY_EMOJIS.get(cat, "")
            embed.add_field(name=f"{prefix}   {it['name']}",
                            value="\u200b", inline=False)
            if it.get("comment"):
                embed.add_field(name="\u200b", value=f"*{it['comment']}*", inline=False)

    return embed


@bot.event
async def on_ready():
    await bot.add_cog(TimerCog(bot))
    await bot.add_cog(LoggingCog(bot))
    await setup_gen_timers(bot)
    
# Sync commands
    if GUILD_ID:
        await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
    else:
        await bot.tree.sync()
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")


# List CRUD

@bot.tree.command(name="create_list", description="Create a new list")
@app_commands.describe(name="Name of the new list")
async def create_list_cmd(interaction: discord.Interaction, name: str):
    if list_exists(name):
        return await interaction.response.send_message(
            f"⚠️ List '{name}' already exists.", ephemeral=True
        )
    save_list(name, [])
    await interaction.response.send_message(
        f"✅ Created list '{name}'.", ephemeral=True
    )


@bot.tree.command(name="delete_list", description="Delete an existing list")
@app_commands.describe(name="Name of the list to delete")
async def delete_list_cmd(interaction: discord.Interaction, name: str):
    if not list_exists(name):
        return await interaction.response.send_message(
            f"❌ No list named '{name}'.", ephemeral=True
        )
    delete_list(name)
    await interaction.response.send_message(
        f"✅ Deleted list '{name}'.", ephemeral=True
    )


@bot.tree.command(name="add_header", description="Add a header to a list")
@app_commands.describe(list_name="List to modify", header="Header text")
async def add_header(interaction: discord.Interaction, list_name: str, header: str):
    if not list_exists(list_name):
        return await interaction.response.send_message(
            f"❌ No list named '{list_name}'.", ephemeral=True
        )
    data = load_list(list_name)
    data.append({"category": "Header", "name": header})
    save_list(list_name, data)
    await interaction.response.send_message(
        f"✅ Added header to '{list_name}': **{header}**", ephemeral=True
    )


@bot.tree.command(name="remove_header", description="Remove a header by its index")
@app_commands.describe(list_name="List to modify", index="Header position (1-based)")
async def remove_header(interaction: discord.Interaction, list_name: str, index: int):
    if not list_exists(list_name):
        return await interaction.response.send_message(
            f"❌ No list named '{list_name}'.", ephemeral=True
        )
    data = load_list(list_name)
    header_idxs = [i for i, x in enumerate(data) if x.get("category") == "Header"]
    if index < 1 or index > len(header_idxs):
        return await interaction.response.send_message(
            "❌ Invalid header index.", ephemeral=True
        )
    removed = data.pop(header_idxs[index - 1])
    save_list(list_name, data)
    await interaction.response.send_message(
        f"✅ Removed header #{index}: **{removed['name']}**", ephemeral=True
    )


@bot.tree.command(name="add_text", description="Add a free-text line to a list")
@app_commands.describe(list_name="List to modify", text="Line of text to add")
async def add_text(interaction: discord.Interaction, list_name: str, text: str):
    if not list_exists(list_name):
        return await interaction.response.send_message(
            f"❌ No list named '{list_name}'.", ephemeral=True
        )
    data = load_list(list_name)
    data.append({"category": "Text", "name": text})
    save_list(list_name, data)
    await interaction.response.send_message(
        f"✅ Added text to '{list_name}': {text}", ephemeral=True
    )


@bot.tree.command(name="edit_text", description="Edit one of the free-text lines")
@app_commands.describe(
    list_name="List to modify",
    index="Text line number (1-based)",
    new_text="Updated text"
)
async def edit_text(interaction: discord.Interaction, list_name: str, index: int, new_text: str):
    if not list_exists(list_name):
        return await interaction.response.send_message(
            f"❌ No list named '{list_name}'.", ephemeral=True
        )
    data = load_list(list_name)
    text_idxs = [i for i, x in enumerate(data) if x.get("category") == "Text"]
    if index < 1 or index > len(text_idxs):
        return await interaction.response.send_message(
            "❌ Invalid text index.", ephemeral=True
        )
    data[text_idxs[index - 1]]["name"] = new_text
    save_list(list_name, data)
    await interaction.response.send_message(
        f"✅ Updated text #{index}.", ephemeral=True
    )


@bot.tree.command(name="remove_text", description="Remove a free-text line")
@app_commands.describe(list_name="List to modify", index="Text line number (1-based)")
async def remove_text(interaction: discord.Interaction, list_name: str, index: int):
    if not list_exists(list_name):
        return await interaction.response.send_message(
            f"❌ No list named '{list_name}'.", ephemeral=True
        )
    data = load_list(list_name)
    text_idxs = [i for i, x in enumerate(data) if x.get("category") == "Text"]
    if index < 1 or index > len(text_idxs):
        return await interaction.response.send_message(
            "❌ Invalid text index.", ephemeral=True
        )
    removed = data.pop(text_idxs[index - 1])
    save_list(list_name, data)
    await interaction.response.send_message(
        f"✅ Removed text #{index}: {removed['name']}", ephemeral=True
    )


@bot.tree.command(name="add_name", description="Add an item to a list with a category")
@app_commands.describe(
    list_name="List to modify",
    category="Category (Owner, Enemy, Friend, Ally, Beta, Item)",
    item_name="Item to add"
)
async def add_name(interaction: discord.Interaction, list_name: str, category: str, item_name: str):
    if not list_exists(list_name):
        return await interaction.response.send_message(
            f"❌ No list named '{list_name}'.", ephemeral=True
        )
    if category not in CATEGORY_EMOJIS:
        return await interaction.response.send_message(
            f"❌ Invalid category. Choose from: {', '.join(CATEGORY_EMOJIS)}", ephemeral=True
        )
    data = load_list(list_name)
    data.append({"category": category, "name": item_name})
    save_list(list_name, data)
    await interaction.response.send_message(
        f"✅ Added {CATEGORY_EMOJIS[category]} **{item_name}** to '{list_name}'.", ephemeral=True
    )


@bot.tree.command(name="remove_name", description="Remove an item from a list")
@app_commands.describe(list_name="List to modify", item_name="Exact item name to remove")
async def remove_name(interaction: discord.Interaction, list_name: str, item_name: str):
    if not list_exists(list_name):
        return await interaction.response.send_message(
            f"❌ No list named '{list_name}'.", ephemeral=True
        )
    data = load_list(list_name)
    for i, it in enumerate(data):
        if it.get("name") == item_name and it.get("category") not in ("Header", "Text", "Timer"):
            data.pop(i)
            save_list(list_name, data)
            return await interaction.response.send_message(
                f"✅ Removed **{item_name}**.", ephemeral=True
            )
    await interaction.response.send_message(
        f"❌ Item '{item_name}' not found.", ephemeral=True
    )


@bot.tree.command(name="edit_name", description="Rename an item in a list")
@app_commands.describe(
    list_name="List to modify",
    old_name="Current item name",
    new_name="New item name"
)
async def edit_name(interaction: discord.Interaction, list_name: str, old_name: str, new_name: str):
    if not list_exists(list_name):
        return await interaction.response.send_message(
            f"❌ No list named '{list_name}'.", ephemeral=True
        )
    data = load_list(list_name)
    for it in data:
        if it.get("name") == old_name and it.get("category") not in ("Header", "Text", "Timer"):
            it["name"] = new_name
            save_list(list_name, data)
            return await interaction.response.send_message(
                f"✅ Renamed **{old_name}** → **{new_name}**.", ephemeral=True
            )
    await interaction.response.send_message(
        f"❌ Item '{old_name}' not found.", ephemeral=True
    )


@bot.tree.command(name="move_name", description="Move an item to a new position in a list")
@app_commands.describe(
    list_name="List to modify",
    item_name="Item to move",
    position="New 1-based position"
)
async def move_name(interaction: discord.Interaction, list_name: str, item_name: str, position: int):
    if not list_exists(list_name):
        return await interaction.response.send_message(
            f"❌ No list named '{list_name}'.", ephemeral=True
        )
    data = load_list(list_name)
    for idx, it in enumerate(data):
        if it.get("name") == item_name and it.get("category") not in ("Header", "Text", "Timer"):
            entry = data.pop(idx)
            break
    else:
        return await interaction.response.send_message(
            f"❌ Item '{item_name}' not found.", ephemeral=True
        )
    pos = max(1, min(position, len(data) + 1))
    data.insert(pos - 1, entry)
    save_list(list_name, data)
    await interaction.response.send_message(
        f"✅ Moved **{item_name}** to position {pos}.", ephemeral=True
    )


@bot.tree.command(name="sort_list", description="Alphabetically sort items (ignores headers/text)")
@app_commands.describe(list_name="List to sort")
async def sort_list(interaction: discord.Interaction, list_name: str):
    if not list_exists(list_name):
        return await interaction.response.send_message(
            f"❌ No list named '{list_name}'.", ephemeral=True
        )
    data = load_list(list_name)
    name_items = sorted(
        [it for it in data if it.get("category") not in ("Header", "Timer", "Text")],
        key=lambda x: x["name"].lower()
    )
    new_data = [it for it in data if it.get("category") in ("Header", "Timer", "Text")] + name_items
    save_list(list_name, new_data)
    await interaction.response.send_message(
        f"✅ Sorted items in '{list_name}'.", ephemeral=True
    )


@bot.tree.command(name="add_comment", description="Attach a comment to a list item")
@app_commands.describe(
    list_name="List to modify",
    item_name="Item to comment on",
    comment="Comment text"
)
async def add_comment(interaction: discord.Interaction, list_name: str, item_name: str, comment: str):
    if not list_exists(list_name):
        return await interaction.response.send_message(
            f"❌ No list named '{list_name}'.", ephemeral=True
        )
    data = load_list(list_name)
    for it in data:
        if it.get("name") == item_name and it.get("category") not in ("Header", "Text", "Timer"):
            it["comment"] = comment
            save_list(list_name, data)
            return await interaction.response.send_message(
                f"✅ Comment added to **{item_name}**.", ephemeral=True
            )
    await interaction.response.send_message(
        f"❌ Item '{item_name}' not found.", ephemeral=True
    )


@bot.tree.command(name="edit_comment", description="Edit an existing comment")
@app_commands.describe(
    list_name="List to modify",
    item_name="Item whose comment to edit",
    new_comment="Updated comment text"
)
async def edit_comment(interaction: discord.Interaction, list_name: str, item_name: str, new_comment: str):
    if not list_exists(list_name):
        return await interaction.response.send_message(
            f"❌ No list named '{list_name}'.", ephemeral=True
        )
    data = load_list(list_name)
    for it in data:
        if it.get("name") == item_name and "comment" in it:
            it["comment"] = new_comment
            save_list(list_name, data)
            return await interaction.response.send_message(
                f"✅ Comment updated for **{item_name}**.", ephemeral=True
            )
    await interaction.response.send_message(
        f"❌ No existing comment on '{item_name}'.", ephemeral=True
    )


@bot.tree.command(name="remove_comment", description="Remove a comment from an item")
@app_commands.describe(
    list_name="List to modify",
    item_name="Item whose comment to remove"
)
async def remove_comment(interaction: discord.Interaction, list_name: str, item_name: str):
    if not list_exists(list_name):
        return await interaction.response.send_message(
            f"❌ No list named '{list_name}'.", ephemeral=True
        )
    data = load_list(list_name)
    for it in data:
        if it.get("name") == item_NAME and "comment" in it:
            del it["comment"]
            save_list(list_name, data)
            return await interaction.response.send_message(
                f"✅ Comment removed from **{item_name}**.", ephemeral=True
            )
    await interaction.response.send_message(
        f"❌ No comment found on '{item_name}'.", ephemeral=True
    )


# Viewing existing lists

@bot.tree.command(name="view_lists", description="View all existing lists")
async def view_lists_cmd(interaction: discord.Interaction):
    names = get_all_list_names()
    if not names:
        return await interaction.response.send_message("⚠️ No lists found.", ephemeral=True)
    await interaction.response.send_message(
        "📋 Existing lists:\n" + "\n".join(f"- `{n}`" for n in sorted(names)),
        ephemeral=True
    )


@bot.tree.command(name="view_gen_lists", description="View all existing generator lists")
async def view_gen_lists_cmd(interaction: discord.Interaction):
    names = get_all_gen_list_names()
    if not names:
        return await interaction.response.send_message("⚠️ No generator lists found.", ephemeral=True)
    await interaction.response.send_message(
        "📊 Existing generator lists:\n" + "\n".join(f"- `{n}`" for n in sorted(names)),
        ephemeral=True
    )


# Deploy commands

@bot.tree.command(name="deploy_list", description="Show or deploy a regular list")
@app_commands.describe(name="Name of the list")
async def deploy_list_cmd(interaction: discord.Interaction, name: str):
    if list_exists(name):
        embed = build_embed(name)
        await interaction.response.send_message(embed=embed)
        sent = await interaction.original_response()
        save_dashboard_id(name, sent.channel.id, sent.id)
    else:
        await interaction.response.send_message(
            f"❌ No list named '{name}'.", ephemeral=True
        )


@bot.tree.command(name="deploy_gen_list", description="Show or deploy a generator dashboard")
@app_commands.describe(name="Name of the generator list")
async def deploy_gen_list_cmd(interaction: discord.Interaction, name: str):
    if gen_list_exists(name):
        embed = build_gen_timetable_embed(name)
        await interaction.response.send_message(embed=embed)
        sent = await interaction.original_response()
        save_gen_dashboard_id(name, sent.channel.id, sent.id)
    else:
        await interaction.response.send_message(
            f"❌ No generator list named '{name}'.", ephemeral=True
        )


# Help & Log Channel

@bot.tree.command(name="help", description="Show usage instructions")
async def help_cmd(interaction: discord.Interaction):
    help_text = (
        "**Gravity List Bot**\n"
        "• `/view_lists` — list all your lists\n"
        "• `/view_gen_lists` — list all your generator lists\n"
        "• `/deploy_list name:<list>` — deploy/update a regular list\n"
        "• `/deploy_gen_list name:<gen_list>` — deploy/update a generator dashboard\n"
        "• **List CRUD**: `/create_list`, `/delete_list`, `/add_header`, `/remove_header`, `/add_text`, `/edit_text`, `/remove_text`, `/add_name`, `/remove_name`, `/edit_name`, `/move_name`, `/sort_list`\n"
        "• **Comments**: `/add_comment`, `/edit_comment`, `/remove_comment`\n"
        "• **Timers**: `/create_timer`, `/pause_timer`, `/resume_timer`, `/edit_timer`, `/delete_timer`\n"
        "• **Gen Dashboards**: `/create_gen_list`, `/delete_gen_list`, `/add_gen`, `/edit_gen`, `/remove_gen`, `/set_gen_role`\n"
        "• `/set_log_channel <#channel>` — change where warnings/errors post\n"
        "Full details in `README.md`."
    )
    await interaction.response.send_message(help_text, ephemeral=True)


@bot.tree.command(
    name="set_log_channel",
    description="Set which channel receives bot logs"
)
@app_commands.default_permissions(administrator=True)
@app_commands.describe(channel="Text channel for logs")
async def set_log_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    cog = bot.get_cog("LoggingCog")
    if not cog or not hasattr(cog, "handler"):
        return await interaction.response.send_message(
            "❌ Logging not enabled. Check `LOG_CHANNEL_ID` in `.env`.", ephemeral=True
        )
    cog.handler.channel_id = channel.id
    await interaction.response.send_message(
        f"✅ Log channel set to {channel.mention}", ephemeral=True
    )


bot.run(TOKEN)
