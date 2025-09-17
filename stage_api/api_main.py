import os
import asyncio
from typing import Optional, List, Set, Any

import asyncpg
import httpx
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

APP_ENV = os.getenv("ENVIRONMENT", "stage")
DATABASE_URL = os.getenv("DATABASE_URL", "")
SHARED = os.getenv("GL_SHARED_SECRET", "")

# ---- alerts config ----
LOG_POSTING_ENABLED = os.getenv("LOG_POSTING_ENABLED", "false").lower() == "true"
WEBHOOK_URL = os.getenv("ALERT_DISCORD_WEBHOOK_URL", "")

def _csv(name: str, default: str = "") -> List[str]:
    raw = os.getenv(name, default)
    if not raw:
        return []
    return [s.strip().upper() for s in raw.split(",") if s.strip()]

ALERT_SEVERITIES: Set[str] = set(_csv("ALERT_SEVERITIES", "CRITICAL,IMPORTANT"))
ALERT_CATEGORIES: Set[str] = set(_csv("ALERT_CATEGORIES", ""))  # empty -> all categories

app = FastAPI()
_pool: Optional[asyncpg.Pool] = None
_http: Optional[httpx.AsyncClient] = None


class TribeEvent(BaseModel):
    server: str
    tribe: str
    ark_day: int = Field(0, ge=0)
    ark_time: str = ""
    severity: str = "INFO"
    category: str = "GENERAL"
    actor: str = "Unknown"
    message: str
    raw_line: str


# ---------- startup/shutdown ----------
@app.on_event("startup")
async def _start():
    global _pool, _http
    # DB
    _pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=3)
    async with _pool.acquire() as con:
        await con.execute(
            """
            create table if not exists tribe_events (
              id serial primary key,
              ingested_at timestamptz not null default now(),
              server text not null,
              tribe text not null,
              ark_day integer not null,
              ark_time text not null,
              severity text not null,
              category text not null,
              actor text not null,
              message text not null,
              raw_line text not null
            );
            """
        )
    # HTTP client for webhook
    _http = httpx.AsyncClient(timeout=10)

@app.on_event("shutdown")
async def _stop():
    global _pool, _http
    if _http:
        await _http.aclose()
    if _pool:
        await _pool.close()


# ---------- helpers ----------
def _authorized(key: Optional[str]) -> bool:
    return bool(SHARED) and (key == SHARED)

def _should_alert(evt: TribeEvent) -> bool:
    if not LOG_POSTING_ENABLED or not WEBHOOK_URL:
        return False
    sev_ok = (not ALERT_SEVERITIES) or (evt.severity.upper() in ALERT_SEVERITIES)
    cat_ok = (not ALERT_CATEGORIES) or (evt.category.upper() in ALERT_CATEGORIES)
    return sev_ok and cat_ok

async def _post_discord(evt: TribeEvent):
    """Post a concise alert to Discord via webhook."""
    if not _http or not WEBHOOK_URL:
        return

    color = 0xE74C3C if evt.severity.upper() == "CRITICAL" else 0xF1C40F
    embed = {
        "title": f"{evt.category} • {evt.severity}",
        "color": color,
        "fields": [
            {"name": "Server", "value": evt.server, "inline": True},
            {"name": "Tribe", "value": evt.tribe, "inline": True},
            {"name": "ARK Time", "value": f"Day {evt.ark_day}, {evt.ark_time}", "inline": True},
            {"name": "Actor", "value": evt.actor or "—", "inline": False},
            {"name": "Msg", "value": evt.message[:1000], "inline": False},
        ],
        "footer": {"text": f"env={APP_ENV}"},
    }
    payload = {"embeds": [embed], "content": None}

    try:
        r = await _http.post(WEBHOOK_URL, json=payload)
        # Discord returns 204 No Content on success
        if r.status_code not in (200, 204):
            print(f"[alert] webhook failed: {r.status_code} {r.text[:200]}")
    except Exception as e:
        print(f"[alert] exception: {type(e).__name__}: {e}")


# ---------- routes ----------
@app.get("/health")
async def health():
    # basic DB check
    try:
        async with _pool.acquire() as con:  # type: ignore
            ver = await con.fetchval("select version()")
        return {"ok": True, "env": APP_ENV, "db": bool(ver)}
    except Exception as e:
        return {"ok": False, "env": APP_ENV, "error": f"{type(e).__name__}: {e}"}

@app.post("/api/tribe-events")
async def ingest(evt: TribeEvent, x_gl_key: Optional[str] = Header(None)):
    if not _authorized(x_gl_key):
        raise HTTPException(status_code=401, detail="unauthorized")

    # Insert
    try:
        async with _pool.acquire() as con:  # type: ignore
            await con.execute(
                """
                insert into tribe_events(server, tribe, ark_day, ark_time, severity, category, actor, message, raw_line)
                values($1,$2,$3,$4,$5,$6,$7,$8,$9)
                """,
                evt.server, evt.tribe, evt.ark_day, evt.ark_time,
                evt.severity, evt.category, evt.actor, evt.message, evt.raw_line
            )
    except Exception as e:
        print(f"[db] insert error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail="db insert failed")

    # Optional alert
    if _should_alert(evt):
        asyncio.create_task(_post_discord(evt))

    return {"ok": True, "alerted": _should_alert(evt), "env": APP_ENV}

@app.get("/api/tribe-events/recent")
async def recent(server: Optional[str] = None, tribe: Optional[str] = None, limit: int = 20):
    """
    Return the most recent rows (default 20, max 100), optionally filtered
    by server and/or tribe. No auth required for staging readbacks.
    """
    limit = max(1, min(int(limit), 100))
    try:
        async with _pool.acquire() as con:  # type: ignore
            where = []
            args: List[Any] = []
            if server:
                where.append(f"server = ${len(args)+1}")
                args.append(server)
            if tribe:
                where.append(f"tribe = ${len(args)+1}")
                args.append(tribe)

            sql = """
                select id, ingested_at, server, tribe, ark_day, ark_time,
                       severity, category, actor, message
                from tribe_events
            """
            if where:
                sql += " where " + " and ".join(where)
            sql += f" order by id desc limit ${len(args)+1}"
            args.append(limit)

            rows = await con.fetch(sql, *args)
            return [dict(r) for r in rows]
    except Exception as e:
        print(f"[db] recent error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail="db query failed")
