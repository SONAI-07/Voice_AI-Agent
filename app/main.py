from contextlib import asynccontextmanager
from fastapi import FastAPI
from prometheus_client import make_asgi_app
from app.core.config import get_settings
from app.core.database import engine
from app.voice.routes import router as voice_router
from app.voice.websocket import router as websocket_router


settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):

    print(
        "Starting CustomerCare AI Agent..."
    )

    yield

    await engine.dispose()

    print(
        "Database connection closed."
    )


app = FastAPI(
    title=settings.app_name,
    description=(
        "Voice AI Customer Care and Sales Agent"
    ),
    version="0.1.0",
    lifespan=lifespan,
)


# ================================================================
# APPLICATION ROUTES
# ================================================================

app.include_router(
    voice_router
)

app.include_router(
    websocket_router
)


# ================================================================
# PROMETHEUS
# ================================================================

metrics_app = make_asgi_app()

app.mount(
    "/metrics",
    metrics_app,
)


# ================================================================
# HEALTH
# ================================================================

@app.get("/health")
async def health_check():

    return {
        "status": "healthy",
        "environment": settings.app_env,
    }


@app.get("/ready")
async def readiness_check():

    # This endpoint intentionally remains lightweight.
    #
    # A full dependency check will be added once Redis and
    # provider health check interfaces are finalized.
    #
    # /health answers:
    #     "Is the process alive?"
    #
    # /ready answers:
    #     "Is the application currently accepting traffic?"

    return {
        "status": "ready",
        "environment": settings.app_env,
    }