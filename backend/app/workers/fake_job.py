'''
    A fake job that simply sleeps for 5 seconds, updating progress every 1 second.
'''
import asyncio
from app.workers.registry import register_job
from app.services.job_manager import JobManager

@register_job("fake_sleep")
async def fake_sleep_job(job_id: str, input_payload: dict):
    """
    Demo job that runs 5 seconds total, updating progress every 1 second.
    """

    total_steps = 5
    for step in range(total_steps):
        progress = int((step / total_steps) * 100)

        await JobManager.update_progress(
            job_id=job_id,
            progress=progress,
            message=f"Fake job running... ({step+1}/{total_steps})",
            stage="fake",
        )

        await asyncio.sleep(1)

    await JobManager.update_progress(
        job_id=job_id,
        progress=100,
        message="Fake job completed.",
        stage="fake",
    )

    return {"result": "fake job success!"}
