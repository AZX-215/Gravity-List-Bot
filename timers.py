import time
import uuid
import discord
from discord.ext import commands, tasks
from discord import app_commands
from data_manager import load_timers, add_timer, save_timers, remove_timer

POLL_INTERVAL = 1  # update every second

class TimerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.timer_loop.start()

    def cog_unload(self):
        self.timer_loop.cancel()

    def build_timer_embed(self, data):
        now = time.time()
        if data.get("paused", False):
            remaining = data.get("remaining_time", 0)
            status    = "⏸️ Paused"
            color     = 0xFFD700
        else:
            remaining = data["end_time"] - now
            if remaining > 0:
                status = "⏳ Running"
                color  = 0x00FF00
            else:
                remaining = 0
                status    = "✅ Expired"
                color     = 0xFF0000
        hrs, rem = divmod(int(remaining), 3600)
        mins, sec= divmod(rem, 60)
        timer_str= f"{hrs:02d}h {mins:02d}m {sec:02d}s"
        embed = discord.Embed(
            title=f"Timer: {data['name']}",
            description=f"{status}\nRemaining: {timer_str}",
            color=color
        )
        return embed

    @app_commands.command(name="create_timer", description="Create a countdown timer")
    @app_commands.describe(name="Timer name", hours="Hours", minutes="Minutes")
    async def create_timer(self, interaction: discord.Interaction, name: str, hours: int, minutes: int):
        total   = hours*3600 + minutes*60
        end_ts  = time.time() + total
        tid     = str(uuid.uuid4())
        timer_data = {
            "name": name,
            "end_time": end_ts,
            "channel_id": interaction.channel_id,
            "message_id": None,
            "paused": False
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
                remaining = data["end_time"] - time.time()
                data["remaining_time"] = remaining
                data["paused"] = True
                data.pop("end_time", None)
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
                remaining = data.get("remaining_time", 0)
                data["end_time"] = time.time() + remaining
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
        await interaction.response.send_message(
            f"❌ No timer named '{name}' found", ephemeral=True
        )

    @tasks.loop(seconds=POLL_INTERVAL)
    async def timer_loop(self):
        if not self.bot.is_ready():
            return
        timers = load_timers()
        for tid, data in timers.items():
            channel = self.bot.get_channel(data["channel_id"])
            if channel:
                try:
                    msg = await channel.fetch_message(data["message_id"])
                    await msg.edit(embed=self.build_timer_embed(data))
                except:
                    pass

async def setup(bot: commands.Bot):
    await bot.add_cog(TimerCog(bot))
