"""
Work Verification Agent for comparing before/after images.
Uses Hugging Face Inference API to verify if contractor completed the work.
"""
import json
import logging
import re
from typing import Any, Dict, Optional

from huggingface_hub import InferenceClient

from app.config.settings import get_settings

# Configure logger
logger = logging.getLogger(__name__)


# Work Verification Agent System Prompt
VERIFICATION_AGENT_SYSTEM_PROMPT = """You are an expert AI Work Verification Analyst specialized in comparing before and after images of civic infrastructure issues to determine if the assigned work has been completed.

## YOUR TASK:

You will receive TWO images and a CATEGORY:
1. **BEFORE IMAGE**: The original complaint image showing the civic issue
2. **AFTER IMAGE**: The image taken by the contractor after completing the work
3. **CATEGORY**: The type of issue that was reported (e.g., "Garbage/Waste accumulation")

## YOUR RESPONSIBILITIES:

1. **Analyze the BEFORE image**: Identify the civic issue based on the provided category
2. **Analyze the AFTER image**: Check if the issue has been resolved
3. **Compare both images**: Determine if the work has been completed

## CATEGORY-SPECIFIC VERIFICATION CRITERIA:

### Garbage/Waste accumulation
- COMPLETED: Area is clean, garbage/waste has been removed, no visible litter or waste piles
- NOT COMPLETED: Garbage/waste is still visible, area is not clean

### Manholes/drainage opening damage
- COMPLETED: Manhole cover is properly installed, no damage visible, cover is secure and level
- NOT COMPLETED: Cover is still missing, damaged, cracked, or improperly placed

### Water leakage
- COMPLETED: No visible water leaking, pipes appear repaired, no wet patches from active leaks
- NOT COMPLETED: Water still leaking, wet patches visible, pipe damage still present

### Drainage overflow
- COMPLETED: Drainage is clear, no overflow, no water accumulation, drain is functioning
- NOT COMPLETED: Drainage still overflowing, water still accumulated, drain still blocked

## OUTPUT FORMAT:
You MUST respond with ONLY a valid JSON object in this exact format, no additional text:

If work is COMPLETED:
```json
{
  "is_completed": true,
  "error": null
}
```

If work is NOT COMPLETED:
```json
{
  "is_completed": false,
  "error": null
}
```

If there's an ERROR (e.g., cannot analyze images, images are unclear):
```json
{
  "is_completed": false,
  "error": "<specific error message>"
}
```

IMPORTANT:
- Respond with ONLY the JSON object, no markdown code blocks, no explanations.
- Focus on whether the SPECIFIC issue (category) has been resolved.
- If you cannot clearly determine completion, return is_completed: false."""


class WorkVerificationAgent:
    """Agent that verifies work completion by comparing before/after images."""
    
    def __init__(self):
        """Initialize the Work Verification Agent with Hugging Face Inference API."""
        settings = get_settings()
        logger.info(f"Initializing WorkVerificationAgent with model: {settings.MODEL_NAME}")
        
        # Use Inference API (no download)
        self.client = InferenceClient(token=settings.HUGGINGFACE_API_KEY)
        self.model_name = settings.MODEL_NAME
        logger.info("WorkVerificationAgent initialized with Inference API")
    
    def _parse_base64_image(self,  base64_string:str, image_label: str) -> str:
        """Parse base64 image string."""
        if "," in base64_string:
            base64_string = base64_string.split(",")[1]
            logger.debug(f"Removed data URL prefix from {image_label}")
        
        image_size_bytes = len(base64_string) * 3 / 4
        logger.info(f"Processing {image_label} - Approximate size: {image_size_bytes / 1024:.2f} KB")
        
        return base64_string
    
    def _extract_json_from_response(self, response_text: str) -> Dict[str, Any]:
        """Extract JSON from model response."""
        text = response_text.strip()
        logger.debug(f"Raw model response (first 500 chars): {text[:500]}...")
        
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        
        if text.endswith("```"):
            text = text[:-3]
        
        text = text.strip()
        
        try:
            parsed = json.loads(text)
            logger.debug("Successfully parsed JSON from response")
            return parsed
        except json.JSONDecodeError as e:
            logger.warning(f"Initial JSON parse failed: {e}. Attempting regex extraction...")
            json_match = re.search(r'\{[\s\S]*\}', text)
            if json_match:
                try:
                    parsed = json.loads(json_match.group())
                    logger.debug("Successfully extracted JSON using regex")
                    return parsed
                except json.JSONDecodeError:
                    pass
            logger.error(f"Failed to parse JSON response: {e}")
            raise ValueError(f"Failed to parse JSON response: {e}")
    
    # ...existing code...

    async def verify_completion(
        self, 
        before_image: str, 
        after_image: str, 
        category: str
    ) -> Dict[str, Any]:
        """
        Verify if work has been completed by comparing before/after images.
        """
        logger.info("=" * 60)
        logger.info("WORK VERIFICATION AGENT - Starting verification")
        logger.info("=" * 60)
        logger.info(f"Category to verify: {category}")
        
        try:
            logger.info("Step 1: Parsing before image...")
            before_image_data = self._parse_base64_image(before_image, "BEFORE image")
            before_url = f"data:image/png;base64,{before_image_data}"
            
            logger.info("Step 2: Parsing after image...")
            after_image_data = self._parse_base64_image(after_image, "AFTER image")
            after_url = f"data:image/png;base64,{after_image_data}"
            
            logger.info("Step 3: Creating chat messages...")
            messages = [
                {"role": "system", "content": VERIFICATION_AGENT_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"Category: {category}. Compare BEFORE and AFTER images. Return JSON only."},
                        {"type": "image_url", "image_url": {"url": before_url}},
                        {"type": "image_url", "image_url": {"url": after_url}},
                    ],
                },
            ]
            
            logger.info("Step 4: Invoking Hugging Face Inference API (chat_completion)...")
            response = self.client.chat_completion(
                model=self.model_name,
                messages=messages,
                max_tokens=2048
            )
            response_text = response.choices[0].message.content
            logger.info("Step 4: Hugging Face response received")
            
            logger.info("Step 5: Parsing JSON response...")
            parsed_response = self._extract_json_from_response(response_text)
            logger.info(f"Step 5: Parsed response: {json.dumps(parsed_response, indent=2)}")
            
            is_completed = parsed_response.get("is_completed", False)
            error = parsed_response.get("error", None)
            
            return {
                "is_completed": is_completed,
                "error": error
            }
            
        except ValueError as e:
            logger.error(f"ValueError during verification: {str(e)}")
            return {
                "is_completed": False,
                "error": f"Failed to parse model response: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Exception during verification: {str(e)}", exc_info=True)
            return {
                "is_completed": False,
                "error": f"Verification failed: {str(e)}"
            }

# ...existing code...


# Singleton instance
_verification_agent: Optional[WorkVerificationAgent] = None


def get_verification_agent() -> WorkVerificationAgent:
    """Get or create singleton Work Verification Agent instance."""
    global _verification_agent
    if _verification_agent is None:
        logger.info("Creating new WorkVerificationAgent instance")
        _verification_agent = WorkVerificationAgent()
    return _verification_agent