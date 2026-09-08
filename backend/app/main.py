from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import get_settings
from backend.app.api.extract import router as extract_router

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Evidence-driven Legal Metrology compliance checker for packaged commodities",
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


# Register API routers
app.include_router(extract_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
