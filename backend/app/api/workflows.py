from fastapi import APIRouter, Header
from uuid import uuid4

router = APIRouter(prefix="/workflows")

@router.get("/")
async def list_workflows(user_id: str = Header(None, alias="X-User-ID")):
    return {
        "message": "Listing workflows for user",
        "user_id": user_id
    }

@router.post("/")
async def create_workflow(user_id: str = Header(None, alias="X-User-ID")):
    workflow_id = str(uuid4())
    return {
        "workflow_id": workflow_id,
        "user_id": user_id
    }
