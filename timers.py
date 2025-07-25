
import time
import asyncio
import uuid
import discord
from discord.ext import commands, tasks
from discord import app_commands
from data_manager import load_timers, add_timer, remove_timer

POLL_INTERVAL = 60  # seconds

class TimerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.timer_loop.start()

    def cog_unload(self):
        self.timer_loop.cancel()

    def build_timer_embed(self, data):
        name = data["name"]
        end_ts = data["end_time"]
        now_ts = time.time()
        remaining = int(end_ts - now_ts)
        if remaining > 0:
            hrs, rem = divmod(remaining, 3600)
            mins, secs = divmod(rem, 60)
            timer_str = f"{hrs:02d}h {mins:02d}m {secs:02d}s"
            status = "⏳ Running"
            color = 0x00FF00
        else:
            timer_str = "00h 00m 00s"
            status = "✅ Expired"
            color = 0xFF0000
        embed = discord.Embed(
            title=f"Timer: {name}",
            description=f"{status}\nRemaining: {timer_str}",
            color=color
        )
        return embed

    @app_commands.command(name="create_timer", description="Create a countdown timer")
    @app_commands.describe(name="Name of the timer", hours="Hours to countdown", minutes="Minutes to countdown")
    async def create_timer(self, interaction: discord.Interaction, name: str, hours: int, minutes: int):
        total = hours*3600 + minutes*60
        end_ts = time.time() + total
        tid = str(uuid.uuid4())
        timer_data = {
            "name": name,
            "end_time": end_ts,
            "channel_id": interaction.channel_id,
            "message_id": None
        }
        embed = self.build_timer_embed(timer_data)
        await interaction.response.send_message(embed=embed)
        msg = await interaction.original_response()
        timer_data["message_id"] = msg.id
        add_timer(tid, timer_data)

    @tasks.loop(seconds=POLL_INTERVAL)
    async def timer_loop(self):
        if not self.bot.is_ready():
            return
        timers = load_timers()
        for tid, data in list(timers.items()):
            channel = self.bot.get_channel(data["channel_id"])
            if channel:
                try:
                    msg = await channel.fetch_message(data["message_id"])
                    embed = self.build_timer_embed(data)
                    await msg.edit(embed=embed)
                    if time.time() >= data["end_time"]:
                        remove_timer(tid)
                except (discord.NotFound, discord.Forbidden):
                    pass

async def setup(bot: commands.Bot):
    await bot.add_cog(TimerCog(bot))
