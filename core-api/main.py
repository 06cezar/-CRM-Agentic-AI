import time
import uuid
import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.routers import auth, leads, activity, stats, google_auth, gmail_watcher, scraper, copilot, icp, emails
from app.services.s3_service import ensure_bucket_exists
from app.logger import logger

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure MinIO bucket exists
    try:
        ensure_bucket_exists()
        logger.info("MinIO bucket check completed")
    except Exception as e:
        logger.error("MinIO bucket check failed", error=str(e))
    yield

app = FastAPI(title="CRM Core API", lifespan=lifespan)

@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id)
    
    start_time = time.perf_counter()
    
    try:
        response = await call_next(request)
        process_time = time.perf_counter() - start_time
        
        logger.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration=process_time,
        )
        return response
    except Exception as e:
        process_time = time.perf_counter() - start_time
        logger.error(
            "request_failed",
            method=request.method,
            path=request.url.path,
            error=str(e),
            duration=process_time,
        )
        raise e

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000",
                   "https://gills-skimming-slick.ngrok-free.dev"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(leads.router)
app.include_router(activity.router)
app.include_router(stats.router)
app.include_router(copilot.router)
app.include_router(icp.router)
app.include_router(google_auth.router)
app.include_router(gmail_watcher.router)
app.include_router(scraper.router)
app.include_router(emails.router)


@app.get("/")
def read_root():
    return {"status": "healthy", "message": "Service is running"}
