import os
import logging
import time
import asyncio
from discord.ext import commands

class DiscordLogHandler(logging.Handler):
    """Buffers log records and periodically sends them to a Discord channel."""
    def __init__(self, bot, channel_id, level=logging.WARNING, interval=60):
        super().__init__(level)
        self.bot = bot
        self.channel_id = channel_id
        self.interval = interval
        self.buffer = []
        self.last_sent = 0

    def emit(self, record):
        try:
            msg = self.format(record)
            self.buffer.append(msg)
            now = time.time()
            # Schedule a flush if interval has elapsed
            if now - self.last_sent >= self.interval:
                asyncio.create_task(self.flush())
        except Exception:
            pass

    async def flush(self):
        if not self.buffer:
            return
        channel = self.bot.get_channel(self.channel_id)
        if not channel:
            return
        content = "```" + "\n".join(self.buffer) + "```"
        try:
            await channel.send(content)
        except Exception:
            pass
        self.buffer.clear()
        self.last_sent = time.time()


class LoggingCog(commands.Cog):
    """Cog to set up Discord logging handler based on LOG_CHANNEL_ID."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Read from environment
        channel_id = int(os.getenv("LOG_CHANNEL_ID", "0"))
        if channel_id:
            handler = DiscordLogHandler(bot, channel_id)
            formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
            handler.setFormatter(formatter)
            # Attach to root logger
            logging.getLogger().addHandler(handler)
            self.handler = handler
        else:
            # No handler until user configures via /set_log_channel
            self.handler = None

    @commands.Cog.listener()
    async def on_app_command_error(self, interaction, error):
        logging.getLogger().error(f"App command {interaction.command.name} error: {error}")

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        logging.getLogger().error(f"Command {ctx.command} error: {error}")

    @commands.Cog.listener()
    async def on_error(self, event_method, *args, **kwargs):
        logging.getLogger().exception(f"Unhandled exception in {event_method}")


async def setup(bot: commands.Bot):
    """Add this cog to the bot; errors if already added are ignored."""
    try:
        await bot.add_cog(LoggingCog(bot))
    except Exception:
        pass
