from datetime import datetime, timezone
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.routers import health, flashcards, analysis, scraper

app = FastAPI(title="StudGrasp AI", version="2.0.0")


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": str(exc),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


app.include_router(health.router)
app.include_router(flashcards.router, prefix="/ai")
app.include_router(analysis.router, prefix="/ai")
app.include_router(scraper.router, prefix="/ai")
