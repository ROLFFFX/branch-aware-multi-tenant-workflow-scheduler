from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.redis_schema import initialize_redis_schema
from app.routes.users import router as users_router
from app.routes.workflows import router as workflows_router
from app.routes.branches import router as branches_router


app = FastAPI(
    title = "BAMT Workflow Scheduler",
    version = "0.1.0",
)

@app.on_event("startup")
async def startup_event():
    await initialize_redis_schema()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins = ["*"],
    allow_credentials = True,
    allow_methods = ["*"],
    allow_headers = ["*"]
)

app.include_router(users_router)
app.include_router(workflows_router)
app.include_router(branches_router)


@app.get("/")
async def root():
    return {"message": "BAMT Workflow Scheduler backend is online!"}

