import os
import asyncio
import discord
# from bm_asa import setup_bm_asa  # ← moved behind a feature flag (see on_ready)
from arkstatus_asa import setup_arkstatus_asa
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv

from data_manager import (
    load_list, save_list, list_exists, delete_list,
    get_all_list_names, get_all_gen_list_names,
    save_dashboard_id, get_dashboard_id,
    save_gen_dashboard_id, gen_list_exists
)
from timers import TimerCog
from gen_timers import setup_gen_timers, build_gen_timetable_embed
from logging_cog import LoggingCog

# ── Screenshot ingest API (safe import) ─────────────────────────────────────
try:
    from screenshots_api import setup_screenshot_api, run_fastapi_in_thread
except Exception:
    setup_screenshot_api = None
    run_fastapi_in_thread = None
# ───────────────────────────────────────────────────────────────────────────

load_dotenv()
TOKEN    = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", 0))

intents = discord.Intents.default()
bot     = commands.Bot(command_prefix="!", intents=intents)

# ── Start FastAPI in a background thread; defer worker until loop exists ───
if setup_screenshot_api and run_fastapi_in_thread:
    try:
        # CHANGED: setup returns (app, start_worker) now
        api_app, start_screenshot_worker = setup_screenshot_api(bot)
        run_fastapi_in_thread(api_app, int(os.getenv("PORT", "8080")))
        # stash starter to call inside on_ready
        bot._start_screenshot_worker = start_screenshot_worker
        print("[screenshots_api] http server started")
    except Exception as e:
        print(f"[screenshots_api] not started: {e}")
# ───────────────────────────────────────────────────────────────────────────

# Category sort order for embed building and sort_list
CATEGORY_EMOJIS = {
    "Owner": "👑", "Friend": "🟢", "Ally": "🔵",
    "Beta":  "🟡", "Enemy":  "🔴", "Item":  "⚫"
}

# --- Embed safety helpers (avoid 1024-char field value limit) ---
EMBED_FIELD_VALUE_MAX = 1024

def add_chunked_comment_field(embed: discord.Embed, comment_text: str) -> None:
    """Add a comment as one or more fields, each ≤1024 chars, keeping italics."""
    if not comment_text:
        return
    s = str(comment_text)
    if len(s) <= EMBED_FIELD_VALUE_MAX:
        embed.add_field(name="​", value=f"*{s}*", inline=False)
        return

    parts = []
    start = 0
    n = len(s)
    while start < n:
        parts.append(s[start:start + EMBED_FIELD_VALUE_MAX])
        start += EMBED_FIELD_VALUE_MAX

    total = len(parts)
    for i, part in enumerate(parts, start=1):
        suffix = "" if i == 1 else f" (cont. {i}/{total})"
        embed.add_field(name=f"​{suffix}", value=f"*{part}*", inline=False)

CATEGORY_ORDER = ["Category", "Text", "Bullet"] + list(CATEGORY_EMOJIS.keys())

# ━━━ helper: update a deployed regular-list dashboard ━━━━━━━━━━━━━━━━━━━━━━━
async def update_list_dashboard(list_name: str):
    dash = get_dashboard_id(list_name)
    if not dash:
        return
    channel_id, message_id = dash
    channel = bot.get_channel(channel_id)
    if not channel:
        return
    try:
        msg = await channel.fetch_message(message_id)
        embed = build_embed(list_name)
        await msg.edit(embed=embed)
    except discord.HTTPException:
        pass
    except Exception:
        pass

# ━━━ embed builder for regular lists ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def build_embed(list_name: str) -> discord.Embed:
    # Load original data and compute per-type ordinals in the ORIGINAL order,
    # so indices match what the edit/move/assign commands expect.
    original = load_list(list_name)

    cat_i = text_i = bullet_i = name_i = 0
    annotated = []
    for it in original:
        it = dict(it)  # shallow copy so we don't mutate stored data
        cat = it.get("category")
        if cat == "Category":
            cat_i += 1
            it["_ord_cat"] = cat_i
        elif cat == "Text":
            text_i += 1
            it["_ord_text"] = text_i
        elif cat == "Bullet":
            bullet_i += 1
            it["_ord_bullet"] = bullet_i
        else:
            # This is a "Name" entry (Owner/Friend/Ally/Beta/Enemy/Item)
            name_i += 1
            it["_ord_name"] = name_i
        annotated.append(it)

    # For display we keep your existing visual sort by CATEGORY_ORDER.
    data = sorted(
        annotated,
        key=lambda x: CATEGORY_ORDER.index(x["category"]) if x["category"] in CATEGORY_ORDER else len(CATEGORY_ORDER)
    )

    embed = discord.Embed(title=f"__**{list_name}**__", color=0x808080)

    for it in data:
        cat = it["category"]
        if cat == "Category":
            # Show the user-facing index for categories
            ord_cat = it.get("_ord_cat", 0)
            embed.add_field(name="​", value=f"**{ord_cat}. {it['name']}**", inline=False)

        elif cat == "Text":
            ord_text = it.get("_ord_text", 0)
            # Put the index in the field name so it’s easy to reference
            embed.add_field(name=f"{ord_text}. {it['name']}", value="​", inline=False)

        elif cat == "Bullet":
            ord_bul = it.get("_ord_bullet", 0)
            embed.add_field(name=f"{ord_bul}. • {it['name']}", value="​", inline=False)

        else:
            # Named entries get an index that matches the /assign_to_category entry_index for "Name"
            ord_name = it.get("_ord_name", 0)
            prefix = CATEGORY_EMOJIS.get(cat, "")
            embed.add_field(name=f"{prefix}   {ord_name}. {it['name']}", value="​", inline=False)

            # Preserve your existing comment handling (chunking elsewhere)
            if it.get("comment"):
                add_chunked_comment_field(embed, it["comment"])

    return embed



@bot.event
async def on_ready():
    # prevent duplicate startup on reconnects
    if getattr(bot, "_startup_done", False):
        print("[on_ready] already initialized; skipping setup")
        return

    # --- Load debug_storage extension (optional; default enabled) ---
    if os.getenv("ENABLE_DEBUG_STORAGE", "1") == "1" and "debug_storage" not in bot.extensions:
        try:
            await bot.load_extension("debug_storage")
            print("[debug_storage] loaded")
        except Exception as e:
            print(f"[debug_storage] not loaded: {e}")

    # --- Load debug extension (non-invasive diagnostics) ---
    if "debug" not in bot.extensions:
        try:
            await bot.load_extension("debug")
            print("[debug] loaded")
        except Exception as e:
            print(f"[debug] not loaded: {e}")

    # Your existing startup wiring (guard cogs to avoid duplicates)
    if not bot.get_cog("TimerCog"):
        await bot.add_cog(TimerCog(bot))
    if not bot.get_cog("LoggingCog"):
        await bot.add_cog(LoggingCog(bot))

    await setup_gen_timers(bot)

    # ── Feature flag: BattleMetrics (enable/disable via env) ────────────────
    if os.getenv("ENABLE_BATTLEMETRICS", "True") == "True":
        try:
            from bm_asa import setup_bm_asa  # import only if enabled
            await setup_bm_asa(bot)
            print("[bm_asa] enabled")
        except Exception as e:
            print(f"[bm_asa] not enabled: {e}")
    else:
        print("[bm_asa] disabled via ENABLE_BATTLEMETRICS")

    # --- Ark Status integration (always on unless it throws) ---
    await setup_arkstatus_asa(bot)

    # --- NEW: Load Gravity Capture downloader (GitHub Releases) ---
    if "gravity_capture" not in bot.extensions:
        try:
            await bot.load_extension("gravity_capture")  # file `gravity_capture.py` next to bot.py or on PYTHONPATH
            print("[gravity_capture] loaded")
        except Exception as e:
            print(f"[gravity_capture] not loaded: {e}")

    # Slash command sync
    if GUILD_ID:
        await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
    else:
        await bot.tree.sync()

    # Start screenshot worker once the loop is alive (runs only once)
    if getattr(bot, "_start_screenshot_worker", None) and not getattr(bot, "_shot_worker_started", False):
        try:
            await bot._start_screenshot_worker()
            bot._shot_worker_started = True
            print("[screenshots_api] worker started")
        except Exception as e:
            print(f"[screenshots_api] worker not started: {e}")

    bot._startup_done = True
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")


# ━━━ List CRUD ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.tree.command(name="create_list", description="Create a new list")
@app_commands.describe(name="Name of the new list")
async def create_list_cmd(interaction: discord.Interaction, name: str):
    if list_exists(name):
        return await interaction.response.send_message(f"⚠️ List '{name}' already exists.", ephemeral=True)
    save_list(name, [])
    await interaction.response.send_message(f"✅ Created list '{name}'.", ephemeral=True)

@bot.tree.command(name="delete_list", description="Delete an existing list")
@app_commands.describe(name="Name of the list to delete")
async def delete_list_cmd(interaction: discord.Interaction, name: str):
    if not list_exists(name):
        return await interaction.response.send_message(f"❌ No list named '{name}'.", ephemeral=True)
    delete_list(name)
    await interaction.response.send_message(f"✅ Deleted list '{name}'.", ephemeral=True)

# ━━━ Plain text entries ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.tree.command(name="add_list_category", description="Add a category header to a list")
@app_commands.describe(list_name="List to modify", title="Category title")
async def add_list_category(interaction: discord.Interaction, list_name: str, title: str):
    if not list_exists(list_name):
        return await interaction.response.send_message(f"❌ No list named '{list_name}'.", ephemeral=True)
    data = load_list(list_name)
    data.append({"category":"Category","name":title})
    save_list(list_name, data)
    await interaction.response.send_message(f"✅ Added category to '{list_name}': **{title}**", ephemeral=True)
    await update_list_dashboard(list_name)

@bot.tree.command(name="edit_list_category", description="Edit a category header")
@app_commands.describe(list_name="List to modify", index="Category position (1-based)", new_title="New category title")
async def edit_list_category(interaction: discord.Interaction, list_name: str, index: int, new_title: str):
    if not list_exists(list_name):
        return await interaction.response.send_message(f"❌ No list named '{list_name}'.", ephemeral=True)
    data = load_list(list_name)
    idxs = [i for i,x in enumerate(data) if x["category"]=="Category"]
    if index<1 or index>len(idxs):
        return await interaction.response.send_message("❌ Invalid category index.", ephemeral=True)
    data[idxs[index-1]]["name"] = new_title
    save_list(list_name, data)
    await interaction.response.send_message(f"✅ Updated category #{index} to **{new_title}**", ephemeral=True)
    await update_list_dashboard(list_name)

@bot.tree.command(name="remove_list_category", description="Remove a category header by index")
@app_commands.describe(list_name="List to modify", index="Category position (1-based)")
async def remove_list_category(interaction: discord.Interaction, list_name: str, index: int):
    if not list_exists(list_name):
        return await interaction.response.send_message(f"❌ No list named '{list_name}'.", ephemeral=True)
    data = load_list(list_name)
    idxs = [i for i,x in enumerate(data) if x["category"]=="Category"]
    if index<1 or index>len(idxs):
        return await interaction.response.send_message("❌ Invalid category index.", ephemeral=True)
    removed = data.pop(idxs[index-1])
    save_list(list_name, data)
    await interaction.response.send_message(f"✅ Removed category #{index}: **{removed['name']}**", ephemeral=True)
    await update_list_dashboard(list_name)

# ━━━ Plain text entries ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.tree.command(name="add_text", description="Add a plain text line to a list")
@app_commands.describe(list_name="List to modify", text="Text line to add")
async def add_text(interaction: discord.Interaction, list_name: str, text: str):
    if not list_exists(list_name):
        return await interaction.response.send_message(f"❌ No list named '{list_name}'.", ephemeral=True)
    data = load_list(list_name)
    data.append({"category":"Text","name":text})
    save_list(list_name, data)
    await interaction.response.send_message(f"✅ Added text to '{list_name}': {text}", ephemeral=True)
    await update_list_dashboard(list_name)

@bot.tree.command(name="edit_text", description="Edit a plain text line")
@app_commands.describe(list_name="List to modify", index="Text line # (1-based)", new_text="New text")
async def edit_text(interaction: discord.Interaction, list_name: str, index: int, new_text: str):
    if not list_exists(list_name):
        return await interaction.response.send_message(f"❌ No list named '{list_name}'.", ephemeral=True)
    data = load_list(list_name)
    txt_idxs = [i for i,x in enumerate(data) if x["category"]=="Text"]
    if index<1 or index>len(txt_idxs):
        return await interaction.response.send_message("❌ Invalid text index.", ephemeral=True)
    data[txt_idxs[index-1]]["name"] = new_text
    save_list(list_name, data)
    await interaction.response.send_message(f"✅ Updated text #{index}.", ephemeral=True)
    await update_list_dashboard(list_name)

@bot.tree.command(name="remove_text", description="Remove a plain text line")
@app_commands.describe(list_name="List to modify", index="Text line # (1-based)")
async def remove_text(interaction: discord.Interaction, list_name: str, index: int):
    if not list_exists(list_name):
        return await interaction.response.send_message(f"❌ No list named '{list_name}'.", ephemeral=True)
    data = load_list(list_name)
    txt_idxs = [i for i,x in enumerate(data) if x["category"]=="Text"]
    if index<1 or index>len(txt_idxs):
        return await interaction.response.send_message("❌ Invalid text index.", ephemeral=True)
    removed = data.pop(txt_idxs[index-1])
    save_list(list_name, data)
    await interaction.response.send_message(f"✅ Removed text #{index}: {removed['name']}", ephemeral=True)
    await update_list_dashboard(list_name)

# ━━━ Bullet entries ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.tree.command(name="add_bullet", description="Add a bullet entry to a list")
@app_commands.describe(list_name="List to modify", bullet="Bullet point to add")
async def add_bullet(interaction: discord.Interaction, list_name: str, bullet: str):
    if not list_exists(list_name):
        return await interaction.response.send_message(f"❌ No list named '{list_name}'.", ephemeral=True)
    data = load_list(list_name)
    data.append({"category":"Bullet","name":bullet})
    save_list(list_name, data)
    await interaction.response.send_message(f"✅ Added bullet to '{list_name}': • {bullet}", ephemeral=True)
    await update_list_dashboard(list_name)

@bot.tree.command(name="edit_bullet", description="Edit a bullet entry")
@app_commands.describe(list_name="List to modify", index="Bullet # (1-based)", new_bullet="Updated bullet text")
async def edit_bullet(interaction: discord.Interaction, list_name: str, index: int, new_bullet: str):
    if not list_exists(list_name):
        return await interaction.response.send_message(f"❌ No list named '{list_name}'.", ephemeral=True)
    data = load_list(list_name)
    bul_idxs = [i for i,x in enumerate(data) if x["category"]=="Bullet"]
    if index<1 or index>len(bul_idxs):
        return await interaction.response.send_message("❌ Invalid bullet index.", ephemeral=True)
    data[bul_idxs[index-1]]["name"] = new_bullet
    save_list(list_name, data)
    await interaction.response.send_message(f"✅ Updated bullet #{index}.", ephemeral=True)
    await update_list_dashboard(list_name)

@bot.tree.command(name="remove_bullet", description="Remove a bullet entry")
@app_commands.describe(list_name="List to modify", index="Bullet # (1-based)")
async def remove_bullet(interaction: discord.Interaction, list_name: str, index: int):
    if not list_exists(list_name):
        return await interaction.response.send_message(f"❌ No list named '{list_name}'.", ephemeral=True)
    data = load_list(list_name)
    bul_idxs = [i for i,x in enumerate(data) if x["category"]=="Bullet"]
    if index<1 or index>len(bul_idxs):
        return await interaction.response.send_message("❌ Invalid bullet index.", ephemeral=True)
    removed = data.pop(bul_idxs[index-1])
    save_list(list_name, data)
    await interaction.response.send_message(f"✅ Removed bullet #{index}: {removed['name']}", ephemeral=True)
    await update_list_dashboard(list_name)

# ━━━ Entries CRUD with dropdowns ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.tree.command(name="add_name", description="Add an entry with category")
@app_commands.describe(
    list_name="List to modify",
    entry_name="Entry to add",
    category="Category for entry"
)
@app_commands.choices(category=[
    app_commands.Choice(name="Owner", value="Owner"),
    app_commands.Choice(name="Friend", value="Friend"),
    app_commands.Choice(name="Ally",   value="Ally"),
    app_commands.Choice(name="Beta",   value="Beta"),
    app_commands.Choice(name="Enemy",  value="Enemy"),
    app_commands.Choice(name="Item",   value="Item"),
])
async def add_name(interaction: discord.Interaction, list_name: str, entry_name: str, category: app_commands.Choice[str]):
    if not list_exists(list_name):
        return await interaction.response.send_message(f"❌ No list named '{list_name}'.", ephemeral=True)
    data = load_list(list_name)
    if any(e['name'].lower() == entry_name.lower() and e['category'] not in ('Category','Text','Bullet') for e in data):
        return await interaction.response.send_message(f"❌ `{entry_name}` already exists in `{list_name}`.", ephemeral=True)
    data.append({"category":category.value,"name":entry_name})
    save_list(list_name, data)
    await interaction.response.send_message(f"✅ Added {CATEGORY_EMOJIS[category.value]} **{entry_name}** as {category.value}", ephemeral=True)
    await update_list_dashboard(list_name)

@bot.tree.command(name="remove_name", description="Remove an entry")
@app_commands.describe(list_name="List to modify", entry_name="Entry to remove")
async def remove_name(interaction: discord.Interaction, list_name: str, entry_name: str):
    if not list_exists(list_name):
        return await interaction.response.send_message(f"❌ No list named '{list_name}'.", ephemeral=True)
    data = load_list(list_name)
    for i,it in enumerate(data):
        if it["name"].lower()==entry_name.lower() and it["category"] not in ("Category","Text","Bullet"):
            data.pop(i)
            save_list(list_name, data)
            await interaction.response.send_message(f"✅ Removed **{entry_name}**.", ephemeral=True)
            await update_list_dashboard(list_name)
            return
    await interaction.response.send_message(f"❌ Entry '{entry_name}' not found.", ephemeral=True)

@bot.tree.command(name="edit_name", description="Rename an entry & change category")
@app_commands.describe(
    list_name="List to modify",
    old_name="Current entry name",
    new_name="New entry name",
    category="New category"
)
@app_commands.choices(category=[
    app_commands.Choice(name="Owner", value="Owner"),
    app_commands.Choice(name="Friend", value="Friend"),
    app_commands.Choice(name="Ally",   value="Ally"),
    app_commands.Choice(name="Beta",   value="Beta"),
    app_commands.Choice(name="Enemy",  value="Enemy"),
    app_commands.Choice(name="Item",   value="Item"),
])
async def edit_name(interaction: discord.Interaction, list_name: str, old_name: str, new_name: str, category: app_commands.Choice[str]):
    if not list_exists(list_name):
        return await interaction.response.send_message(f"❌ No list named '{list_name}'.", ephemeral=True)
    data = load_list(list_name)
    for it in data:
        if it['name']==old_name and it['category'] not in ('Category','Text','Bullet'):
            it['name']     = new_name
            it['category'] = category.value
            save_list(list_name, data)
            await interaction.response.send_message(
                f"✅ Renamed **{old_name}**→**{new_name}** & set category to {category.value}",
                ephemeral=True
            )
            await update_list_dashboard(list_name)
            return
    await interaction.response.send_message(f"❌ Entry '{old_name}' not found.", ephemeral=True)

@bot.tree.command(name="move_name", description="Move an entry")
@app_commands.describe(
    list_name="List to modify",
    entry_name="Entry to move",
    position="New 1-based position"
)
async def move_name(interaction: discord.Interaction, list_name: str, entry_name: str, position: int):
    if not list_exists(list_name):
        return await interaction.response.send_message(f"❌ No list named '{list_name}'.", ephemeral=True)
    data = load_list(list_name)
    for idx,it in enumerate(data):
        if it['name']==entry_name and it['category'] not in ('Category','Text','Bullet'):
            entry = data.pop(idx)
            break
    else:
        return await interaction.response.send_message(f"❌ Entry '{entry_name}' not found.", ephemeral=True)
    pos = max(1,min(position,len(data)+1))
    data.insert(pos-1,entry)
    save_list(list_name, data)
    await interaction.response.send_message(f"✅ Moved **{entry_name}** to position {pos}.", ephemeral=True)
    await update_list_dashboard(list_name)

@bot.tree.command(name="sort_list", description="Sort by category priority then name")
@app_commands.describe(list_name="List to sort")
async def sort_list(interaction: discord.Interaction, list_name: str):
    if not list_exists(list_name):
        return await interaction.response.send_message(f"❌ No list named '{list_name}'.", ephemeral=True)
    data = load_list(list_name)
    categories = [it for it in data if it['category']=='Category']
    texts     = [it for it in data if it['category']=='Text']
    bullets   = [it for it in data if it['category']=='Bullet']
    entries   = [it for it in data if it['category'] not in ('Category','Text','Bullet')]
    sorted_entries = []
    for cat in CATEGORY_EMOJIS.keys():
        grp = [it for it in entries if it['category']==cat]
        grp.sort(key=lambda x:x['name'].lower())
        sorted_entries.extend(grp)
    new_data = categories + texts + bullets + sorted_entries
    save_list(list_name,new_data)
    await interaction.response.send_message(f"✅ Sorted items in '{list_name}'.", ephemeral=True)
    await update_list_dashboard(list_name)

# ━━━ Comments ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# (Only applies to named entries)
@bot.tree.command(name="add_comment", description="Add a comment to an entry")
@app_commands.describe(list_name="List to modify", entry_name="Entry to comment on", comment="Comment text")
async def add_comment(interaction: discord.Interaction, list_name: str, entry_name: str, comment: str):
    if not list_exists(list_name):
        return await interaction.response.send_message(f"❌ No list named '{list_name}'.", ephemeral=True)
    data = load_list(list_name)
    for it in data:
        if it['name']==entry_name and it['category'] not in ('Category','Text','Bullet'):
            it['comment'] = comment
            save_list(list_name,data)
            await interaction.response.send_message(f"✅ Comment added to **{entry_name}**.", ephemeral=True)
            await update_list_dashboard(list_name)
            return
    await interaction.response.send_message(f"❌ Entry '{entry_name}' not found.", ephemeral=True)

@bot.tree.command(name="edit_comment", description="Edit a comment")
@app_commands.describe(list_name="List to modify", entry_name="Entry whose comment to edit", new_comment="Updated text")
async def edit_comment(interaction: discord.Interaction, list_name: str, entry_name: str, new_comment: str):
    if not list_exists(list_name):
        return await interaction.response.send_message(f"❌ No list named '{list_name}'.", ephemeral=True)
    data=load_list(list_name)
    for it in data:
        if it['name']==entry_name and 'comment' in it:
            it['comment']=new_comment
            save_list(list_name,data)
            await interaction.response.send_message(f"✅ Comment updated for **{entry_name}**.", ephemeral=True)
            await update_list_dashboard(list_name)
            return
    await interaction.response.send_message(f"❌ No comment on '{entry_name}'.", ephemeral=True)

@bot.tree.command(name="remove_comment", description="Remove a comment")
@app_commands.describe(list_name="List to modify", entry_name="Entry whose comment to remove")
async def remove_comment(interaction: discord.Interaction, list_name: str, entry_name: str):
    if not list_exists(list_name):
        return await interaction.response.send_message(f"❌ No list named '{list_name}'.", ephemeral=True)
    data=load_list(list_name)
    for it in data:
        if it['name']==entry_name and 'comment' in it:
            del it['comment']
            save_list(list_name,data)
            await interaction.response.send_message(f"✅ Removed comment from **{entry_name}**.", ephemeral=True)
            await update_list_dashboard(list_name)
            return
    await interaction.response.send_message(f"❌ Entry '{entry_name}' not found.", ephemeral=True)

# ━━━ Assign to Category ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.tree.command(name="assign_to_category", description="Move an entry under a specific category")
@app_commands.describe(
    list_name="List to modify",
    category_index="Category position (1-based)",
    entry_type="Type of entry (Text, Bullet, Name)",
    entry_index="Entry position within that type (1-based)"
)
@app_commands.choices(entry_type=[
    app_commands.Choice(name="Text", value="Text"),
    app_commands.Choice(name="Bullet", value="Bullet"),
    app_commands.Choice(name="Name", value="Name"),
])
async def assign_to_category(
    interaction: discord.Interaction,
    list_name: str,
    category_index: int,
    entry_type: app_commands.Choice[str],
    entry_index: int
):
    if not list_exists(list_name):
        return await interaction.response.send_message(f"❌ No list named '{list_name}'.", ephemeral=True)
    data = load_list(list_name)
    cat_idxs = [i for i,v in enumerate(data) if v["category"]=="Category"]
    if not cat_idxs:
        return await interaction.response.send_message("❌ No categories in this list.", ephemeral=True)
    if category_index < 1 or category_index > len(cat_idxs):
        return await interaction.response.send_message("❌ Invalid category index.", ephemeral=True)
    et = entry_type.value
    if et == "Text":
        pos_list = [i for i,v in enumerate(data) if v["category"]=="Text"]
    elif et == "Bullet":
        pos_list = [i for i,v in enumerate(data) if v["category"]=="Bullet"]
    else:  # Name
        pos_list = [i for i,v in enumerate(data) if v["category"] not in ("Category","Text","Bullet")]
    if entry_index < 1 or entry_index > len(pos_list):
        return await interaction.response.send_message(f"❌ Invalid {et} index.", ephemeral=True)
    entry = data.pop(pos_list[entry_index-1])
    # recompute category positions after removal
    new_cat_idxs = [i for i,v in enumerate(data) if v["category"]=="Category"]
    insert_at = new_cat_idxs[category_index-1] + 1
    data.insert(insert_at, entry)
    save_list(list_name, data)
    await interaction.response.send_message(
        f"✅ Moved {et} #{entry_index} under category #{category_index}.", ephemeral=True
    )
    await update_list_dashboard(list_name)

# ━━━ Viewing & Deploy ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.tree.command(name="view_lists", description="List all your lists")
async def view_lists_cmd(interaction: discord.Interaction):
    names=get_all_list_names()
    if not names:
        return await interaction.response.send_message("⚠️ No lists found.", ephemeral=True)
    await interaction.response.send_message("📋 Lists:\n"+ "\n".join(f"- `{n}`" for n in sorted(names)), ephemeral=True)

@bot.tree.command(name="view_gen_lists", description="List all your generator lists")
async def view_gen_lists_cmd(interaction: discord.Interaction):
    names=get_all_gen_list_names()
    if not names:
        return await interaction.response.send_message("⚠️ No gen lists found.", ephemeral=True)
    await interaction.response.send_message("📊 Gen lists:\n"+ "\n".join(f"- `{n}`" for n in sorted(names)), ephemeral=True)

# ━━━ Deploy ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.tree.command(name="deploy_list", description="Deploy/update a regular list")
@app_commands.describe(name="Name of the list")
async def deploy_list_cmd(interaction: discord.Interaction, name: str):
    if list_exists(name):
        embed = build_embed(name)
        await interaction.response.send_message(embed=embed)
        sent = await interaction.original_response()
        save_dashboard_id(name, sent.channel.id, sent.id)
    else:
        await interaction.response.send_message(f"❌ No list named '{name}'.", ephemeral=True)

@bot.tree.command(name="deploy_gen_list", description="Deploy/update a generator dashboard")
@app_commands.describe(name="Name of the generator list")
async def deploy_gen_list_cmd(interaction: discord.Interaction, name: str):
    if gen_list_exists(name):
        embed = build_gen_timetable_embed(name)
        await interaction.response.send_message(embed=embed)
        sent = await interaction.original_response()
        save_gen_dashboard_id(name, sent.channel.id, sent.id)
    else:
        await interaction.response.send_message(f"❌ No generator list named '{name}'.", ephemeral=True)

# ━━━ Help & Logs ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.tree.command(name="help", description="Show usage instructions")
async def help_cmd(interaction: discord.Interaction):
    # Build an embed-based help to avoid the 2000-char message content limit.
    embed = discord.Embed(
        title="Gravity List — Commands",
        description="Clean dashboards for names, notes, timers, generators, and server status.",
        color=discord.Color.blurple()
    )
    embed.set_footer(text="All commands are slash commands. Use autocomplete where available.")

    def add_section(title: str, lines: list[str]):
        """Add a section to the embed, splitting into multiple fields if >1024 chars."""
        text = "\n".join(lines)
        chunks = []
        while len(text) > 1024:
            cut = text.rfind("\n", 0, 1000)  # try to break on a newline
            if cut == -1:
                cut = 1000
            chunks.append(text[:cut])
            text = text[cut:].lstrip("\n")
        chunks.append(text)

        total = len(chunks)
        for i, chunk in enumerate(chunks, start=1):
            name = f"{title} ({i}/{total})" if total > 1 else title
            embed.add_field(name=name, value=chunk or "​", inline=False)

    # — Regular lists —
    add_section("Regular Lists — Create, View, Deploy", [
        "• `/view_lists` — list your lists",
        "• `/deploy_list name:<list>` — (re)render a list in-channel",
        "• `/create_list`, `/delete_list`",
    ])

    add_section("Regular Lists — Organize & Edit", [
        "• Categories: `/add_list_category`, `/edit_list_category`, `/remove_list_category`",
        "• Text: `/add_text`, `/edit_text`, `/remove_text`",
        "• Bullets: `/add_bullet`, `/edit_bullet`, `/remove_bullet`",
        "• Names: `/add_name`, `/remove_name`, `/edit_name`, `/move_name`, `/sort_list`",
        "• Comments on names: `/add_comment`, `/edit_comment`, `/remove_comment`",
        "• Assign items under a category: `/assign_to_category`",
        "_Tip: Indices are shown in the list embed so index-based commands are easy to use._",
    ])

    # — Generator lists & timers —
    add_section("Generator Lists (Fuel Timers)", [
        "• `/view_gen_lists`, `/deploy_gen_list name:<gen_list>`",
        "• Create/delete: `/create_gen_list`, `/delete_gen_list`",
        "• Tek: `/add_gen_tek`, `/edit_gen_tek`, `/update_all_gens_tek`",
        "• Electrical: `/add_gen_electrical`, `/edit_gen_electrical`, `/update_all_gens_electrical`",
        "• Remove generator: `/remove_gen`",
        "• Reorder: `/reorder_gen`",
        "• Ping role: `/set_gen_role`",
        "• Mute/unmute: `/mute_gen_alerts`, `/unmute_gen_alerts`",
        "_Gen dashboards auto-refresh; LOW=≤12h remaining; EMPTY=0._",
    ])

    add_section("Standalone Timers", [
        "• `/create_timer`, `/pause_timer`, `/resume_timer`, `/edit_timer`, `/delete_timer`",
    ])

    # — Server dashboards —
    add_section("ASA Official — BattleMetrics", [
        "• `/bm_asa_server_query server_id:<bm_id>` — one-off snapshot",
        "• `/bm_asa_dashboard_start` / `/bm_asa_dashboard_stop` / `/bm_asa_dashboard_refresh`",
        "_Uses BattleMetrics public API; free tier limits may apply._",
    ])

    add_section("ASA — Ark Status", [
        "• `/as_server_query target:<ArkStatus ID or Name>` — one-off snapshot",
        "• `/as_dashboard_start` / `/as_dashboard_stop` / `/as_dashboard_refresh`",
        "_Env: `AS_API_KEY` (required), `AS_CHANNEL_ID`, `AS_TARGETS`; optional: `AS_REFRESH_SEC`, `AS_TIER`._",
    ])

    # — Downloads —
    add_section("Downloads — Gravity Capture", [
        "• `/download_grav_capture` — buttons for the latest **Installer (.exe)** and **Portable (.zip)** from GitHub Releases",
        "• `/grav_capture_version` — latest tag + checksum files (.sha256)",
        "_Repo is configurable via env: `GC_REPO_OWNER`, `GC_REPO_NAME`; optional `GITHUB_TOKEN` for higher rate limits._",
    ])

    # — Diagnostics & admin —
    add_section("Diagnostics", [
        "• `/diag summary` — deployment/uptime/thresholds/maintenance",
        "• `/diag tail_logs [lines]` — in-memory log tail",
        "• `/diag ratelimit` — 429 counts (15m/1h/24h)",
        "• `/diag set_disconnect_threshold seconds:<int>` — store override",
        "• `/diag maintenance on|off [note]` — toggle maintenance flag",
        "_Set `DEBUG_POST_DEPLOY=1` to announce new deployments in the log channel._",
    ])

    add_section("Administration", [
        "• `/set_log_channel` — set the channel where the bot posts logs/alerts (admin only)",
    ])

    # Send as ephemeral embed (safe; avoids 2000-char content cap).
    await interaction.response.send_message(embed=embed, ephemeral=True)

# Run
bot.run(TOKEN)
