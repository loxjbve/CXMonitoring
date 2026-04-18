from __future__ import annotations

from .config import Settings


def create_app():
    from .server.app import create_app as create_server_app

    return create_server_app(Settings.from_env())


def run() -> None:
    try:
        import uvicorn
    except ImportError as exc:  # pragma: no cover
        raise SystemExit(
            "uvicorn is not installed. Run `python -m pip install -e .` first."
        ) from exc

    settings = Settings.from_env()
    uvicorn.run(
        "cxmonitoring.main:create_app",
        host=settings.host,
        port=settings.port,
        factory=True,
        reload=False,
    )
