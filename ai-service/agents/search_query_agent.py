"""
SearchQueryAgent — analyzes existing CRM leads and suggests LinkedIn Sales Navigator
search queries to find similar high-quality prospects.

Uses the same Ollama/OpenAI-compatible setup as research_agent.py.
"""

import os
import json
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434/v1")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
MAX_RETRIES = 2

client = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "suggest_search_queries",
            "description": (
                "Suggest 3 to 5 LinkedIn Sales Navigator keyword search queries "
                "based on patterns found in the provided leads. "
                "Each query should target a specific role/industry combination "
                "that would produce high-intent prospects similar to the existing leads."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "queries": {
                        "type": "array",
                        "description": "List of 3-5 suggested search queries.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "description": 'LinkedIn Sales Navigator keyword query, e.g. "CEO SaaS fintech"',
                                },
                                "reasoning": {
                                    "type": "string",
                                    "description": "One sentence explaining why this query will find good leads.",
                                },
                                "expected_title": {
                                    "type": "string",
                                    "description": "The typical job title this query targets, e.g. Chief Executive Officer",
                                },
                            },
                            "required": ["query", "reasoning", "expected_title"],
                        },
                    }
                },
                "required": ["queries"],
            },
        },
    }
]


def _build_system_prompt() -> str:
    return (
        "You are a B2B sales intelligence assistant. "
        "Your task: analyze a list of CRM leads and suggest LinkedIn Sales Navigator search queries "
        "to find similar high-quality prospects. "
        "LinkedIn Sales Navigator searches use simple keyword combinations like 'CEO SaaS', "
        "'VP Sales fintech Europe', 'CTO startup', 'Head of Marketing B2B'. "
        "Identify patterns (common industries, seniority levels, company types) from the leads "
        "and suggest 3-5 targeted search queries. "
        "Call the suggest_search_queries tool with your recommendations."
    )


def _build_user_prompt(leads: list[dict]) -> str:
    if not leads:
        return (
            "No existing leads in the CRM yet. "
            "Suggest 3 general search queries for B2B SaaS decision-makers."
        )

    lines = ["Here are the current leads in the CRM:\n"]
    for i, lead in enumerate(leads[:10], 1):
        signals = ", ".join(lead.get("signals", [])) if lead.get("signals") else "none"
        lines.append(
            f"{i}. {lead.get('name', 'N/A')} — {lead.get('role', 'N/A')} at {lead.get('company', 'N/A')} "
            f"[signals: {signals}]"
        )

    lines.append(
        "\n\nAnalyze these leads and call suggest_search_queries with 3-5 LinkedIn Sales Navigator "
        "search queries to find similar high-quality prospects."
    )
    return "\n".join(lines)


def _extract_queries_from_args(arguments: dict) -> list[dict]:
    queries = arguments.get("queries", [])
    if isinstance(queries, list):
        return queries
    nested = arguments.get("object", {})
    if isinstance(nested, dict):
        return nested.get("queries", [])
    return []


def run(leads: list[dict]) -> dict:
    """
    Run the SearchQueryAgent.

    Args:
        leads: list of lead dicts with name, company, role, signals

    Returns:
        dict with: queries (list of {query, reasoning, expected_title})
    """
    messages = [
        {"role": "system", "content": _build_system_prompt()},
        {"role": "user", "content": _build_user_prompt(leads)},
    ]

    extracted_queries: list[dict] = []

    for iteration in range(4):
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

                if tool_call.function.name == "suggest_search_queries":
                    extracted_queries = _extract_queries_from_args(args)
                    logger.info(f"SearchQueryAgent extracted {len(extracted_queries)} queries")

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps({"status": "ok", "count": len(extracted_queries)}),
                })
            continue

        break

    # Fallback if tool was never called
    if not extracted_queries:
        extracted_queries = [
            {"query": "CEO SaaS startup", "reasoning": "Target early-stage SaaS founders.", "expected_title": "Chief Executive Officer"},
            {"query": "VP Sales B2B software", "reasoning": "Decision-makers for software purchasing.", "expected_title": "VP of Sales"},
            {"query": "CTO fintech", "reasoning": "Technical decision-makers in financial technology.", "expected_title": "Chief Technology Officer"},
        ]

    return {"queries": extracted_queries}
