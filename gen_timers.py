import os
import time
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

    embed = discord.Embed(
        title=list_name,
        color=TEK_COLOR,
        timestamp=datetime.datetime.utcnow()
    )
    embed.set_thumbnail(url=TEK_THUMBNAIL)
    embed.set_footer(text="Gravity List Bot • Powered by AZX")

    for idx, item in enumerate(data, start=1):
        name             = item.get("name")
        gen_type         = item.get("type")
        start_ts         = item.get("timestamp", now)
        elapsed          = now - start_ts

        # Initial fuel amounts
        initial_elements = item.get("element", 0)
        initial_shards   = item.get("shards", 0)
        shard_duration   = 648      # seconds per shard burn
        element_duration = 64800    # seconds per element burn

        total_shard_time   = initial_shards * shard_duration
        total_element_time = initial_elements * element_duration
        total_fuel_time    = total_shard_time + total_element_time
        remaining_time     = max(total_fuel_time - elapsed, 0)

        # Calculate remaining shards
        shards_used          = int(min(elapsed, total_shard_time) // shard_duration)
        rem_shards           = max(initial_shards - shards_used, 0)

        # Then calculate remaining elements after shards
        elapsed_after_shards = max(elapsed - total_shard_time, 0)
        elems_used           = int(min(elapsed_after_shards, total_element_time) // element_duration)
        rem_elements         = max(initial_elements - elems_used, 0)

        # Format remaining time
        days    = int(remaining_time // 86400)
        hours   = int((remaining_time % 86400) // 3600)
        minutes = int((remaining_time % 3600) // 60)
        parts   = []
        if days:
            parts.append(f"{days} days")
        if hours:
            parts.append(f"{hours} hours")
        parts.append(f"{minutes} minutes")
        rem_str = " ".join(parts)

        # Timer icon & status
        timer_icon   = "⩇⩇:⩇⩇" if remaining_time == 0 else "⏱️"
        status_emoji = "🔴" if remaining_time == 0 else "🟢"
        status_word  = "Offline" if remaining_time == 0 else "Online"

        # Fuel info display
        if gen_type == "Tek":
            fuel_info  = f"{rem_shards} shards / {rem_elements} element"
            embed.color = TEK_COLOR
        else:
            # Electrical: recalc from item.get("gas") and item.get("imbued")
            initial_gas     = item.get("gas", 0)
            initial_imbued  = item.get("imbued", 0)
            total_gas_time  = initial_gas * 3600
            total_imb_time  = initial_imbued * 14400

            gas_used         = int(min(elapsed, total_gas_time) // 3600)
            rem_gas          = max(initial_gas - gas_used, 0)
            elapsed_after_gas = max(elapsed - total_gas_time, 0)
            imb_used         = int(min(elapsed_after_gas, total_imb_time) // 14400)
            rem_imbued       = max(initial_imbued - imb_used, 0)

            fuel_info   = f"{rem_gas} gas / {rem_imbued} imbued gas"
            embed.color = ELEC_COLOR

        emoji      = GEN_EMOJIS.get(gen_type, "")
        entry_name = f"{emoji} __{name}__"
        value_text = (
            f"{timer_icon} {rem_str} remaining   —   "
            f"{fuel_info}   —   {status_emoji} {status_word}"
        )

        embed.add_field(name=f"{idx}. {entry_name}", value=value_text, inline=False)

    return embed

# ─── Generator Cog ─────────────────────────────────────────────────────────────
class GeneratorCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot         = bot
        self.backoff_until = 0
        self.loop        = self.generator_list_loop
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
        await refresh_dashboard(self.bot, name)

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
        if any(g["name"].lower() == gen_name.lower() for g in data):
            return await interaction.response.send_message(
                f"❌ Generator `{gen_name}` already exists.", ephemeral=True
            )
        add_to_gen_list(list_name, gen_name, "Tek", element, shards, 0, 0)
        await interaction.response.send_message(
            f"✅ Added Tek generator `{gen_name}`.", ephemeral=True
        )
        await refresh_dashboard(self.bot, list_name)

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
        await refresh_dashboard(self.bot, list_name)

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
                await interaction.response.send_message(
                    f"✅ Updated Tek generator `{gen_name}`.", ephemeral=True
                )
                await refresh_dashboard(self.bot, list_name)
                return
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
                await interaction.response.send_message(
                    f"✅ Updated Electrical generator `{gen_name}`.", ephemeral=True
                )
                await refresh_dashboard(self.bot, list_name)
                return
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
                await interaction.response.send_message(
                    f"✅ Removed generator `{gen_name}`.", ephemeral=True
                )
                await refresh_dashboard(self.bot, list_name)
                return
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
        await refresh_dashboard(self.bot, list_name)

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

# alias for import
build_gen_timetable_embed = build_gen_embed
