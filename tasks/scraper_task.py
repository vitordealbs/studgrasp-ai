import logging
from celery import Celery

from app.config import get_settings
from app.services.scraper_service import scrape_all_roadmaps

logger = logging.getLogger(__name__)

settings = get_settings()

celery_app = Celery(
    "studgrasp_tasks",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.timezone = "UTC"


@celery_app.task(name="tasks.scraper_task.scrape_roadmaps_task", bind=True, max_retries=3)
def scrape_roadmaps_task(self) -> dict:
    try:
        summary = scrape_all_roadmaps(java_api_url=settings.java_api_url)
        logger.info("Roadmap scraping complete: %s", summary)
        return summary
    except Exception as exc:
        logger.error("Scraping failed: %s", exc)
        raise self.retry(exc=exc, countdown=300)
