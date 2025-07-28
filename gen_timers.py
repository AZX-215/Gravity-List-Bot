import os
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

# ─── Configuration ─────────────────────────────────────────────────────────────
TEK_THUMBNAIL = "https://raw.githubusercontent.com/AZX-215/Gravity-List-Bot/main/images/Tek_Generator.png"
TEK_COLOR     = 0x0099FF
ELEC_COLOR    = 0xFFC300
GEN_EMOJIS    = {"Tek": "⚡", "Electrical": "🔌"}

BACKOFF_SECONDS = 10 * 60  # pause updates for 10 minutes on rate‑limit

# ─── Utility: log to channel ────────────────────────────────────────────────────
async def log_to_channel(bot: commands.Bot, message: str):
    channel_id = os.getenv("LOG_CHANNEL_ID", None)
    if not channel_id:
        return
    ch = bot.get_channel(int(channel_id))
    if ch:
        await ch.send(message)

# ─── Utility: refresh a single dashboard message ────────────────────────────────
async def refresh_dashboard(bot: commands.Bot, list_name: str):
    dash = get_gen_dashboard_id(list_name)
    if not dash:
        return
    channel_id, message_id = dash
    ch = bot.get_channel(channel_id)
    if not ch:
        return
    msg = await ch.fetch_message(message_id)
    await msg.edit(embed=build_gen_embed(list_name))

# ─── Embed builder ────────────────────────────────────────────────────────────
def build_gen_embed(list_name: str) -> discord.Embed:
    data = load_gen_list(list_name)
    now = time.time()

    # Title is just the list name
    embed = discord.Embed(
        title=list_name,
        color=TEK_COLOR,
        timestamp=datetime.datetime.utcnow()
    )
    embed.set_thumbnail(url=TEK_THUMBNAIL)
    embed.set_footer(text="Gravity List Bot • Powered by AZX")

    # Sort: Tek first, then Electrical; then alphabetical
    def sort_key(item):
        return (0 if item["type"] == "Tek" else 1, item["name"].lower())

    for item in sorted(data, key=sort_key):
        name = item["name"]
        gen_type = item["type"]
        start = item["timestamp"]

        # Determine total duration and prefix emoji
        if gen_type == "Tek":
            total_sec = item.get("shards", 0) * 648 + item.get("element", 0) * 64800
            color = TEK_COLOR
        else:
            total_sec = item.get("gas", 0) * 3600 + item.get("imbued", 0) * 14400
            color = ELEC_COLOR

        end_ts = int(start + total_sec)
        rem_sec = max(0, end_ts - now)
        hrs, rem = divmod(rem_sec, 3600)
        mins, _ = divmod(rem, 60)

        # Status logic
        expired = item.get("expired", False)
        if expired or rem_sec <= 0:
            status = ("❌", "Offline")
        elif gen_type == "Tek":
            # low if < 30 min or ≤0 shards/element thresholds
            status = ("⚠️", "Low Fuel") if (mins < 30 or item.get("element",0)==0) else ("🔋", "Online")
        else:
            # low if < 1 h gas or < 1 block imbued
            status = ("⚠️", "Low Fuel") if (hrs < 1 or item.get("gas",0)==0) else ("🔋", "Online")

        # Build field
        emoji = GEN_EMOJIS.get(gen_type, "")
        rem_str = f"{int(hrs)}h {int(mins)}m"
        field_name = f"{emoji} {name}"
        field_value = (
            f"⏳ {rem_str} left — {status[0]} {status[1]}\n"
            f"<t:{end_ts}:R>"
        )
        embed.add_field(name=field_name, value=field_value, inline=False)

    # If empty:
    if not data:
        embed.description = "No generators in this list."

    return embed

# ─── Generator Cog ─────────────────────────────────────────────────────────────
class GeneratorCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.backoff_until = 0
        self.loop = self.generator_list_loop
        self.loop.start()

    def cog_unload(self):
        self.loop.cancel()

    @tasks.loop(minutes=5)
    async def generator_list_loop(self):
        now = time.time()
        if now < self.backoff_until:
            return

        # 1) Refresh dashboards
        for name in get_all_gen_list_names():
            try:
                await refresh_dashboard(self.bot, name)
            except discord.HTTPException as e:
                if e.status == 429:
                    self.backoff_until = time.time() + BACKOFF_SECONDS
                    await log_to_channel(
                        self.bot,
                        f"⚠️ Rate limit hit on `{name}`, pausing for {BACKOFF_SECONDS//60}m."
                    )
                    return
                else:
                    await log_to_channel(self.bot, f"[GenRefresh] {name}: {e}")
            except Exception as e:
                await log_to_channel(self.bot, f"[GenRefresh] {name}: {e}")
            await asyncio.sleep(1)  # stagger

        # 2) Expiry checks & pings
        changed = False
        for name in get_all_gen_list_names():
            data = load_gen_list(name)
            role_id = get_gen_list_role(name)
            for item in data:
                if item.get("expired"):
                    continue
                # compute total again
                if item["type"] == "Tek":
                    total = item.get("shards",0)*648 + item.get("element",0)*64800
                else:
                    total = item.get("gas",0)*3600 + item.get("imbued",0)*14400
                if now >= item["timestamp"] + total:
                    item["expired"] = True
                    changed = True
                    dash = get_gen_dashboard_id(name)
                    if dash:
                        ch = self.bot.get_channel(dash[0])
                        ping = f"<@&{role_id}>" if role_id else ""
                        if ch:
                            await ch.send(f"⏰ **{item['name']}** expired! {ping}")

        if changed:
            # persist updates
            for name in get_all_gen_list_names():
                save_gen_list(name, load_gen_list(name))

    @generator_list_loop.before_loop
    async def _before_loop(self):
        await self.bot.wait_until_ready()

    @app_commands.command(name="create_gen_list", description="Create a new generator list")
    @app_commands.describe(name="List name")
    async def create_gen_list(self, interaction: discord.Interaction, name: str):
        if gen_list_exists(name):
            return await interaction.response.send_message(f"⚠️ `{name}` exists.", ephemeral=True)
        save_gen_list(name, [])
        await interaction.response.send_message(f"✅ Created generator list `{name}`.", ephemeral=True)

    @app_commands.command(name="delete_gen_list", description="Delete a generator list")
    @app_commands.describe(name="List name")
    async def delete_gen_list_cmd(self, interaction: discord.Interaction, name: str):
        if not gen_list_exists(name):
            return await interaction.response.send_message(f"❌ `{name}` not found.", ephemeral=True)
        delete_gen_list(name)
        await interaction.response.send_message(f"✅ Deleted generator list `{name}`.", ephemeral=True)

    @app_commands.command(name="add_gen", description="Add a generator entry")
    @app_commands.describe(
        list_name="List name",
        gen_name="Entry name",
        gen_type="Tek or Electrical",
        element="Element for Tek",
        shards="Shards for Tek",
        gas="Gas for Electrical",
        imbued="Imbued gas for Electrical"
    )
    @app_commands.choices(gen_type=[
        app_commands.Choice(name="Tek", value="Tek"),
        app_commands.Choice(name="Electrical", value="Electrical")
    ])
    async def add_gen(
        self,
        interaction: discord.Interaction,
        list_name: str,
        gen_name: str,
        gen_type: app_commands.Choice[str],
        element: int = 0,
        shards: int = 0,
        gas: int = 0,
        imbued: int = 0
    ):
        if not gen_list_exists(list_name):
            return await interaction.response.send_message(f"❌ `{list_name}` not found.", ephemeral=True)
        add_to_gen_list(list_name, gen_name, gen_type.value, element, shards, gas, imbued)
        await interaction.response.send_message(f"✅ Added `{gen_name}`.", ephemeral=True)

    @app_commands.command(name="edit_gen", description="Edit a generator entry")
    @app_commands.describe(
        list_name="List name",
        gen_name="Entry to edit",
        new_name="Optional new name",
        element="New element (Tek)",
        shards="New shards (Tek)",
        gas="New gas (Electrical)",
        imbued="New imbued (Electrical)"
    )
    async def edit_gen(
        self,
        interaction: discord.Interaction,
        list_name: str,
        gen_name: str,
        new_name: str = None,
        element: int = None,
        shards: int = None,
        gas: int = None,
        imbued: int = None
    ):
        if not gen_list_exists(list_name):
            return await interaction.response.send_message(f"❌ `{list_name}` not found.", ephemeral=True)
        data = load_gen_list(list_name)
        for item in data:
            if item["name"] == gen_name:
                if new_name:   item["name"]    = new_name
                if element is not None: item["element"] = element
                if shards is not None:  item["shards"]  = shards
                if gas is not None:     item["gas"]     = gas
                if imbued is not None:  item["imbued"]  = imbued
                save_gen_list(list_name, data)
                return await interaction.response.send_message(f"✅ Updated `{gen_name}`.", ephemeral=True)
        await interaction.response.send_message(f"❌ `{gen_name}` not in `{list_name}`.", ephemeral=True)

    @app_commands.command(name="remove_gen", description="Remove a generator entry")
    @app_commands.describe(list_name="List name", gen_name="Entry to remove")
    async def remove_gen(self, interaction: discord.Interaction, list_name: str, gen_name: str):
        if not gen_list_exists(list_name):
            return await interaction.response.send_message(f"❌ `{list_name}` not found.", ephemeral=True)
        data = load_gen_list(list_name)
        for i, item in enumerate(data):
            if item["name"] == gen_name:
                data.pop(i)
                save_gen_list(list_name, data)
                return await interaction.response.send_message(f"✅ Removed `{gen_name}`.", ephemeral=True)
        await interaction.response.send_message(f"❌ `{gen_name}` not in `{list_name}`.", ephemeral=True)

    @app_commands.command(name="set_gen_role", description="Set a ping role for expirations")
    @app_commands.describe(list_name="List name", role="Role to ping")
    async def set_gen_role(self, interaction: discord.Interaction, list_name: str, role: discord.Role):
        if not gen_list_exists(list_name):
            return await interaction.response.send_message(f"❌ `{list_name}` not found.", ephemeral=True)
        set_gen_list_role(list_name, role.id)
        await interaction.response.send_message(f"✅ Ping role set for `{list_name}`.", ephemeral=True)


# ─── Setup for bot.py ───────────────────────────────────────────────────────────
async def setup_gen_timers(bot: commands.Bot):
    try:
        await bot.add_cog(GeneratorCog(bot))
    except CommandAlreadyRegistered:
        pass
