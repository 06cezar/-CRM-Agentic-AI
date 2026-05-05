"""
LeadResearchAgent — analyzes a lead and returns:
  - intent_score (0-100)
  - signals (detected buying signals)
  - summary (human-readable description)
  - confidence (0.0-1.0)

Uses Ollama via OpenAI-compatible API.
llama3.2:3b does not reliably follow tool parameter schemas, so this agent
uses structured JSON prompting (no tool use) and extracts the result from
the model's text response.
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

    return (
        "You are a sales analyst. Analyze the lead below and respond with ONLY a JSON object.\n\n"
        f"Lead:\n"
        f"- Name: {_val('name')}\n"
        f"- Company: {_val('company')}\n"
        f"- Role: {_val('role')}\n"
        f"- Deal value: {_val('deal_value_display')}\n"
        f"- Last activity: {_val('last_activity_description', 'unknown')}\n\n"
        "Respond with ONLY this JSON (no markdown, no explanation, no extra text):\n"
        "{\n"
        '  "signals": ["signal1", "signal2"],\n'
        '  "intent_score": 75,\n'
        '  "reasoning": "brief explanation",\n'
        '  "confidence": 0.8\n'
        "}\n\n"
        "Rules:\n"
        "- signals: 2-4 short buying signals (e.g. 'Demo Requested', 'Budget Approved', "
        "'Decision Maker', 'Competitor Churn', 'Actively Researching', 'Trial Active')\n"
        "- intent_score: integer 0-100 (80-100=hot ready to buy, 60-79=warm, 0-59=cool)\n"
        "- confidence: decimal 0.0-1.0\n"
        "- Return ONLY the JSON object, nothing else."
    )


def _extract_json(text: str) -> dict | None:
    """Extrage primul obiect JSON valid din răspunsul modelului."""
    if not text:
        return None
    # Încearcă direct dacă textul e JSON pur
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass
    # Caută primul bloc {...} în text (modelul uneori adaugă explicații înainte/după)
    match = re.search(r'\{[^{}]*"intent_score"[^{}]*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    # Caută orice bloc JSON valid
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return None


def _parse_result(data: dict) -> dict:
    """Extrage și validează câmpurile din JSON-ul modelului."""
    # signals — acceptă list sau string CSV
    raw_signals = data.get("signals", [])
    if isinstance(raw_signals, list):
        signals = [str(s).strip() for s in raw_signals if str(s).strip() and not str(s).startswith("{")]
    elif isinstance(raw_signals, str):
        signals = [s.strip() for s in raw_signals.split(",") if s.strip()]
    else:
        signals = []

    # intent_score
    try:
        intent_score = max(0, min(100, int(data.get("intent_score", 50))))
    except (TypeError, ValueError):
        intent_score = 50

    # confidence
    try:
        confidence = max(0.0, min(1.0, float(data.get("confidence", 0.5))))
    except (TypeError, ValueError):
        confidence = 0.5

    reasoning = str(data.get("reasoning", "")).strip()

    return {
        "signals": signals,
        "intent_score": intent_score,
        "confidence": confidence,
        "reasoning": reasoning,
    }


def run(lead: dict) -> dict:
    """
    Run the LeadResearchAgent for a lead, cu până la 3 încercări.

    Args:
        lead: dict with lead fields (name, company, role, etc.)

    Returns:
        dict with: intent_score, signals, summary, confidence
    """
    prompt = _build_prompt(lead)
    result = None

    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model=OLLAMA_MODEL,
                messages=[
                    {"role": "system", "content": "You are a sales analyst. Always respond with valid JSON only."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
            )
            content = response.choices[0].message.content or ""
            logger.info(f"Attempt {attempt + 1} raw response: {content[:200]}")

            data = _extract_json(content)
            if data:
                parsed = _parse_result(data)
                if parsed["intent_score"] != 50 or parsed["signals"]:
                    result = parsed
                    break
                # Scorul e 50 și no signals — poate fi corect pentru lead rece,
                # dar acceptăm doar dacă avem reasoning
                if parsed["reasoning"]:
                    result = parsed
                    break
            logger.warning(f"Attempt {attempt + 1} could not extract valid JSON from: {content[:100]}")
        except Exception as e:
            logger.error(f"Ollama call failed (attempt {attempt + 1}): {e}")

    if not result:
        result = {"signals": [], "intent_score": 50, "reasoning": "", "confidence": 0.5}

    # ── Build summary ────────────────────────────────────────────────────────
    signals_text = ", ".join(result["signals"]) if result["signals"] else "no signals detected"
    summary = (
        f"Researched prospect {lead.get('name', 'N/A')} "
        f"({lead.get('company', 'N/A')}) — "
        f"score: {result['intent_score']}, "
        f"signals: {signals_text}. "
        f"{result['reasoning']}"
    ).strip()

    return {
        "intent_score": result["intent_score"],
        "signals": result["signals"],
        "summary": summary,
        "confidence": result["confidence"],
    }
