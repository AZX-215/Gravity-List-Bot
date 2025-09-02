# debug.py — self-contained diagnostics module (non-invasive)
# - Redeploy vs outage detection (records state; optional deploy announcement)
# - Disconnect threshold override storage (no behavior change unless your logging cog reads it)
# - Maintenance mode flag (for future use)
# - Rate-limit (429) tracking via a logging.Filter (does not suppress logs)
# - In-memory tail of recent logs for quick /diag tail
# - Ephemeral /diag commands
#
# Drop this file alongside your other cogs and load it from bot.py:
#   await bot.load_extension("debug")
#
# Optional ENV:
#   LOG_CHANNEL_ID                     -> where optional deploy announcements can go
#   BOT_RUNTIME_STATE_PATH                  -> path to persistent state (default: lists/debug/runtime_state.json)
#   DEBUG_POST_DEPLOY=1                -> if set, post a small "new deployment" message on startup
#   DEBUG_DEPLOY_LABEL                 -> optional label for your builds
#
from __future__ import annotations

import os, json, time, logging, signal, asyncio
from typing import Any, Dict, List, Optional
from pathlib import Path

import discord
from discord.ext import commands
from discord import app_commands

# ----------------------- storage location defaults ----------------------------
# Prefer your existing paths from data_manager if available
try:
    from data_manager import BASE_DATA, BASE_DIR
except Exception:
    BASE_DATA = os.getenv("DATABASE_PATH", "./data.json")
    BASE_DIR  = os.path.dirname(BASE_DATA) or "."

# Prefer BOT_RUNTIME_STATE_PATH, fall back to BOT_RUNTIME_STATE, then default
STATE_PATH = Path(
    os.getenv("BOT_RUNTIME_STATE_PATH")
    or os.getenv("BOT_RUNTIME_STATE")
    or os.path.join(BASE_DIR, "runtime_state.json")
)

# ----------------------------- tiny JSON store --------------------------------
def _ensure_dir(p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)

def _read_json(p: Path, default: Any) -> Any:
    try:
        with p.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def _write_json_atomic(p: Path, obj: Any) -> None:
    try:
        _ensure_dir(p)
        tmp = p.with_suffix(p.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(obj, f)
        os.replace(tmp, p)
    except Exception:
        pass

_DEFAULT = {
    "last_boot_ts": None,
    "last_shutdown_ts": None,
    "last_shutdown_reason": None,   # "redeploy" | "crash" | "unknown"
    "last_deployment_id": None,
    "last_git_sha": None,
    "last_git_branch": None,
    "maintenance": False,
    "maintenance_note": "",
    "config": {"disconnect_threshold_sec": None},
    "events": [],
    "events_max": 200,
    "ratelimit_ts": [],
    "ratelimit_max": 2000,
}

class State:
    def __init__(self, path: Path):
        self.path = path
        self._s = _read_json(self.path, dict(_DEFAULT))

    # persistence
    def save(self): _write_json_atomic(self.path, self._s)

    # generic
    def get(self, k, d=None): return self._s.get(k, d)
    def set(self, k, v): self._s[k]=v; self.save()

    # config
    def set_cfg(self, k, v): self._s.setdefault("config", {})[k]=v; self.save()
    def get_cfg(self, k, d=None): return self._s.get("config", {}).get(k, d)
    def get_cfg_int(self, k)->Optional[int]:
        v=self.get_cfg(k,None)
        try: return int(v) if v is not None else None
        except: return None

    # events
    def push_event(self, etype:str, msg:str):
        arr=self._s.setdefault("events", [])
        arr.append({"ts": time.time(), "type": etype, "msg": msg})
        maxn=int(self._s.get("events_max",200) or 200)
        if len(arr)>maxn: del arr[:len(arr)-maxn]
        self.save()

    # ratelimits
    def record_rl(self):
        arr=self._s.setdefault("ratelimit_ts", [])
        arr.append(time.time())
        maxn=int(self._s.get("ratelimit_max",2000) or 2000)
        if len(arr)>maxn: del arr[:len(arr)-maxn]
        self.save()
    def summarize_rl(self)->Dict[str,int]:
        now=time.time()
        arr=self._s.get("ratelimit_ts", [])
        def c(win): cutoff=now-win; return sum(1 for t in arr if t>=cutoff)
        return {"15m":c(900),"1h":c(3600),"24h":c(86400),"total_kept":len(arr)}

    # boot/shutdown
    def record_boot(self, dep_id:str="", sha:str="", branch:str=""):
        self._s["last_boot_ts"]=time.time()
        if dep_id: self._s["last_deployment_id"]=dep_id
        if sha:    self._s["last_git_sha"]=sha
        if branch: self._s["last_git_branch"]=branch
        self.save()
    def record_shutdown(self, reason:str="unknown", dep_id:str="", sha:str="", branch:str=""):
        self._s["last_shutdown_ts"]=time.time()
        self._s["last_shutdown_reason"]=reason
        if dep_id: self._s["last_deployment_id"]=dep_id
        if sha:    self._s["last_git_sha"]=sha
        if branch: self._s["last_git_branch"]=branch
        self.save()

STATE = State(STATE_PATH)

# ------------------------------ log helpers -----------------------------------

class RatelimitFilter(logging.Filter):
    KEYWORDS=("429","rate limit","ratelimit","too many requests")
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage().lower()
            if any(k in msg for k in self.KEYWORDS):
                STATE.record_rl()
        except Exception:
            pass
        return True  # never block

class MemoryRingHandler(logging.Handler):
    """Keeps an in-memory tail of recent log lines (INFO+). Non-invasive."""
    def __init__(self, capacity:int=500, level=logging.INFO):
        super().__init__(level)
        self.capacity=capacity
        self.ring: List[str]=[]
        self._fmt = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg=self._fmt.format(record)
            self.ring.append(msg)
            if len(self.ring)>self.capacity:
                del self.ring[:len(self.ring)-self.capacity]
        except Exception:
            pass

    def tail(self, n:int=50)->List[str]:
        n=max(1, min(int(n), self.capacity))
        return self.ring[-n:]

# global handler instance
MEM_HANDLER = MemoryRingHandler()

def attach_debug_filters_and_handlers():
    root=logging.getLogger()
    try:
        root.addFilter(RatelimitFilter())
    except Exception:
        pass
    try:
        root.addHandler(MEM_HANDLER)
    except Exception:
        pass

# --------------------------- signals / metadata -------------------------------

DEPLOYMENT_ID = os.getenv("RAILWAY_DEPLOYMENT_ID") or os.getenv("RAILWAY_BUILD_ID") or ""
GIT_SHA       = (os.getenv("RAILWAY_GIT_COMMIT_SHA","") or "")[:7]
GIT_BRANCH    = os.getenv("RAILWAY_GIT_BRANCH","") or ""
DEBUG_POST_DEPLOY = os.getenv("DEBUG_POST_DEPLOY","0") == "1"
DEPLOY_LABEL  = os.getenv("DEBUG_DEPLOY_LABEL","").strip()
LOG_CHANNEL_ID= int(os.getenv("LOG_CHANNEL_ID","0") or "0")

def _fmt_dur(sec: float)->str:
    s=int(sec); d,rem=divmod(s,86400); h,rem=divmod(rem,3600); m,ss=divmod(rem,60)
    parts=[]
    if d: parts.append(f"{d}d")
    if h: parts.append(f"{h}h")
    if m: parts.append(f"{m}m")
    if not parts: parts.append(f"{ss}s")
    return " ".join(parts)

def register_sigterm():
    def _handle(*_):
        STATE.record_shutdown("redeploy", DEPLOYMENT_ID, GIT_SHA, GIT_BRANCH)
        STATE.push_event("shutdown","SIGTERM (planned redeploy) received")
    try:
        signal.signal(signal.SIGTERM, _handle)
    except Exception:
        pass

# ------------------------------ Cog & commands --------------------------------

class DebugCog(commands.Cog):
    """General diagnostics (non-invasive)."""
    def __init__(self, bot: commands.Bot):
        self.bot=bot
        attach_debug_filters_and_handlers()
        register_sigterm()
        # record boot later in on_ready

    async def _send_log(self, content:str):
        if not LOG_CHANNEL_ID: return
        ch=self.bot.get_channel(LOG_CHANNEL_ID)
        if ch:
            try:
                await ch.send(content)
            except Exception:
                pass

    @commands.Cog.listener()
    async def on_ready(self):
        # --- Read prior state BEFORE writing the new boot info ---
        prev_reason = STATE.get("last_shutdown_reason")
        prev_ts     = STATE.get("last_shutdown_ts")
        prev_deploy = STATE.get("last_deployment_id")

        # Record current boot (writes current deployment metadata)
        STATE.record_boot(DEPLOYMENT_ID, GIT_SHA, GIT_BRANCH)

        # Optional deploy announcement (planned redeploy OR first deploy after adding debug.py)
        if DEBUG_POST_DEPLOY:
            try:
                planned = (prev_reason == "redeploy" and prev_ts)
                id_changed = bool(DEPLOYMENT_ID and prev_deploy and DEPLOYMENT_ID != prev_deploy)

                if planned or id_changed:
                    downtime = (time.time() - float(prev_ts)) if planned else 0
                    label = f"`{GIT_SHA}`@{GIT_BRANCH}" if (GIT_SHA or GIT_BRANCH) else "new build"
                    if DEPLOY_LABEL:
                        label = DEPLOY_LABEL
                    msg = f"🔁 Deployment detected ({label})."
                    if planned:
                        msg += f" Startup after **{_fmt_dur(downtime)}**."
                    await self._send_log(msg)
            except Exception:
                pass

        # Regular ready trace (root logger)
        logging.getLogger().info("debug.py on_ready: diagnostics ready")

    # ---- /diag group ----
    diag = app_commands.Group(name="diag", description="Diagnostics and runtime state")

    @diag.command(name="summary", description="Show bot diagnostics summary")
    async def summary(self, interaction: discord.Interaction):
        now=time.time()
        lb=STATE.get("last_boot_ts")
        ls=STATE.get("last_shutdown_ts")
        reason=STATE.get("last_shutdown_reason") or "n/a"
        dep=STATE.get("last_deployment_id") or "n/a"
        sha=STATE.get("last_git_sha") or "n/a"
        br =STATE.get("last_git_branch") or "n/a"
        mt =STATE.get("maintenance")
        note=STATE.get("maintenance_note") or ""
        thr_env=int(os.getenv("DISCONNECT_ALERT_THRESHOLD_SEC","300") or "300")
        thr_ovr=STATE.get_cfg_int("disconnect_threshold_sec")
        thr=thr_ovr or thr_env
        rl=STATE.summarize_rl()

        lines=[
            f"**Deployment**: `{sha}` @{br} (id: `{dep}`)",
            f"**Uptime**: {_fmt_dur(now-lb)}" if lb else "**Uptime**: n/a",
            f"**Last shutdown**: {reason} {f'({_fmt_dur(now-ls)} ago)' if ls else ''}",
            f"**Maintenance mode**: {'ON' if mt else 'off'}{' — ' + note if note else ''}",
            f"**Disconnect threshold**: {thr}s {'(override)' if thr_ovr else '(env)'}",
            f"**State file**: `{STATE_PATH}`",
        ]
        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    @diag.command(name="set_disconnect_threshold", description="Override disconnect alert threshold (seconds) — stored only")
    @app_commands.describe(seconds="Seconds (e.g., 300 for 5 minutes). Use 0 to clear override.")
    async def set_disconnect_threshold(self, interaction: discord.Interaction, seconds: int):
        if seconds<=0:
            STATE.set_cfg("disconnect_threshold_sec", None)
            await interaction.response.send_message("✅ Cleared override (stored).", ephemeral=True)
        else:
            STATE.set_cfg("disconnect_threshold_sec", int(seconds))
            await interaction.response.send_message(f"✅ Stored override set to {seconds}s.", ephemeral=True)

    @diag.command(name="maintenance", description="Set maintenance mode flag (does not alter current logging).")
    @app_commands.describe(on="True to enable, False to disable", note="Optional note")
    async def maintenance(self, interaction: discord.Interaction, on: bool, note: Optional[str]=None):
        STATE.set("maintenance", bool(on))
        if note is not None:
            STATE.set("maintenance_note", str(note))
        await interaction.response.send_message(f"✅ Maintenance mode {'ENABLED' if on else 'disabled'}.", ephemeral=True)

    @diag.command(name="ratelimit", description="Show 429/rate-limit summary (tracked from logs)")
    async def ratelimit(self, interaction: discord.Interaction):
        rl=STATE.summarize_rl()
        await interaction.response.send_message(
            f"429s — 15m: **{rl['15m']}**, 1h: **{rl['1h']}**, 24h: **{rl['24h']}** (kept={rl['total_kept']})",
            ephemeral=True
        )

    @diag.command(name="tail_logs", description="Show the last N log lines observed by the bot (in-memory).")
    @app_commands.describe(lines="How many lines (default 50, max 150)")
    async def tail_logs(self, interaction: discord.Interaction, lines: Optional[int]=50):
        n=max(1, min(int(lines or 50), 150))
        tail = MEM_HANDLER.tail(n)
        if not tail:
            return await interaction.response.send_message("No logs captured yet.", ephemeral=True)
        content = "```\n" + "\n".join(tail) + "\n```"
        await interaction.response.send_message(content, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(DebugCog(bot))
