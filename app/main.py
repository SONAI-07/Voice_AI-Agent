from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.config import get_settings
from app.core.database import engine
from app.voice.routes import router as voice_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting CustomerCare AI Agent...")
    yield
    await engine.dispose()
    print("Database connection closed.")


app = FastAPI(
    title=settings.app_name,
    description="Voice AI Customer Care and Sales Agent",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(voice_router)

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "environment": settings.app_env,
    }