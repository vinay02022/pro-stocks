"""
StockPro Backend - FastAPI Application

Main entry point for the backend API.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.v1 import router as api_v1_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    print(f"Starting {settings.app_name} v{settings.app_version}")
    print(f"Environment: {settings.environment}")
    print(f"Live data: {settings.enable_live_data}")

    # Initialize SQLite database
    from app.db.database import init_db, close_db
    await init_db()
    print("Database initialized")

    # Initialize Redis cache
    from app.services.cache.redis_client import init_redis, close_redis
    redis_client = await init_redis()
    if redis_client:
        print("Redis cache connected")
    else:
        print("Redis unavailable - using in-memory cache")

    # Start WebSocket manager (for real-time data)
    from app.services.websocket.manager import start_websocket_manager, stop_websocket_manager
    if settings.enable_live_data:
        ws_manager = await start_websocket_manager()
        print("WebSocket manager started")
    else:
        ws_manager = None
        print("WebSocket manager disabled (enable_live_data=false)")

    yield

    # Shutdown
    print("Shutting down...")
    if ws_manager:
        await stop_websocket_manager()
    await close_redis()
    await close_db()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
    StockPro AI-Assisted Trading System API

    ## Architecture
    - **Data Ingestion**: Fetches market data from Groww, Angel One, News APIs
    - **Indicator Engine**: Calculates technical indicators (pure Python/NumPy)
    - **Reasoning Layer**: LLM-powered trade idea generation
    - **Risk Engine**: Deterministic risk validation
    - **Explanation Layer**: Human-readable trade explanations

    ## Core Principles
    - AI suggests, human executes
    - Probabilistic confidence bands (not certainty)
    - Risk-first approach with strict controls
    """,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware - allow both frontend ports
cors_origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
]
# Add any additional origins from settings
if settings.allowed_origins:
    cors_origins.extend([o for o in settings.allowed_origins if o not in cors_origins])

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_v1_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "StockPro Backend API",
        "docs": "/docs",
        "health": "/health",
    }
