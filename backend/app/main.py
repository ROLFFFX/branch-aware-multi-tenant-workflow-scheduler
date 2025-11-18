from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import workflows

app = FastAPI(
    title = "BAMT Workflow Scheduler",
    version = "0.1.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins = ["*"],
    allow_credentials = True,
    allow_methods = ["*"],
    allow_headers = ["*"]
)

app.include_router(workflows.router)

@app.get("/")
async def root():
    return {"message": "BAMT Workflow Scheduler backend is online!"}

