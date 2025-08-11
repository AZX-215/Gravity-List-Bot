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

BACKOFF_SECONDS = 10 * 60   # pause updates for 10 minutes on 429
LOW_THRESHOLD   = 12 * 3600 # 12 hours in seconds

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
        return  # not deployed yet
    ch_id, msg_id = dash
    ch = bot.get_channel(ch_id)
    if not ch:
        return

    embed = build_gen_embed(list_name)
    try:
        msg = await ch.fetch_message(msg_id)
        await msg.edit(embed=embed)
    except discord.NotFound:
        # Message was deleted—recreate and save the new ID
        sent = await ch.send(embed=embed)
        save_gen_dashboard_id(list_name, ch.id, sent.id)
        await log_to_channel(bot, f"ℹ️ Recreated missing gen dashboard for `{list_name}` in <#{ch_id}>.")
    except discord.Forbidden:
        await log_to_channel(bot, f"❌ Missing permissions to edit gen dashboard for `{list_name}` in <#{ch_id}>.")
    except discord.HTTPException as e:
        await log_to_channel(bot, f"⚠️ Failed to update gen dashboard `{list_name}`: {e}")

# ─── Build the embed ───────────────────────────────────────────────────────────
def build_gen_embed(list_name: str) -> discord.Embed:
    data = load_gen_list(list_name)
    now = time.time()

    embed = discord.Embed(
        title=list_name,
        color=TEK_COLOR if any(item.get("type") == "Tek" for item in data) else ELEC_COLOR
    )
    embed.set_thumbnail(url=TEK_THUMBNAIL)

    lines = []
    role_id = get_gen_list_role(list_name)
    if role_id:
        embed.description = f"<@&{role_id}>"

    for item in data:
        gtype = item.get("type", "Tek")
        emoji = GEN_EMOJIS.get(gtype, "⚙️")
        name  = item.get("name", "Unknown")
        ts    = item.get("timestamp", now)
        elapsed = max(now - ts, 0)

        if gtype == "Tek":
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

            # Choose a color indicator if low
            low = remaining_time <= LOW_THRESHOLD
            low_marker = " **(LOW)**" if low else ""

            line = f"{emoji} **{name}** — ⏳ {rem_str} — 🧩 {rem_shards} shards, 🔷 {rem_elements} element{low_marker}"
            lines.append(line)

        elif gtype == "Electrical":
            gas     = item.get("gas", 0)
            imbued  = item.get("imbued", 0)
            # No timed burn for Electrical here; just display counts
            line = f"{emoji} **{name}** — ⛽ {gas} gas, ✨ {imbued} imbued"
            lines.append(line)

    if not lines:
        lines.append("_No generators yet. Use `/add_gen_tek` or `/add_gen_electrical`._")

    # Discord embeds max ~6000 chars; keep safe
    joined = "\n".join(lines)
    if len(joined) > 5500:
        joined = joined[:5490] + "\n…"

    embed.add_field(name="Generators", value=joined, inline=False)
    embed.set_footer(text=f"Updated {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    return embed

# ─── Cog ───────────────────────────────────────────────────────────────────────
class GeneratorCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.backoff_until = 0.0
        self.generator_list_loop.start()

    def cog_unload(self):
        self.generator_list_loop.cancel()

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

    @app_commands.command(name="delete_gen_list", description="Delete a generator list")
    @app_commands.describe(name="Name of generator list to delete")
    async def delete_gen_list_cmd(self, interaction: discord.Interaction, name: str):
        if not gen_list_exists(name):
            return await interaction.response.send_message(
                f"❌ `{name}` not found.", ephemeral=True
            )
        delete_gen_list(name)
        await interaction.response.send_message(
            f"🗑️ Deleted generator list `{name}`.", ephemeral=True
        )
        await refresh_dashboard(self.bot, name)

    @app_commands.command(name="add_gen_tek", description="Add a Tek generator")
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

    @app_commands.command(name="add_gen_electrical", description="Add an Electrical generator")
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
                try:
                    await refresh_dashboard(self.bot, list_name)
                except Exception as e:
                    await log_to_channel(self.bot, f"⚠️ refresh_dashboard failed for `{list_name}` after edit: {e}")
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
        new_data = [i for i in data if i.get("name") != gen_name]
        if len(new_data) == len(data):
            return await interaction.response.send_message(
                f"❌ Generator `{gen_name}` not found.", ephemeral=True
            )
        save_gen_list(list_name, new_data)
        await interaction.response.send_message(
            f"🗑️ Removed `{gen_name}`.", ephemeral=True
        )
        await refresh_dashboard(self.bot, list_name)

    @app_commands.command(name="set_gen_role", description="Set a role to ping when low or expiring soon")
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
