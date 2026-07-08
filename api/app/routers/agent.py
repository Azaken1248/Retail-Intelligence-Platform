import logging

from fastapi import APIRouter, HTTPException

from app.schemas.sales_dto import AgentRequest, AgentResponse
from app.services.gemini_agent import run_agent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/agent", tags=["AI Agent"])


@router.post("/chat", response_model=AgentResponse, summary="Chat with the AI Agent")
async def agent_chat(request: AgentRequest):
    """
    Send a natural-language message to the Gemini 2.5 Flash AI agent.

    The agent will analyse your query, call the appropriate data tools
    (SQL queries, pre-built analytics views), and return a synthesised
    human-readable answer.

    **Example prompts:**
    - "Generate this week's executive report"
    - "Show sales by country"
    - "Who are our top 10 customers by lifetime value?"
    - "What's our year-over-year revenue growth?"
    """
    try:
        result = await run_agent(request.message)
        return AgentResponse(
            response=result["response"],
            tools_used=result["tools_used"],
        )
    except ValueError as e:
        # Missing API key or config error
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.exception("Agent request failed")
        raise HTTPException(
            status_code=500,
            detail=f"Agent error: {e}",
        )
