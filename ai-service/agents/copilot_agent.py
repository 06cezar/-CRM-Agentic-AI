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
    first_name = _val("name").split()[0]

    try:
        score = int(lead.get("intent_score") or 0)
    except (TypeError, ValueError):
        score = 0

    # Tier-based instructions — tone and strategy vary by intent score
    # NOTE: scorul numeric NU apare în prompt — modelul îl copia literal în argumente.
    # Folosim doar descriptori acționabili (urgency, barriers etc.)
    if score >= 80:
        tier = "HOT"
        tier_descriptor = "strong buying intent, urgent, ready to close"
        argument_instruction = (
            "Write a CLOSING argument for the sales rep: explain the specific urgency "
            "and business risk of NOT acting now. Reference their signals and last activity. "
            "Use language like 'urgent window', 'momentum', 'competitive risk'. "
            "Do NOT mention any numeric score. 20-150 words."
        )
        email_instruction = (
            "Write a CLOSING email: acknowledge their recent strong signals by name "
            "(e.g. the demo request, the NDA, the on-site visit), create urgency around "
            "timing, propose one concrete next step (call, contract, demo date). "
            "Confident and direct tone. 50-200 words."
        )
        confidence_hint = "0.88"
    elif score >= 50:
        tier = "WARM"
        tier_descriptor = "moderate interest, engaged but not yet committed"
        argument_instruction = (
            "Write a NURTURING argument for the sales rep: explain what specific value "
            "they would gain by moving forward now versus waiting. Reference their engagement "
            "signals by name. Focus on value, differentiation. "
            "Do NOT mention any numeric score. 20-150 words."
        )
        email_instruction = (
            "Write a NURTURING email: open by referencing their specific engagement "
            "(name the webinar, the pricing page visits, the intro call — whatever applies). "
            "Offer a relevant insight or case study, propose a low-friction next step. "
            "Helpful, consultative tone. 50-200 words."
        )
        confidence_hint = "0.72"
    elif score >= 20:
        tier = "COLD"
        tier_descriptor = "low engagement, clear objection or barrier present"
        argument_instruction = (
            "Write a RE-ENGAGEMENT argument for the sales rep: identify the specific barrier "
            "(competitor lock-in, bad experience, budget freeze, silence) and suggest ONE "
            "realistic way to address it. Be honest — do NOT oversell. "
            "Do NOT mention any numeric score. 20-150 words."
        )
        email_instruction = (
            "Write a RE-ENGAGEMENT email: acknowledge the specific obstacle or silence directly "
            "(don't pretend everything is fine). Ask ONE open question to understand if their "
            "situation has changed. Short, low pressure, 40-100 words. Do NOT pitch features."
        )
        confidence_hint = "0.45"
    else:
        tier = "LOST"
        tier_descriptor = "negative signals, effectively disengaged or hostile"
        argument_instruction = (
            "Write a WIN-BACK argument for the sales rep: given the negative signals and last "
            "activity, suggest the ONLY realistic path to re-open this deal — or state honestly "
            "that there is no realistic path right now. "
            "Do NOT mention any numeric score. 20-150 words."
        )
        email_instruction = (
            "Write a WIN-BACK email: be very brief, acknowledge the negative experience or "
            "long silence directly, do NOT pitch features or benefits. "
            "Ask one simple human question to see if circumstances have changed. "
            "Humble, no-pressure tone. Under 80 words."
        )
        confidence_hint = "0.25"

    return (
        f"You are an AI sales co-pilot. Lead tier: {tier} ({tier_descriptor}). "
        f"Respond with ONLY a JSON object.\n\n"
        f"Lead:\n"
        f"- Name: {_val('name')}\n"
        f"- Company: {_val('company')}\n"
        f"- Role: {_val('role')}\n"
        f"- Deal value: {_val('deal_value_display')}\n"
        f"- Engagement tier: {tier}\n"
        f"- Signals: {signals_text}\n"
        f"- Last activity: {_val('last_activity_description', 'unknown')}\n\n"
        "Respond with ONLY this JSON (no markdown, no explanation, no extra text):\n"
        "{\n"
        '  "winning_argument": "...",\n'
        '  "draft_message": "...",\n'
        f'  "confidence": {confidence_hint}\n'
        "}\n\n"
        "Rules:\n"
        f"- winning_argument: {argument_instruction}\n"
        f"- draft_message: Start with 'Hi {first_name},' — {email_instruction} No placeholders.\n"
        "- confidence: decimal 0.0-1.0 reflecting how confident you are in this strategy\n"
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
