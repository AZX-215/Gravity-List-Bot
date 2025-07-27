import os
import time
import discord
import logging
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv

from data_manager import (
    load_list, save_list, list_exists, delete_list,
    get_all_list_names, get_all_gen_list_names,
    save_dashboard_id, get_dashboard_id,
    save_gen_dashboard_id, get_gen_dashboard_id,
    gen_list_exists
)
from gen_timers import setup as setup_gen_timers, build_gen_dashboard_embed
from logging_cog import LoggingCog

# ━━━ Load configuration ━━━
load_dotenv()
TOKEN          = os.getenv("DISCORD_TOKEN")
CLIENT_ID      = int(os.getenv("CLIENT_ID"))
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", 0))

# ━━━ Logging setup ━━━
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()
console = logging.StreamHandler()
console.setLevel(logging.INFO)
fmt = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
console.setFormatter(fmt)
logger.addHandler(console)

# ━━━ Bot setup ━━━
intents = discord.Intents.default()
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents, application_id=CLIENT_ID)

CATEGORY_EMOJIS = {
    "Owner": "👑", "Enemy": "🔴", "Friend": "🟢",
    "Ally":   "🔵", "Beta":   "🟡", "Item":  "⚫"
}

def build_embed(list_name: str) -> discord.Embed:
    data = load_list(list_name)
    embed = discord.Embed(title=f"{list_name} List", color=0x808080)
    now = time.time()

    # ordering headers, text, timers, then entries
    data.sort(key=lambda x: (
        0 if isinstance(x, dict) and x.get("category")=="Header" else
        1 if isinstance(x, dict) and x.get("category")=="Text"   else
        2 if isinstance(x, dict) and x.get("category")=="Timer"  else
        3
    ))

    for item in data:
        if not isinstance(item, dict):
            continue
        cat = item["category"]

        if cat == "Header":
            embed.add_field(name="\u200b", value=f"**{item['name']}**", inline=False)

        elif cat == "Text":
            embed.add_field(name=f"• {item['name']}", value="\u200b", inline=False)

        elif cat == "Timer":
            end_ts = int(item.get("timer_end") or (item["timer_start"] + item["timer_duration"]))
            embed.add_field(
                name=f"⏳   {item['name']} — <t:{end_ts}:R>",
                value="\u200b", inline=False
            )

        else:
            prefix = CATEGORY_EMOJIS.get(cat, "")
            embed.add_field(name=f"{prefix}   {item['name']}", value="\u200b", inline=False)
            if item.get("comment"):
                embed.add_field(name="\u200b", value=f"*{item['comment']}*", inline=False)

    return embed

@bot.event
async def on_ready():
    if not getattr(bot, "_setup_done", False):
        await setup_gen_timers(bot)
        await bot.tree.sync()
        if LOG_CHANNEL_ID:
            await bot.add_cog(LoggingCog(bot, LOG_CHANNEL_ID))
            logger.info(f"Logging enabled → channel ID {LOG_CHANNEL_ID}")
        bot._setup_done = True
        print(f"Bot ready. Commands synced for {bot.user}")
    else:
        print(f"Bot reconnected: {bot.user}")

# ━━━ Slash Commands ━━━

@bot.tree.command(name="create_list", description="Create a new list")
@app_commands.describe(name="Name of the new list")
async def create_list(interaction: discord.Interaction, name: str):
    if list_exists(name):
        return await interaction.response.send_message(f"⚠️ List '{name}' exists.", ephemeral=True)
    save_list(name, [])
    await interaction.response.send_message(f"✅ Created list '{name}'.", ephemeral=True)

@bot.tree.command(name="lists", description="Show or deploy a list or generator dashboard")
@app_commands.describe(name="Name of the list")
async def lists_cmd(interaction: discord.Interaction, name: str):
    if gen_list_exists(name):
        embed = build_gen_dashboard_embed(name)
        await interaction.response.send_message(embed=embed)
        sent = await interaction.original_response()
        save_gen_dashboard_id(name, sent.channel.id, sent.id)
        return
    if list_exists(name):
        embed = build_embed(name)
        await interaction.response.send_message(embed=embed)
        sent = await interaction.original_response()
        save_dashboard_id(name, sent.channel.id, sent.id)
        return
    await interaction.response.send_message(f"❌ No list named '{name}'.", ephemeral=True)

@bot.tree.command(name="help", description="Show usage instructions")
async def help_cmd(interaction: discord.Interaction):
    help_text = (
        "**Gravity List Bot**\n"
        "• `/lists name:<list>` to deploy/update any list\n"
        "• Regular timers now use Discord timestamps—no more per‑second edits\n"
        "• Generator dashboards auto‑refresh every 5 minutes\n"
        "• Standalone timers ping on expiry (see `/create_timer`)\n"
        "• Internal logs (warnings & errors) optionally post to a channel\n"
        "Full command details in `README.md`."
    )
    await interaction.response.send_message(help_text, ephemeral=True)

@bot.tree.command(
    name="set_log_channel",
    description="Set which channel receives bot logs (warnings & errors)"
)
@app_commands.default_permissions(administrator=True)
@app_commands.describe(channel="The text channel where logs will be posted")
async def set_log_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    cog = bot.get_cog("LoggingCog")
    if cog is None or not hasattr(cog, "handler"):
        return await interaction.response.send_message(
            "❌ Logging is not enabled. Make sure `LOG_CHANNEL_ID` is set in your .env and the bot has been restarted.",
            ephemeral=True
        )
    cog.handler.channel_id = channel.id
    await interaction.response.send_message(f"✅ Log channel updated to {channel.mention}", ephemeral=True)

bot.run(TOKEN)
