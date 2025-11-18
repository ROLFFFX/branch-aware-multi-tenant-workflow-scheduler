import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME: stre = "BAMT Workflow Scheduler"
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")

settings = Settings()