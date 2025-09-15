import time
import uuid
import discord
from discord.ext import commands, tasks
from discord import app_commands
from data_manager import load_timers, add_timer, save_timers, remove_timer


class TimerCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.expiration_loop.start()

    def cog_unload(self):
        self.expiration_loop.cancel()

    def build_timer_embed(self, data):
        embed = discord.Embed(title=f"Timer: {data['name']}")
        # Paused state
        if data.get("paused", False):
            remaining = int(data.get("remaining_time", 0))
            hrs, rem = divmod(remaining, 3600)
            mins, sec = divmod(rem, 60)
            embed.description = f"⏸️ Paused — {hrs:02d}h{mins:02d}m{sec:02d}s"
            embed.color = 0xFFD700
        # Expired state
        elif data.get("expired", False):
            embed.description = "✅ Expired"
            embed.color = 0xFF0000
        # Active state
        else:
            end_ts = int(data["end_time"])
            embed.description = f"⏳ Ends <t:{end_ts}:R>"
            embed.color = 0x00FF00

        # Footer ping role or owner
        if data.get("role_id"):
            embed.set_footer(text=f"Pings: <@&{data['role_id']}>")
        elif data.get("owner_id"):
            embed.set_footer(text=f"Pings: <@{data['owner_id']}>")

        return embed

    @app_commands.command(name="create_timer", description="Create a countdown timer")
    @app_commands.describe(
        name="Timer name", hours="Hours", minutes="Minutes", role="Role to ping when timer expires"
    )
    async def create_timer(
        self,
        interaction: discord.Interaction,
        name: str,
        hours: int,
        minutes: int,
        role: discord.Role = None,
    ):
        total = hours * 3600 + minutes * 60
        end_ts = time.time() + total
        tid = str(uuid.uuid4())
        timer_data = {
            "name": name,
            "end_time": end_ts,
            "channel_id": interaction.channel_id,
            "message_id": None,
            "paused": False,
            "owner_id": interaction.user.id,
            "role_id": role.id if role else None,
            "expired": False,
        }
        embed = self.build_timer_embed(timer_data)
        await interaction.response.send_message(embed=embed)
        msg = await interaction.original_response()
        timer_data["message_id"] = msg.id
        add_timer(tid, timer_data)

    @app_commands.command(name="pause_timer", description="Pause a running timer")
    @app_commands.describe(name="Name of timer to pause")
    async def pause_timer(self, interaction: discord.Interaction, name: str):
        timers = load_timers()
        for tid, data in timers.items():
            if data["name"].lower() == name.lower() and not data.get("paused", False):
                data["remaining_time"] = data["end_time"] - time.time()
                data["paused"] = True
                save_timers(timers)
                channel = self.bot.get_channel(data["channel_id"])
                if channel:
                    try:
                        msg = await channel.fetch_message(data["message_id"])
                        await msg.edit(embed=self.build_timer_embed(data))
                    except:
                        pass
                return await interaction.response.send_message(
                    f"⏸️ Paused timer '{name}'", ephemeral=True
                )
        await interaction.response.send_message(
            f"❌ No running timer named '{name}' found", ephemeral=True
        )

    @app_commands.command(name="resume_timer", description="Resume a paused timer")
    @app_commands.describe(name="Name of timer to resume")
    async def resume_timer(self, interaction: discord.Interaction, name: str):
        timers = load_timers()
        for tid, data in timers.items():
            if data["name"].lower() == name.lower() and data.get("paused", False):
                data["end_time"] = time.time() + data["remaining_time"]
                data["paused"] = False
                data.pop("remaining_time", None)
                save_timers(timers)
                channel = self.bot.get_channel(data["channel_id"])
                if channel:
                    try:
                        msg = await channel.fetch_message(data["message_id"])
                        await msg.edit(embed=self.build_timer_embed(data))
                    except:
                        pass
                return await interaction.response.send_message(
                    f"▶️ Resumed timer '{name}'", ephemeral=True
                )
        await interaction.response.send_message(
            f"❌ No paused timer named '{name}' found", ephemeral=True
        )

    @app_commands.command(name="edit_timer", description="Edit duration of an existing timer")
    @app_commands.describe(name="Name of timer to edit", hours="New hours", minutes="New minutes")
    async def edit_timer(
        self, interaction: discord.Interaction, name: str, hours: int, minutes: int
    ):
        timers = load_timers()
        for tid, data in timers.items():
            if data["name"].lower() == name.lower():
                total = hours * 3600 + minutes * 60
                if data.get("paused", False):
                    data["remaining_time"] = total
                else:
                    data["end_time"] = time.time() + total
                save_timers(timers)
                channel = self.bot.get_channel(data["channel_id"])
                if channel:
                    try:
                        msg = await channel.fetch_message(data["message_id"])
                        await msg.edit(embed=self.build_timer_embed(data))
                    except:
                        pass
                return await interaction.response.send_message(
                    f"✏️ Updated timer '{name}' to {hours}h{minutes}m", ephemeral=True
                )
        await interaction.response.send_message(f"❌ No timer named '{name}' found", ephemeral=True)

    @app_commands.command(name="delete_timer", description="Delete a timer")
    @app_commands.describe(name="Name of timer to delete")
    async def delete_timer(self, interaction: discord.Interaction, name: str):
        timers = load_timers()
        for tid, data in list(timers.items()):
            if data["name"].lower() == name.lower():
                remove_timer(tid)
                return await interaction.response.send_message(
                    f"🗑️ Deleted timer '{name}'", ephemeral=True
                )
        await interaction.response.send_message(f"❌ No timer named '{name}' found", ephemeral=True)

    @tasks.loop(minutes=1)
    async def expiration_loop(self):
        if not self.bot.is_ready():
            return
        timers = load_timers()
        now = time.time()
        changed = False
        for tid, data in timers.items():
            if not data.get("expired", False) and not data.get("paused", False):
                if now >= data["end_time"]:
                    data["expired"] = True
                    changed = True
                    channel = self.bot.get_channel(data["channel_id"])
                    ping = (
                        f"<@&{data['role_id']}>"
                        if data.get("role_id")
                        else f"<@{data['owner_id']}>"
                    )
                    if channel:
                        await channel.send(f"⏰ Timer **{data['name']}** expired! {ping}")
        if changed:
            save_timers(timers)


async def setup(bot: commands.Bot):
    await bot.add_cog(TimerCog(bot))
