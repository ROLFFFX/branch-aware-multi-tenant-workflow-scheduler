from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio

from app.core.redis_schema import initialize_redis_schema
from app.services.user_manager import UserManager
from app.scheduler.scheduler_main import scheduler_loop


import app.jobs.fake_sleep
import app.jobs.wsi_initialize


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[LIFESPAN] Startup triggered")
    await initialize_redis_schema()

    # Start global scheduler (it will sit idle if state=paused)
    print("[LIFESPAN] Starting global scheduler loop...")
    asyncio.create_task(scheduler_loop())

    yield

    print("[LIFESPAN] Shutdown triggered")


app = FastAPI(
    title="BAMT Workflow Scheduler",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.routes.users import router as users_router
from app.routes.workflows import router as workflows_router
from app.routes.branches import router as branches_router
from app.routes.jobs import router as jobs_router
from app.routes.execution import router as execution_router
from app.routes.scheduler import router as scheduler_router
from app.routes.files import router as files_router


app.include_router(users_router)
app.include_router(workflows_router)
app.include_router(branches_router)
app.include_router(jobs_router)
app.include_router(execution_router)
app.include_router(scheduler_router)
app.include_router(files_router)


@app.get("/")
async def root():
    return {"message": "BAMT Workflow Scheduler backend is online!"}
