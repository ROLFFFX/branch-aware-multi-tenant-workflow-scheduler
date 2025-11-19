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
    input_payload: dict = {}


class JobSpec(BaseModel):
    template_id: str
    input_payload: dict = {}


class BranchJobsResponse(BaseModel):
    workflow_id: str
    branch_id: str
    jobs: List[JobSpec]


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
    summary="Append a job template (with payload) to a branch",
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
        input_payload=payload.input_payload,
    )
    if not added:
        raise HTTPException(status_code=404, detail="Branch not found.")

    return {
        "message": "Job template added to branch.",
        "workflow_id": workflow_id,
        "branch_id": branch_id,
        "job_template_id": payload.job_template_id,
        "input_payload": payload.input_payload,
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
    summary="List jobs (with payloads) in a branch",
)
async def get_branch_jobs(workflow_id: str, branch_id: str):
    if not await WorkflowManager.workflow_exists(workflow_id):
        raise HTTPException(status_code=404, detail="Workflow not found.")

    jobs = await BranchManager.get_branch_jobs(workflow_id, branch_id)
    branches = await BranchManager.list_branches(workflow_id)
    if branch_id not in branches:
        raise HTTPException(status_code=404, detail="Branch not found.")

    # jobs is a list[dict] of {"template_id": ..., "input_payload": {...}}
    job_models = [JobSpec(**job) for job in jobs]

    return BranchJobsResponse(
        workflow_id=workflow_id,
        branch_id=branch_id,
        jobs=job_models,
    )


# delete branch
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

@router.delete("/{workflow_id}/branches/{branch_id}/jobs/{index}",
               summary="Delete a job from a branch")
async def delete_branch_job(workflow_id: str, branch_id: str, index: int):

    # Workflow exists?
    if not await WorkflowManager.workflow_exists(workflow_id):
        raise HTTPException(404, "Workflow not found.")

    # Branch exists?
    if not await BranchManager.branch_exists(workflow_id, branch_id):
        raise HTTPException(404, "Branch not found.")

    # Delete job
    deleted = await BranchManager.delete_job_from_branch(
        workflow_id, branch_id, index
    )

    if not deleted:
        raise HTTPException(404, "Job index out of range.")

    return {
        "message": "Job deleted.",
        "workflow_id": workflow_id,
        "branch_id": branch_id,
        "deleted_index": index,
    }

