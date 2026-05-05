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
    # Safe nested object extraction — llama3.2:3b uneori returnează un string
    # sub cheia "object" în loc de dict, deci verificăm tipul explicit
    obj = arguments.get("object")
    obj = obj if isinstance(obj, dict) else {}

    if tool_name == "set_winning_argument":
        raw = arguments.get("argument") or obj.get("argument", "")
        raw_conf = arguments.get("confidence") or obj.get("confidence", 0.5)
        # Dacă modelul pasează argument ca dict Python direct, extragem textul
        if isinstance(raw, dict):
            raw_str = (
                raw.get("value") or
                raw.get("argument") or
                raw.get("text") or
                ""
            ).strip()
        else:
            raw_str = str(raw).strip()
            # llama3.2:3b sometimes passes the schema definition as the value:
            # {"type": "string", "description": "...", "value": "actual text"}
            # Extract the real text from the "value" key if present.
            try:
                parsed = json.loads(raw_str)
                if isinstance(parsed, dict):
                    extracted = (
                        parsed.get("value") or
                        parsed.get("argument") or
                        parsed.get("text") or
                        ""
                    )
                    # Only use extracted if non-empty; otherwise keep original raw_str
                    raw_str = str(extracted).strip() if extracted else raw_str
            except (json.JSONDecodeError, TypeError, ValueError):
                pass
        state["winning_argument"] = raw_str
        state["confidence"] = max(0.0, min(1.0, float(raw_conf)))
        return json.dumps({"status": "ok"})

    if tool_name == "set_draft_message":
        raw = arguments.get("message") or obj.get("message", "")
        # llama3.2:3b poate pasa message ca dict Python (nu string JSON).
        # Dacă e dict, extragem body direct fără str() → json.loads() roundtrip.
        if isinstance(raw, dict):
            raw_str = (
                raw.get("body") or
                raw.get("message") or
                raw.get("content") or
                ""
            ).strip()
        else:
            raw_str = str(raw).strip()
            # Unele modele returnează emailul wrapped într-un JSON string
            # ex: '{"subject": "...", "body": "Hi Maria,...", "from": "[YOUR EMAIL]"}'
            # Extragem doar câmpul body/message/content dacă e cazul
            try:
                parsed = json.loads(raw_str)
                if isinstance(parsed, dict):
                    raw_str = (
                        parsed.get("body") or
                        parsed.get("message") or
                        parsed.get("content") or
                        raw_str
                    )
            except (json.JSONDecodeError, TypeError, ValueError):
                pass
        # Replace placeholder signatures (toate variantele de case)
        for placeholder, replacement in [
            ("[YOUR NAME]", "Your Sales Team"),
            ("[Your Name]", "Your Sales Team"),
            ("[your name]", "Your Sales Team"),
            ("[YOUR EMAIL]", "sales@company.com"),
            ("[Your Email]", "sales@company.com"),
            ("[your email]", "sales@company.com"),
        ]:
            raw_str = raw_str.replace(placeholder, replacement)
        state["draft_message"] = raw_str
        return json.dumps({"status": "ok"})

    return json.dumps({"error": f"Unknown tool: {tool_name}"})


def _run_once(lead: dict, state: dict) -> None:
    """Single attempt of the agent loop. Updates state in-place."""
    messages = [
        {"role": "system", "content": _build_system_prompt()},
        {"role": "user", "content": _build_user_prompt(lead)},
    ]

    # ── Agent loop — max 6 iterations ────────────────────────────────────────
    for iteration in range(6):
        both_done = bool(state["winning_argument"]) and bool(state["draft_message"])
        if both_done:
            break

        # Force tool use until we have both outputs.
        # llama3.2:3b sometimes ignores tools when using "auto", leaving outputs empty.
        # When winning_argument is filled but draft_message is not, nudge the model.
        if state["winning_argument"] and not state["draft_message"] and iteration >= 2:
            messages.append({
                "role": "user",
                "content": "Good. Now call set_draft_message to write the personalized outreach email.",
            })
        tool_choice = "required"
        try:
            response = client.chat.completions.create(
                model=OLLAMA_MODEL,
                messages=messages,
                tools=TOOLS,
                tool_choice=tool_choice,
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


def run(lead: dict) -> dict:
    """
    Run the CopilotAgent for a lead, with up to 3 attempts on empty output.

    Args:
        lead: dict with lead fields including signals and intent_score from LeadResearchAgent

    Returns:
        dict with: winning_argument, draft_message, confidence
    """
    for attempt in range(3):
        state = {"winning_argument": "", "draft_message": "", "confidence": 0.5}
        _run_once(lead, state)
        if state["winning_argument"] and state["draft_message"]:
            break
        if attempt < 2:
            logger.warning(
                f"Attempt {attempt + 1} produced incomplete output "
                f"(wa={bool(state['winning_argument'])}, dm={bool(state['draft_message'])}), retrying..."
            )

    return {
        "winning_argument": state["winning_argument"],
        "draft_message": state["draft_message"],
        "confidence": state["confidence"],
    }
