import time
import asyncio
import datetime
import discord
from discord.ext import commands, tasks
from discord import app_commands
from discord.app_commands import CommandAlreadyRegistered
from data_manager import (
    load_gen_list,
    save_gen_list,
    gen_list_exists,
    delete_gen_list,
    get_all_gen_list_names,
    add_to_gen_list,
    get_all_gen_dashboards,
    get_gen_dashboard_id,
    set_gen_list_role,
    get_gen_list_role
)
import os

# Thumbnails and colors
TEK_THUMBNAIL = "https://raw.githubusercontent.com/AZX-215/Gravity-List-Bot/refs/heads/main/images/Tek_Generator.png"
TEK_COLOR = 0x0099FF
ELEC_COLOR = 0xFFC300
GEN_EMOJIS = {"Tek": "⚡", "Electrical": "🔌"}

BACKOFF_SECONDS = 10 * 60  # 10 minutes

def build_gen_embed(list_name: str) -> discord.Embed:
    data = load_gen_list(list_name)
    embed = discord.Embed(
        title=f"{GEN_EMOJIS['Tek']} {list_name} Dashboard",
        color=TEK_COLOR,
        timestamp=datetime.datetime.utcnow()
    )
    embed.set_footer(text="Gravity List Bot • Powered by AZX")
    embed.set_thumbnail(url=TEK_THUMBNAIL)

    now = time.time()
    tek_items = [item for item in data if item["type"] == "Tek"]
    elec_items = [item for item in data if item["type"] == "Electrical"]

    def format_tek(item):
        emoji = GEN_EMOJIS["Tek"]
        start = item["timestamp"]
        init_shards = item.get("shards", 0)
        init_elem   = item.get("element", 0)
        shard_sec   = init_shards * 648
        elem_sec    = init_elem * 64800
        elapsed     = max(0, now - start)

        rem_shards  = max(0, init_shards - int(elapsed / 648)) if shard_sec > 0 else init_shards
        rem_elem    = max(0, init_elem   - int((elapsed - (init_shards * 648)) / 64800)) if elem_sec > 0 else init_elem

        end_ts = int(start + (init_shards * 648) + (init_elem * 64800))
        mins_left = int((end_ts - now) / 60)
        if rem_elem == 0 and rem_shards == 0 or mins_left <= 0:
            status_emoji = "❌"
            status_text = "Offline"
        elif rem_elem <= 5 or mins_left < 30:
            status_emoji = "⚠️"
            status_text = "Low Fuel"
        else:
            status_emoji = "🔋"
            status_text = "Online"
        return (
            f"**{emoji} {item['name']}**\n"
            f"Element Left: **{rem_elem}**\n"
            f"Shards Left: **{rem_shards}**\n"
            f"⏳ Time Left: <t:{end_ts}:R>\n"
            f"{status_emoji} Status: {status_text}"
        )

    def format_elec(item):
        emoji = GEN_EMOJIS["Electrical"]
        start = item["timestamp"]
        gas    = item.get("gas", 0)
        imbued = item.get("imbued", 0)
        dur = gas * 3600 + imbued * 14400
        elapsed = max(0, now - start)
        rem_gas = max(0, gas - int(elapsed / 3600)) if gas > 0 else gas
        rem_imbued = max(0, imbued - int(elapsed / 14400)) if imbued > 0 else imbued
        end_ts = int(start + dur)
        mins_left = int((end_ts - now) / 60)
        if rem_gas == 0 and rem_imbued == 0 or mins_left <= 0:
            status_emoji = "❌"
            status_text = "Offline"
        elif rem_gas <= 1 or mins_left < 60:
            status_emoji = "⚠️"
            status_text = "Low Fuel"
        else:
            status_emoji = "🔋"
            status_text = "Online"
        return (
            f"**{emoji} {item['name']}**\n"
            f"Gas Left: **{rem_gas}**\n"
            f"Imbued: **{rem_imbued}**\n"
            f"⏳ Time Left: <t:{end_ts}:R>\n"
            f"{status_emoji} Status: {status_text}"
        )

    if tek_items:
        lines = [format_tek(it) for it in tek_items]
        embed.add_field(name="⚡ Tek Generators", value="\n\n".join(lines), inline=False)
    if elec_items:
        lines = [format_elec(it) for it in elec_items]
        embed.add_field(name="🔌 Electrical Generators", value="\n\n".join(lines), inline=False)
    if not tek_items and not elec_items:
        embed.description = "No generators in this list."
    return embed

async def log_to_channel(bot, message):
    try:
        log_channel_id = int(os.environ.get("LOG_CHANNEL_ID", "0"))
        if not log_channel_id:
            return
        channel = bot.get_channel(log_channel_id)
        if channel:
            await channel.send(message)
    except Exception as e:
        print(f"[Logging] Failed to send log: {e}")

async def refresh_dashboard(bot: commands.Bot, list_name: str):
    dash = get_gen_dashboard_id(list_name)
    if not dash:
        return
    if isinstance(dash, (tuple, list)):
        channel_id, message_id = dash
    else:
        channel_id, message_id = dash.get("channel_id"), dash.get("message_id")
    channel = bot.get_channel(channel_id)
    if not channel:
        return
    try:
        msg = await channel.fetch_message(message_id)
        await msg.edit(embed=build_gen_embed(list_name))
    except discord.errors.HTTPException as e:
        if e.status == 429:
            raise  # We'll handle this at the loop level!
        else:
            await log_to_channel(bot, f"Error updating dashboard `{list_name}`: {e}")
    except Exception as e:
        await log_to_channel(bot, f"Error updating dashboard `{list_name}`: {e}")

class GeneratorCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.generator_list_loop.start()
        self.backoff_until = 0

    def cog_unload(self):
        self.generator_list_loop.cancel()

    @tasks.loop(minutes=5)
    async def generator_list_loop(self):
        # Only one update loop—stagger within it!
        now = time.time()
        if now < getattr(self, 'backoff_until', 0):
            # Still backing off
            return

        for name in get_all_gen_list_names():
            try:
                await refresh_dashboard(self.bot, name)
            except discord.errors.HTTPException as e:
                if e.status == 429:
                    # Hit a rate limit!
                    self.backoff_until = time.time() + BACKOFF_SECONDS
                    await log_to_channel(
                        self.bot,
                        f"⚠️ **Rate limit detected!**\nPausing all generator dashboard updates for {BACKOFF_SECONDS//60} minutes."
                    )
                    return  # Stop trying to update others this loop
                else:
                    await log_to_channel(self.bot, f"Dashboard update error for `{name}`: {e}")
            except Exception as e:
                await log_to_channel(self.bot, f"Dashboard update error for `{name}`: {e}")
            await asyncio.sleep(1)  # Stagger updates (never all at once)

        # Check for expired gens and ping (as before)
        now = time.time()
        changed = False
        for list_name in get_all_gen_list_names():
            data = load_gen_list(list_name)
            ping_role = get_gen_list_role(list_name)
            for item in data:
                dur = (
                    (item.get("element",0) * 64800 + item.get("shards",0) * 648)
                    if item["type"] == "Tek"
                    else item.get("gas",0) * 3600 + item.get("imbued",0) * 14400
                )
                if not item.get("expired") and now > item["timestamp"] + dur:
                    item["expired"] = True
                    changed = True
                    channel = self.bot.get_channel(get_gen_dashboard_id(list_name)[0])
                    ping = f"<@&{ping_role}>" if ping_role else ""
                    if channel:
                        await channel.send(f"⏰ **{item['name']}** expired! {ping}")
        if changed:
            for ln in get_all_gen_list_names():
                save_gen_list(ln, load_gen_list(ln))

    @generator_list_loop.before_loop
    async def before_generator_loop(self):
        await self.bot.wait_until_ready()

    @app_commands.command(name="list_gen_lists", description="List all generator lists")
    async def list_gen_lists(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Admin only.", ephemeral=True)
        names = get_all_gen_list_names()
        desc = "\n".join(f"• {n}" for n in names) or "No generator lists found."
        embed = discord.Embed(title="Generator Lists", description=desc, color=0x404040)
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot):
    try:
        await bot.add_cog(GeneratorCog(bot))
    except CommandAlreadyRegistered:
        print("[GeneratorCog] Commands already registered, skipping registration.")

# Alias for compatibility
build_gen_dashboard_embed = build_gen_embed
