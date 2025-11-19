from enum import Enum
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, Dict, Any
from datetime import datetime
import json


def parse_optional_datetime(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except:
        return None


def parse_json_field(value):
    if value is None or value == "":
        return {}
    if isinstance(value, dict):
        return value
    try:
        return json.loads(value)
    except:
        return {}


class JobStatus(str, Enum):
    PENDING = "PENDING"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    FAILED = "FAILED"
    SUCCESS = "SUCCESS"


class JobInstance(BaseModel):
    model_config = ConfigDict(extra="allow")   # allow fields like progress, progress_message, stage, eta_seconds

    job_id: str
    workflow_id: str
    run_id: str
    branch_id: str
    job_template_id: str
    user_id: str

    status: JobStatus

    created_at: Optional[datetime] = Field(default=None)
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    input_payload: Dict[str, Any] = Field(default_factory=dict)
    output_payload: Optional[Dict[str, Any]] = None

    # --- FIELD VALIDATORS (run before normal parsing) ---

    @field_validator("created_at", "scheduled_at", "started_at", "finished_at", mode="before")
    @classmethod
    def _parse_dt(cls, v):
        return parse_optional_datetime(v)

    @field_validator("input_payload", "output_payload", mode="before")
    @classmethod
    def _parse_json(cls, v):
        return parse_json_field(v)
