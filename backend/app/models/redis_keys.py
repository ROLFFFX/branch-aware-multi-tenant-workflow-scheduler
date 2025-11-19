'''
============
Users
============
'''
def users_key() -> str:
    '''
        Set of all registered users. <uuid>
        e.g.:
            SADD users <user_id>
    '''
    return "users"

def user_key(user_id: str) -> str:
    '''
        Hash containing metadata for a specific user.
        e.g.:
            HSET user:<id> || status idle|running
    '''
    return f"user:{user_id}"

def active_users_key() -> str:
    '''
        Set of users currently allowed to run jobs. (max size = 3), <uuid>
        e.g.:
            SADD active_users <user_id>
    '''
    return "active_users"

def user_running_jobs_key(user_id: str) -> str:
    '''
        Key to track how many jobs the user is currently running.
        e.g.:
            INCR user_running_jobs:<id>
    '''
    return f"user_running_jobs:{user_id}"

'''
============
Workflows (dummy node for branches)
============
'''
def workflows_key() -> str:
    '''
        Set of all workflow IDs.
        e.g.:
            SADD workflows <workflow_id>
    '''
    return "workflows"

def workflow_key(workflow_id: str) -> str:
    '''
        Hash containing metadata for a specific workflow.
        e.g.:
            - name
            - owner_user_id
            - entry_branch
    '''
    return f"workflow:{workflow_id}"

def workflow_state_key(workflow_id: str, user_id: str) -> str:
    '''
        Hash containing runtime state of a workflow isntance for a given user.
        e.g.:
            - current_branch
            - current_job_index
            - status
    '''
    return f"workflow:{workflow_id}:state:{user_id}"

'''
============
Branches
============
'''
def workflow_branches_key(workflow_id: str) -> str:
    '''
        Set of branch IDs belonging to a given workflow
        e.g.:
            SADD workflow:<wf_id>:branches <branch_id>
    '''
    return f"workflow:{workflow_id}:branches"

def workflow_branch_key(workflow_id: str, branch_id: str) -> str:
    '''
        Ordered List of job_template_ids for branch
        e.g.:
        RPUSH workflow:<wf_id>:branch:<branch_id> <job_template_id>
    '''
    return f"workflow:{workflow_id}:branch:{branch_id}"

'''
============
Jobs
============
'''
def job_key(job_id: str) -> str:
    return f"job:{job_id}:data"

def workflow_runs_key(workflow_id: str) -> str:
    return f"workflow:{workflow_id}:runs"

def workflow_run_jobs_key(workflow_id: str, run_id: str) -> str:
    return f"workflow:{workflow_id}:run:{run_id}:jobs"

GLOBAL_PENDING_JOBS = "scheduler:pending_jobs"
ACTIVE_USERS_KEY = "scheduler:active_users"
GLOBAL_RUNNING_JOBS = "scheduler:running_jobs"
GLOBAL_JOB_PROGRESS = "scheduler:job_progress"

def user_queue_key(user_id: str) -> str:
    return f"user:{user_id}:queue"

'''
============
Scheduler
============
'''
def scheduler_state_key() -> str:
    return "scheduler:state"

'''
============
Slides (WSI uploads)
============
'''

def user_slides_key(user_id: str) -> str:
    """
    Set of slide_ids uploaded by this user.
    e.g.:
        SADD user:<user_id>:slides <slide_id>
    """
    return f"user:{user_id}:slides"


def slide_key(slide_id: str) -> str:
    """
    Hash containing metadata about a slide.
    e.g.:
        - slide_id
        - user_id
        - slide_path
        - size_bytes
    """
    return f"slide:{slide_id}"


def slide_preview_key(slide_id: str) -> str:
    """
    Optional: path or bytes for a low-resolution JPEG preview.
    e.g.:
        GET slide:<id>:preview
    """
    return f"slide:{slide_id}:preview"

'''
============
Global monitoring
============
'''
def global_running_jobs_key() -> str:
    return "global:running_jobs"   # SET of job_ids currently RUNNING

def global_job_progress_key() -> str:
    return "global:job_progress"   # HASH: job_id -> JSON string

def global_active_users_key() -> str:
    return "global:active_users"   # SET of user_ids currently allowed to run

def global_worker_usage_key() -> str:
    return "global:worker_usage"   # HASH: worker_id -> job_id (or empty)