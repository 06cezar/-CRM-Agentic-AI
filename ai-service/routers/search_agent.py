from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from agents import search_query_agent

router = APIRouter(tags=["agent"])


class LeadSummary(BaseModel):
    name: str
    company: str
    role: str
    signals: list[str] = []


class SearchQueryRequest(BaseModel):
    leads: list[LeadSummary] = []


class SearchQuerySuggestion(BaseModel):
    query: str
    reasoning: str
    expected_title: str


class SearchQueryResponse(BaseModel):
    queries: list[SearchQuerySuggestion]


@router.post("/search-queries", response_model=SearchQueryResponse)
def suggest_search_queries(payload: SearchQueryRequest):
    """Run the SearchQueryAgent and return LinkedIn Sales Navigator query suggestions."""
    try:
        leads_dicts = [lead.model_dump() for lead in payload.leads]
        result = search_query_agent.run(leads_dicts)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")
