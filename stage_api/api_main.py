import os
import ssl
import asyncpg
from fastapi import FastAPI, Request, HTTPException

app = FastAPI(title="Gravity List – Stage API")

GL_SHARED_SECRET = os.environ["GL_SHARED_SECRET"]
DATABASE_URL = os.environ["DATABASE_URL"]

# ---- Robust TLS setup for Railway Postgres ----
def build_ssl_ctx(insecure: bool = False) -> ssl.SSLContext:
    """
    Create an SSL context for Postgres.
    If insecure=True (only for debugging), disable cert verification.
    """
    ctx = ssl.create_default_context()
    if insecure:
        # DEBUG ONLY: turn off verification if you see certificate errors.
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return ctx

# Toggle this to True ONLY if logs show a certificate verify error.
ALLOW_INSECURE_DB_SSL = os.getenv("ALLOW_INSECURE_DB_SSL", "false").lower() == "true"
SSL_CTX = build_ssl_ctx(insecure=ALLOW_INSECURE_DB_SSL)

_pool = None
async def get_pool():
    global _pool
    if _pool is None:
        try:
            # FIX: set both min_size and max_size so min <= max
            _pool = await asyncpg.create_pool(
                DATABASE_URL,
                min_size=1,   # small is fine for stage
                max_size=5,
                ssl=SSL_CTX
            )
        except Exception as e:
            print(f"[db] create_pool failed: {type(e).__name__}: {e}")
            raise
    return _pool

@app.get("/health")
async def health():
    return {"ok": True, "env": os.getenv("ENVIRONMENT", "unknown")}

# Quick DB connectivity probe
@app.get("/debug/db")
async def debug_db():
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            v = await conn.fetchval("select version()")
        return {"db_ok": True, "version": v}
    except Exception as e:
        return {"db_ok": False, "error": f"{type(e).__name__}: {e}"}

@app.post("/api/tribe-events")
async def tribe_events(req: Request):
    if req.headers.get("x-gl-key") != GL_SHARED_SECRET:
        raise HTTPException(status_code=401, detail="bad key")

    try:
        p = await req.json()
    except Exception:
        raise HTTPException(status_code=400, detail="invalid JSON")

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
    create index if not exists tribe_events_ingested_at_idx on tribe_events(ingested_at desc);
    """
    sql_insert = """
    insert into tribe_events
      (server, tribe, ark_day, ark_time, severity, category, actor, message, raw_line)
    values ($1,$2,$3,$4,$5,$6,$7,$8,$9)
    on conflict (raw_line) do nothing;
    """

    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.transaction():
                for stmt in [s for s in sql_create.split(';') if s.strip()]:
                    await conn.execute(stmt)
                await conn.execute(sql_insert,
                    p["server"], p["tribe"], int(p["ark_day"]), p["ark_time"],
                    p["severity"], p["category"], p["actor"], p["message"], p["raw_line"])
        return {"ok": True}
    except Exception as e:
        print(f"[api] /api/tribe-events failed: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail="internal error")

