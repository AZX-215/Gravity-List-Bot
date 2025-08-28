# bm_asa.py
# Gravity List Bot — BattleMetrics (ASA Official) integration, single-file
# Free-tier only. Keeps dashboard message IDs across restarts.

from __future__ import annotations
import os, json, asyncio, datetime as dt
from pathlib import Path
from typing import Dict, Any, Optional, List
from discord.ext import commands
import aiohttp
import discord
from discord.ext import tasks
from discord import app_commands

# -----------------------
# Config via ENV (Railway)
# -----------------------
BM_SERVER_IDS = [s.strip() for s in os.getenv("BM_SERVER_IDS", "").split(",") if s.strip()]
BM_CHANNEL_ID = int(os.getenv("BM_CHANNEL_ID", "0"))
BM_API_KEY    = os.getenv("BM_API_KEY", "").strip() or None  # optional
BM_REFRESH_SEC= int(os.getenv("BM_REFRESH_SEC", "45"))        # 30–120 is polite
BRAND_NAME    = os.getenv("BRAND_NAME", "Gravity")
BM_STATE_PATH = Path(os.getenv("BM_STATE_PATH", "./bm_asa_state.json"))  # persists message IDs
# -----------------------

BM_BASE = "https://api.battlemetrics.com"

# ---------- tiny JSON state (server_id -> message_id) ----------
def _load_state() -> Dict[str, int]:
    if BM_STATE_PATH.exists():
        try:
            return json.loads(BM_STATE_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def _save_state(state: Dict[str, int]) -> None:
    try:
        BM_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        BM_STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=0), encoding="utf-8")
    except Exception as e:
        print("[BM_ASA] Warning: could not save state:", e)

# ---------- BM API: free-tier server snapshot ----------
async def get_server_snapshot(server_id: str, api_key: Optional[str] = None) -> Optional[Dict[str, Any]]:
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    url = f"{BM_BASE}/servers/{server_id}"
    timeout = aiohttp.ClientTimeout(total=12)
    async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
        try:
            async with session.get(url) as r:
                if r.status != 200:
                    return None
                data = await r.json()
        except Exception:
            return None

    try:
        attrs = data["data"]["attributes"]
        details = attrs.get("details") or {}
        return {
            "id": server_id,
            "name": attrs.get("name"),
            "status": attrs.get("status"),
            "players": attrs.get("players"),
            "maxPlayers": attrs.get("maxPlayers"),
            "map": details.get("map"),
            "ip": attrs.get("ip"),
            "port": attrs.get("port"),
            "raw": attrs,  # retained for future tweaks
        }
    except Exception:
        return None

# ---------- theming ----------
ACCENT      = 0x2B90D9
OK_GREEN    = 0x3CB371
WARN_YELLOW = 0xE3B341
ERR_RED     = 0xD64545
DOTS = {"online": "🟢", "offline": "🔴", "dead": "⚫️", "unknown": "⚪️"}

def _status_color(status: Optional[str]) -> int:
    s = (status or "unknown").lower()
    if s == "online": return OK_GREEN
    if s in ("offline","dead"): return ERR_RED
    return WARN_YELLOW

def _dot(status: Optional[str]) -> str:
    return DOTS.get((status or "unknown").lower(), DOTS["unknown"])

def _pct(num: Optional[int], den: Optional[int]) -> int:
    try:
        if not den: return 0
        return max(0, min(100, int(round((num or 0) * 100 / den))))
    except Exception:
        return 0

def bar(current: Optional[int], maximum: Optional[int], width: int = 22) -> str:
    cur = max(0, int(current or 0))
    mx  = max(cur, int(maximum or 0))
    if mx <= 0: return "—"
    filled = int(round((cur / mx) * width))
    return "▰" * filled + "▱" * (width - filled)

def build_embed(snapshot: Dict[str, Any], bm_server_id: str) -> discord.Embed:
    title_game  = "ARK: Survival Ascended (Official)"
    server_name = snapshot.get("name") or f"Server {bm_server_id}"
    full_title  = f"{title_game} • {server_name}"

    status  = snapshot.get("status") or "unknown"
    players = snapshot.get("players") or 0
    maxp    = snapshot.get("maxPlayers") or 0
    map_    = snapshot.get("map") or "—"
    ip      = snapshot.get("ip") or "—"
    port    = snapshot.get("port") or "—"

    color = _status_color(status)
    dot   = _dot(status)
    pct   = _pct(players, maxp)
    usage = bar(players, maxp, width=22)

    desc  = f"{dot} **Status:** `{status.upper()}`  •  **Players:** `{players}/{maxp}`  •  **Map:** `{map_}`\n"
    desc += f"{usage}  **{pct}%**\n"
    desc += f"`{ip}:{port}`  •  [View on BattleMetrics](https://www.battlemetrics.com/servers/ark/{bm_server_id})"

    embed = discord.Embed(title=full_title, description=desc, color=color)
    embed.timestamp = dt.datetime.utcnow()
    embed.set_footer(text=f"{BRAND_NAME} • auto-refresh")
    embed.add_field(name="Slots", value=f"{players}/{maxp}", inline=True)
    embed.add_field(name="Map", value=map_, inline=True)
    embed.add_field(name="BM ID", value=str(bm_server_id), inline=True)
    return embed

# ---------- Cog ----------
class BM_ASA(discord.ext.commands.Cog):
    """BattleMetrics integration for ASA Official — free-tier only, persistent dashboard."""
    def __init__(self, bot: discord.Client):
        self.bot = bot
        self.message_ids: Dict[str, int] = _load_state()  # server_id -> message_id
        self._dashboard_loop = tasks.loop(seconds=BM_REFRESH_SEC)(self._tick)

    # Slash: one-off query (ephemeral)
    @app_commands.command(
        name="bm_asa_server_query",
        description="(ASA Official) Show a BattleMetrics snapshot for a server ID."
    )
    @app_commands.describe(server_id="BattleMetrics numeric server ID (from the BM URL)")
    async def bm_asa_server_query(self, interaction: discord.Interaction, server_id: str):
        await interaction.response.defer(thinking=True, ephemeral=True)
        snap = await get_server_snapshot(server_id, BM_API_KEY)
        if not snap:
            await interaction.followup.send("Could not fetch BattleMetrics data. Check the server ID or try again.", ephemeral=True)
            return
        await interaction.followup.send(embed=build_embed(snap, server_id), ephemeral=True)

    @app_commands.command(
        name="bm_asa_dashboard_start",
        description="(ASA Official) Start the auto-refresh dashboard using BM_SERVER_IDS."
    )
    async def bm_asa_dashboard_start(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("Manage Server permission required.", ephemeral=True)
            return
        if not BM_SERVER_IDS or not BM_CHANNEL_ID:
            await interaction.response.send_message("Set BM_SERVER_IDS and BM_CHANNEL_ID env vars first.", ephemeral=True)
            return
        if not self._dashboard_loop.is_running():
            self._dashboard_loop.start()
        await interaction.response.send_message("ASA dashboard started ✅", ephemeral=True)

    @app_commands.command(
        name="bm_asa_dashboard_stop",
        description="(ASA Official) Stop the auto-refresh dashboard."
    )
    async def bm_asa_dashboard_stop(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("Manage Server permission required.", ephemeral=True)
            return
        if self._dashboard_loop.is_running():
            self._dashboard_loop.cancel()
            await interaction.response.send_message("ASA dashboard stopped ⏹️", ephemeral=True)
        else:
            await interaction.response.send_message("Dashboard is not running.", ephemeral=True)

    @app_commands.command(
        name="bm_asa_dashboard_refresh",
        description="(ASA Official) Force a one-time dashboard refresh."
    )
    async def bm_asa_dashboard_refresh(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("Manage Server permission required.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        await self._tick(force=True)
        await interaction.followup.send("Refreshed.", ephemeral=True)

    # ---- loop ----
    async def _tick(self, force: bool = False):
        try:
            channel = self.bot.get_channel(BM_CHANNEL_ID) or await self.bot.fetch_channel(BM_CHANNEL_ID)
        except Exception:
            return
        for sid in BM_SERVER_IDS:
            snap = await get_server_snapshot(sid, BM_API_KEY)
            if snap:
                embed = build_embed(snap, sid)
            else:
                embed = discord.Embed(
                    title=f"ARK: Survival Ascended (Official) • Server {sid}",
                    description="Could not fetch BattleMetrics data (temporary issue or invalid ID).",
                    color=ERR_RED
                )
                embed.timestamp = dt.datetime.utcnow()
                embed.set_footer(text=f"{BRAND_NAME} • auto-refresh")

            await self._send_or_edit(channel, sid, embed)
            await asyncio.sleep(1)  # polite spacing

    async def _send_or_edit(self, channel: discord.abc.Messageable, server_id: str, embed: discord.Embed):
        mid = self.message_ids.get(server_id)
        try:
            if mid:
                msg = await channel.fetch_message(mid)
                await msg.edit(embed=embed)
            else:
                msg = await channel.send(embed=embed)
                self.message_ids[server_id] = msg.id
                _save_state(self.message_ids)
        except Exception:
            msg = await channel.send(embed=embed)
            self.message_ids[server_id] = msg.id
            _save_state(self.message_ids)

# ---------- setup helper ----------
async def setup_bm_asa(bot: discord.Client):
    cog = BM_ASA(bot)
    try:
        bot.tree.add_command(cog.bm_asa_server_query)
        bot.tree.add_command(cog.bm_asa_dashboard_start)
        bot.tree.add_command(cog.bm_asa_dashboard_stop)
        bot.tree.add_command(cog.bm_asa_dashboard_refresh)
    except Exception:
        pass
    # Optional auto-start if env set
    if BM_SERVER_IDS and BM_CHANNEL_ID and not cog._dashboard_loop.is_running():
        cog._dashboard_loop.start()
    # prevent GC
    if not hasattr(bot, "_bm_asa_ref"):
        bot._bm_asa_ref = cog  # type: ignore

