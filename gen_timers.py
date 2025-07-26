
import time
import discord
from discord.ext import commands, tasks
from discord import app_commands
from data_manager import (
    load_gen_list, save_gen_list, gen_list_exists, delete_gen_list, get_all_gen_list_names,
    add_to_gen_list, get_all_gen_dashboards, get_gen_dashboard_id, save_gen_dashboard_id, get_gen_list_hash
)

GEN_EMOJIS = {"Tek":"🔄", "Electrical":"⛽"}

def build_gen_embed(list_name: str) -> discord.Embed:
    data = load_gen_list(list_name)
    embed = discord.Embed(title=f"{list_name} Generators", color=0x404040)
    now = time.time()
    for item in data:
        emoji = GEN_EMOJIS.get(item["type"], "")
        if item["type"] == "Tek":
            dur = item["element"] * 18*3600 + item["shards"] * 600
        else:
            dur = item["gas"] * 3600 + item["imbued"] * 4*3600
        rem = max(0, int(item["timestamp"] + dur - now))
        h, r = divmod(rem, 3600)
        m, s = divmod(r, 60)
        timer_str = f"{h:02d}h {m:02d}m {s:02d}s"
        embed.add_field(name=f"{emoji} {item['name']}", value=timer_str, inline=False)
    return embed

class GeneratorCog(commands.Cog):
    """Cog for Ark generator list commands and live countdowns."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.generator_list_loop.start()

    def cog_unload(self):
        self.generator_list_loop.cancel()

    @tasks.loop(seconds=2)
    async def generator_list_loop(self):
        for name, dash in get_all_gen_dashboards().items():
            channel = self.bot.get_channel(dash["channel_id"])
            if not channel:
                continue
            try:
                msg = await channel.fetch_message(dash["message_id"])
                await msg.edit(embed=build_gen_embed(name))
            except:
                pass

    @app_commands.command(name="create_generator_list", description="Create a new generator timer list")
    @app_commands.describe(name="Name of the generator list")
    async def create_generator_list(self, interaction: discord.Interaction, name: str):
        if gen_list_exists(name):
            return await interaction.response.send_message(f"⚠️ Generator list '{name}' exists.", ephemeral=True)
        save_gen_list(name, [])
        await interaction.response.send_message(f"✅ Created generator list '{name}'.", ephemeral=True)

    @app_commands.command(name="add_generator", description="Add a generator entry to a list")
    @app_commands.describe(
        list_name="Which generator list", entry_name="Generator name",
        gen_type="Generator type", element="Element amount", shards="Shards amount",
        gas="Gas amount", imbued="Element imbued gas amount"
    )
    @app_commands.choices(gen_type=[
        app_commands.Choice(name="Tek", value="Tek"),
        app_commands.Choice(name="Electrical", value="Electrical")
    ])
    async def add_generator(
        self, interaction: discord.Interaction, list_name: str, entry_name: str, gen_type: app_commands.Choice[str],
        element: int = 0, shards: int = 0, gas: int = 0, imbued: int = 0
    ):
        if not gen_list_exists(list_name):
            return await interaction.response.send_message(f"❌ Generator list '{list_name}' not found.", ephemeral=True)
        if gen_type.value == "Tek" and (element + shards) == 0:
            return await interaction.response.send_message("❌ Provide element or shards.", ephemeral=True)
        if gen_type.value == "Electrical" and (gas + imbued) == 0:
            return await interaction.response.send_message("❌ Provide gas or imbued gas.", ephemeral=True)
        add_to_gen_list(list_name, entry_name, gen_type.value, element, shards, gas, imbued)
        await interaction.response.send_message(f"✅ Added '{entry_name}' to '{list_name}'.", ephemeral=True)

    @app_commands.command(name="edit_generator", description="Edit a generator entry")
    @app_commands.describe(
        list_name="Which generator list", old_name="Existing entry", new_name="New entry name",
        element="Element amount", shards="Shards amount", gas="Gas amount", imbued="Element imbued gas amount"
    )
    async def edit_generator(
        self, interaction: discord.Interaction, list_name: str, old_name: str, new_name: str,
        element: int = 0, shards: int = 0, gas: int = 0, imbued: int = 0
    ):
        if not gen_list_exists(list_name):
            return await interaction.response.send_message(f"❌ Generator list '{list_name}' not found.", ephemeral=True)
        data = load_gen_list(list_name)
        for item in data:
            if item["name"].lower() == old_name.lower():
                item.update({"name": new_name, "element": element, "shards": shards, "gas": gas, "imbued": imbued})
                break
        save_gen_list(list_name, data)
        await interaction.response.send_message(f"✏️ Updated generator '{old_name}'.", ephemeral=True)

    @app_commands.command(name="remove_generator", description="Remove a generator entry")
    @app_commands.describe(list_name="Which generator list", entry_name="Entry to remove")
    async def remove_generator(self, interaction: discord.Interaction, list_name: str, entry_name: str):
        if not gen_list_exists(list_name):
            return await interaction.response.send_message(f"❌ Generator list '{list_name}' not found.", ephemeral=True)
        data = [e for e in load_gen_list(list_name) if e["name"].lower() != entry_name.lower()]
        save_gen_list(list_name, data)
        await interaction.response.send_message(f"🗑️ Removed '{entry_name}' from '{list_name}'.", ephemeral=True)

    @app_commands.command(name="delete_generator_list", description="Delete a generator list")
    @app_commands.describe(name="Name of the generator list to delete")
    async def delete_generator_list(self, interaction: discord.Interaction, name: str):
        if not gen_list_exists(name):
            return await interaction.response.send_message(f"❌ Generator list '{name}' not found.", ephemeral=True)
        delete_gen_list(name)
        await interaction.response.send_message(f"🗑️ Deleted generator list '{name}'.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(GeneratorCog(bot))
