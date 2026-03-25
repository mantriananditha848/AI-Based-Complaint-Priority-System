"""
Vision Analysis Agent for civic complaint image classification.
Uses local zero-shot image classification for category detection and local YOLO models
for severity estimation.
"""
import base64
import logging
import os
from io import BytesIO
from typing import Any, Dict, Optional, List

from app.utils.severity_rules import override_severity
from app.services.severity_predictor import predict_severity

from PIL import Image
from transformers import pipeline

from app.config.settings import get_settings
from app.api.schemas.complaint import DepartmentType

# Configure logger
logger = logging.getLogger(__name__)

VISION_AGENT_SYSTEM_PROMPT = """
You are an expert AI Vision Analyst for civic infrastructure complaints.

Your task:
1) Validate image quality.
2) Detect civic issues ONLY from the allowed list.
3) Assign severity based on strict rules.
4) Return ONLY valid JSON (no extra text).

----------------------------------------
ALLOWED ISSUE CATEGORIES (choose only from these):
1. Garbage/Waste accumulation
2. Manholes/drainage opening damage
3. Water leakage
4. Drainage overflow
5. Potholes/Road damage
6. Electric wire hazard 
7. Unknown (if not clear)

----------------------------------------
IMAGE VALIDATION:
Return is_valid=false if:
- image is too blurry/dark to identify objects
- image is not related to civic issues
- image does not contain any visible civic problem

----------------------------------------
SEVERITY RULES:
Low:
- small issue, minor impact, localized

Medium:
- clearly visible issue, moderate impact, affects public convenience

High:
- major risk, large area affected, health hazard, unsafe condition

Emergency:
- immediate danger (fire, exposed electric wire, major sewage overflow)

----------------------------------------
OUTPUT JSON FORMAT (STRICT):
Return ONLY JSON exactly in this format:

{
  "is_valid": true,
  "data": [
    {
      "category": "<one allowed category>",
      "severity": "Low/Medium/High/Emergency",
      "suggested_tools": [],
      "safety_equipment": []
    }
  ],
  "error": null
}

If invalid image:
{
  "is_valid": false,
  "data": [],
  "error": "<reason>"
}
"""


class VisionAnalysisAgent:
    """Agent that analyzes civic complaint images using local models."""

    _CLASSIFIER_MODEL = "openai/clip-vit-base-patch32"
    _NO_ISSUE_LABEL = "a clean street or scene with no civic infrastructure issue"
    _CATEGORY_LABELS: Dict[str, str] = {
        "Garbage/Waste accumulation": "a garbage dump, litter pile, or roadside waste accumulation",
        "Manholes/drainage opening damage": "a broken manhole, missing manhole cover, or damaged drainage opening",
        "Water leakage": "water leaking from a pipe, a burst line, or water leakage on a street",
        "Drainage overflow": "a clogged drain, sewage spill, or drainage overflow on a road",
        "Potholes/Road damage": "a pothole, broken road surface, or damaged street",
        "Electric wire hazard": "exposed electric wires, fallen electrical cables, or an electrical hazard on a street",
    }

    # Suggested tools / safety equipment per category
    _TOOLS_MAP: Dict[str, List[str]] = {
        "Garbage/Waste accumulation": ["Broom", "Garbage bags", "Shovel", "Wheelbarrow"],
        "Potholes/Road damage": ["Asphalt patch", "Shovel", "Road roller", "Traffic cones"],
        "Water leakage": ["Pipe wrench", "Sealing tape", "Replacement pipes"],
        "Drainage overflow": ["Drain rods", "High-pressure jet", "Vacuum truck"],
        "Manholes/drainage opening damage": ["Manhole cover", "Crowbar", "Lifting hooks"],
        "Electric wire hazard": ["Insulated gloves", "Wire clippers", "Safety cones"],
    }
    _SAFETY_MAP: Dict[str, List[str]] = {
        "Garbage/Waste accumulation": ["Heavy-duty gloves", "Face mask", "Safety boots"],
        "Potholes/Road damage": ["Helmet", "Reflective vest", "Safety boots"],
        "Water leakage": ["Waterproof gloves", "Rubber boots", "Safety vest"],
        "Drainage overflow": ["Full PPE suit", "Rubber boots", "Face shield"],
        "Manholes/drainage opening damage": ["Safety harness", "Hard hat", "Safety boots"],
        "Electric wire hazard": ["Insulated gloves", "Rubber boots", "Face shield"],
    }

    def __init__(self):
        """Initialize the Vision Analysis Agent with local models."""
        self.settings = get_settings()
        logger.info("Initializing VisionAnalysisAgent (local category classifier + YOLO severity)")
        self._load_category_classifier()
        self._load_yolo_models()
        logger.info("VisionAnalysisAgent initialized")

    def _load_category_classifier(self) -> None:
        """Load the local zero-shot image classifier used for category detection."""
        try:
            self._category_classifier = pipeline(
                task="zero-shot-image-classification",
                model=self._CLASSIFIER_MODEL,
            )
            self._category_classifier_loaded = True
            logger.info("Local image classifier loaded successfully: %s", self._CLASSIFIER_MODEL)
        except Exception as exc:
            logger.error("Failed to load local image classifier: %s", exc)
            self._category_classifier_loaded = False

    def _load_yolo_models(self) -> None:
        """Load the local YOLO models used for severity estimation."""
        try:
            from ultralytics import YOLO
            base = os.path.join(os.path.dirname(__file__), "..", "models")
            self._yolo_garbage = YOLO(os.path.join(base, "best_garbage.pt"))
            self._yolo_road    = YOLO(os.path.join(base, "best_road.pt"))
            self._yolo_water   = YOLO(os.path.join(base, "best_water.pt"))
            self._yolo_loaded  = True
            logger.info("Local YOLO severity models loaded successfully")
        except Exception as exc:
            logger.error("Failed to load YOLO models: %s", exc)
            self._yolo_loaded = False

    def _map_category_to_department(self, category: str) -> str:
        """Map category string to department string."""
        category_mapping = {
            "Garbage/Waste accumulation": DepartmentType.SANITATION.value,
            "Manholes/drainage opening damage": DepartmentType.ROADS_INFRASTRUCTURE.value,
            "Water leakage": DepartmentType.WATER_SUPPLY.value,
            "Drainage overflow": DepartmentType.DRAINAGE.value,
            "Potholes/Road damage": DepartmentType.ROADS_INFRASTRUCTURE.value,
            "Electric wire hazard": DepartmentType.ROADS_INFRASTRUCTURE.value,
        }
        return category_mapping.get(category, "Unknown Department")

    def _classify_category(self, image: Image.Image) -> Dict[str, Any]:
        """Detect the most likely civic issue category using a local zero-shot image classifier."""
        candidate_labels = list(self._CATEGORY_LABELS.values()) + [self._NO_ISSUE_LABEL]

        results = self._category_classifier(image, candidate_labels=candidate_labels)
        if not results:
            return {"category": None, "confidence": 0.0, "raw_label": None}

        best = results[0]
        raw_label = best["label"]
        confidence = float(best["score"])

        if raw_label == self._NO_ISSUE_LABEL:
            return {"category": None, "confidence": confidence, "raw_label": raw_label}

        for category, label in self._CATEGORY_LABELS.items():
            if label == raw_label:
                return {"category": category, "confidence": confidence, "raw_label": raw_label}

        return {"category": None, "confidence": confidence, "raw_label": raw_label}

    async def analyze_image(self, base64_image: str, image_path: str) -> Dict[str, Any]:
        """
        Analyze a civic complaint image using local category detection and YOLO severity models.
        Returns detected issues with category, department, severity, tools and equipment.
        """
        logger.info("=" * 60)
        logger.info("VISION ANALYSIS AGENT - Starting image analysis (local YOLO)")
        logger.info("=" * 60)

        try:
            # --- Decode base64 ---
            b64 = base64_image
            if "," in b64:
                b64 = b64.split(",")[1]
            missing = len(b64) % 4
            if missing:
                b64 += "=" * (4 - missing)

            try:
                image_bytes = base64.b64decode(b64)
            except Exception as exc:
                return {"is_valid": False, "data": [], "error": f"Invalid base64 encoding: {exc}"}

            try:
                image = Image.open(BytesIO(image_bytes))
                image.verify()          # raises on corrupt/non-image data
                image = Image.open(BytesIO(image_bytes))   # re-open after verify
                logger.info("Image validated: %s %s %s", image.format, image.size, image.mode)
            except Exception as exc:
                return {"is_valid": False, "data": [], "error": f"Cannot identify image file: {exc}"}

            if not self._category_classifier_loaded:
                return {"is_valid": False, "data": [], "error": "Local image classifier failed to load at startup"}

            category_result = self._classify_category(image.convert("RGB"))
            category = category_result["category"]
            confidence = category_result["confidence"]

            logger.info(
                "Category classifier result: category=%s raw_label=%s confidence=%.3f",
                category,
                category_result["raw_label"],
                confidence,
            )

            if category is None or confidence < 0.22:
                return {
                    "is_valid": False,
                    "data": [],
                    "error": "Image does not appear to contain a recognizable civic issue"
                }

            if not self._yolo_loaded:
                return {"is_valid": False, "data": [], "error": "Local YOLO severity models failed to load at startup"}

            raw_severity = predict_severity(image_path, category)
            severity = override_severity(category, raw_severity)
            department = self._map_category_to_department(category)
            suggested_tools = self._TOOLS_MAP.get(category, [])
            safety_equipment = self._SAFETY_MAP.get(category, [])

            return {
                "is_valid": True,
                "data": [{
                    "category":         category,
                    "department":       department,
                    "severity":         severity,
                    "suggested_tools":  suggested_tools,
                    "safety_equipment": safety_equipment,
                }],
                "error": None,
            }

        except Exception as exc:
            logger.exception("Unexpected error in analyze_image")
            return {"is_valid": False, "data": [], "error": f"Image analysis failed: {exc}"}


# Singleton instance
_vision_agent: Optional[VisionAnalysisAgent] = None


def get_vision_agent() -> VisionAnalysisAgent:
    """Get or create singleton Vision Analysis Agent instance."""
    global _vision_agent
    if _vision_agent is None:
        logger.info("Creating new VisionAnalysisAgent instance")
        _vision_agent = VisionAnalysisAgent()
    return _vision_agent