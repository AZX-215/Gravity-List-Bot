import time
import asyncio
import random
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

GEN_EMOJIS = {"Tek": "🔧", "Electrical": "🔌"}

def build_gen_embed(list_name: str) -> discord.Embed:
    data = load_gen_list(list_name)
    embed = discord.Embed(
        title=f"⛽ {list_name} Dashboard",
        color=0x1ABC9C,
        timestamp=datetime.datetime.utcnow()
    )
    embed.set_footer(text="Auto‑refresh every 5 min")
    # Optional: set a thumbnail if you have a URL
    # embed.set_thumbnail(url="https://your-cdn/azx-logo.png")

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

        rem_shards  = max(0, init_shards - int(elapsed / shard_sec)) if shard_sec > 0 else init_shards
        rem_elem    = max(0, init_elem   - int((elapsed - (init_shards * shard_sec)) / elem_sec)) if elem_sec > 0 else init_elem

        end_ts = int(start + (init_shards * shard_sec) + (init_elem * elem_sec))
        return f"**{item['name']}** {emoji}  <t:{end_ts}:R>\n• Element: {rem_elem}  │  Shards: {rem_shards}"

    def format_elec(item):
        emoji = GEN_EMOJIS["Electrical"]
        start = item["timestamp"]
        gas    = item.get("gas", 0)
        imbued = item.get("imbued", 0)
        dur = gas * 3600 + imbued * 14400
        elapsed = max(0, now - start)
        rem = max(0, int(dur - elapsed))
        end_ts = int(start + dur)
        return f"**{item['name']}** {emoji}  <t:{end_ts}:R>\n• Gas: {item['gas']}  │  Imbued: {item['imbued']}"

    # Add fields
    if tek_items:
        lines = [format_tek(it) for it in tek_items]
        embed.add_field(name="⚙️ Tek Generators", value="\n\n".join(lines), inline=False)
    if elec_items:
        lines = [format_elec(it) for it in elec_items]
        embed.add_field(name="🔋 Electrical Generators", value="\n\n".join(lines), inline=False)

    if not tek_items and not elec_items:
        embed.description = "No generators in this list."

    return embed

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
    except Exception:
        pass

class GeneratorCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.generator_list_loop.start()

    def cog_unload(self):
        self.generator_list_loop.cancel()

    @tasks.loop(minutes=5)
    async def generator_list_loop(self):
        # Batch update each dashboard with a stagger to avoid bursts
        for name in get_all_gen_list_names():
            await refresh_dashboard(self.bot, name)
            await asyncio.sleep(1)  # stagger updates by 1s
        # Check for expirations (existing logic)
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

    # … include all existing slash commands here without changes …

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
