"""
API routes for complaint analysis.
"""
from app.api.schemas.combined import CombinedComplaintResponse
import logging
import base64
from fastapi import APIRouter, UploadFile, File, Form

from app.api.schemas.complaint import (
    ComplaintAnalysisResponseWithWard,
    DetectedIssue
)

# ✅ NEW imports for prioritization
from app.api.schemas.priority import PriorityRequest, PriorityResponse
from app.utils.priority_engine import compute_scores
from app.agents.vision_agent import VisionAnalysisAgent

from app.agents.workflow import analyze_complaint_image
from app.services.ward_mapper import get_ward_mapper

# Configure logger
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analyze", tags=["Complaint Analysis"])

# ✅ NEW: Create once and reuse
vision_agent = VisionAnalysisAgent()


@router.post(
    "/complaint",
    response_model=ComplaintAnalysisResponseWithWard,
    summary="Analyze a civic complaint image",
    description="Upload an image file of a civic issue to get automatic categorization."
)
async def analyze_complaint(
    image: UploadFile = File(..., description="Image file (PNG, JPG, JPEG)"),
    street: str = Form(..., description="Street name"),
    area: str = Form(..., description="Area/locality"),
    postal_code: str = Form(..., description="Postal code"),
    latitude: float = Form(..., description="Latitude coordinate"),
    longitude: float = Form(..., description="Longitude coordinate")
) -> ComplaintAnalysisResponseWithWard:

    logger.info("=" * 80)
    logger.info("API REQUEST - POST /api/v1/analyze/complaint")
    logger.info("=" * 80)

    try:
        # -----------------------------
        # Read uploaded image
        # -----------------------------
        logger.info("Reading uploaded image file...")
        image_bytes = await image.read()

        logger.info(f"Image size: {len(image_bytes)} bytes (~{len(image_bytes) / 1024:.2f} KB)")

        # -----------------------------
        # Save temporary image for YOLO
        # -----------------------------
        import tempfile
        import os

        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
        temp_file.write(image_bytes)
        temp_file.close()

        image_path = temp_file.name
        logger.info(f"Temporary image saved at: {image_path}")

        # -----------------------------
        # Convert image to base64
        # -----------------------------
        base64_image = base64.b64encode(image_bytes).decode("utf-8")

        logger.info("Calling analyze_complaint_image workflow...")

        result = await analyze_complaint_image(
            base64_image,
            image_path=image_path
        )

        # -----------------------------
        # Validate workflow result
        # -----------------------------
        if not isinstance(result, dict):
            logger.error(f"Unexpected workflow result: {result}")

            os.remove(image_path)

            return ComplaintAnalysisResponseWithWard(
                is_valid=False,
                data=[],
                ward_no=None,
                error="Workflow returned invalid result"
            )

        is_valid = result.get("is_valid", False)
        data = result.get("data", [])
        error = result.get("error", None)

        detected_issues = []

        # -----------------------------
        # Convert issues to schema
        # -----------------------------
        if isinstance(data, list):
            for issue in data:

                if isinstance(issue, str):
                    issue = {"category": issue}

                detected_issues.append(
                    DetectedIssue(
                        category=issue.get("category", "Unknown"),
                        department=issue.get("department", "General"),
                        severity=issue.get("severity", "Medium"),
                        suggested_tools=issue.get("suggested_tools", []),
                        safety_equipment=issue.get("safety_equipment", [])
                    )
                )

        # -----------------------------
        # Ward mapping
        # -----------------------------
        ward_no = None

        if is_valid:
            try:
                ward_mapper = get_ward_mapper()
                ward_data = ward_mapper.find_ward(latitude, longitude)

                if ward_data:
                    ward_no = ward_data.get("ward_no")
                    logger.info(f"Ward found: {ward_no}")

            except Exception as e:
                logger.error(f"Ward mapping failed: {str(e)}")

        response = ComplaintAnalysisResponseWithWard(
            is_valid=is_valid,
            data=detected_issues,
            ward_no=ward_no,
            error=error
        )

        # -----------------------------
        # Cleanup temp file
        # -----------------------------
        os.remove(image_path)

        logger.info("Complaint analysis completed successfully")

        return response

    except Exception as e:

        logger.error(
            f"Exception during complaint analysis: {str(e)}",
            exc_info=True
        )

        return ComplaintAnalysisResponseWithWard(
            is_valid=False,
            data=[],
            ward_no=None,
            error=f"Internal processing error: {str(e)}"
        )


# =============================================================================
# ✅ NEW ENDPOINT: DROPDOWN BASED PRIORITIZATION (NO EMOTION / NO HF)
# =============================================================================
@router.post(
    "/prioritize",
    response_model=PriorityResponse,
    summary="Prioritize complaint using dropdown inputs",
    description="Computes priority score using category + severity + time delay (no AI)."
)
async def prioritize_complaint(req: PriorityRequest) -> PriorityResponse:
    """Prioritize complaint based on dropdown selections."""
    try:
        urgency_score, priority_score, label = compute_scores(
            category=req.category,
            severity_selected=req.severity_selected,
            time_selected=req.time_selected
        )

        department = vision_agent._map_category_to_department(req.category)

        return PriorityResponse(
            is_valid=True,
            ward_no=req.ward_no,
            category=req.category,
            department=department,
            severity_selected=req.severity_selected,
            time_selected=req.time_selected,
            optional_text=req.optional_text,
            urgency_score=urgency_score,
            priority_score=priority_score,
            priority_label=label,
            error=None
        )

    except Exception as e:
        return PriorityResponse(
            is_valid=False,
            ward_no=req.ward_no,
            category=req.category,
            department="Unknown",
            severity_selected=req.severity_selected,
            time_selected=req.time_selected,
            optional_text=req.optional_text,
            urgency_score=0,
            priority_score=0,
            priority_label="Low",
            error=str(e)
        )


# =============================================================================
# ✅ NEW ENDPOINT: COMBINED ANALYSIS + PRIORITIZATION
# =============================================================================
@router.post(
    "/combined",
    response_model=CombinedComplaintResponse,
    summary="Analyze image + auto-prioritize complaint",
    description="Uploads complaint image, detects issues, maps ward, and computes priority score using category + model severity."
)
async def analyze_and_prioritize(
    image: UploadFile = File(..., description="Image file (PNG, JPG, JPEG)"),
    street: str = Form(..., description="Street name"),
    area: str = Form(..., description="Area/locality"),
    postal_code: str = Form(..., description="Postal code"),
    latitude: float = Form(..., description="Latitude coordinate"),
    longitude: float = Form(..., description="Longitude coordinate"),
):

    try:
        import tempfile
        import os

        # -----------------------------
        # Read uploaded image
        # -----------------------------
        image_bytes = await image.read()

        # -----------------------------
        # Save temporary image for YOLO
        # -----------------------------
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
        temp_file.write(image_bytes)
        temp_file.close()

        image_path = temp_file.name

        # -----------------------------
        # Convert to base64 for vision model
        # -----------------------------
        base64_image = base64.b64encode(image_bytes).decode("utf-8")

        # -----------------------------
        # Run AI workflow
        # -----------------------------
        result = await analyze_complaint_image(
            base64_image,
            image_path=image_path
        )

        if not isinstance(result, dict):

            os.remove(image_path)

            return CombinedComplaintResponse(
                is_valid=False,
                ward_no=None,
                detected_issues=[],
                urgency_score=0,
                priority_score=0,
                priority_label="Low",
                error="Image analysis failed"
            )

        is_valid = result.get("is_valid", False)
        data = result.get("data", [])
        error = result.get("error", None)

        detected_issues = []

        if isinstance(data, list):
            for issue in data:

                if isinstance(issue, str):
                    issue = {"category": issue}

                detected_issues.append(
                    DetectedIssue(
                        category=issue.get("category", "Unknown"),
                        department=issue.get("department", "General"),
                        severity=issue.get("severity", "Medium"),
                        suggested_tools=issue.get("suggested_tools", []),
                        safety_equipment=issue.get("safety_equipment", [])
                    )
                )

        # -----------------------------
        # Ward Mapping
        # -----------------------------
        ward_no = None

        if is_valid:
            ward_mapper = get_ward_mapper()
            ward_data = ward_mapper.find_ward(latitude, longitude)

            if ward_data:
                ward_no = ward_data.get("ward_no")

        # -----------------------------
        # Use first issue for priority
        # -----------------------------
        if detected_issues:
            category_used = detected_issues[0].category
            severity_used = detected_issues[0].severity
        else:
            category_used = "Unknown"
            severity_used = "Medium"

        department = vision_agent._map_category_to_department(category_used)

        # -----------------------------
        # Compute priority score
        # -----------------------------
        urgency_score, priority_score, label = compute_scores(
            category=category_used,
            severity=severity_used
        )

        # -----------------------------
        # Cleanup temp file
        # -----------------------------
        os.remove(image_path)

        return CombinedComplaintResponse(
            is_valid=is_valid,
            ward_no=ward_no,
            detected_issues=detected_issues,
            urgency_score=urgency_score,
            priority_score=priority_score,
            priority_label=label,
            error=error
        )

    except Exception as e:

        return CombinedComplaintResponse(
            is_valid=False,
            ward_no=None,
            detected_issues=[],
            urgency_score=0,
            priority_score=0,
            priority_label="Low",
            error=str(e)
        )

@router.get(
    "/health",
    summary="Health check for the analysis service",
    description="Returns the health status of the analysis service."
)
async def health_check():
    """Health check endpoint for the analysis service."""
    logger.debug("Health check endpoint called")
    return {"status": "healthy", "service": "complaint-analysis"}