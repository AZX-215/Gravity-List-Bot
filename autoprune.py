import asyncio
import logging
import os
from datetime import timedelta

import discord
from typing import Optional
from discord import app_commands
from discord.ext import commands, tasks

# Auto-prune interval (minutes). Set AUTOPRUNE_INTERVAL_MINUTES on Railway to change cadence.
def _get_autoprune_interval_minutes() -> float:
    """Return interval minutes (default 120). Clamped to [5, 1440]."""
    raw = os.getenv("AUTOPRUNE_INTERVAL_MINUTES")
    if raw is None or str(raw).strip() == "":
        # Back-compat: allow hours variable
        raw_h = os.getenv("AUTOPRUNE_INTERVAL_HOURS")
        if raw_h is not None and str(raw_h).strip() != "":
            try:
                minutes = float(raw_h) * 60.0
            except Exception:
                minutes = 120.0
        else:
            minutes = 120.0
    else:
        try:
            minutes = float(raw)
        except Exception:
            minutes = 120.0

    if minutes < 5.0:
        minutes = 5.0
    if minutes > 1440.0:
        minutes = 1440.0
    return minutes


AUTOPRUNE_INTERVAL_MINUTES = _get_autoprune_interval_minutes()


def _interval_human() -> str:
    mins = AUTOPRUNE_INTERVAL_MINUTES
    if abs(mins - round(mins)) < 1e-9:
        mins = int(round(mins))
    if isinstance(mins, int) and mins % 60 == 0:
        hrs = mins // 60
        return f"{hrs} hour" + ("s" if hrs != 1 else "")
    return f"{mins} minute" + ("s" if mins != 1 else "")


from data_manager import (
    get_autoprune_channels,
    set_autoprune_channel,
    remove_autoprune_channel,
)


LOG = logging.getLogger("glb.autoprune")

# Logging controls (for Railway stdout; separate from Discord log-channel levels)
LOG_TICKS = os.getenv("AUTOPRUNE_LOG_TICKS", "1").strip().lower() not in {"0", "false", "no"}
LOG_NOOP = os.getenv("AUTOPRUNE_LOG_NOOP", "1").strip().lower() not in {"0", "false", "no"}
LOG_SKIPS = os.getenv("AUTOPRUNE_LOG_SKIPS", "1").strip().lower() not in {"0", "false", "no"}


def _guild_me(guild: discord.Guild, bot: commands.Bot):
    try:
        return guild.me or guild.get_member(bot.user.id)
    except Exception:
        return None


DELETE_DELAY_SECONDS = float(os.getenv("AUTOPRUNE_DELETE_DELAY_SECONDS", "1.10"))
USE_BULK_DELETE = os.getenv("AUTOPRUNE_USE_BULK_DELETE", "1").strip().lower() not in {"0", "false", "no"}
BULK_SAFE_DAYS = float(os.getenv("AUTOPRUNE_BULK_SAFE_DAYS", "13.5"))  # keep under 14d hard limit
BULK_DELAY_SECONDS = float(os.getenv("AUTOPRUNE_BULK_DELAY_SECONDS", "0.80"))


async def _resolve_channel(bot: commands.Bot, channel_id: int):
    ch = bot.get_channel(channel_id)
    if ch is not None:
        return ch
    try:
        return await bot.fetch_channel(channel_id)
    except Exception:
        return None


async def _find_cutoff_message(
    channel: discord.abc.Messageable,
    keep_last: int,
    include_pinned: bool,
) -> Optional[discord.Message]:
    """Return the oldest message that should be kept.

    - include_pinned=True: keeps last N messages total.
    - include_pinned=False: keeps last N NON-PINNED messages (pins preserved and ignored for the count).

    If the channel has fewer than N keepable messages, returns None.
    """
    if keep_last <= 0:
        return None

    if include_pinned:
        keep = [m async for m in channel.history(limit=keep_last, oldest_first=False)]
        if len(keep) < keep_last:
            return None
        return min(keep, key=lambda m: m.id)

    kept = []
    async for m in channel.history(limit=None, oldest_first=False):
        if getattr(m, "pinned", False):
            continue
        kept.append(m)
        if len(kept) >= keep_last:
            break

    if len(kept) < keep_last:
        return None
    return min(kept, key=lambda m: m.id)


async def _prune_channel(
    channel: discord.TextChannel,
    keep_last: int,
    include_pinned: bool,
    max_deletes_per_run: int,
) -> int:
    """Delete oldest messages so that only the latest N are kept.

    Uses bulk delete for messages newer than ~14 days to reduce rate limits.
    Returns number of messages deleted this run.
    """
    cutoff = await _find_cutoff_message(channel, keep_last, include_pinned)
    if cutoff is None:
        return 0

    before_obj = discord.Object(id=cutoff.id)

    # Gather candidates (oldest first) up to max_deletes_per_run
    candidates: list[discord.Message] = []
    async for msg in channel.history(limit=None, before=before_obj, oldest_first=True):
        if not include_pinned and getattr(msg, "pinned", False):
            continue
        candidates.append(msg)
        if max_deletes_per_run and len(candidates) >= max_deletes_per_run:
            break

    if not candidates:
        return 0

    deleted = 0

    # Discord bulk delete cannot delete messages older than 14 days.
    now = discord.utils.utcnow()
    bulk_cutoff = now - timedelta(days=BULK_SAFE_DAYS)

    old_msgs: list[discord.Message] = []
    bulk_msgs: list[discord.Message] = []

    for msg in candidates:
        try:
            if USE_BULK_DELETE and msg.created_at and msg.created_at > bulk_cutoff:
                bulk_msgs.append(msg)
            else:
                old_msgs.append(msg)
        except Exception:
            old_msgs.append(msg)

    # Always delete oldest messages first
    for msg in old_msgs:
        try:
            await msg.delete()
            deleted += 1
        except discord.Forbidden:
            break
        except discord.NotFound:
            pass
        except discord.HTTPException:
            # Let discord.py handle retries internally; we just slow down a bit.
            await asyncio.sleep(1.5)

        await asyncio.sleep(DELETE_DELAY_SECONDS)

    # Bulk delete remaining newer messages in chunks (up to 100 per call)
    if bulk_msgs:
        chunk: list[discord.Message] = []
        for msg in bulk_msgs:
            chunk.append(msg)
            if len(chunk) >= 100:
                try:
                    await channel.delete_messages(chunk)
                    deleted += len(chunk)
                except discord.Forbidden:
                    break
                except discord.HTTPException:
                    # fallback to individual deletes for this chunk
                    for m in chunk:
                        try:
                            await m.delete()
                            deleted += 1
                        except Exception:
                            pass
                        await asyncio.sleep(DELETE_DELAY_SECONDS)
                chunk = []
                await asyncio.sleep(BULK_DELAY_SECONDS)

        if chunk:
            if len(chunk) == 1:
                try:
                    await chunk[0].delete()
                    deleted += 1
                except Exception:
                    pass
                await asyncio.sleep(DELETE_DELAY_SECONDS)
            else:
                try:
                    await channel.delete_messages(chunk)
                    deleted += len(chunk)
                except discord.HTTPException:
                    for m in chunk:
                        try:
                            await m.delete()
                            deleted += 1
                        except Exception:
                            pass
                        await asyncio.sleep(DELETE_DELAY_SECONDS)

    return deleted


class AutoPruneCog(commands.Cog):
    """On the configured interval, prunes channels by deleting oldest messages while keeping the last N."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.prune_loop.start()

    def cog_unload(self):
        self.prune_loop.cancel()

    @tasks.loop(minutes=AUTOPRUNE_INTERVAL_MINUTES)
    async def prune_loop(self):
        await self.bot.wait_until_ready()

        if LOG_TICKS:
            try:
                LOG.info(
                    "[autoprune] tick interval=%s guilds=%d",
                    _interval_human(),
                    len(self.bot.guilds),
                )
            except Exception:
                pass

        # iterate all guilds the bot is in
        for guild in self.bot.guilds:
            channels = get_autoprune_channels(guild.id)
            if not channels:
                continue

            for ch_id_str, cfg in list(channels.items()):
                try:
                    ch_id = int(ch_id_str)
                except Exception:
                    if LOG_SKIPS:
                        LOG.warning("[autoprune] invalid channel id in config: %r (guild=%s)", ch_id_str, guild.id)
                    continue

                channel = await _resolve_channel(self.bot, ch_id)
                if not isinstance(channel, discord.TextChannel):
                    if LOG_SKIPS:
                        LOG.warning("[autoprune] channel not found or not text: %s (guild=%s)", ch_id, guild.id)
                    continue

                keep_last = int(cfg.get("keep_last", 10))
                include_pinned = bool(cfg.get("include_pinned", False))
                max_deletes = int(cfg.get("max_deletes_per_run", 100))

                # If the bot can't manage messages, skip (but log why)
                me = _guild_me(channel.guild, self.bot)
                if me is None:
                    if LOG_SKIPS:
                        LOG.warning("[autoprune] unable to resolve bot member (guild=%s channel=%s)", guild.id, channel.id)
                    continue

                perms = channel.permissions_for(me)
                if not perms.manage_messages:
                    if LOG_SKIPS:
                        LOG.warning(
                            "[autoprune] missing Manage Messages; skipping (guild=%s channel=%s #%s)",
                            guild.id,
                            channel.id,
                            channel.name,
                        )
                    continue

                try:
                    deleted = await _prune_channel(channel, keep_last, include_pinned, max_deletes)
                    if deleted > 0:
                        LOG.info(
                            "[autoprune] deleted=%d (guild=%s channel=%s #%s keep_last=%d include_pinned=%s max=%d)",
                            deleted,
                            guild.id,
                            channel.id,
                            channel.name,
                            keep_last,
                            include_pinned,
                            max_deletes,
                        )
                    else:
                        if LOG_NOOP:
                            LOG.info(
                                "[autoprune] no-op (guild=%s channel=%s #%s keep_last=%d include_pinned=%s)",
                                guild.id,
                                channel.id,
                                channel.name,
                                keep_last,
                                include_pinned,
                            )
                except Exception:
                    LOG.exception("[autoprune] run failed (guild=%s channel=%s)", guild.id, channel.id)
                    continue

    @prune_loop.before_loop
    async def before_prune_loop(self):
        await self.bot.wait_until_ready()

    # ───────────────────────────── Slash commands ─────────────────────────────

    @app_commands.command(
        name="autoprune_enable",
        description="Automatically delete oldest messages on an interval, keeping the last N.",
    )
    @app_commands.describe(
        channel="Channel to prune",
        keep_last="How many messages to keep (default 10)",
        include_pinned="If true, pinned messages can be deleted and count toward the keep_last total",
        max_deletes_per_run="Max messages to delete per run (default 100)",
    )
    @app_commands.checks.has_permissions(manage_messages=True)
    async def autoprune_enable(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        keep_last: int = 10,
        include_pinned: bool = False,
        max_deletes_per_run: int = 100,
    ):
        keep_last = max(1, min(int(keep_last), 200))
        max_deletes_per_run = max(1, min(int(max_deletes_per_run), 500))

        # Validate bot perms now, so we don't "enable" something that can never run.
        me = _guild_me(channel.guild, self.bot)
        if me is None:
            await interaction.response.send_message(
                f"Unable to resolve the bot member in this server. Try again in a moment.",
                ephemeral=True,
            )
            return
        perms = channel.permissions_for(me)
        if not perms.manage_messages:
            await interaction.response.send_message(
                f"I can't enable auto-prune in {channel.mention} because I'm missing **Manage Messages** there.",
                ephemeral=True,
            )
            return

        set_autoprune_channel(
            guild_id=interaction.guild_id,
            channel_id=channel.id,
            keep_last=keep_last,
            include_pinned=include_pinned,
            max_deletes_per_run=max_deletes_per_run,
        )

        # Kick off the first run immediately (in the background) so enable takes effect right away.
        async def _kickoff_first_run():
            try:
                deleted = await _prune_channel(channel, keep_last, include_pinned, max_deletes_per_run)
                if deleted > 0:
                    LOG.info(
                        "[autoprune] kickoff deleted=%d (guild=%s channel=%s #%s)",
                        deleted,
                        interaction.guild_id,
                        channel.id,
                        channel.name,
                    )
                else:
                    if LOG_NOOP:
                        LOG.info(
                            "[autoprune] kickoff no-op (guild=%s channel=%s #%s)",
                            interaction.guild_id,
                            channel.id,
                            channel.name,
                        )
            except Exception:
                LOG.exception("[autoprune] kickoff failed (guild=%s channel=%s)", interaction.guild_id, channel.id)

        asyncio.create_task(_kickoff_first_run())

        await interaction.response.send_message(
            f"Auto-prune enabled for {channel.mention} (first run started now; then every {_interval_human()}, keeps last {keep_last}, "
            f"{'includes' if include_pinned else 'excludes'} pinned, max {max_deletes_per_run} deletes/run).",
            ephemeral=True,
        )

    @app_commands.command(
        name="autoprune_disable",
        description="Disable auto-prune for a channel.",
    )
    @app_commands.describe(channel="Channel to stop pruning")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def autoprune_disable(self, interaction: discord.Interaction, channel: discord.TextChannel):
        ok = remove_autoprune_channel(interaction.guild_id, channel.id)
        msg = f"Auto-prune disabled for {channel.mention}." if ok else f"No auto-prune job found for {channel.mention}."
        await interaction.response.send_message(msg, ephemeral=True)

    @app_commands.command(
        name="autoprune_list",
        description="List auto-prune channels configured in this server.",
    )
    @app_commands.checks.has_permissions(manage_messages=True)
    async def autoprune_list(self, interaction: discord.Interaction):
        channels = get_autoprune_channels(interaction.guild_id)
        if not channels:
            await interaction.response.send_message("No auto-prune channels configured.", ephemeral=True)
            return

        lines = []
        for ch_id_str, cfg in channels.items():
            try:
                ch_id = int(ch_id_str)
            except Exception:
                continue
            ch = interaction.guild.get_channel(ch_id)
            mention = ch.mention if ch else f"<#{ch_id}>"
            keep_last = int(cfg.get("keep_last", 10))
            include_pinned = bool(cfg.get("include_pinned", False))
            max_deletes = int(cfg.get("max_deletes_per_run", 100))
            lines.append(
                f"- {mention}: keep {keep_last}, "
                f"{'includes' if include_pinned else 'excludes'} pinned, "
                f"max {max_deletes} deletes/run"
            )

        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    @app_commands.command(
        name="autoprune_run_now",
        description="Run auto-prune immediately for a configured channel.",
    )
    @app_commands.describe(channel="Channel to prune now")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def autoprune_run_now(self, interaction: discord.Interaction, channel: discord.TextChannel):
        channels = get_autoprune_channels(interaction.guild_id)
        cfg = channels.get(str(channel.id))
        if not cfg:
            await interaction.response.send_message(
                f"{channel.mention} is not configured. Use /autoprune_enable first.",
                ephemeral=True,
            )
            return

        me = _guild_me(channel.guild, self.bot)
        if me is None:
            await interaction.response.send_message(
                f"Unable to resolve bot member for {channel.mention}.",
                ephemeral=True,
            )
            return
        perms = channel.permissions_for(me)
        if not perms.manage_messages:
            await interaction.response.send_message(
                f"Missing permission: Manage Messages in {channel.mention}.",
                ephemeral=True,
            )
            return

        keep_last = int(cfg.get("keep_last", 10))
        include_pinned = bool(cfg.get("include_pinned", False))
        max_deletes = int(cfg.get("max_deletes_per_run", 100))

        await interaction.response.defer(ephemeral=True, thinking=True)
        deleted = await _prune_channel(channel, keep_last, include_pinned, max_deletes)

        if deleted > 0:
            LOG.info(
                "[autoprune] manual deleted=%d (guild=%s channel=%s #%s)",
                deleted,
                interaction.guild_id,
                channel.id,
                channel.name,
            )
        else:
            if LOG_NOOP:
                LOG.info(
                    "[autoprune] manual no-op (guild=%s channel=%s #%s)",
                    interaction.guild_id,
                    channel.id,
                    channel.name,
                )

        await interaction.followup.send(f"Auto-prune complete for {channel.mention}. Deleted {deleted} message(s).")


async def setup(bot: commands.Bot):
    await bot.add_cog(AutoPruneCog(bot))
