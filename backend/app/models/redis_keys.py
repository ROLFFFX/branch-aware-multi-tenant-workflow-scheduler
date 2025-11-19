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