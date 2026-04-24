"""
LeadResearchAgent — analizează un lead și returnează:
  - intent_score (0-100)
  - signals (buying signals detectate)
  - summary (descriere human-readable)
  - confidence (0.0-1.0)

Folosește Ollama via OpenAI-compatible API cu tool use.
Model configurat prin env var OLLAMA_MODEL (default: llama3.1:8b).
"""

import os
import json
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)

# ── Config — schimbă OLLAMA_MODEL în .env sau docker-compose ─────────────────
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434/v1")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
MAX_RETRIES = 2

client = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")

# ── Tool definitions ──────────────────────────────────────────────────────────
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "extract_signals",
            "description": (
                "Analizează profilul unui lead și extrage buying signals — "
                "indicii că lead-ul este pregătit să cumpere acum. "
                "Exemple: 'Budget Approved', 'Decision Maker', 'Competitor Churn', "
                "'Demo Requested', 'Actively Researching', 'Q1 Budget', 'Fast-Mover'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "signals": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Lista de buying signals detectate (2-4 semnale scurte).",
                    }
                },
                "required": ["signals"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "score_intent",
            "description": (
                "Pe baza semnalelor și profilului lead-ului, calculează un scor "
                "de intenție de cumpărare între 0 și 100. "
                "80-100 = hot (gata să cumpere), 60-79 = warm (interesat), "
                "0-59 = cool (necesită nurturing)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "intent_score": {
                        "type": "integer",
                        "description": "Scor de intenție între 0 și 100.",
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Explicație scurtă (1-2 propoziții) pentru scorul acordat.",
                    },
                    "confidence": {
                        "type": "number",
                        "description": "Nivelul de încredere în scor, între 0.0 și 1.0.",
                    },
                },
                "required": ["intent_score", "reasoning", "confidence"],
            },
        },
    },
]


def _build_system_prompt() -> str:
    return (
        "Ești un agent AI specializat în analiza lead-urilor de vânzări. "
        "Misiunea ta: analizează profilul unui lead și determină cât de pregătit este să cumpere. "
        "Folosește tool-urile disponibile în ordine: mai întâi extract_signals, apoi score_intent. "
        "Fii concis și practic."
    )


def _build_user_prompt(lead: dict) -> str:
    def _val(key: str, fallback: str = "N/A") -> str:
        v = lead.get(key)
        return str(v) if v is not None else fallback

    return (
        f"Analizează acest lead:\n\n"
        f"Nume: {_val('name')}\n"
        f"Companie: {_val('company')}\n"
        f"Rol: {_val('role')}\n"
        f"Email: {_val('email')}\n"
        f"Valoare deal: {_val('deal_value_display')}\n"
        f"Ultima activitate: {_val('last_activity_description', 'necunoscută')}\n\n"
        f"Folosește tool-urile pentru a extrage semnalele de cumpărare și a calcula scorul de intenție."
    )


def _extract_list(arguments: dict, key: str) -> list:
    """Extrage o listă din arguments, cu fallback pentru modele care nested-uiesc sub 'object'."""
    value = arguments.get(key)
    if isinstance(value, list):
        return value
    # Unele modele (ex. llama3.2:3b) returnează {"object": {"signals": [...]}}
    nested = arguments.get("object", {})
    if isinstance(nested, dict):
        value = nested.get(key)
        if isinstance(value, list):
            return value
    return []


def _handle_tool_call(tool_name: str, arguments: dict, state: dict) -> str:
    """Procesează un tool call și actualizează starea agentului."""
    if tool_name == "extract_signals":
        state["signals"] = _extract_list(arguments, "signals")
        return json.dumps({"status": "ok", "signals_detected": len(state["signals"])})

    if tool_name == "score_intent":
        raw_score = arguments.get("intent_score") or (arguments.get("object") or {}).get("intent_score", 50)
        raw_conf = arguments.get("confidence") or (arguments.get("object") or {}).get("confidence", 0.5)
        raw_reasoning = arguments.get("reasoning") or (arguments.get("object") or {}).get("reasoning", "")
        state["intent_score"] = max(0, min(100, int(raw_score)))
        state["reasoning"] = raw_reasoning
        state["confidence"] = max(0.0, min(1.0, float(raw_conf)))
        return json.dumps({"status": "ok"})

    return json.dumps({"error": f"Unknown tool: {tool_name}"})


def run(lead: dict) -> dict:
    """
    Rulează LeadResearchAgent pentru un lead.

    Args:
        lead: dict cu câmpurile lead-ului (name, company, role, etc.)

    Returns:
        dict cu: intent_score, signals, summary, confidence
    """
    state = {"signals": [], "intent_score": 50, "reasoning": "", "confidence": 0.5}

    messages = [
        {"role": "system", "content": _build_system_prompt()},
        {"role": "user", "content": _build_user_prompt(lead)},
    ]

    # ── Agent loop — max 6 iterații (tool use + răspuns final) ───────────────
    for iteration in range(6):
        try:
            response = client.chat.completions.create(
                model=OLLAMA_MODEL,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
                temperature=0.3,
            )
        except Exception as e:
            logger.error(f"Ollama call failed (iteration {iteration}): {e}")
            break

        message = response.choices[0].message

        # Dacă modelul vrea să apeleze tool-uri
        if message.tool_calls:
            messages.append(message)
            for tool_call in message.tool_calls:
                try:
                    args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    args = {}

                result = _handle_tool_call(tool_call.function.name, args, state)
                logger.info(f"Tool called: {tool_call.function.name} → {result}")

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                })
            continue  # continuă loop-ul cu tool results

        # Modelul a terminat — ieșim din loop
        break

    # ── Construiește summary ─────────────────────────────────────────────────
    signals_text = ", ".join(state["signals"]) if state["signals"] else "niciun semnal detectat"
    summary = (
        f"Am cercetat prospectul {lead.get('name', 'N/A')} "
        f"({lead.get('company', 'N/A')}) — "
        f"scor: {state['intent_score']}, "
        f"semnale: {signals_text}. "
        f"{state['reasoning']}"
    ).strip()

    return {
        "intent_score": state["intent_score"],
        "signals": state["signals"],
        "summary": summary,
        "confidence": state["confidence"],
    }
