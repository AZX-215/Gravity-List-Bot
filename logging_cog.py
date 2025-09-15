import os
import logging
import time
import asyncio
import signal
import discord
from discord.ext import commands

# Optional: read runtime state/overrides from the non-invasive debug module
# If debug.py isn't loaded, DEBUG_STATE stays None and we just skip extras.
try:
    from debug import STATE as DEBUG_STATE  # provides get_cfg(), get(), record_shutdown(), push_event()
except Exception:
    DEBUG_STATE = None


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


def _fmt_duration(seconds: float) -> str:
    seconds = int(seconds)
    d, rem = divmod(seconds, 86400)
    h, rem = divmod(rem, 3600)
    m, s = divmod(rem, 60)
    parts = []
    if d:
        parts.append(f"{d}d")
    if h:
        parts.append(f"{h}h")
    if m:
        parts.append(f"{m}m")
    if not parts:
        parts.append(f"{s}s")
    return " ".join(parts)


class LoggingCog(commands.Cog):
    """Cog to send INFO+ logs to a Discord channel and track key events, with gated disconnect alerts."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        # Root logger to channel (buffered)
        root = logging.getLogger()
        root.setLevel(logging.INFO)

        channel_id = os.getenv("LOG_CHANNEL_ID")
        if channel_id:
            handler = DiscordLogHandler(bot, int(channel_id), level=logging.INFO, interval=10)
            formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
            handler.setFormatter(formatter)
            root.addHandler(handler)
            self.handler = handler
            self._log_channel_id = int(channel_id)
        else:
            self.handler = None
            self._log_channel_id = None

        # Disconnect gating (env default; may be overridden by debug.py state)
        self._env_threshold = int(os.getenv("DISCONNECT_ALERT_THRESHOLD_SEC", "300") or "300")
        self._disconnect_since = None      # type: float | None
        self._disconnect_task = None       # type: asyncio.Task | None

        # Planned shutdown / maintenance flags
        self._planned_shutdown_flag = False

        # Optional Railway metadata for nicer state recording
        self._deployment_id = (
            os.getenv("RAILWAY_DEPLOYMENT_ID") or
            os.getenv("RAILWAY_BUILD_ID") or
            ""
        )
        self._git_sha = (os.getenv("RAILWAY_GIT_COMMIT_SHA", "") or "")[:7]
        self._git_branch = os.getenv("RAILWAY_GIT_BRANCH", "") or ""

        # Register SIGTERM so redeploys are treated as planned (suppress outage spam)
        try:
            signal.signal(signal.SIGTERM, self._handle_sigterm)
        except Exception:
            # Some environments (e.g., Windows containers) might not allow signals
            pass

    # --- helpers ---------------------------------------------------------------
    def _threshold(self) -> int:
        """Effective disconnect threshold. debug.py override > env var."""
        if DEBUG_STATE is not None:
            try:
                ovr = DEBUG_STATE.get_cfg("disconnect_threshold_sec", None)
                if ovr is not None:
                    return int(ovr)
            except Exception:
                pass
        return self._env_threshold

    def _maintenance_on(self) -> bool:
        """Consult debug.py's maintenance flag, if available."""
        if DEBUG_STATE is None:
            return False
        try:
            return bool(DEBUG_STATE.get("maintenance", False))
        except Exception:
            return False

    async def _send_log(self, content: str):
        """Send a single message directly to LOG_CHANNEL_ID, if configured."""
        if not self._log_channel_id:
            return
        ch = self.bot.get_channel(self._log_channel_id)
        if ch:
            try:
                await ch.send(content)
            except Exception:
                pass

    async def _disconnect_watchdog(self):
        """After threshold, if still disconnected and not planned/maintenance, send one alert."""
        try:
            await asyncio.sleep(self._threshold())
            if self._disconnect_since is not None and not self._planned_shutdown_flag and not self._maintenance_on():
                started = int(self._disconnect_since)
                mins = self._threshold() // 60
                await self._send_log(
                    f"🚨 Bot has been **disconnected** from the Discord gateway for > **{mins}m** "
                    f"(since <t:{started}:R>). I’ll post when it reconnects."
                )
        except asyncio.CancelledError:
            pass
        except Exception:
            pass

    def _handle_sigterm(self, *_):
        """Mark this shutdown as planned (redeploy) and persist a hint if debug.py is available."""
        self._planned_shutdown_flag = True
        if DEBUG_STATE is not None:
            try:
                DEBUG_STATE.record_shutdown("redeploy", self._deployment_id, self._git_sha, self._git_branch)
                DEBUG_STATE.push_event("shutdown", "SIGTERM (planned redeploy) received")
            except Exception:
                pass
        # Allow normal shutdown to proceed

    # --- lifecycle -------------------------------------------------------------
    @commands.Cog.listener()
    async def on_ready(self):
        logging.getLogger().info("🤖 Bot is ready")

    @commands.Cog.listener())
    async def on_disconnect(self):
        # Don't spam the root logger; just a debug trace.
        logging.getLogger().debug("Gateway disconnect detected")

        # Record first time we notice a disconnect and start watchdog
        if self._disconnect_since is None:
            self._disconnect_since = time.time()
            # start or restart watchdog
            if self._disconnect_task is None or self._disconnect_task.done():
                self._disconnect_task = asyncio.create_task(self._disconnect_watchdog())

    @commands.Cog.listener()
    async def on_connect(self):
        # If we were disconnected and now connected again, decide whether to post a summary
        if self._disconnect_since is not None:
            down_for = time.time() - self._disconnect_since
            # Cancel any pending watchdog
            if self._disconnect_task and not self._disconnect_task.done():
                self._disconnect_task.cancel()
            self._disconnect_task = None

            if down_for >= self._threshold() and not self._planned_shutdown_flag and not self._maintenance_on():
                await self._send_log(f"✅ Reconnected to gateway after **{_fmt_duration(down_for)}** of downtime.")
            # Reset state
            self._disconnect_since = None

    @commands.Cog.listener()
    async def on_resumed(self):
        # Some reconnects come as RESUME; treat the same as connect
        await self.on_connect()

    # --- Interaction / Command Logging ----------------------------------------
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type is discord.InteractionType.application_command:
            name = interaction.data.get("name", "unknown")
            user = interaction.user
            logging.getLogger().info(f"📥 {user} used /{name}")

    # --- Errors ----------------------------------------------------------------
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
