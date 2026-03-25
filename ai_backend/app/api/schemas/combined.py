from pydantic import BaseModel
from typing import Optional, List
from app.api.schemas.complaint import DetectedIssue


class CombinedComplaintResponse(BaseModel):
    is_valid: bool
    ward_no: Optional[int]
    detected_issues: List[DetectedIssue]

    urgency_score: int
    priority_score: int
    priority_label: str

    error: Optional[str] = None
