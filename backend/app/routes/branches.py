from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.workflow_manager import WorkflowManager
from app.services.branch_manager import BranchManager

router = APIRouter(prefix="/workflows", tags=["Branches"])

class CreateBranchRequest(BaseModel):
    branch_id: str

class AddJobRequest(BaseModel):
    job_template_id: str

class BranchJobsResponse(BaseModel):
    workflow_id: str
    branch_id: str
    jobs: List[str]

# add new branch to workflow id
@router.post("/{workflow_id}/branches", summary="Create a branch for a workflow")
async def create_branch(workflow_id: str, payload: CreateBranchRequest):
    if not await WorkflowManager.workflow_exists(workflow_id):
        raise HTTPException(status_code=404, detail="Workflow not found.")

    created = await BranchManager.create_branch(workflow_id, payload.branch_id)
    if not created:
        raise HTTPException(status_code=400, detail="Branch already exists.")

    return {
        "message": "Branch created.",
        "workflow_id": workflow_id,
        "branch_id": payload.branch_id,
    }

# add job template to a branch
@router.post(
    "/{workflow_id}/branches/{branch_id}/jobs",
    summary="Append a job template to a branch",
)
async def add_job_to_branch(
    workflow_id: str,
    branch_id: str,
    payload: AddJobRequest,
):
    if not await WorkflowManager.workflow_exists(workflow_id):
        raise HTTPException(status_code=404, detail="Workflow not found.")

    added = await BranchManager.add_job_to_branch(
        workflow_id=workflow_id,
        branch_id=branch_id,
        job_template_id=payload.job_template_id,
    )
    if not added:
        raise HTTPException(status_code=404, detail="Branch not found.")

    return {
        "message": "Job template added to branch.",
        "workflow_id": workflow_id,
        "branch_id": branch_id,
        "job_template_id": payload.job_template_id,
    }


# get all branches given a workflow
@router.get(
    "/{workflow_id}/branches",
    summary="List all branches for a workflow",
)
async def list_branches(workflow_id: str) -> List[str]:
    if not await WorkflowManager.workflow_exists(workflow_id):
        raise HTTPException(status_code=404, detail="Workflow not found.")

    branches = await BranchManager.list_branches(workflow_id)
    return branches


# get all job templates in a branch
@router.get(
    "/{workflow_id}/branches/{branch_id}",
    response_model=BranchJobsResponse,
    summary="List job templates in a branch",
)
async def get_branch_jobs(workflow_id: str, branch_id: str):
    if not await WorkflowManager.workflow_exists(workflow_id):
        raise HTTPException(status_code=404, detail="Workflow not found.")

    jobs = await BranchManager.get_branch_jobs(workflow_id, branch_id)
    branches = await BranchManager.list_branches(workflow_id)
    if branch_id not in branches:
        raise HTTPException(status_code=404, detail="Branch not found.")

    return BranchJobsResponse(
        workflow_id=workflow_id,
        branch_id=branch_id,
        jobs=jobs,
    )

# delete job from workflow = delete branch
@router.delete(
    "/{workflow_id}/branches/{branch_id}",
    summary="Delete a branch from a workflow",
)
async def delete_branch(workflow_id: str, branch_id: str):
    if not await WorkflowManager.workflow_exists(workflow_id):
        raise HTTPException(status_code=404, detail="Workflow not found.")

    deleted = await BranchManager.delete_branch(workflow_id, branch_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Branch not found.")

    return {
        "message": "Branch deleted.",
        "workflow_id": workflow_id,
        "branch_id": branch_id,
    }
