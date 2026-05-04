"""
CopilotAgent — generates personalized sales co-pilot content for a lead:
  - winning_argument: strategic selling argument based on lead signals
  - draft_message: ready-to-send outreach email
  - confidence: 0.0-1.0

Uses Ollama via OpenAI-compatible API with tool use.
Model configured via OLLAMA_MODEL env var (default: llama3.2:3b).
"""

import os
import json
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434/v1")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")

client = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")

# ── Tool definitions ──────────────────────────────────────────────────────────
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "set_winning_argument",
            "description": (
                "Set the winning sales argument for this lead. "
                "The argument must be personalized — reference the lead's company, role, "
                "and at least one buying signal. Explain concisely why they should buy now. "
                "Keep it between 20-150 words. Be specific, not generic."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "argument": {
                        "type": "string",
                        "description": "The personalized winning sales argument.",
                    },
                    "confidence": {
                        "type": "number",
                        "description": "Confidence in this argument, between 0.0 and 1.0.",
                    },
                },
                "required": ["argument", "confidence"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_draft_message",
            "description": (
                "Set the personalized outreach email draft for this lead. "
                "The email must use the lead's actual name in the greeting (not [NAME] or Dear Sir). "
                "Keep it between 50-300 words — professional, specific, and actionable. "
                "Never use placeholder text like [COMPANY], [INSERT], or [YOUR NAME]."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "The ready-to-send email draft.",
                    },
                },
                "required": ["message"],
            },
        },
    },
]


def _build_system_prompt() -> str:
    return (
        "You are an AI sales co-pilot. Your mission: help a sales rep close a deal "
        "by generating a personalized winning argument and a ready-to-send outreach email. "
        "Use the available tools in order: first set_winning_argument, then set_draft_message. "
        "Base your outputs on the lead's profile, buying signals, and intent score. "
        "Be specific — use the lead's real name, company, and detected signals. "
        "Never use placeholder text."
    )


def _build_user_prompt(lead: dict) -> str:
    def _val(key: str, fallback: str = "N/A") -> str:
        v = lead.get(key)
        return str(v) if v is not None else fallback

    signals = lead.get("signals", [])
    signals_text = ", ".join(signals) if signals else "none detected"

    return (
        f"Generate co-pilot content for this lead:\n\n"
        f"Name: {_val('name')}\n"
        f"Company: {_val('company')}\n"
        f"Role: {_val('role')}\n"
        f"Email: {_val('email')}\n"
        f"Deal value: {_val('deal_value_display')}\n"
        f"Intent score: {_val('intent_score')}/100\n"
        f"Buying signals: {signals_text}\n"
        f"Last activity: {_val('last_activity_description', 'unknown')}\n\n"
        f"Use set_winning_argument to set a personalized winning argument, "
        f"then set_draft_message to draft a personalized outreach email."
    )


def _handle_tool_call(tool_name: str, arguments: dict, state: dict) -> str:
    """Process a tool call and update agent state."""
    if tool_name == "set_winning_argument":
        raw = arguments.get("argument") or (arguments.get("object") or {}).get("argument", "")
        raw_conf = arguments.get("confidence") or (arguments.get("object") or {}).get("confidence", 0.5)
        state["winning_argument"] = str(raw).strip()
        state["confidence"] = max(0.0, min(1.0, float(raw_conf)))
        return json.dumps({"status": "ok"})

    if tool_name == "set_draft_message":
        raw = arguments.get("message") or (arguments.get("object") or {}).get("message", "")
        state["draft_message"] = str(raw).strip()
        return json.dumps({"status": "ok"})

    return json.dumps({"error": f"Unknown tool: {tool_name}"})


def run(lead: dict) -> dict:
    """
    Run the CopilotAgent for a lead.

    Args:
        lead: dict with lead fields including signals and intent_score from LeadResearchAgent

    Returns:
        dict with: winning_argument, draft_message, confidence
    """
    state = {"winning_argument": "", "draft_message": "", "confidence": 0.5}

    messages = [
        {"role": "system", "content": _build_system_prompt()},
        {"role": "user", "content": _build_user_prompt(lead)},
    ]

    # ── Agent loop — max 6 iterations ────────────────────────────────────────
    for iteration in range(6):
        try:
            response = client.chat.completions.create(
                model=OLLAMA_MODEL,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
                temperature=0.4,
            )
        except Exception as e:
            logger.error(f"Ollama call failed (iteration {iteration}): {e}")
            break

        message = response.choices[0].message

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
            continue

        break

    return {
        "winning_argument": state["winning_argument"],
        "draft_message": state["draft_message"],
        "confidence": state["confidence"],
    }
