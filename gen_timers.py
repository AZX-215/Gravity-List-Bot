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
    set_gen_list_role,
    get_gen_list_role,
    save_gen_dashboard_id,
    get_gen_dashboard_id
)

# ─── Configuration ──────────────────────
TEK_THUMBNAIL   = "https://raw.githubusercontent.com/AZX-215/Gravity-List-Bot/main/images/Tek_Generator.png"
TEK_COLOR       = 0x0099FF
ELEC_COLOR      = 0xFFC300
GEN_EMOJIS      = {"Tek": "⚡", "Electrical": "🔌"}

BACKOFF_SECONDS = 10 * 60   # pause updates for 10 minutes on 429
LOW_THRESHOLD   = 12 * 3600 # 12 hours in seconds

# ─── Utility: log to a configured channel ───────────────────────────────────────
async def log_to_channel(bot: commands.Bot, message: str):
    cid = os.getenv("LOG_CHANNEL_ID")
    if not cid:
        return
    ch = bot.get_channel(int(cid))
    if ch:
        await ch.send(message)

# ─── Utility: refresh one dashboard ────────────────────────────────────────────
async def refresh_dashboard(bot: commands.Bot, list_name: str):
    dash = get_gen_dashboard_id(list_name)
    if not dash:
        return
    ch_id, msg_id = dash
    ch = bot.get_channel(ch_id)
    if not ch:
        return
    msg = await ch.fetch_message(msg_id)
    embed = build_gen_embed(list_name)
    await msg.edit(embed=embed)

# ─── Build the embed ───────────────────────────────────────────────────────────
def build_gen_embed(list_name: str) -> discord.Embed:
    data = load_gen_list(list_name)
    now = time.time()

    # Use Tek color for embed border
    embed = discord.Embed(
        title=list_name,
        color=TEK_COLOR,
        timestamp=datetime.datetime.utcnow()
    )
    embed.set_thumbnail(url=TEK_THUMBNAIL)
    embed.set_footer(text="Gravity List Bot • Powered by AZX")

    for idx, item in enumerate(data, start=1):
        name     = item.get("name")
        gen_type = item.get("type")
        start_ts = item.get("timestamp", now)

        # Calculate total runtime and remaining
        if gen_type == "Tek":
            total_sec = item.get("shards", 0) * 648 + item.get("element", 0) * 64800
        else:
            total_sec = item.get("gas", 0) * 3600 + item.get("imbued", 0) * 14400

        end_ts    = start_ts + total_sec
        remaining = max(0, end_ts - now)

        # Format remaining time
        days, rem = divmod(int(remaining), 86400)
        hours, rem = divmod(rem, 3600)
        minutes, _ = divmod(rem, 60)
        parts = []
        if days:
            parts.append(f"{days}d")
        if hours:
            parts.append(f"{hours}h")
        parts.append(f"{minutes}m")
        rem_str = " ".join(parts)

        # Status and fuel info
        status = "✅" if remaining == 0 else "⏳"
        if gen_type == "Tek":
            fuel_info = f"{item.get('element', 0)}e / {item.get('shards', 0)}s"
        else:
            fuel_info = f"{item.get('gas', 0)}g / {item.get('imbued', 0)}ig"

        emoji     = GEN_EMOJIS.get(gen_type, "")
        entry_name = f"{emoji} __{name}__"
        value_text = f"{status} {rem_str} remaining   —   {fuel_info}"

        # Add numbered field
        embed.add_field(name=f"{idx}. {entry_name}", value=value_text, inline=False)

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

    @tasks.loop(seconds=90)
    async def generator_list_loop(self):
        now = time.time()
        if now < self.backoff_until:
            return

        for name in get_all_gen_list_names():
            try:
                await refresh_dashboard(self.bot, name)
            except discord.HTTPException as e:
                if getattr(e, 'status', None) == 429:
                    self.backoff_until = time.time() + BACKOFF_SECONDS
                    await log_to_channel(
                        self.bot,
                        f"⚠️ Rate limit hit on `{name}`, pausing for {BACKOFF_SECONDS//60}m."
                    )

    # ─── Commands ────────────────────────────────────────────────────────────
    @app_commands.command(name="create_gen_list", description="Create a new generator list")
    @app_commands.describe(name="Name of new generator list")
    async def create_gen_list(self, interaction: discord.Interaction, name: str):
        if gen_list_exists(name):
            return await interaction.response.send_message(
                f"⚠️ Generator list `{name}` already exists.", ephemeral=True
            )
        save_gen_list(name, [])
        await interaction.response.send_message(
            f"✅ Created generator list `{name}`.", ephemeral=True
        )

    @app_commands.command(name="delete_gen_list", description="Delete an existing generator list")
    @app_commands.describe(name="Generator list to delete")
    async def delete_gen_list_cmd(self, interaction: discord.Interaction, name: str):
        if not gen_list_exists(name):
            return await interaction.response.send_message(
                f"❌ Generator list `{name}` not found.", ephemeral=True
            )
        delete_gen_list(name)
        await interaction.response.send_message(
            f"✅ Deleted generator list `{name}`.", ephemeral=True
        )

    @app_commands.command(name="add_gen_tek", description="Add a Tek generator entry")
    @app_commands.describe(
        list_name="Generator list",
        gen_name="Generator name",
        element="Element count",
        shards="Shard count"
    )
    async def add_gen_tek(
        self,
        interaction: discord.Interaction,
        list_name: str,
        gen_name: str,
        element: int = 0,
        shards: int = 0
    ):
        if not gen_list_exists(list_name):
            return await interaction.response.send_message(
                f"❌ `{list_name}` not found.", ephemeral=True
            )
        data = load_gen_list(list_name)
        # Reject duplicates
        if any(g["name"].lower() == gen_name.lower() for g in data):
            return await interaction.response.send_message(
                f"❌ Generator `{gen_name}` already exists.", ephemeral=True
            )
        add_to_gen_list(list_name, gen_name, "Tek", element, shards, 0, 0)
        await interaction.response.send_message(
            f"✅ Added Tek generator `{gen_name}`.", ephemeral=True
        )

    @app_commands.command(name="add_gen_electrical", description="Add an Electrical generator entry")
    @app_commands.describe(
        list_name="Generator list",
        gen_name="Generator name",
        gas="Gas count",
        imbued="Imbued gas count"
    )
    async def add_gen_electrical(
        self,
        interaction: discord.Interaction,
        list_name: str,
        gen_name: str,
        gas: int = 0,
        imbued: int = 0
    ):
        if not gen_list_exists(list_name):
            return await interaction.response.send_message(
                f"❌ `{list_name}` not found.", ephemeral=True
            )
        data = load_gen_list(list_name)
        if any(g["name"].lower() == gen_name.lower() for g in data):
            return await interaction.response.send_message(
                f"❌ Generator `{gen_name}` already exists.", ephemeral=True
            )
        add_to_gen_list(list_name, gen_name, "Electrical", 0, 0, gas, imbued)
        await interaction.response.send_message(
            f"✅ Added Electrical generator `{gen_name}`.", ephemeral=True
        )

    @app_commands.command(name="edit_gen_tek", description="Edit a Tek generator entry")
    @app_commands.describe(
        list_name="Generator list",
        gen_name="Generator to edit",
        element="New element count",
        shards="New shard count"
    )
    async def edit_gen_tek(
        self,
        interaction: discord.Interaction,
        list_name: str,
        gen_name: str,
        element: int,
        shards: int
    ):
        if not gen_list_exists(list_name):
            return await interaction.response.send_message(
                f"❌ `{list_name}` not found.", ephemeral=True
            )
        data = load_gen_list(list_name)
        for item in data:
            if item.get("name") == gen_name and item.get("type") == "Tek":
                item["element"] = element
                item["shards"]  = shards
                save_gen_list(list_name, data)
                return await interaction.response.send_message(
                    f"✅ Updated Tek generator `{gen_name}`.", ephemeral=True
                )
        await interaction.response.send_message(
            f"❌ Tek generator `{gen_name}` not found.", ephemeral=True
        )

    @app_commands.command(name="edit_gen_electrical", description="Edit an Electrical generator entry")
    @app_commands.describe(
        list_name="Generator list",
        gen_name="Generator to edit",
        gas="New gas count",
        imbued="New imbued gas count"
    )
    async def edit_gen_electrical(
        self,
        interaction: discord.Interaction,
        list_name: str,
        gen_name: str,
        gas: int,
        imbued: int
    ):
        if not gen_list_exists(list_name):
            return await interaction.response.send_message(
                f"❌ `{list_name}` not found.", ephemeral=True
            )
        data = load_gen_list(list_name)
        for item in data:
            if item.get("name") == gen_name and item.get("type") == "Electrical":
                item["gas"]    = gas
                item["imbued"] = imbued
                save_gen_list(list_name, data)
                return await interaction.response.send_message(
                    f"✅ Updated Electrical generator `{gen_name}`.", ephemeral=True
                )
        await interaction.response.send_message(
            f"❌ Electrical generator `{gen_name}` not found.", ephemeral=True
        )

    @app_commands.command(name="remove_gen", description="Remove a generator entry")
    @app_commands.describe(
        list_name="Generator list",
        gen_name="Generator to remove"
    )
    async def remove_gen(
        self,
        interaction: discord.Interaction,
        list_name: str,
        gen_name: str
    ):
        if not gen_list_exists(list_name):
            return await interaction.response.send_message(
                f"❌ `{list_name}` not found.", ephemeral=True
            )
        data = load_gen_list(list_name)
        for i, item in enumerate(data):
            if item.get("name") == gen_name:
                data.pop(i)
                save_gen_list(list_name, data)
                return await interaction.response.send_message(
                    f"✅ Removed generator `{gen_name}`.", ephemeral=True
                )
        await interaction.response.send_message(
            f"❌ Generator `{gen_name}` not found.", ephemeral=True
        )

    @app_commands.command(name="reorder_gen", description="Reorder generator entries by index")
    @app_commands.describe(
        list_name="Generator list",
        from_index="Current position (1-based)",
        to_index="New position (1-based)"
    )
    async def reorder_gen(
        self,
        interaction: discord.Interaction,
        list_name: str,
        from_index: int,
        to_index: int
    ):
        if not gen_list_exists(list_name):
            return await interaction.response.send_message(
                f"❌ `{list_name}` not found.", ephemeral=True
            )
        data = load_gen_list(list_name)
        length = len(data)
        if not (1 <= from_index <= length and 1 <= to_index <= length):
            return await interaction.response.send_message(
                f"❌ Invalid indices. Must be between 1 and {length}.", ephemeral=True
            )
        item = data.pop(from_index - 1)
        data.insert(to_index - 1, item)
        save_gen_list(list_name, data)
        await interaction.response.send_message(
            f"✅ Moved generator from position {from_index} → {to_index}.", ephemeral=True
        )

    @app_commands.command(name="set_gen_role", description="Set a ping role for a gen list")
    @app_commands.describe(
        list_name="Generator list",
        role="Role to ping on low fuel/expiry"
    )
    async def set_gen_role(
        self,
        interaction: discord.Interaction,
        list_name: str,
        role: discord.Role
    ):
        if not gen_list_exists(list_name):
            return await interaction.response.send_message(
                f"❌ `{list_name}` not found.", ephemeral=True
            )
        set_gen_list_role(list_name, role.id)
        await interaction.response.send_message(
            f"✅ Ping role set for `{list_name}`.", ephemeral=True
        )

# ─── Cog setup for bot.py ─────────────────────────────────────────────────────────
async def setup_gen_timers(bot: commands.Bot):
    try:
        await bot.add_cog(GeneratorCog(bot))
    except CommandAlreadyRegistered:
        pass

# ─── Alias for bot.py import ──────────────────────────────────────────────────
build_gen_timetable_embed = build_gen_embed
