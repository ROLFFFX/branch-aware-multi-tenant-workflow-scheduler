'''
    Note that upon designing the "branch" or stream of jobs in frontend, we are designing the "Job templates"
    Here we define the mapping between "Job Templates" : Job Instances to be executed by workers
'''

from typing import Callable, Dict

JOB_REGISTRY: Dict[str, Callable] = {}

def register_job(name: str):
    """Decorator to register jobs by name."""
    def decorator(func):
        JOB_REGISTRY[name] = func
        print(f"[JOB_REGISTRY] Registered job: {name}")  # Debugging line
        return func
    return decorator