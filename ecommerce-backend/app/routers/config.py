"""Runtime LLM configuration endpoint."""
import os
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from app.services import ai_service

router = APIRouter(prefix="/api/config", tags=["config"])


class LLMConfig(BaseModel):
    mode: Literal["direct", "gateway"]
    # Direct Anthropic
    api_key: str = ""
    model: str = ""
    # Gateway extras
    base_url: str = ""
    keycloak_url: str = ""
    client_id: str = ""
    client_secret: str = ""
    llm_username: str = ""
    llm_password: str = ""


@router.post("")
def apply_llm_config(cfg: LLMConfig) -> dict:
    """Apply LLM settings at runtime by updating os.environ and clearing the token cache."""

    # Always update model if provided
    if cfg.model:
        os.environ["CLAUDE_MODEL"] = cfg.model

    if cfg.mode == "direct":
        os.environ["LLM_API_KEY"] = cfg.api_key
        os.environ["LLM_BASE_URL"] = ""           # disable gateway
        # Clear Keycloak vars so the gateway path is never triggered
        for var in ("KEYCLOAK_URL", "CLIENT_ID", "CLIENT_SECRET", "llm_username", "llm_password"):
            os.environ.pop(var, None)
    else:
        os.environ["LLM_BASE_URL"] = cfg.base_url.rstrip("/")
        os.environ["LLM_API_KEY"] = cfg.api_key or os.getenv("LLM_API_KEY", "")
        os.environ["KEYCLOAK_URL"] = cfg.keycloak_url
        os.environ["CLIENT_ID"] = cfg.client_id
        os.environ["CLIENT_SECRET"] = cfg.client_secret
        os.environ["llm_username"] = cfg.llm_username
        os.environ["llm_password"] = cfg.llm_password

    # Invalidate the cached Keycloak token so it's refetched with new creds
    ai_service._token_cache["token"] = None
    ai_service._token_cache["expires_at"] = 0.0

    return {"status": "ok", "mode": cfg.mode, "model": os.getenv("CLAUDE_MODEL", "")}


@router.get("")
def get_llm_config() -> dict:
    """Return current LLM configuration (secrets masked)."""
    base_url = os.getenv("LLM_BASE_URL", "").strip()
    return {
        "mode": "gateway" if base_url else "direct",
        "model": os.getenv("CLAUDE_MODEL", ""),
        "base_url": base_url,
        "keycloak_url": os.getenv("KEYCLOAK_URL", ""),
        "client_id": os.getenv("CLIENT_ID", ""),
        "llm_username": os.getenv("llm_username", ""),
        "api_key_set": bool(os.getenv("LLM_API_KEY", "")),
        "client_secret_set": bool(os.getenv("CLIENT_SECRET", "")),
        "llm_password_set": bool(os.getenv("llm_password", "")),
    }
