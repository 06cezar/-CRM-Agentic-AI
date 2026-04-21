from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, leads

app = FastAPI(title="CRM Core API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(leads.router, prefix="/api/v1/leads", tags=["leads"])


@app.get("/")
def read_root():
    return {"status": "healthy", "message": "Service is running"}
