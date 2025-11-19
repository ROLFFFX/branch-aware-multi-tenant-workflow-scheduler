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