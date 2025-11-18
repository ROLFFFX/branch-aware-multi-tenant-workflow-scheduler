### Backend - BAMT Workflow Scheduler

This backend implements the branch-aware multi-tennat workflow scheduler. It is build with FastAPI, Redis, and Python 3.10.16.

### Prerequisites

- Python 3.10.16
- Redis Server (local or Docker)

### Create & Activate Virtual Environment:

Inside the backend/ directory, execute:

```
python3 -m venv venv
source venv/bin/activate
```

Terminal prompt should now start with (venv).

### Install Dependencies

Install all backend requirements:

```
pip install -r requirements.txt
```

### Start Redis Server

If were to spin up the server locally, execute:

```
redis-server
```

Or, via brew:

```
brew install redis
brew services start redis
redis-cli ping
```

### Run FastAPI Dev Server

```
uvicorn app.main:app --reload
```

You should see:
INFO: Uvicorn running on http://127.0.0.1:8000

### Test Server

visit: http://127.0.0.1:8000/

### Deactivating

If new dependencies were used, freeze before exiting:

```
pip freeze > requirements.txt
```

and then

```
deactivate
```
