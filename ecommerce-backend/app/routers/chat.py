"""Chat / AI endpoints for the BI agent."""
from typing import Any

from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel

from app.services import ai_service

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatMessage(BaseModel):
    role: str          # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    question: str
    history: list[ChatMessage] = []


class QueryRequest(BaseModel):
    sql: str


@router.post("")
def chat_endpoint(req: ChatRequest) -> dict[str, Any]:
    """
    Main BI agent endpoint.

    Accepts a natural-language question and optional conversation history.
    Returns SQL, raw data rows, and AI-generated analysis.
    """
    history = [{"role": m.role, "content": m.content} for m in req.history]
    result = ai_service.chat(req.question, history)
    return result

@router.post("/stream")
async def chat_stream_endpoint(req: ChatRequest) -> dict[str, Any]:
    """
    Streamed version of the chat endpoint.

    Accepts a natural-language question and optional conversation history.
    Returns a generator that yields partial responses as they are generated.
    """
    history = [{"role": m.role, "content": m.content} for m in req.history]
    try:
        return ai_service.chat_stream(req.question, history)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.post("/query")
def run_custom_query(req: QueryRequest) -> dict[str, Any]:
    """
    Execute a raw SQL SELECT against the database.
    Intended for the Query Builder UI panel — SELECT only.
    """
    try:
        rows = ai_service.execute_sql(req.sql, limit=1000)
        return {"rows": rows, "row_count": len(rows), "error": None}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
