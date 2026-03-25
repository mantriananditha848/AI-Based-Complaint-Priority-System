"""
LangGraph workflow for civic complaint analysis.
Orchestrates the Vision Analysis Agent for image processing.
"""

import logging
from typing import TypedDict, Optional, List, Dict, Any
from langgraph.graph import StateGraph, END

from app.agents.vision_agent import get_vision_agent

# Configure logger
logger = logging.getLogger(__name__)


class ComplaintState(TypedDict):
    """State schema for the complaint analysis workflow."""

    # Input
    base64_image: str
    image_path: str

    # Output
    is_valid: bool
    data: List[Dict[str, Any]]
    error: Optional[str]

    # Processing flags
    processed: bool


async def vision_analysis_node(state: ComplaintState) -> ComplaintState:
    """
    Vision Analysis Node - Analyzes the image for civic issues.
    """

    logger.info("-" * 60)
    logger.info("WORKFLOW NODE: vision_analysis - Starting")
    logger.info("-" * 60)

    agent = get_vision_agent()
    logger.info("Retrieved VisionAnalysisAgent instance")

    # Log image preview safely
    image_preview_len = min(50, len(state["base64_image"]))
    logger.debug(
        f"Image preview (first {image_preview_len} chars): "
        f"{state['base64_image'][:image_preview_len]}..."
    )

    logger.info("Calling agent.analyze_image()...")

    result = await agent.analyze_image(
        state["base64_image"],
        state["image_path"]
    )

    # Validate result
    if not isinstance(result, dict):
        logger.error(f"Agent returned non-dict type: {type(result)}")
        logger.error(f"Agent result value: {result}")

        return {
            **state,
            "is_valid": False,
            "data": [],
            "error": f"Vision agent error: {str(result)}",
            "processed": True
        }

    is_valid = result.get("is_valid", False)
    data = result.get("data", [])
    error = result.get("error", None)

    logger.info(
        f"Agent returned: is_valid={is_valid}, "
        f"issues_count={len(data) if isinstance(data, list) else 0}"
    )

    updated_state = {
        **state,
        "is_valid": is_valid,
        "data": data,
        "error": error,
        "processed": True
    }

    logger.info("-" * 60)
    logger.info("WORKFLOW NODE: vision_analysis - Completed")
    logger.info("-" * 60)

    return updated_state


def create_complaint_workflow() -> StateGraph:
    """
    Create and compile the LangGraph workflow for complaint analysis.
    """

    logger.info("Creating complaint analysis workflow...")

    workflow = StateGraph(ComplaintState)

    workflow.add_node("vision_analysis", vision_analysis_node)

    workflow.set_entry_point("vision_analysis")

    workflow.add_edge("vision_analysis", END)

    compiled = workflow.compile()

    logger.info("Complaint analysis workflow compiled successfully")

    return compiled


# Singleton workflow instance
_workflow = None


def get_complaint_workflow():
    """Get or create the singleton complaint workflow instance."""
    global _workflow

    if _workflow is None:
        logger.info("Creating new complaint workflow instance")
        _workflow = create_complaint_workflow()

    return _workflow


async def analyze_complaint_image(base64_image: str, image_path: str) -> Dict[str, Any]:
    """
    Main entry point for analyzing a complaint image.
    """

    logger.info("=" * 70)
    logger.info("LANGGRAPH WORKFLOW - Starting complaint image analysis")
    logger.info("=" * 70)

    workflow = get_complaint_workflow()
    logger.info("Retrieved workflow instance")

    # Initialize workflow state
    initial_state: ComplaintState = {
        "base64_image": base64_image,
        "image_path": image_path,
        "is_valid": False,
        "data": [],
        "error": None,
        "processed": False
    }

    logger.info("Initialized workflow state")

    # Run workflow
    logger.info("Invoking workflow...")
    final_state = await workflow.ainvoke(initial_state)

    logger.info("Workflow execution completed")

    response = {
        "is_valid": final_state.get("is_valid", False),
        "data": final_state.get("data", []),
        "error": final_state.get("error", None)
    }

    logger.info(
        f"Final Result: is_valid={response['is_valid']}, "
        f"issues_count={len(response['data'])}, "
        f"error={response['error']}"
    )

    logger.info("=" * 70)
    logger.info("LANGGRAPH WORKFLOW - Completed")
    logger.info("=" * 70)

    return response