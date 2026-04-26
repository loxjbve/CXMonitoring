from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, PlainTextResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles

from ..collector.models import utc_now_iso
from ..collector.monitor import RolloutMonitor
from ..config import Settings


def create_app(
    settings: Settings | None = None, monitor: RolloutMonitor | None = None
) -> FastAPI:
    settings = settings or Settings.from_env()
    monitor = monitor or RolloutMonitor(settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        await monitor.start()
        try:
            yield
        finally:
            await monitor.stop()

    app = FastAPI(
        title="CXMonitoring",
        docs_url=None,
        redoc_url=None,
        lifespan=lifespan,
    )
    app.state.monitor = monitor

    static_dir = settings.static_dir
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/")
    async def index() -> Response:
        index_path = static_dir / "index.html"
        if not index_path.exists():
            return PlainTextResponse("Dashboard assets are missing.", status_code=503)
        return FileResponse(index_path)

    @app.get("/api/current")
    async def current() -> dict[str, object]:
        return await monitor.get_snapshot()

    @app.get("/api/health")
    async def health() -> dict[str, object]:
        return await monitor.get_health()

    @app.post("/api/messages")
    async def messages(payload: dict[str, object]) -> dict[str, object]:
        content = str(payload.get("content") or "").strip()
        if not content:
            raise HTTPException(status_code=400, detail="Message content is required.")

        kind = str(payload.get("kind") or "instruction")
        reply_to = payload.get("reply_to")
        try:
            return await monitor.record_message(
                content,
                kind=kind,
                reply_to=None if reply_to is None else str(reply_to),
            )
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.get("/api/stream")
    async def stream(request: Request) -> StreamingResponse:
        queue = await monitor.subscribe()

        async def event_source() -> AsyncIterator[str]:
            try:
                yield _format_sse("snapshot", await monitor.get_snapshot())
                while True:
                    if await request.is_disconnected():
                        break
                    try:
                        item = await asyncio.wait_for(queue.get(), timeout=5.0)
                    except asyncio.TimeoutError:
                        yield _format_sse("heartbeat", {"ts": utc_now_iso()})
                        continue
                    yield _format_sse(item.event, item.payload)
            finally:
                await monitor.unsubscribe(queue)

        return StreamingResponse(
            event_source(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    return app


def _format_sse(event_name: str, payload: dict[str, object]) -> str:
    return f"event: {event_name}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
