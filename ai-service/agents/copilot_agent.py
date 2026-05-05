"""
CopilotAgent — generates personalized sales co-pilot content for a lead:
  - winning_argument: strategic selling argument based on lead signals
  - draft_message: ready-to-send outreach email
  - confidence: 0.0-1.0

Uses Ollama via OpenAI-compatible API.
llama3.2:3b does not reliably use the tool_calls field (known Ollama issue #13519) —
it outputs tool calls as JSON in the content field instead.
This agent uses structured JSON prompting (no tool use) and extracts the result
from the model's text response.
Model configured via OLLAMA_MODEL env var in docker-compose.yml (default: llama3.2:3b).
"""

import os
import json
import re
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434/v1")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")

client = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")


def _build_prompt(lead: dict) -> str:
    def _val(key: str, fallback: str = "N/A") -> str:
        v = lead.get(key)
        return str(v) if v is not None else fallback

    signals = lead.get("signals", [])
    signals_text = ", ".join(signals) if signals else "none detected"

    return (
        "You are an AI sales co-pilot. Analyze the lead below and respond with ONLY a JSON object.\n\n"
        f"Lead:\n"
        f"- Name: {_val('name')}\n"
        f"- Company: {_val('company')}\n"
        f"- Role: {_val('role')}\n"
        f"- Email: {_val('email')}\n"
        f"- Deal value: {_val('deal_value_display')}\n"
        f"- Intent score: {_val('intent_score')}/100\n"
        f"- Buying signals: {signals_text}\n"
        f"- Last activity: {_val('last_activity_description', 'unknown')}\n\n"
        "Respond with ONLY this JSON (no markdown, no explanation, no extra text):\n"
        "{\n"
        '  "winning_argument": "Strategic reason why this lead should buy NOW. Reference their company, role, and signals. 20-150 words. NOT an email.",\n'
        '  "draft_message": "Hi FirstName,\\n\\nEmail body 50-300 words...\\n\\nBest regards,\\nYour Sales Team",\n'
        '  "confidence": 0.85\n'
        "}\n\n"
        "Rules:\n"
        f"- winning_argument: internal strategic note for the sales rep, NOT an email. "
        f"Explain WHY {_val('name')} at {_val('company')} should buy now. Mention signals. 20-150 words.\n"
        f"- draft_message: outreach EMAIL to send to {_val('name')}. "
        f"Start with 'Hi {_val('name').split()[0]},' — professional, specific, 50-300 words, no placeholders.\n"
        "- confidence: decimal 0.0-1.0\n"
        "- Return ONLY the JSON object, nothing else."
    )


def _extract_json(text: str) -> dict | None:
    """Extrage primul obiect JSON valid care conține winning_argument sau draft_message.
    Gestionează cazul frecvent la llama3.2:3b unde JSON-ul e tăiat (lipsește } final).
    """
    if not text:
        return None

    # 1. Încearcă direct
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # 2. Caută orice bloc care începe cu { și încearcă cu/fără } adăugat
    match = re.search(r'\{.*', text, re.DOTALL)
    if match:
        candidate = match.group().strip()
        # Încearcă as-is
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass
        # Încearcă cu } adăugat (modelul uită closing brace)
        try:
            return json.loads(candidate + "}")
        except json.JSONDecodeError:
            pass
        # Încearcă cu "} adăugat (câmpul string e deschis și lipsesc closing)
        try:
            return json.loads(candidate + '"}\n}')
        except json.JSONDecodeError:
            pass

    return None


def _clean_placeholders(text: str) -> str:
    """Înlocuiește placeholder-ele comune lăsate de model."""
    replacements = {
        "[YOUR NAME]": "Your Sales Team",
        "[Your Name]": "Your Sales Team",
        "[your name]": "Your Sales Team",
        "[YOUR EMAIL]": "sales@company.com",
        "[Your Email]": "sales@company.com",
        "[your email]": "sales@company.com",
        "[NAME]": "",
        "[COMPANY]": "",
        "[INSERT]": "",
        "[DATE]": "",
        "[ROLE]": "",
    }
    for placeholder, replacement in replacements.items():
        text = text.replace(placeholder, replacement)
    return text.strip()


def _parse_result(data: dict) -> dict:
    """Extrage și validează câmpurile din JSON-ul modelului."""
    winning_argument = str(data.get("winning_argument") or "").strip()
    draft_message = str(data.get("draft_message") or "").strip()

    # Dacă draft_message e un dict (model a returnat {"body": "..."})
    raw_dm = data.get("draft_message")
    if isinstance(raw_dm, dict):
        draft_message = (
            raw_dm.get("body") or
            raw_dm.get("message") or
            raw_dm.get("content") or
            ""
        ).strip()

    winning_argument = _clean_placeholders(winning_argument)
    draft_message = _clean_placeholders(draft_message)

    try:
        confidence = max(0.0, min(1.0, float(data.get("confidence", 0.5))))
    except (TypeError, ValueError):
        confidence = 0.5

    return {
        "winning_argument": winning_argument,
        "draft_message": draft_message,
        "confidence": confidence,
    }


def run(lead: dict) -> dict:
    """
    Run the CopilotAgent for a lead, cu până la 3 încercări.

    Args:
        lead: dict with lead fields including signals and intent_score

    Returns:
        dict with: winning_argument, draft_message, confidence
    """
    prompt = _build_prompt(lead)
    result = None

    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model=OLLAMA_MODEL,
                messages=[
                    {"role": "system", "content": "You are a sales co-pilot. Always respond with valid JSON only."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.4,
                max_tokens=1024,
            )
            content = response.choices[0].message.content or ""
            logger.info(f"Attempt {attempt + 1} raw response: {content[:200]}")

            data = _extract_json(content)
            if data:
                parsed = _parse_result(data)
                if parsed["winning_argument"] and parsed["draft_message"]:
                    result = parsed
                    break
                logger.warning(
                    f"Attempt {attempt + 1} incomplete output "
                    f"(wa={bool(parsed['winning_argument'])}, dm={bool(parsed['draft_message'])})"
                )
            else:
                logger.warning(f"Attempt {attempt + 1} could not extract JSON from: {content[:150]}")
        except Exception as e:
            logger.error(f"Ollama call failed (attempt {attempt + 1}): {e}")

    if not result:
        result = {"winning_argument": "", "draft_message": "", "confidence": 0.5}

    return result
