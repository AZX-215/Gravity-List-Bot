# screenshots_api.py
import os
import io
import time
import asyncio
import threading
from datetime import datetime, timezone
from queue import Queue, Full

from fastapi import FastAPI, UploadFile, File, Form, Header, HTTPException
from discord import File as DFile

# NOTE: This module exposes two entry points:
#   setup_screenshot_api(bot) -> (fastapi_app, start_worker_coroutine)
#   run_fastapi_in_thread(app, port)
#
# The FastAPI server runs in a background thread (uvicorn has its own event loop).
# Because of that, we MUST NOT use asyncio.Queue to pass items between FastAPI and
# discord.py. We use a threadsafe Queue and bridge it into the discord loop.


def setup_screenshot_api(bot):
    """
    Create FastAPI app and return (app, start_worker) where start_worker is an
    async callable that schedules the background worker on the running event loop.
    """
    app = FastAPI(title="Gravity List – Screenshot Ingest")

    # Thread-safe cross-thread queue (FastAPI thread -> discord loop)
    queue_max = int(os.getenv("SCREENSHOT_QUEUE_MAX", "50") or "50")
    q: Queue = Queue(maxsize=max(1, queue_max))

    SECRET = os.getenv("SCREENSHOT_AGENT_KEY", "")
    DEFAULT_CH = int(os.getenv("SCREENSHOT_CHANNEL_ID", "0"))
    MAX_BYTES = int(os.getenv("SCREENSHOT_MAX_BYTES", str(8 * 1024 * 1024)) or str(8 * 1024 * 1024))

    @app.post("/api/screenshots")
    async def receive_screenshot(
        file: UploadFile = File(...),
        channel_id: int | None = Form(None),
        ts: float | None = Form(None),
        caption: str | None = Form(None),
        x_gl_key: str | None = Header(None, alias="X-GL-Key"),
    ):
        if not SECRET or x_gl_key != SECRET:
            raise HTTPException(401, "Unauthorized (bad key)")

        target_ch = channel_id or DEFAULT_CH
        if not target_ch:
            raise HTTPException(400, "No channel_id provided and SCREENSHOT_CHANNEL_ID not set")

        data = await file.read()
        if MAX_BYTES and len(data) > MAX_BYTES:
            raise HTTPException(413, f"File too large (>{MAX_BYTES} bytes)")

        item = {
            "bytes": data,
            "filename": file.filename or f"screenshot_{int(time.time())}.jpg",
            "channel_id": target_ch,
            "caption": caption
            or f"Screenshot {datetime.fromtimestamp(ts or time.time(), tz=timezone.utc).astimezone().isoformat(timespec='seconds')}",
        }

        try:
            q.put_nowait(item)
        except Full:
            raise HTTPException(429, "Queue full, try again shortly")

        return {"queued": True}

    async def worker():
        await bot.wait_until_ready()
        while True:
            # Block in a thread so we don't block the discord event loop
            item = await asyncio.to_thread(q.get)
            try:
                channel = bot.get_channel(item["channel_id"]) or await bot.fetch_channel(
                    item["channel_id"]
                )
                bio = io.BytesIO(item["bytes"])
                bio.seek(0)
                await channel.send(
                    content=item["caption"], file=DFile(bio, filename=item["filename"])
                )
                await asyncio.sleep(1.5)  # gentle spacing for rate limits
            except Exception as e:
                print(f"[screenshot-worker] {e}")
                await asyncio.sleep(3)
            finally:
                try:
                    q.task_done()
                except Exception:
                    pass

    async def start_worker():
        # Schedule the worker on the already-running discord loop
        asyncio.create_task(worker())

    return app, start_worker


def run_fastapi_in_thread(app, port: int):
    """Run uvicorn in a background thread so discord.py can keep running."""
    import uvicorn

    def _run():
        uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")

    th = threading.Thread(target=_run, daemon=True)
    th.start()
