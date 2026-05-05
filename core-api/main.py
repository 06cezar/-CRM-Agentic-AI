from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, leads, activity, stats, google_auth, gmail_watcher, scraper

app = FastAPI(title="CRM Core API")

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
app.include_router(google_auth.router)
app.include_router(gmail_watcher.router)
app.include_router(scraper.router)


@app.get("/")
def read_root():
    return {"status": "healthy", "message": "Service is running"}
