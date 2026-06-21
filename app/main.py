from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.core.config import get_settings

UI_STATIC_DIR = Path(__file__).resolve().parent / "ui" / "static"


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
    )
    app.mount("/ui/static", StaticFiles(directory=UI_STATIC_DIR), name="ui-static")
    app.router.routes.extend(router.routes)

    return app


app = create_app()
