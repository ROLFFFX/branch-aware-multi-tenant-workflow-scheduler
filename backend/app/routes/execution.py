from fastapi import APIRouter, HTTPException
from app.services.execution_manager import ExecutionManager
from app.services.workflow_manager import WorkflowManager

router = APIRouter(prefix="/workflows", tags=["Execution"])


@router.post("/{workflow_id}/execute")
async def execute_workflow(workflow_id: str):

    if not await WorkflowManager.workflow_exists(workflow_id):
        raise HTTPException(status_code=404, detail="Workflow not found")

    result = await ExecutionManager.execute_workflow(workflow_id)

    return {
        "message": "Workflow execution started",
        "workflow_id": workflow_id,
        "run_id": result["run_id"],
        "job_ids": result["job_ids"],
    }
