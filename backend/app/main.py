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
    departments,
    mentor,
    mentor_mapping,
    mentors,
    notifications,
    planned_absence,
    push,
    sections,
    sessions,
    student_attendance,
    students,
    timetable,
    uploads,
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
    
    # Synchronize student batch and academic year mapping
    try:
        from app.services.student_service import sync_all_students_batch_and_year
        from app.db.mongodb import get_database
        db = get_database()
        updated_count = await sync_all_students_batch_and_year(db)
        logger.info(f"Student batch/year synchronization completed ({updated_count} records updated).")
    except Exception as e:
        logger.warning("Student batch/year synchronization warning (%s).", type(e).__name__)

    # Generate / sync real-time sessions for current date
    try:
        from app.services.session_service import generate_and_sync_sessions_for_date
        await generate_and_sync_sessions_for_date()
        logger.info("Real-time sessions synchronized for current date.")
    except Exception as e:
        logger.warning("Session sync warning (%s).", type(e).__name__)

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

# CORS setup — include all known origins explicitly plus regex for previews
origins = [
    # ── Production deployments ────────────────────────────────────────────────
    "https://session-monitoring-system.vercel.app",
    "https://session-monitoring-system.onrender.com",
    # ── Local development ─────────────────────────────────────────────────────
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5175",
    "http://localhost:3000",
    "http://localhost:4173",
    "http://localhost:8080",
    "http://localhost:8081",
    "http://localhost:8082",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://127.0.0.1:5175",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:4173",
    "http://127.0.0.1:8080",
    "http://127.0.0.1:8081",
    "http://127.0.0.1:8082",
]

# Also allow dynamic Vercel preview URLs and any Render/Netlify deployment
_CORS_ORIGIN_REGEX = (
    r"^https?://("
    r"localhost(:\d+)?"
    r"|127\.0\.0\.1(:\d+)?"
    r"|([a-zA-Z0-9-]+\.)*vercel\.app"
    r"|([a-zA-Z0-9-]+\.)*onrender\.com"
    r"|([a-zA-Z0-9-]+\.)*netlify\.app"
    r")(:\d+)?$"
)

if settings.FRONTEND_URL:
    for raw_url in settings.FRONTEND_URL.split(","):
        cleaned_url = raw_url.strip().rstrip("/")
        if cleaned_url and cleaned_url not in origins:
            origins.append(cleaned_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=_CORS_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
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
    logger.error("Unhandled server exception (%s).", type(exc).__name__)
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


# Healthcheck endpoints
@app.get("/", tags=["Health"])
@app.head("/", tags=["Health"])
@app.get("/health", tags=["Health"])
@app.head("/health", tags=["Health"])
@app.get(f"{settings.API_V1_STR}", tags=["Health"])
@app.head(f"{settings.API_V1_STR}", tags=["Health"])
@app.get(f"{settings.API_V1_STR}/", tags=["Health"])
@app.head(f"{settings.API_V1_STR}/", tags=["Health"])
@app.get(f"{settings.API_V1_STR}/health", tags=["Health"])
@app.head(f"{settings.API_V1_STR}/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "project": settings.PROJECT_NAME, "version": settings.VERSION}


# Include API Routers under /api
api_router_prefix = settings.API_V1_STR

app.include_router(auth.router, prefix=api_router_prefix)
app.include_router(users.router, prefix=api_router_prefix)
app.include_router(uploads.router, prefix=api_router_prefix)
app.include_router(mentors.router, prefix=api_router_prefix)
app.include_router(mentor_mapping.router, prefix=api_router_prefix)
app.include_router(planned_absence.router, prefix=api_router_prefix)
app.include_router(departments.router, prefix=api_router_prefix)
app.include_router(mentor.router, prefix=api_router_prefix)
app.include_router(students.router, prefix=api_router_prefix)
app.include_router(sections.router, prefix=api_router_prefix)
app.include_router(timetable.router, prefix=api_router_prefix)
app.include_router(sessions.router, prefix=api_router_prefix)
app.include_router(attendance.router, prefix=api_router_prefix)
app.include_router(student_attendance.router, prefix=api_router_prefix)
app.include_router(notifications.router, prefix=api_router_prefix)
app.include_router(push.router, prefix=api_router_prefix)
app.include_router(analytics.router, prefix=api_router_prefix)
