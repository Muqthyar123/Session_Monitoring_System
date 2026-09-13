import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.scheduler.jobs import process_scheduled_sessions_job

logger = logging.getLogger("fams.scheduler")

scheduler = AsyncIOScheduler()


def start_scheduler():
    """Initializes and starts background APScheduler instance."""
    if not scheduler.running:
        scheduler.add_job(
            process_scheduled_sessions_job,
            "interval",
            seconds=30,  # Checks every 30 seconds for precise 10-min escalation
            id="process_scheduled_sessions_job",
            replace_existing=True,
        )
        scheduler.start()
        logger.info("APScheduler initialized and started successfully.")


def shutdown_scheduler():
    """Gracefully shuts down APScheduler."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("APScheduler shutdown complete.")
