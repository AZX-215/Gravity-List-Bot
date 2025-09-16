# Standalone FastAPI entrypoint for Railway STAGE
# - exposes /health for checks
# - exposes /api/tribe-events for our Milestone 1 test inserts

import os
import asyncpg
from fastapi import FastAPI, Request, HTTPException

app = FastAPI(title="Gravity List – Stage API")

GL_SHARED_SECRET = os.environ["GL_SHARED_SECRET"]
DATABASE_URL = os.environ["DATABASE_URL"]

_pool = None
async def get_pool():
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(DATABASE_URL, max_size=5)
    return _pool

@app.get("/health")
async def health():
    return {"ok": True, "env": os.getenv("ENVIRONMENT", "unknown")}

@app.post("/api/tribe-events")
async def tribe_events(req: Request):
    # simple header auth
    if req.headers.get("x-gl-key") != GL_SHARED_SECRET:
        raise HTTPException(status_code=401, detail="bad key")

    p = await req.json()
    required = ["server","tribe","ark_day","ark_time","severity","category","actor","message","raw_line"]
    missing = [k for k in required if k not in p]
    if missing:
        raise HTTPException(status_code=400, detail=f"missing fields: {', '.join(missing)}")

    sql_create = """
    create table if not exists tribe_events (
      id bigserial primary key,
      ingested_at timestamptz not null default now(),
      server text,
      tribe text,
      ark_day int,
      ark_time text,
      severity text check (severity in ('CRITICAL','IMPORTANT','INFO')),
      category text,
      actor text,
      message text,
      raw_line text unique
    );
    create index if not exists tribe_events_ingested_at_idx
      on tribe_events (ingested_at desc);
    """
    sql_insert = """
    insert into tribe_events
      (server, tribe, ark_day, ark_time, severity, category, actor, message, raw_line)
    values ($1,$2,$3,$4,$5,$6,$7,$8,$9)
    on conflict (raw_line) do nothing;
    """

    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            for stmt in [s for s in sql_create.split(';') if s.strip()]:
                await conn.execute(stmt)
            await conn.execute(sql_insert,
                p["server"], p["tribe"], int(p["ark_day"]), p["ark_time"],
                p["severity"], p["category"], p["actor"], p["message"], p["raw_line"])
    return {"ok": True}
