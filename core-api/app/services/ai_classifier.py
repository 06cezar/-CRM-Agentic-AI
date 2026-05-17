import httpx
import json
import logging
from pydantic import BaseModel
from app.config import settings

logger = logging.getLogger(__name__)

class EmailClassificationResult(BaseModel):
    is_business_related: bool
    is_potential_lead: bool
    is_worth_saving: bool
    confidence_score: int  # 1-100
    reasoning: str

async def classify_incoming_email(subject: str, body: str) -> EmailClassificationResult:
    """
    Uses Ollama to classify if an incoming email is a valuable B2B lead.
    Instructs the model to act as a strict SDR and evaluate the content.
    """
    prompt = f"""
    You are a strict B2B Sales Development Representative. 
    Evaluate the following email to determine if it's a legitimate business inquiry, a reply from a prospect, or a valuable lead.
    Reject newsletters, spam, marketing blasts, and personal chatter.
    
    Email Subject: {subject}
    Email Body: {body}
    
    Respond ONLY with a JSON object following this schema:
    {{
        "is_business_related": boolean,
        "is_potential_lead": boolean,
        "is_worth_saving": boolean,
        "confidence_score": integer (1-100),
        "reasoning": "short explanation of the decision"
    }}
    """
    
    url = f"{settings.ollama_base_url}/api/generate"
    payload = {
        "model": settings.email_classifier_model,
        "prompt": prompt,
        "stream": False,
        "format": "json"
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            result_data = response.json()
            
            # Ollama returns the generated text in the 'response' field when using /api/generate
            generated_text = result_data.get("response", "")
            classification_dict = json.loads(generated_text)
            
            return EmailClassificationResult(**classification_dict)
            
    except Exception as e:
        logger.error(f"Ollama classification error: {str(e)}")
        # Default to saving if AI service goes down or returns invalid JSON
        return EmailClassificationResult(
            is_business_related=True,
            is_potential_lead=True,
            is_worth_saving=True,
            confidence_score=0,
            reasoning=f"AI Classification failed (defaulting to save): {str(e)}"
        )
