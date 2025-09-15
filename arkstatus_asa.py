# arkstatus_asa.py
# Gravity List Bot — Ark Status (ASA) integration
# Near real-time ASA server widgets with polite rate limiting and persistent dashboard.

from __future__ import annotations

import os
import json
import asyncio
import time
import datetime as dt
from pathlib import Path
from typing import Dict, Any, Optional
from urllib.parse import quote

import aiohttp
import discord
from discord.ext import commands, tasks
from discord import app_commands

# ───────────────────────────── Config (Railway ENV) ─────────────────────────────
AS_API_KEY = os.getenv("AS_API_KEY", "").strip() or None
AS_CHANNEL_ID = int(os.getenv("AS_CHANNEL_ID", "0"))
# Comma-separated list of Ark Status identifiers: numeric IDs or exact server names (case-sensitive).
AS_TARGETS = [s.strip() for s in os.getenv("AS_TARGETS", "").split(",") if s.strip()]
AS_REFRESH_SEC = int(os.getenv("AS_REFRESH_SEC", "60"))  # overall dashboard cadence
AS_BACKOFF_SEC = int(os.getenv("AS_BACKOFF_SEC", "600"))  # fallback cooldown on 429/no-remaining
AS_TIER = os.getenv("AS_TIER", "free").lower()  # "free" or "premium"
BRAND_NAME = os.getenv("BRAND_NAME", "Gravity")
AS_STATE_PATH = Path(os.getenv("AS_STATE_PATH", "./arkstatus_state.json"))

# ✅ NEW: optional thumbnail for each widget (defaults to your Specimen Implant image)
AS_THUMBNAIL_URL = (
    os.getenv(
        "AS_THUMBNAIL_URL",
        "https://raw.githubusercontent.com/AZX-215/Gravity-List-Bot/refs/heads/main/images/Specimen_Implant.png",
    ).strip()
    or None
)
# ────────────────────────────────────────────────────────────────────────────────

AS_BASE = "https://arkstatus.com/api/v1"


# ──────────────────────── tiny JSON state (target -> message_id) ─────────────────
def _load_state() -> Dict[str, int]:
    if AS_STATE_PATH.exists():
        try:
            return json.loads(AS_STATE_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_state(state: Dict[str, int]) -> None:
    try:
        AS_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        AS_STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=0), encoding="utf-8")
    except Exception as e:
        print("[ARKSTATUS] Warning: could not save state:", e)


# ──────────────────────────────── HTTP helpers ──────────────────────────────────
def _headers() -> Dict[str, str]:
    if AS_API_KEY:
        # Prefer X-API-Key per docs; Bearer also supported.
        return {"X-API-Key": AS_API_KEY}
    return {}


def _parse_rate_headers(hdrs: aiohttp.typedefs.LooseHeaders) -> Dict[str, Optional[int]]:
    def _int(h: str) -> Optional[int]:
        try:
            v = hdrs.get(h)
            return int(v) if v is not None else None
        except Exception:
            return None

    return {
        "global_limit": _int("X-RateLimit-Limit"),
        "global_remaining": _int("X-RateLimit-Remaining"),
        "reset_sec": _int("X-RateLimit-Reset"),
        "ep_limit": _int("X-RateLimit-Endpoint-Limit"),
        "ep_remaining": _int("X-RateLimit-Endpoint-Remaining"),
    }


async def _get_json(path: str) -> tuple[Optional[Dict[str, Any]], Dict[str, Optional[int]], int]:
    url = f"{AS_BASE}{path}"
    timeout = aiohttp.ClientTimeout(total=12)
    async with aiohttp.ClientSession(headers=_headers(), timeout=timeout) as session:
        try:
            async with session.get(url) as r:
                rate = _parse_rate_headers(r.headers)
                if r.status != 200:
                    return None, rate, r.status
                try:
                    data = await r.json()
                except Exception:
                    return None, rate, r.status
                return data, rate, r.status
        except Exception:
            return None, {}, 0


# ─────────────────────────────── Data fetch/shape ───────────────────────────────
async def get_server_details(
    target: str,
) -> tuple[Optional[Dict[str, Any]], Dict[str, Optional[int]], int]:
    # The API supports numeric ID or name right in the path.
    path_id_or_name = target if target.isdigit() else quote(target, safe="")
    data, rate, status = await _get_json(f"/servers/{path_id_or_name}")
    if not data or not data.get("success"):
        return None, rate, status
    try:
        d = data["data"]
        # normalize to a "snapshot" dict the embed builder can use
        snap = {
            "id": d.get("id"),
            "name": d.get("name"),
            "map": d.get("map"),
            "status": d.get("status"),
            "players": d.get("players"),
            "max_players": d.get("max_players"),
            "player_percentage": d.get("player_percentage"),
            "platform": d.get("platform"),
            "game_mode": d.get("game_mode"),
            "version": d.get("version"),
            "day_number": d.get("day_number"),
            "ping": d.get("ping"),
            "last_updated": d.get("last_updated"),
            "last_snapshot": d.get("last_snapshot"),
            "statistics": d.get("statistics") or {},
        }
        return snap, rate, status
    except Exception:
        return None, rate, status


# ─────────────────────────────── Theming/format ────────────────────────────────
ACCENT = 0x2B90D9
OK_GREEN = 0x3CB371
WARN_YELLOW = 0xE3B341
ERR_RED = 0xD64545
DOTS = {"online": "🟢", "offline": "🔴", "dead": "⚫️", "unknown": "⚪️"}


def _status_color(status: Optional[str]) -> int:
    s = (status or "unknown").lower()
    if s == "online":
        return OK_GREEN
    if s in ("offline", "dead"):
        return ERR_RED
    return WARN_YELLOW


def _dot(status: Optional[str]) -> str:
    return DOTS.get((status or "unknown").lower(), DOTS["unknown"])


def _pct(num: Optional[int], den: Optional[int]) -> int:
    try:
        if not den:
            return 0
        return max(0, min(100, int(round((num or 0) * 100 / den))))
    except Exception:
        return 0


def bar(current: Optional[int], maximum: Optional[int], width: int = 22) -> str:
    cur = max(0, int(current or 0))
    mx = max(cur, int(maximum or 0))
    if mx <= 0:
        return "—"
    filled = int(round((cur / mx) * width))
    return "▰" * filled + "▱" * (width - filled)


def _fmt_pct(x: Optional[float]) -> str:
    try:
        return f"{float(x):.2f}%"
    except Exception:
        return "—"


def _fmt_ms(x: Optional[int]) -> str:
    try:
        val = int(x)
        return f"{val} ms" if val >= 0 else "—"
    except Exception:
        return "—"


def build_embed(s: Dict[str, Any]) -> discord.Embed:
    title_game = "ARK: Survival Ascended"
    server_name = s.get("name") or f"Server {s.get('id','?')}"
    full_title = f"{title_game} • {server_name}"

    status = s.get("status") or "unknown"
    players = s.get("players") or 0
    maxp = s.get("max_players") or 0
    pct = s.get("player_percentage")
    pct_i = _pct(players, maxp) if pct is None else int(round(pct))
    map_ = s.get("map") or "—"
    platform = s.get("platform") or "—"
    mode = s.get("game_mode") or "—"
    ver = s.get("version") or "—"
    day = s.get("day_number")
    ping = _fmt_ms(s.get("ping"))
    updated = s.get("last_updated")
    last_ss = s.get("last_snapshot")

    color = _status_color(status)
    dot = _dot(status)
    usage = bar(players, maxp, width=22)

    # Top description: status + players + map + usage bar
    desc = f"{dot} **Status:** `{status.upper()}`  •  **Players:** `{players}/{maxp}`  •  **Map:** `{map_}`\n"
    desc += f"{usage}  **{pct_i}%**\n"
    # Meta line
    meta_bits = [
        f"Platform: `{platform}`",
        f"Mode: `{mode}`",
        f"Version: `{ver}`",
        f"Ping: `{ping}`",
    ]
    if isinstance(day, int):
        meta_bits.append(f"Day: `{day}`")
    desc += " • ".join(meta_bits)

    embed = discord.Embed(title=full_title, description=desc, color=color)
    embed.timestamp = dt.datetime.utcnow()
    embed.set_footer(text=f"{BRAND_NAME} • auto-refresh — Ark Status")

    # ✅ NEW: thumbnail (matches your gen_timers style)
    if AS_THUMBNAIL_URL:
        embed.set_thumbnail(url=AS_THUMBNAIL_URL)

    # Quick facts fields
    embed.add_field(name="Slots", value=f"{players}/{maxp}", inline=True)
    embed.add_field(name="Platform", value=platform, inline=True)
    embed.add_field(name="Mode", value=mode, inline=True)

    # Uptime & player trend fields if present
    stats = s.get("statistics") or {}
    s7 = stats.get("7_days") or {}
    s30 = stats.get("30_days") or {}
    if s7:
        embed.add_field(
            name="Uptime 7d",
            value=f"{_fmt_pct(s7.get('uptime_percentage'))}\nAvg: {s7.get('average_players','—')}  •  Peak: {s7.get('peak_players','—')}",
            inline=True,
        )
    if s30:
        embed.add_field(
            name="Uptime 30d",
            value=f"{_fmt_pct(s30.get('uptime_percentage'))}\nAvg: {s30.get('average_players','—')}  •  Peak: {s30.get('peak_players','—')}",
            inline=True,
        )

    # Timestamps (if provided by API)
    if updated or last_ss:
        when = []
        if updated:
            when.append(f"Updated: `{updated}`")
        if last_ss:
            when.append(f"Snapshot: `{last_ss}`")
        embed.add_field(name="Data times", value="\n".join(when), inline=False)

    return embed


# ───────────────────────────── Cog (dashboard) ────────────────────────────────
class ArkStatusASA(commands.Cog):
    """Ark Status integration for ASA — persistent dashboard with polite rate limiting."""

    def __init__(self, bot: discord.Client):
        self.bot = bot
        self.message_ids: Dict[str, int] = _load_state()  # target -> message_id
        self._dashboard_loop = tasks.loop(seconds=AS_REFRESH_SEC)(self._tick)
        self._backoff_until = 0.0  # global cooldown based on headers/429

        # Safe spacing between per-server requests:
        # Free tier allows 10 req/min per endpoint & globally; space ~6s per request.
        self._per_request_sleep = 1 if AS_TIER == "premium" else 6

    # ── Slash: one-off query (ephemeral)
    @app_commands.command(
        name="as_server_query",
        description="(Ark Status) Show server details by ArkStatus ID or Name.",
    )
    @app_commands.describe(target="Ark Status server ID or exact Name (spaces ok)")
    async def as_server_query(self, interaction: discord.Interaction, target: str):
        await interaction.response.defer(thinking=True, ephemeral=True)
        snap, rate, status = await get_server_details(target)
        if not snap:
            msg = (
                f"Could not fetch Ark Status data (HTTP {status}). Check the ID/name or try again."
            )
            await interaction.followup.send(msg, ephemeral=True)
            return
        await interaction.followup.send(embed=build_embed(snap), ephemeral=True)

    @app_commands.command(
        name="as_dashboard_start",
        description="(Ark Status) Start the auto-refresh dashboard using AS_TARGETS.",
    )
    async def as_dashboard_start(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message(
                "Manage Server permission required.", ephemeral=True
            )
            return
        if not AS_TARGETS or not AS_CHANNEL_ID:
            await interaction.response.send_message(
                "Set AS_TARGETS and AS_CHANNEL_ID env vars first.", ephemeral=True
            )
            return
        if not self._dashboard_loop.is_running():
            self._dashboard_loop.start()
        await interaction.response.send_message("Ark Status dashboard started ✅", ephemeral=True)

    @app_commands.command(
        name="as_dashboard_stop", description="(Ark Status) Stop the auto-refresh dashboard."
    )
    async def as_dashboard_stop(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message(
                "Manage Server permission required.", ephemeral=True
            )
            return
        if self._dashboard_loop.is_running():
            self._dashboard_loop.cancel()
            await interaction.response.send_message(
                "Ark Status dashboard stopped ⏹️", ephemeral=True
            )
        else:
            await interaction.response.send_message("Dashboard is not running.", ephemeral=True)

    @app_commands.command(
        name="as_dashboard_refresh", description="(Ark Status) Force a one-time dashboard refresh."
    )
    async def as_dashboard_refresh(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message(
                "Manage Server permission required.", ephemeral=True
            )
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        await self._tick(force=True)
        await interaction.followup.send("Refreshed.", ephemeral=True)

    # ── Loop ────────────────────────────────────────────────────────────────
    async def _tick(self, force: bool = False):
        now = time.time()
        if now < self._backoff_until:
            return
        # Safety: ensure refresh pacing respects free-tier math:
        # Per-minute budget = 10; we space per request to ~6s when on "free" tier.
        sleep_between = self._per_request_sleep

        # Find channel
        try:
            channel = self.bot.get_channel(AS_CHANNEL_ID) or await self.bot.fetch_channel(
                AS_CHANNEL_ID
            )
        except Exception:
            return

        for target in AS_TARGETS:
            snap, rate, status = await get_server_details(target)

            if snap:
                embed = build_embed(snap)
            else:
                embed = discord.Embed(
                    title=f"ARK: Survival Ascended • {target}",
                    description=f"Could not fetch Ark Status data (HTTP {status}).",
                    color=ERR_RED,
                )
                embed.timestamp = dt.datetime.utcnow()
                embed.set_footer(text=f"{BRAND_NAME} • auto-refresh — Ark Status")
                if AS_THUMBNAIL_URL:
                    embed.set_thumbnail(url=AS_THUMBNAIL_URL)

            await self._send_or_edit(channel, target, embed)

            # Check rate headers; if remaining exhausted, respect reset
            if rate:
                rem = (rate.get("global_remaining"), rate.get("ep_remaining"))
                reset = rate.get("reset_sec") or 0
                if any(v is not None and v <= 0 for v in rem):
                    self._backoff_until = time.time() + max(reset, AS_BACKOFF_SEC)
                    return

            await asyncio.sleep(sleep_between)  # polite spacing

    async def _send_or_edit(
        self, channel: discord.abc.Messageable, target: str, embed: discord.Embed
    ):
        mid = self.message_ids.get(target)
        try:
            if mid:
                msg = await channel.fetch_message(mid)
                old_desc = msg.embeds[0].description if msg.embeds else None
                if old_desc == embed.description:
                    return
                await msg.edit(embed=embed)
            else:
                msg = await channel.send(embed=embed)
                self.message_ids[target] = msg.id
                _save_state(self.message_ids)

        except discord.NotFound:
            sent = await channel.send(embed=embed)
            self.message_ids[target] = sent.id
            _save_state(self.message_ids)

        except discord.Forbidden:
            print(f"[ARKSTATUS] Missing permissions to edit dashboard for {target}")

        except discord.HTTPException as e:
            # If Discord itself rate-limits us, do a temporary backoff
            if getattr(e, "status", None) == 429:
                self._backoff_until = time.time() + AS_BACKOFF_SEC
                print(f"[ARKSTATUS] Discord 429; backing off for {AS_BACKOFF_SEC}s")
            else:
                print(f"[ARKSTATUS] HTTPException updating {target}: {e}")

        except Exception as e:
            print(f"[ARKSTATUS] Unexpected error updating {target}: {e}")


# ───────────────────────────── setup helper ────────────────────────────────────
async def setup_arkstatus_asa(bot: discord.Client):
    cog = ArkStatusASA(bot)
    try:
        bot.tree.add_command(cog.as_server_query)
        bot.tree.add_command(cog.as_dashboard_start)
        bot.tree.add_command(cog.as_dashboard_stop)
        bot.tree.add_command(cog.as_dashboard_refresh)
    except Exception:
        pass
    # Optional auto-start if env set
    if AS_TARGETS and AS_CHANNEL_ID and not cog._dashboard_loop.is_running():
        cog._dashboard_loop.start()
    # prevent GC
    if not hasattr(bot, "_arkstatus_ref"):
        bot._arkstatus_ref = cog  # type: ignore
