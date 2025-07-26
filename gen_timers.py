import time
import discord
from discord.ext import commands, tasks
from discord import app_commands
from data_manager import (
    load_gen_list, save_gen_list, gen_list_exists, delete_gen_list, get_all_gen_list_names,
    add_to_gen_list, get_all_gen_dashboards, get_gen_dashboard_id, save_gen_dashboard_id, get_gen_list_hash,
    set_gen_list_role, get_gen_list_role
)

GEN_EMOJIS = {"Tek": "🔄", "Electrical": "⛽"}

def build_gen_embed(list_name: str) -> discord.Embed:
    data = load_gen_list(list_name)
    embed = discord.Embed(title=f"{list_name} Generators", color=0x404040)
    now = time.time()
    for item in data:
        emoji = GEN_EMOJIS.get(item["type"], "")
        start_time = item["timestamp"]
        if item["type"] == "Tek":
            # 1 element = 18h (64800s), 100 shards = 18h, 1 shard = 648s
            total_seconds = item["element"] * 64800 + item["shards"] * 648
            elapsed = max(0, now - start_time)
            total_shards = item["shards"] + item["element"] * 100
            elapsed_shards = min(total_shards, int(elapsed / 648))
            rem_shards = max(0, total_shards - elapsed_shards)
            rem_element = rem_shards // 100
            rem_shards = rem_shards % 100
            rem = max(0, int(item["timestamp"] + total_seconds - now))
            h, r = divmod(rem, 3600)
            m, s = divmod(r, 60)
            timer_str = f"{h:02d}h {m:02d}m {s:02d}s | Element: {rem_element} | Shards: {rem_shards}"
        else:
            # 1 gas = 1h (3600s), 1 imbued = 4h (14400s)
            total_seconds = item["gas"] * 3600 + item["imbued"] * 14400
            elapsed = max(0, now - start_time)
            gas_used = min(item["gas"], int(elapsed // 3600))
            imbued_used = min(item["imbued"], int(elapsed // 14400))
            rem_gas = max(0, item["gas"] - gas_used)
            rem_imbued = max(0, item["imbued"] - imbued_used)
            rem = max(0, int(item["timestamp"] + total_seconds - now))
            h, r = divmod(rem, 3600)
            m, s = divmod(r, 60)
            timer_str = f"{h:02d}h {m:02d}m {s:02d}s | Gas: {rem_gas} | Imbued: {rem_imbued}"
        embed.add_field(name=f"{emoji} {item['name']}", value=timer_str, inline=False)
    return embed

class GeneratorCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.generator_list_loop.start()

    def cog_unload(self):
        self.generator_list_loop.cancel()

@tasks.loop(minutes=2)
async def generator_list_loop(self):
    # 1. Update dashboards
    for name, dash in get_all_gen_dashboards().items():
        channel = None
        message_id = None
        if dash:
            if isinstance(dash, (tuple, list)):
                channel = self.bot.get_channel(dash[0])
                message_id = dash[1]
            elif isinstance(dash, dict):
                channel = self.bot.get_channel(dash.get("channel_id"))
                message_id = dash.get("message_id")
        if not channel or not message_id:
            continue
        try:
            msg = await channel.fetch_message(message_id)
            await msg.edit(embed=build_gen_embed(name))
        except Exception as e:
            print(f"[GenTimer Dashboard] Error: {e}")

    # 2. Expiry ping logic
    now = time.time()
    for list_name in get_all_gen_list_names():
        data = load_gen_list(list_name)
        ping_role = get_gen_list_role(list_name)
        dash = get_gen_dashboard_id(list_name)
        channel = None
        if dash:
            if isinstance(dash, (tuple, list)):
                channel = self.bot.get_channel(dash[0])
            elif isinstance(dash, dict):
                channel = self.bot.get_channel(dash.get("channel_id"))
        for item in data:
            if not item.get("expired"):
                if item["type"] == "Tek":
                    dur = item["element"] * 64800 + item["shards"] * 648
                else:
                    dur = item["gas"] * 3600 + item["imbued"] * 14400
                if now > item["timestamp"] + dur:
                    item["expired"] = True
                    mention = f"<@&{ping_role}>" if ping_role else ""
                    if channel:
                        try:
                            await channel.send(f"⚡ Generator **{item['name']}** expired! {mention}")
                        except Exception as e:
                            print(f"[GenTimer Ping] Error: {e}")
        save_gen_list(list_name, data)


    @app_commands.command(name="create_generator_list", description="Create a new generator timer list")
    @app_commands.describe(name="Name of the generator list", role="Role to ping if any generator timer expires")
    async def create_generator_list(self, interaction: discord.Interaction, name: str, role: discord.Role = None):
        if gen_list_exists(name):
            return await interaction.response.send_message(f"⚠️ Generator list '{name}' exists.", ephemeral=True)
        save_gen_list(name, [])
        if role:
            set_gen_list_role(name, role.id)
        await interaction.response.send_message(f"✅ Created generator list '{name}'{' with role ping' if role else ''}.", ephemeral=True)

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
