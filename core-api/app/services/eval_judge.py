import json
import httpx
import os
import structlog
from typing import Optional

logger = structlog.get_logger()

OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434/v1")
# We use a larger model for the judge
JUDGE_MODEL = os.getenv("JUDGE_MODEL", "llama3.1:8b") 
PRODUCTION_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")

async def run_llm_judge(original_email: str, production_ai_result: dict, lead_id: Optional[int] = None):
    """
    Asynchronously evaluates the production AI decision using a larger judge model.
    """
    try:
        judge_prompt = f"""
        You are an expert Sales Operations Analyst grading an AI classifier.
        
        CRITERIA:
        1. Is it a legitimate B2B business inquiry (demo request, pricing, technical question)?
        2. Is it spam, marketing, or personal?
        
        PRODUCTION AI DECISION: {json.dumps(production_ai_result)}
        EMAIL BODY: {original_email}
        
        TASK: Grade the production AI's decision on a scale of 1 to 5.
        1: Completely wrong (classified spam as lead or vice versa)
        3: Ambiguous or missed nuance
        5: Perfectly correct
        
        Respond ONLY with a JSON object: {{"score": <int>, "reasoning": "<string>"}}
        """

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{OLLAMA_URL}/chat/completions",
                json={
                    "model": JUDGE_MODEL,
                    "messages": [{"role": "user", "content": judge_prompt}],
                    "response_format": {"type": "json_object"},
                    "temperature": 0
                }
            )
            response.raise_for_status()
            result = response.json()
            judge_output = json.loads(result['choices'][0]['message']['content'])
            
            score = judge_output.get("score")
            
            logger.info(
                "llm_judge_score",
                original_model=PRODUCTION_MODEL,
                judge_model=JUDGE_MODEL,
                score=score,
                lead_id=lead_id,
                reasoning=judge_output.get("reasoning")
            )
            
            return score

    except Exception as e:
        logger.error("llm_judge_failed", error=str(e), lead_id=lead_id)
        return None
