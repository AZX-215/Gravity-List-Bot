# debug_storage.py
import os, glob, shutil, discord
from discord.ext import commands
from discord import app_commands
from data_manager import (
    BASE_DATA, BASE_DIR,
    LISTS_DIR, GEN_LISTS_DIR,
    DASHBOARDS_PATH, GEN_DASHBOARDS_PATH,
    TIMERS_PATH
)

def _ls_json(dirpath: str):
    try:
        return sorted(os.path.basename(p) for p in glob.glob(os.path.join(dirpath, "*.json")))
    except Exception:
        return []

class DebugStorageCog(commands.Cog):
    """Admin-only utilities to inspect and migrate list files on the live container."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="debug_storage",
                          description="Show where the bot stores data and list the json files it sees.")
    async def debug_storage(self, interaction: discord.Interaction):
        lists = _ls_json(LISTS_DIR)
        gen_lists = _ls_json(GEN_LISTS_DIR)
        text = []
        text.append(f"DATABASE_PATH: {BASE_DATA}")
        text.append(f"BASE_DIR: {BASE_DIR}")
        text.append(f"LISTS_DIR: {LISTS_DIR} ({len(lists)} files)")
        text += [f"  - {n}" for n in lists]
        text.append(f"GEN_LISTS_DIR: {GEN_LISTS_DIR} ({len(gen_lists)} files)")
        text += [f"  - {n}" for n in gen_lists]
        text.append(f"DASHBOARDS_PATH: {DASHBOARDS_PATH}")
        text.append(f"GEN_DASHBOARDS_PATH: {GEN_DASHBOARDS_PATH}")
        text.append(f"TIMERS_PATH: {TIMERS_PATH}")
        await interaction.response.send_message("```\n" + "\n".join(text) + "\n```", ephemeral=True)

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(
        name="migrate_regular_lists_to_subdir",
        description="Copy *.json from /app/lists (old) → /app/lists/lists (new)."
    )
    @app_commands.describe(cleanup="If true, delete originals after copy")
    async def migrate_regular_lists_to_subdir(self, interaction: discord.Interaction, cleanup: bool=False):
        # old layout: /app/lists/*.json
        src_glob = os.path.join(os.path.dirname(LISTS_DIR), "*.json")
        dst_dir = LISTS_DIR
        os.makedirs(dst_dir, exist_ok=True)
        moved = []
        try:
            for path in glob.glob(src_glob):
                base = os.path.basename(path)
                if not base.endswith(".json"): 
                    continue
                shutil.copy2(path, os.path.join(dst_dir, base))
                moved.append(base)
                if cleanup:
                    os.remove(path)
        except Exception as e:
            return await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)
        if not moved:
            return await interaction.response.send_message("No top-level list JSONs found to migrate.", ephemeral=True)
        await interaction.response.send_message(
            f"✅ Copied {len(moved)} file(s) into `{dst_dir}`:\n" + "\n".join(f"- {m}" for m in moved),
            ephemeral=True
        )

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(
        name="migrate_gen_lists_to_volume",
        description="Copy generator lists to a volume dir (default: /app/lists/generator_lists)."
    )
    @app_commands.describe(target_dir="Destination directory", cleanup="If true, delete originals after copy")
    async def migrate_gen_lists_to_volume(self, interaction: discord.Interaction,
                                          target_dir: str="/app/lists/generator_lists", cleanup: bool=False):
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
