"""
OpenAI-compatible routes for the single SLM.

Endpoints (OpenAI Chat Completions convention — see
https://platform.openai.com/docs/api-reference/chat):

    GET  /v1/models                — list loaded models (one entry)
    POST /v1/chat/completions      — chat (non-streaming), returns OpenAI shape

Why OpenAI-compatible: any OpenAI client SDK (Python `openai`, LangChain
`ChatOpenAI`, the `openai` Node SDK, curl examples in every blog post)
works against this server by changing `base_url` to point here. Same
contract used by vLLM, Ollama, LM Studio, Text Generation Inference,
and llama.cpp's server.

Streaming (`stream: true`) is not implemented in this template — add SSE
later via `StreamingResponse` if you need it.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field


router = APIRouter(prefix="/v1", tags=["slm"])


# ── OpenAI-compatible request/response schemas ────────────────────────────

class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class ChatCompletionRequest(BaseModel):
    """Subset of OpenAI's ChatCompletionRequest. Unknown fields are ignored."""
    model: Optional[str] = None
    messages: List[ChatMessage]
    temperature: float = Field(0.2, ge=0.0, le=2.0)
    top_p: float = Field(0.9, ge=0.0, le=1.0)
    max_tokens: int = Field(500, ge=16, le=2048)
    stream: bool = False  # accepted but not honored — see module docstring


class ChatCompletionChoice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: Literal["stop", "length"]


class ChatCompletionUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionResponse(BaseModel):
    id: str
    object: Literal["chat.completion"] = "chat.completion"
    created: int
    model: str
    choices: List[ChatCompletionChoice]
    usage: ChatCompletionUsage


class ModelCard(BaseModel):
    id: str
    object: Literal["model"] = "model"
    created: int
    owned_by: str = "vxstudio"


class ModelList(BaseModel):
    object: Literal["list"] = "list"
    data: List[ModelCard]


# ── helpers ────────────────────────────────────────────────────────────────

def _get_backend(req: Request):
    backend = getattr(req.app.state, "slm", None)
    if backend is None:
        raise HTTPException(status_code=503, detail="SLM backend not initialised")
    return backend


def _messages_to_prompt(messages: List[ChatMessage]) -> str:
    """Flatten chat messages into a single prompt the causal LM can consume.

    The system prompt baked into the backend is prepended automatically by
    `backend.build_prompt`, so we only forward the user's most recent turn
    plus any conversation history.
    """
    history = []
    user_turn = ""
    for m in messages:
        if m.role == "system":
            continue  # backend.cfg.system_prompt wins
        if m.role == "user":
            user_turn = m.content
            history.append(f"User: {m.content}")
        elif m.role == "assistant":
            history.append(f"Assistant: {m.content}")
    if len(history) <= 1:
        return user_turn or (messages[-1].content if messages else "")
    return "\n".join(history) + "\nAssistant:"


# ── routes ─────────────────────────────────────────────────────────────────

@router.get("/models", response_model=ModelList)
async def list_models(req: Request) -> ModelList:
    backend = _get_backend(req)
    return ModelList(
        data=[
            ModelCard(
                id=backend.cfg.display_name,
                created=int(time.time()),
            )
        ]
    )


@router.post("/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(payload: ChatCompletionRequest, req: Request) -> ChatCompletionResponse:
    backend = _get_backend(req)
    if not payload.messages:
        raise HTTPException(status_code=400, detail="messages must not be empty")
    if payload.stream:
        raise HTTPException(
            status_code=501,
            detail="Streaming is not implemented in this template. Set stream=false.",
        )

    prompt = _messages_to_prompt(payload.messages)
    result: Dict[str, Any] = backend.generate(
        prompt=prompt,
        max_new_tokens=payload.max_tokens,
        temperature=payload.temperature,
        top_p=payload.top_p,
    )
    answer = str(result.get("response", ""))
    prompt_tokens = max(1, len(prompt) // 4)
    completion_tokens = max(1, len(answer) // 4)

    return ChatCompletionResponse(
        id=f"chatcmpl-{uuid.uuid4().hex[:24]}",
        created=int(time.time()),
        model=backend.cfg.display_name,
        choices=[
            ChatCompletionChoice(
                index=0,
                message=ChatMessage(role="assistant", content=answer),
                finish_reason="length" if completion_tokens >= payload.max_tokens else "stop",
            )
        ],
        usage=ChatCompletionUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        ),
    )
