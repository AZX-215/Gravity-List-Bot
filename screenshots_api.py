# screenshots_api.py
import os
import io
import time
import asyncio
import threading
from datetime import datetime, timezone

from fastapi import FastAPI, UploadFile, File, Form, Header, HTTPException
from discord import File as DFile

# NOTE: This module exposes two entry points:
#   setup_screenshot_api(bot) -> (fastapi_app, start_worker_coroutine)
#   run_fastapi_in_thread(app, port)
#
# The worker is intentionally NOT scheduled here (to avoid touching the
# event loop before discord.py is running). bot.py awaits the returned
# start_worker coroutine inside on_ready.

def setup_screenshot_api(bot):
    """
    Create FastAPI app and return (app, start_worker) where start_worker is an
    async callable that schedules the background worker on the running event loop.
    """
    app = FastAPI(title="Gravity List – Screenshot Ingest")
    queue: asyncio.Queue = asyncio.Queue()

    SECRET = os.getenv("SCREENSHOT_AGENT_KEY", "")
    DEFAULT_CH = int(os.getenv("SCREENSHOT_CHANNEL_ID", "0"))

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

        data = await file.read()
        await queue.put({
            "bytes": data,
            "filename": file.filename or f"screenshot_{int(time.time())}.jpg",
            "channel_id": channel_id or DEFAULT_CH,
            "caption": caption or f"Screenshot {datetime.fromtimestamp(ts or time.time(), tz=timezone.utc).astimezone().isoformat(timespec='seconds')}",
        })
        return {"queued": True}

    async def worker():
        await bot.wait_until_ready()
        while True:
            item = await queue.get()
            try:
                channel = bot.get_channel(item["channel_id"]) or await bot.fetch_channel(item["channel_id"])
                bio = io.BytesIO(item["bytes"]); bio.seek(0)
                await channel.send(content=item["caption"], file=DFile(bio, filename=item["filename"]))
                await asyncio.sleep(1.5)  # gentle spacing for rate limits
            except Exception as e:
                print(f"[screenshot-worker] {e}")
                await asyncio.sleep(3)
            finally:
                queue.task_done()

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
