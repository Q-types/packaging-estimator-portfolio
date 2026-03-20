"""
PackagePro Estimator - FastAPI Application

Main entry point for the web application.
"""

import logging
from contextlib import asynccontextmanager

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from backend.app.config import get_settings
from backend.app.middleware import (
    GlobalExceptionMiddleware,
    RateLimitMiddleware,
    RequestLoggingMiddleware,
)

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
TEMPLATES_DIR = BASE_DIR / "frontend" / "templates"
STATIC_DIR = BASE_DIR / "frontend" / "static"

settings = get_settings()

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown."""
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {settings.environment}")

    yield

    # Shutdown
    logger.info("Shutting down application")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Intelligent cost estimation platform for bespoke packaging manufacturers",
    lifespan=lifespan,
    docs_url="/api/docs" if settings.debug else None,
    redoc_url="/api/redoc" if settings.debug else None,
)

# Middleware (order matters: first added = outermost)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(GlobalExceptionMiddleware)
if not settings.debug:
    app.add_middleware(RateLimitMiddleware, requests_per_minute=60)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else ["https://packagepro-demo.example.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "version": settings.app_version,
        "environment": settings.environment,
    }


# API version info
@app.get("/api/v1", tags=["System"])
async def api_info():
    """API version information."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "api_version": "v1",
    }


# Import and include routers
from backend.app.routers import admin, analytics, auth, customers, estimates, feedback, materials, prospects

app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(estimates.router, prefix="/api/v1/estimates", tags=["Estimates"])
app.include_router(materials.router, prefix="/api/v1/materials", tags=["Materials"])
app.include_router(customers.router, prefix="/api/v1/customers", tags=["Customers"])
app.include_router(feedback.router, prefix="/api/v1/feedback", tags=["Feedback"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["Analytics"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])
app.include_router(prospects.router, prefix="/api/v1/prospects", tags=["Prospects"])

# Serve static files if directory exists
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Setup templates
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


# Serve the main UI
@app.get("/", response_class=HTMLResponse, tags=["UI"])
async def home(request: Request):
    """Serve the main estimator UI."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/prospects", response_class=HTMLResponse, tags=["UI"])
async def prospects_ui(request: Request):
    """Serve the prospect search UI."""
    return templates.TemplateResponse("prospects.html", {"request": request})



def run():
    """Run the application with uvicorn."""
    import uvicorn

    uvicorn.run(
        "backend.app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        workers=1 if settings.debug else settings.workers,
    )


if __name__ == "__main__":
    run()
