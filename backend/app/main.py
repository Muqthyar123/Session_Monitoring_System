import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api import (
    analytics,
    attendance,
    auth,
    notifications,
    push,
    sections,
    sessions,
    timetable,
    users,
)
from app.core.config import settings
from app.db.indexes import create_db_indexes
from app.db.mongodb import close_mongo_connection, connect_to_mongo
from app.scheduler.scheduler import shutdown_scheduler, start_scheduler

# Configure logging format
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("fams.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup tasks
    logger.info("Initializing FastAPI Backend Services...")
    await connect_to_mongo()
    await create_db_indexes()
    logger.info("Database indexes created successfully.")
    start_scheduler()
    logger.info("Scheduler initialized.")
    logger.info("Application startup complete.")
    yield
    # Shutdown tasks
    logger.info("Shutting down FastAPI Backend Services...")
    shutdown_scheduler()
    await close_mongo_connection()
    logger.info("Shutdown complete.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS setup
origins = [
    settings.FRONTEND_URL,
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception Handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": str(exc.detail),
                "details": getattr(exc, "headers", None),
            },
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid request parameter or payload structure.",
                "details": exc.errors(),
            },
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled server exception: %s", str(exc), exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected server error occurred. Please try again later.",
            },
        },
    )


# Healthcheck endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "project": settings.PROJECT_NAME, "version": settings.VERSION}


# Include API Routers under /api
api_router_prefix = settings.API_V1_STR

app.include_router(auth.router, prefix=api_router_prefix)
app.include_router(users.router, prefix=api_router_prefix)
app.include_router(sections.router, prefix=api_router_prefix)
app.include_router(timetable.router, prefix=api_router_prefix)
app.include_router(sessions.router, prefix=api_router_prefix)
app.include_router(attendance.router, prefix=api_router_prefix)
app.include_router(notifications.router, prefix=api_router_prefix)
app.include_router(push.router, prefix=api_router_prefix)
app.include_router(analytics.router, prefix=api_router_prefix)
