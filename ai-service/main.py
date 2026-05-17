from fastapi import FastAPI
from routers import agent, search_agent

app = FastAPI(title="CRM AI Service")


app.include_router(agent.router, prefix="/agent")
app.include_router(search_agent.router, prefix="/agent")


@app.get("/")
def read_root():
    return {"status": "healthy", "message": "AI Service is running"}
