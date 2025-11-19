from typing import Optional, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.user_manager import UserManager
from app.services.workflow_manager import WorkflowManager

router = APIRouter(prefix="/workflows", tags=["Workflows"])

class WorkflowCreateRequest(BaseModel):
    workflow_id: str
    name: str
    owner_user_id: str
    
class WorkflowResponse(BaseModel):
    workflow_id: str
    name: str
    owner_user_id: str
    entry_branch: Optional[str] = None
    
@router.post("/", response_model=WorkflowResponse,
             summary="Create a new workflow (dummy branch node)")
async def create_workflow(payload: WorkflowCreateRequest):

    if not await UserManager.is_registered(payload.owner_user_id):
        raise HTTPException(status_code=400, detail="Owner user is not registered.")

    created = await WorkflowManager.create_workflow(
        workflow_id=payload.workflow_id,
        name=payload.name,
        owner_user_id=payload.owner_user_id,
    )

    if not created:
        raise HTTPException(status_code=400, detail="Workflow ID already exists.")

    wf = await WorkflowManager.get_workflow(payload.workflow_id)

    return WorkflowResponse(
        workflow_id=wf["workflow_id"],
        name=wf.get("name", ""),
        owner_user_id=wf.get("owner_user_id", ""),
        entry_branch=wf.get("entry_branch"),
    )



# get all workflows
@router.get("/", response_model=List[WorkflowResponse], summary="List all workflows")
async def list_workflows():
    workflows = await WorkflowManager.list_workflows()
    # normalize missing entry_branch
    return [
        WorkflowResponse(
            workflow_id=wf["workflow_id"],
            name=wf.get("name", ""),
            owner_user_id=wf.get("owner_user_id", ""),
            entry_branch=wf.get("entry_branch"),
        )
        for wf in workflows
    ]    

@router.get("/{workflow_id}", response_model=WorkflowResponse, summary="Get workflow")
async def get_workflow(workflow_id: str):
    wf = await WorkflowManager.get_workflow(workflow_id)
    if wf is None:
        raise HTTPException(status_code=404, detail="Workflow not found.")

    return WorkflowResponse(
        workflow_id=wf["workflow_id"],
        name=wf.get("name"),
        owner_user_id=wf.get("owner_user_id", ""),
        entry_branch=wf.get("entry_branch"),
    )
    
@router.delete("/{workflow_id}", summary="Delete a workflow")
async def delete_workflow(workflow_id: str):
    deleted = await WorkflowManager.delete_workflow(workflow_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Workflow not found.")

    return {"message": "Workflow deleted successfully.", "workflow_id": workflow_id}

@router.get("/by_user/{user_id}", summary="List all workflows owned by a user")
async def list_workflows_by_user(user_id: str):
    from app.services.user_manager import UserManager
    if not await UserManager.is_registered(user_id):
        raise HTTPException(status_code=404, detail="User not found.")

    workflows = await WorkflowManager.list_workflows_by_user(user_id)
    return [
        {
            "workflow_id": wf["workflow_id"],
            "name": wf.get("name", ""),
            "owner_user_id": wf.get("owner_user_id", ""),
            "entry_branch": wf.get("entry_branch"),
        }
        for wf in workflows
    ]
