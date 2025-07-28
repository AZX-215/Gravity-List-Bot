import os
import logging
import time
import asyncio
import discord
from discord.ext import commands

class DiscordLogHandler(logging.Handler):
    """Buffers log records and periodically sends them to a Discord channel."""
    def __init__(self, bot, channel_id, level=logging.INFO, interval=10):
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
    """Cog to send INFO+ logs to a Discord channel and track key events."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        # Capture INFO+ on the root logger
        root = logging.getLogger()
        root.setLevel(logging.INFO)

        channel_id = os.getenv("LOG_CHANNEL_ID")
        if channel_id:
            handler = DiscordLogHandler(bot, int(channel_id), level=logging.INFO, interval=10)
            formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
            handler.setFormatter(formatter)
            root.addHandler(handler)
            self.handler = handler
        else:
            self.handler = None

    # ─── Lifecycle ─────────────────────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_ready(self):
        # This fires after the cog is added, so we see it in the channel
        logging.getLogger().info("🤖 Bot is ready")

    @commands.Cog.listener()
    async def on_disconnect(self):
        logging.getLogger().warning("💤 Bot disconnected from gateway")

    # ─── Interaction / Command Logging ──────────────────────────────────────────
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type is discord.InteractionType.application_command:
            name = interaction.data.get("name", "unknown")
            user = interaction.user
            logging.getLogger().info(f"📥 {user} used /{name}")

    # ─── Errors ─────────────────────────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_app_command_error(self, interaction, error):
        cmd = interaction.command.name if interaction.command else "unknown"
        logging.getLogger().error(f"❌ Error in /{cmd}: {error}")

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        name = ctx.command.name if ctx.command else "unknown"
        logging.getLogger().error(f"❌ Error in !{name}: {error}")

    @commands.Cog.listener()
    async def on_error(self, event_method, *args, **kwargs):
        logging.getLogger().exception(f"💥 Unhandled exception in {event_method}")


async def setup(bot: commands.Bot):
    """Register the LoggingCog."""
    try:
        await bot.add_cog(LoggingCog(bot))
    except Exception:
        pass
