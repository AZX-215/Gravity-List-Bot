import time
import asyncio
import random
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
    save_gen_dashboard_id,
    set_gen_list_role,
    get_gen_list_role
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
            total_seconds = item["element"] * 64800 + item["shards"] * 648
            elapsed = max(0, now - start_time)
            total_shards = item["shards"] + item["element"] * 100
            elapsed_shards = min(total_shards, int(elapsed / 648))
            rem_shards = max(0, total_shards - elapsed_shards)
            rem_element = rem_shards // 100
            rem_shards %= 100
            rem = max(0, int(start_time + total_seconds - now))
            d, rem_hr = divmod(rem, 86400)
            h, r = divmod(rem_hr, 3600)
            m, s = divmod(r, 60)
            time_str = f"{d}d {h:02d}h {m:02d}m {s:02d}s" if d else f"{h:02d}h {m:02d}m {s:02d}s"
            timer_str = (
                f"{emoji}   {item['name']} — {time_str} | "
                f"Element: {rem_element} | Shards: {rem_shards}"
            )
        else:
            total_seconds = item["gas"] * 3600 + item["imbued"] * 14400
            elapsed = max(0, now - start_time)
            rem = max(0, int(start_time + total_seconds - now))
            d, rem_hr = divmod(rem, 86400)
            h, r = divmod(rem_hr, 3600)
            m, s = divmod(r, 60)
            time_str = f"{d}d {h:02d}h {m:02d}m {s:02d}s" if d else f"{h:02d}h {m:02d}m {s:02d}s"
            gas_used = min(item["gas"], int(elapsed // 3600))
            imbued_used = min(item["imbued"], int(elapsed // 14400))
            rem_gas = max(0, item["gas"] - gas_used)
            rem_imbued = max(0, item["imbued"] - imbued_used)
            timer_str = (
                f"{emoji}   {item['name']} — {time_str} | "
                f"Gas: {rem_gas} | Imbued: {rem_imbued}"
            )

        embed.add_field(name=timer_str, value="\u200b", inline=False)
    return embed

class GeneratorCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.generator_list_loop.start()

    def cog_unload(self):
        self.generator_list_loop.cancel()

    @tasks.loop(minutes=5)
    async def generator_list_loop(self):
        # Refresh all dashboards
        for name, dash in get_all_gen_dashboards().items():
            channel, message_id = (dash if isinstance(dash, (tuple, list))
                                   else (self.bot.get_channel(dash.get("channel_id")), dash.get("message_id")))
            if not channel or not message_id:
                continue
            try:
                msg = await channel.fetch_message(message_id)
                await msg.edit(embed=build_gen_embed(name))
                await asyncio.sleep(1 + random.random())
            except discord.errors.RateLimited as e:
                await asyncio.sleep(e.retry_after)
                try:
                    msg = await channel.fetch_message(message_id)
                    await msg.edit(embed=build_gen_embed(name))
                    await asyncio.sleep(1 + random.random())
                except Exception as ex:
                    print(f"[Dashboard Retry] {ex}")
            except Exception as e:
                print(f"[Dashboard Error] {e}")

        # Expiry ping logic
        now = time.time()
        for list_name in get_all_gen_list_names():
            data = load_gen_list(list_name)
            ping_role = get_gen_list_role(list_name)
            dash = get_gen_dashboard_id(list_name)
            channel = (self.bot.get_channel(dash[0]) if isinstance(dash, (tuple, list))
                       else self.bot.get_channel(dash.get("channel_id")) if dash else None)
            if not channel:
                continue

            for item in data:
                if not item.get("expired"):
                    dur = (item["element"] * 64800 + item["shards"] * 648
                           if item["type"] == "Tek"
                           else item["gas"] * 3600 + item["imbued"] * 14400)
                    if now > item["timestamp"] + dur:
                        item["expired"] = True
                        mention = f"<@&{ping_role}>" if ping_role else ""
                        try:
                            await channel.send(f"⚡ Generator **{item['name']}** expired! {mention}")
                            await asyncio.sleep(1 + random.random())
                        except discord.errors.RateLimited as e:
                            await asyncio.sleep(e.retry_after)
                            await channel.send(f"⚡ Generator **{item['name']}** expired! {mention}")
                            await asyncio.sleep(1 + random.random())
                        except Exception as e:
                            print(f"[Ping Error] {e}")
            save_gen_list(list_name, data)

    @app_commands.command(name="resync_gens", description="Force-refresh all generator dashboards (admin only)")
    async def resync_gens(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Admin only.", ephemeral=True)
        await interaction.response.defer(thinking=True)
        for name, dash in get_all_gen_dashboards().items():
            channel, message_id = (dash if isinstance(dash, (tuple, list))
                                   else (self.bot.get_channel(dash.get("channel_id")), dash.get("message_id")))
            if not channel or not message_id:
                continue
            try:
                msg = await channel.fetch_message(message_id)
                await msg.edit(embed=build_gen_embed(name))
                await asyncio.sleep(1 + random.random())
            except discord.errors.RateLimited as e:
                await asyncio.sleep(e.retry_after)
                try:
                    msg = await channel.fetch_message(message_id)
                    await msg.edit(embed=build_gen_embed(name))
                    await asyncio.sleep(1 + random.random())
                except Exception as ex:
                    print(f"[Manual Retry] {ex}")
            except Exception as e:
                print(f"[Manual Force Sync Error] {e}")
        await interaction.followup.send("✅ Force-refreshed all generator dashboards.", ephemeral=True)

    @app_commands.command(name="create_gen_list", description="Create a new generator list")
    @app_commands.describe(name="Name of the new generator list")
    async def create_gen_list(self, interaction: discord.Interaction, name: str):
        if gen_list_exists(name):
            return await interaction.response.send_message(f"⚠️ Gen list '{name}' exists.", ephemeral=True)
        save_gen_list(name, [])
        await interaction.response.send_message(f"✅ Created generator list '{name}'.", ephemeral=True)

    @app_commands.command(name="add_gen", description="Add a generator entry")
    @app_commands.describe(
        list_name="Which generator list",
        entry_name="Entry name",
        gen_type="Generator type",
        element="Element baskets (Tek)",
        shards="Shards (Tek)",
        gas="Gas hours (Electrical)",
        imbued="Imbued gas hours (Electrical)"
    )
    @app_commands.choices(gen_type=[
        app_commands.Choice(name="Tek", value="Tek"),
        app_commands.Choice(name="Electrical", value="Electrical")
    ])
    async def add_gen(
        self,
        interaction: discord.Interaction,
        list_name: str,
        entry_name: str,
        gen_type: app_commands.Choice[str],
        element: int = 0,
        shards: int = 0,
        gas: int = 0,
        imbued: int = 0
    ):
        if not gen_list_exists(list_name):
            return await interaction.response.send_message(f"❌ Gen list '{list_name}' not found.", ephemeral=True)
        add_to_gen_list(list_name, entry_name, gen_type.value, element, shards, gas, imbued)
        await interaction.response.send_message(f"✅ Added '{entry_name}' to '{list_name}'.", ephemeral=True)

    @app_commands.command(name="remove_gen", description="Remove a generator entry")
    @app_commands.describe(list_name="Which generator list", name="Entry to remove")
    async def remove_gen(self, interaction: discord.Interaction, list_name: str, name: str):
        if not gen_list_exists(list_name):
            return await interaction.response.send_message(f"❌ Gen list '{list_name}' not found.", ephemeral=True)
        data = load_gen_list(list_name)
        new_data = [item for item in data if item["name"].lower() != name.lower()]
        save_gen_list(list_name, new_data)
        await interaction.response.send_message(f"🗑️ Removed '{name}' from '{list_name}'.", ephemeral=True)

    @app_commands.command(name="delete_gen_list", description="Delete an entire generator list")
    @app_commands.describe(name="Name of the list to delete")
    async def delete_gen_list_cmd(self, interaction: discord.Interaction, name: str):
        if not gen_list_exists(name):
            return await interaction.response.send_message(f"❌ Gen list '{name}' not found.", ephemeral=True)
        delete_gen_list(name)
        await interaction.response.send_message(f"🗑️ Deleted generator list '{name}'.", ephemeral=True)

    @app_commands.command(name="set_gen_role", description="Set the ping role for a generator list")
    @app_commands.describe(list_name="Which generator list", role="Role to ping on expiration")
    async def set_gen_role(self, interaction: discord.Interaction, list_name: str, role: discord.Role):
        if not gen_list_exists(list_name):
            return await interaction.response.send_message(f"❌ Gen list '{list_name}' not found.", ephemeral=True)
        set_gen_list_role(list_name, role.id)
        await interaction.response.send_message(f"✅ Ping role set for '{list_name}'.", ephemeral=True)

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
