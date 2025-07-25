
import time
import uuid
import asyncio
import discord
from discord.ext import commands
from discord import app_commands
from data_manager import load_timers, add_timer, remove_timer

POLL_INTERVAL = 60  # seconds

def build_timer_embed(data: dict) -> discord.Embed:
    name = data["name"]
    end_ts = data["end_time"]
    now = time.time()
    remaining = int(end_ts - now)
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

class TimerCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.loop.create_task(self._timer_loop())

    @app_commands.command(name="create_timer", description="Create a countdown timer")
    @app_commands.describe(name="Timer name", hours="Hours to countdown", minutes="Minutes to countdown")
    async def create_timer(self, interaction: discord.Interaction, name: str, hours: int, minutes: int):
        total = hours * 3600 + minutes * 60
        end_ts = time.time() + total
        tid = str(uuid.uuid4())
        timer_data = {
            "name": name,
            "end_time": end_ts,
            "channel_id": interaction.channel_id,
            "message_id": None
        }
        embed = build_timer_embed(timer_data)
        await interaction.response.send_message(embed=embed)
        msg = await interaction.original_response()
        timer_data["message_id"] = msg.id
        add_timer(tid, timer_data)

    async def _timer_loop(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            timers = load_timers()
            for tid, data in list(timers.items()):
                channel = self.bot.get_channel(data["channel_id"])
                if not channel:
                    continue
                try:
                    msg = await channel.fetch_message(data["message_id"])
                    embed = build_timer_embed(data)
                    await msg.edit(embed=embed)
                    if time.time() >= data["end_time"]:
                        remove_timer(tid)
                except (discord.NotFound, discord.Forbidden):
                    pass
            await asyncio.sleep(POLL_INTERVAL)

async def setup(bot: commands.Bot):
    await bot.add_cog(TimerCog(bot))
