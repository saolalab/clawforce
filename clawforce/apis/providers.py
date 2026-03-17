"""Proxy endpoint to list models from LLM providers using a user-supplied API key."""

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from clawforce.auth import get_current_user
from clawforce.core.store.agent_config import AgentConfigStore
from clawforce.deps import get_agent_config_store

router = APIRouter(tags=["providers"])

# Provider base URLs for model listing (OpenAI-compatible /v1/models pattern)
PROVIDER_ENDPOINTS: dict[str, dict] = {
    "anthropic": {
        "url": "https://api.anthropic.com/v1/models",
        "auth": "x-api-key",
        "extra_headers": {"anthropic-version": "2023-06-01"},
        "prefix": "anthropic",
        "extract": lambda data: [
            {"id": m["id"], "name": m.get("display_name", m["id"])} for m in data.get("data", [])
        ],
    },
    "openai": {
        "url": "https://api.openai.com/v1/models",
        "auth": "bearer",
        "prefix": "openai",
        "extract": lambda data: [
            {"id": m["id"], "name": m["id"]}
            for m in sorted(data.get("data", []), key=lambda m: m["id"])
        ],
    },
    "openrouter": {
        "url": "https://openrouter.ai/api/v1/models",
        "auth": "bearer",
        "prefix": "openrouter",
        "extract": lambda data: [
            {"id": m["id"], "name": m.get("name", m["id"])}
            for m in sorted(data.get("data", []), key=lambda m: m.get("name", m["id"]))
        ],
    },
    "deepseek": {
        "url": "https://api.deepseek.com/models",
        "auth": "bearer",
        "prefix": "deepseek",
        "extract": lambda data: [
            {"id": m["id"], "name": m["id"]}
            for m in sorted(data.get("data", []), key=lambda m: m["id"])
        ],
    },
    "gemini": {
        "url": "https://generativelanguage.googleapis.com/v1beta/models",
        "auth": "query_key",
        "prefix": "gemini",
        "extract": lambda data: [
            {"id": m["name"].replace("models/", ""), "name": m.get("displayName", m["name"])}
            for m in data.get("models", [])
            if "generateContent" in m.get("supportedGenerationMethods", [])
        ],
    },
    "groq": {
        "url": "https://api.groq.com/openai/v1/models",
        "auth": "bearer",
        "prefix": "groq",
        "extract": lambda data: [
            {"id": m["id"], "name": m["id"]}
            for m in sorted(data.get("data", []), key=lambda m: m["id"])
        ],
    },
    "moonshot": {
        "url": "https://api.moonshot.cn/v1/models",
        "auth": "bearer",
        "prefix": "moonshot",
        "extract": lambda data: [
            {"id": m["id"], "name": m["id"]}
            for m in sorted(data.get("data", []), key=lambda m: m["id"])
        ],
    },
    "dashscope": {
        "url": "https://dashscope.aliyuncs.com/compatible-mode/v1/models",
        "auth": "bearer",
        "prefix": "dashscope",
        "extract": lambda data: [
            {"id": m["id"], "name": m["id"]}
            for m in sorted(data.get("data", []), key=lambda m: m["id"])
        ],
    },
    "mistral": {
        "url": "https://api.mistral.ai/v1/models",
        "auth": "bearer",
        "prefix": "mistral",
        "extract": lambda data: [
            {"id": m["id"], "name": m["id"]}
            for m in sorted(data.get("data", []), key=lambda m: m["id"])
        ],
    },
    "together": {
        "url": "https://api.together.xyz/v1/models",
        "auth": "bearer",
        "prefix": "together_ai",
        "extract": lambda data: (
            [
                {"id": m["id"], "name": m.get("display_name", m["id"])}
                for m in sorted(
                    data.get("data", data) if isinstance(data, dict) else data,
                    key=lambda m: m.get("display_name", m["id"]),
                )
                if m.get("type", "chat") == "chat"
            ]
            if isinstance(data, (dict, list))
            else []
        ),
    },
    "xai": {
        "url": "https://api.x.ai/v1/models",
        "auth": "bearer",
        "prefix": "xai",
        "extract": lambda data: [
            {"id": m["id"], "name": m["id"]}
            for m in sorted(data.get("data", []), key=lambda m: m["id"])
        ],
    },
    "bedrock": {
        "url": None,  # No simple REST endpoint; handled separately or uses static list
        "static": True,
        "prefix": "bedrock",
        "models": [
            {"id": "anthropic.claude-sonnet-4-20250514-v1:0", "name": "Claude Sonnet 4"},
            {"id": "anthropic.claude-3-5-haiku-20241022-v1:0", "name": "Claude 3.5 Haiku"},
            {"id": "anthropic.claude-3-5-sonnet-20241022-v2:0", "name": "Claude 3.5 Sonnet v2"},
            {"id": "anthropic.claude-3-haiku-20240307-v1:0", "name": "Claude 3 Haiku"},
            {"id": "meta.llama3-1-70b-instruct-v1:0", "name": "Llama 3.1 70B"},
            {"id": "meta.llama3-1-8b-instruct-v1:0", "name": "Llama 3.1 8B"},
            {"id": "mistral.mistral-large-2407-v1:0", "name": "Mistral Large"},
        ],
    },
    "azure": {
        "url": None,
        "static": True,
        "prefix": "azure",
        "models": [
            {"id": "gpt-4o", "name": "GPT-4o"},
            {"id": "gpt-4o-mini", "name": "GPT-4o Mini"},
            {"id": "gpt-4-turbo", "name": "GPT-4 Turbo"},
            {"id": "gpt-4", "name": "GPT-4"},
            {"id": "gpt-35-turbo", "name": "GPT-3.5 Turbo"},
        ],
    },
}


class ListModelsRequest(BaseModel):
    provider: str
    api_key: str = ""
    agent_id: str = ""


@router.post("/api/providers/models")
async def list_provider_models(
    body: ListModelsRequest,
    _: dict = Depends(get_current_user),
    agent_config_store: AgentConfigStore = Depends(get_agent_config_store),
):
    """Fetch available models from a provider using the given API key.

    If api_key is empty but agent_id is provided, the stored key for that
    provider is read from the agent's persisted config.
    """
    provider = body.provider.lower()
    ep = PROVIDER_ENDPOINTS.get(provider)
    if not ep:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown provider: {body.provider}",
        )

    prefix = ep.get("prefix", provider)

    # Static providers (bedrock, azure) return a fixed list
    if ep.get("static"):
        return {
            "provider": provider,
            "prefix": prefix,
            "models": ep["models"],
        }

    api_key = body.api_key

    # Fall back to stored key when no explicit key provided
    if not api_key and body.agent_id:
        config = agent_config_store.get_config(body.agent_id) or {}
        provider_cfg = (config.get("providers") or {}).get(provider) or {}
        api_key = provider_cfg.get("api_key") or provider_cfg.get("apiKey") or ""

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="API key is required to fetch models",
        )

    url = ep["url"]
    headers: dict[str, str] = {}
    params: dict[str, str] = {}

    auth_mode = ep.get("auth", "bearer")
    if auth_mode == "bearer":
        headers["Authorization"] = f"Bearer {api_key}"
    elif auth_mode == "x-api-key":
        headers["x-api-key"] = api_key
    elif auth_mode == "query_key":
        params["key"] = api_key

    if ep.get("extra_headers"):
        headers.update(ep["extra_headers"])

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, headers=headers, params=params)
        if resp.status_code == 401:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
            )
        if resp.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Provider returned {resp.status_code}: {resp.text[:200]}",
            )
        data = resp.json()
        models = ep["extract"](data)
        return {
            "provider": provider,
            "prefix": prefix,
            "models": models,
        }
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Timed out connecting to provider",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch models: {str(e)[:200]}",
        )
