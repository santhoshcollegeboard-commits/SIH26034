from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import get_settings
from backend.app.core.logging import setup_logging, log_startup, log_shutdown
from backend.app.api.extract import router as extract_router
from backend.app.api.verify import router as verify_router

settings = get_settings()

# Initialize file logger eagerly at module import
setup_logging(
    max_bytes=settings.LOG_MAX_BYTES,
    backup_count=settings.LOG_BACKUP_COUNT,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager handling startup and shutdown logging."""
    setup_logging(
        max_bytes=settings.LOG_MAX_BYTES,
        backup_count=settings.LOG_BACKUP_COUNT,
    )
    log_startup(
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
    )
    yield
    log_shutdown(app_name=settings.APP_NAME)


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Evidence-driven Legal Metrology compliance checker for packaged commodities",
    lifespan=lifespan,
)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint confirming service status."""
    return {"status": "ok"}


from pathlib import Path
from fastapi.staticfiles import StaticFiles

# Register API routers
app.include_router(extract_router)
app.include_router(verify_router)

# Mount static evidence directory if present
evidence_static_dir = Path(__file__).resolve().parents[2] / "frontend" / "public" / "evidence"
if evidence_static_dir.exists():
    app.mount("/evidence", StaticFiles(directory=str(evidence_static_dir)), name="evidence")



if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
