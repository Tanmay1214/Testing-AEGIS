"""
main.py
FastAPI application entry point.
Handles startup (DB tables, model loading) and shutdown.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import create_all_tables
from app.api.routes import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("aegis.main")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    # ── Startup ──────────────────────────────────────────────
    logger.info("AEGIS Backend starting up...")

    # Create DB tables (idempotent)
    await create_all_tables()
    logger.info("Database tables ready")

    # Load trained ML models
    try:
        from app.ml.detector import load_models
        app.state.models = load_models()
        logger.info("ML models loaded successfully")
    except FileNotFoundError as e:
        logger.warning("ML models not found — inference disabled. Run train_model.py. (%s)", e)
        app.state.models = None

    yield  # ── Application is running ───────────────────────

    # ── Shutdown ─────────────────────────────────────────────
    logger.info("AEGIS Backend shutting down...")
    try:
        from app.core.cache import get_redis
        await get_redis().aclose()
    except Exception:
        pass


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "AEGIS Cyber-Infrastructure Defense System — "
            "real-time anomaly detection, forensic node mapping, "
            "and schema-aware telemetry analysis for Nexus City."
        ),
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:8000",
            "http://127.0.0.1:8000",
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5500", # Live Server
            "*", # fallback
        ] if not settings.DEBUG else ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health-check")
    async def health_check():
        return {"status": "operational", "version": settings.APP_VERSION}

    app.include_router(router)
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
