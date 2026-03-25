from pydantic import BaseModel
from typing import Optional


class PriorityRequest(BaseModel):
    ward_no: Optional[int] = None
    category: str
    severity_selected: str
    time_selected: str
    optional_text: Optional[str] = ""


class PriorityResponse(BaseModel):
    is_valid: bool
    ward_no: Optional[int]
    category: str
    department: str
    severity_selected: str
    time_selected: str
    optional_text: Optional[str]
    urgency_score: int
    priority_score: int
    priority_label: str
    error: Optional[str] = None
