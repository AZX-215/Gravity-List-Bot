import time
import asyncio
import random
import discord
from discord.ext import commands, tasks
from discord import app_commands
from data_manager import (
    load_gen_list, save_gen_list, gen_list_exists, delete_gen_list, get_all_gen_list_names,
    add_to_gen_list, get_all_gen_dashboards, get_gen_dashboard_id,
    save_gen_dashboard_id, set_gen_list_role, get_gen_list_role
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
            rem_shards = rem_shards % 100
            rem = max(0, int(start_time + total_seconds - now))
        else:
            total_seconds = item["gas"] * 3600 + item["imbued"] * 14400
            elapsed = max(0, now - start_time)
            rem = max(0, int(start_time + total_seconds - now))

        d, rem_hr = divmod(rem, 86400)
        h, r = divmod(rem_hr, 3600)
        m, s = divmod(r, 60)
        time_str = f"{h:02d}h {m:02d}m {s:02d}s" if d == 0 else f"{d}d {h:02d}h {m:02d}m {s:02d}s"

        if item["type"] == "Tek":
            timer_str = (
                f"{emoji}   {item['name']} — {time_str} | "
                f"Element: {rem_element} | Shards: {rem_shards}"
            )
        else:
            gas_used = min(item["gas"], int(elapsed // 3600))
            imbued_used = min(item["imbued"], int(elapsed // 14400))
            rem_gas = max(0, item["gas"] - gas_used)
            rem_imbued = max(0, item["imbued"] - imbued_used)
            timer_str = (
                f"{emoji}   {item['name']} — {time_str} | "
                f"Gas: {rem_gas} | Imbued: {rem_imbued}"
            )

        embed.add_field(name=timer_str, value="​", inline=False)

    return embed


class GeneratorCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.generator_list_loop.start()

    def cog_unload(self):
        self.generator_list_loop.cancel()

    @tasks.loop(minutes=2)
    async def generator_list_loop(self):
        for name, dash in get_all_gen_dashboards().items():
            channel = None
            message_id = None
            if dash:
                if isinstance(dash, (tuple, list)):
                    channel, message_id = dash
                elif isinstance(dash, dict):
                    channel = self.bot.get_channel(dash.get("channel_id"))
                    message_id = dash.get("message_id")
            if not channel or not message_id:
                continue
            try:
                msg = await channel.fetch_message(message_id)
                await msg.edit(embed=build_gen_embed(name))
                # throttle with jitter to avoid hitting rate limits
                await asyncio.sleep(1 + random.random())
            except discord.errors.RateLimited as e:
                print(f"[RateLimited] Sleeping for {e.retry_after}s before retry")
                await asyncio.sleep(e.retry_after)
                try:
                    msg = await channel.fetch_message(message_id)
                    await msg.edit(embed=build_gen_embed(name))
                except Exception as ex:
                    print(f"[GenTimer Dashboard Retry] {ex}")
                await asyncio.sleep(1 + random.random())
            except Exception as e:
                print(f"[GenTimer Dashboard] {e}")

        now = time.time()
        for list_name in get_all_gen_list_names():
            data = load_gen_list(list_name)
            ping_role = get_gen_list_role(list_name)
            dash = save_gen_dashboard_id if False else get_gen_dashboard_id(list_name)
            channel = None
            if dash:
                if isinstance(dash, (tuple, list)):
                    channel = self.bot.get_channel(dash[0])
                elif isinstance(dash, dict):
                    channel = self.bot.get_channel(dash.get("channel_id"))
            for item in data:
                if not item.get("expired"):
                    dur = (
                        item["element"] * 64800 + item["shards"] * 648
                        if item["type"] == "Tek"
                        else item["gas"] * 3600 + item["imbued"] * 14400
                    )
                    if now > item["timestamp"] + dur:
                        item["expired"] = True
                        mention = f"<@&{ping_role}>" if ping_role else ""
                        if channel:
                            try:
                                await channel.send(f"⚡ Generator **{item['name']}** expired! {mention}")
                                await asyncio.sleep(1 + random.random())
                            except discord.errors.RateLimited as e:
                                print(f"[Ping RateLimited] Sleeping for {e.retry_after}s")
                                await asyncio.sleep(e.retry_after)
                                await channel.send(f"⚡ Generator **{item['name']}** expired! {mention}")
                                await asyncio.sleep(1 + random.random())
                            except Exception as e:
                                print(f"[GenTimer Ping] {e}")
            save_gen_list(list_name, data)

    @app_commands.command(
        name="resync_gens",
        description="Force-refresh all generator list dashboards (admin only)"
    )
    async def resync_gens(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(
                "❌ Admin only.", ephemeral=True
            )
        await interaction.response.defer(thinking=True)

        for name, dash in get_all_gen_dashboards().items():
            channel = None
            message_id = None
            if dash:
                if isinstance(dash, (tuple, list)):
                    channel, message_id = dash
                elif isinstance(dash, dict):
                    channel = self.bot.get_channel(dash.get("channel_id"))
                    message_id = dash.get("message_id")
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
                except Exception as ex:
                    print(f"[Manual Retry] {ex}")
                await asyncio.sleep(1 + random.random())
            except Exception as e:
                print(f"[GenTimer Manual Force Sync] {e}")

        await interaction.followup.send(
            "✅ Force-refreshed all generator dashboards.", ephemeral=True
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(GeneratorCog(bot))
