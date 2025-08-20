# debug_storage.py
import os
import glob
import shutil
import discord
from discord.ext import commands
from discord import app_commands

# Use your existing path constants from data_manager
from data_manager import (
    BASE_DATA, BASE_DIR,
    LISTS_DIR, GEN_LISTS_DIR,
    DASHBOARDS_PATH, GEN_DASHBOARDS_PATH,
    TIMERS_PATH
)

RESERVED_JSON = {
    "dashboards.json", "generator_dashboards.json", "timers.json", "data.json"
}

def _ls_json(dirpath: str):
    try:
        return sorted(os.path.basename(p) for p in glob.glob(os.path.join(dirpath, "*.json")))
    except Exception:
        return []

def _clip(text: str, limit: int = 1800) -> str:
    if len(text) <= limit:
        return text
    cut = text.rfind("\n", 0, limit)
    if cut == -1:
        cut = limit
    return text[:cut] + "\n... (truncated) ..."

class DebugStorageCog(commands.Cog):
    """Admin-only utilities to inspect and migrate list files on the live container."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="debug_storage",
                          description="Show storage paths and the *.json files the bot can see.")
    async def debug_storage(self, interaction: discord.Interaction):
        lists = _ls_json(LISTS_DIR)
        gen_lists = _ls_json(GEN_LISTS_DIR)

        lines = []
        lines.append(f"DATABASE_PATH: {BASE_DATA}")
        lines.append(f"BASE_DIR: {BASE_DIR}")
        lines.append(f"LISTS_DIR: {LISTS_DIR} ({len(lists)} file(s))")
        lines += [f"  - {n}" for n in lists]
        lines.append(f"GEN_LISTS_DIR: {GEN_LISTS_DIR} ({len(gen_lists)} file(s))")
        lines += [f"  - {n}" for n in gen_lists]
        lines.append(f"DASHBOARDS_PATH: {DASHBOARDS_PATH}")
        lines.append(f"GEN_DASHBOARDS_PATH: {GEN_DASHBOARDS_PATH}")
        lines.append(f"TIMERS_PATH: {TIMERS_PATH}")

        body = _clip("\n".join(lines))
        await interaction.response.send_message(f"```\n{body}\n```", ephemeral=True)

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(
        name="migrate_regular_lists_to_subdir",
        description="Copy real list JSONs from the parent dir into LISTS_DIR (skips dashboards/timers)."
    )
    @app_commands.describe(cleanup="If true, delete originals after successful copy.")
    async def migrate_regular_lists_to_subdir(self, interaction: discord.Interaction, cleanup: bool = False):
        # Example when BASE_DIR=/app/lists:
        #   src_glob -> /app/lists/*.json
        #   dst_dir  -> /app/lists/lists
        src_glob = os.path.join(os.path.dirname(LISTS_DIR), "*.json")
        dst_dir = LISTS_DIR
        os.makedirs(dst_dir, exist_ok=True)

        moved = []
        try:
            for path in glob.glob(src_glob):
                base = os.path.basename(path)
                if not base.endswith(".json"):
                    continue
                if base in RESERVED_JSON:
                    continue  # don't pollute LISTS_DIR with reserved config files
                shutil.copy2(path, os.path.join(dst_dir, base))
                moved.append(base)
                if cleanup:
                    os.remove(path)
        except Exception as e:
            return await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

        if not moved:
            return await interaction.response.send_message("No regular list JSONs found to migrate.", ephemeral=True)

        await interaction.response.send_message(
            f"✅ Copied {len(moved)} file(s) into `{dst_dir}`:\n" + "\n".join(f"- {m}" for m in moved),
            ephemeral=True
        )

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(
        name="migrate_gen_lists_to_volume",
        description="Copy GEN_LISTS_DIR/*.json → target_dir (default /app/lists/generator_lists)."
    )
    @app_commands.describe(
        target_dir="Destination directory (default: /app/lists/generator_lists)",
        cleanup="If true, delete originals after successful copy."
    )
    async def migrate_gen_lists_to_volume(
        self,
        interaction: discord.Interaction,
        target_dir: str = "/app/lists/generator_lists",
        cleanup: bool = False
    ):
        src_dir = GEN_LISTS_DIR
        dst_dir = target_dir
        os.makedirs(dst_dir, exist_ok=True)

        moved = []
        try:
            for path in glob.glob(os.path.join(src_dir, "*.json")):
                base = os.path.basename(path)
                shutil.copy2(path, os.path.join(dst_dir, base))
                moved.append(base)
                if cleanup:
                    os.remove(path)
        except Exception as e:
            return await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

        if not moved:
            return await interaction.response.send_message("No generator list JSONs found to migrate.", ephemeral=True)

        await interaction.response.send_message(
            f"✅ Copied {len(moved)} file(s) from `{src_dir}` to `{dst_dir}`:\n" +
            "\n".join(f"- {m}" for m in moved),
            ephemeral=True
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(DebugStorageCog(bot))
