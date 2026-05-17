from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.routers import auth, leads, activity, stats, google_auth, gmail_watcher, scraper, copilot, icp, emails
from app.services.s3_service import ensure_bucket_exists

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure MinIO bucket exists
    try:
        ensure_bucket_exists()
        print("MinIO bucket check completed.")
    except Exception as e:
        print(f"MinIO bucket check failed: {e}")
    yield

app = FastAPI(title="CRM Core API", lifespan=lifespan)

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
