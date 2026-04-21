"""Proxy endpoint to list models from LLM providers using a user-supplied API key."""

import asyncio
import json
import os
import time
import urllib.parse

import httpx

try:
    import docker as _docker_module  # type: ignore[import]
except ImportError:
    _docker_module = None  # type: ignore[assignment]

from fastapi import APIRouter, Depends, HTTPException, Request, status
from loguru import logger
from oauth_cli_kit import OPENAI_CODEX_PROVIDER, OAuthProviderConfig, OAuthToken, get_token
from oauth_cli_kit.flow import _exchange_code_for_token_async
from oauth_cli_kit.pkce import _create_state, _generate_pkce
from oauth_cli_kit.server import _start_local_server
from oauth_cli_kit.storage import FileTokenStorage
from pydantic import BaseModel

from clawforce.auth import get_current_user
from clawforce.core.store.agent_config import AgentConfigStore
from clawforce.deps import get_agent_config_store

router = APIRouter(tags=["providers"])

# OAuth provider configurations — maps provider config field name → OAuthProviderConfig.
# OpenAI Codex and ChatGPT Plus share the same OpenAI login (same codex.json token file).
# GitHub Copilot is NOT here — it has no public PKCE OAuth app; users supply a token
# obtained from the GitHub CLI (`gh auth token`) or the VS Code Copilot extension.
OAUTH_PROVIDER_CONFIGS: dict[str, OAuthProviderConfig] = {
    "openai_codex": OPENAI_CODEX_PROVIDER,
    "chatgpt": OPENAI_CODEX_PROVIDER,
}

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
    "openai_codex": {
        "url": None,
        "static": True,
        "prefix": "openai-codex",
        "models": [
            {"id": "gpt-5.1-codex", "name": "GPT-5.1 Codex"},
            {"id": "codex-mini-latest", "name": "Codex Mini (Latest)"},
        ],
    },
    "chatgpt": {
        "url": None,
        "static": True,
        "prefix": "chatgpt",
        "models": [
            {"id": "gpt-4o", "name": "GPT-4o"},
            {"id": "gpt-4o-mini", "name": "GPT-4o Mini"},
            {"id": "o3", "name": "o3"},
            {"id": "o4-mini", "name": "o4 Mini"},
        ],
    },
    "github_copilot": {
        "url": None,
        "static": True,
        "prefix": "github_copilot",
        "models": [
            {"id": "gpt-4o", "name": "GPT-4o (Copilot)"},
            {"id": "claude-sonnet-4-5", "name": "Claude Sonnet 4.5 (Copilot)"},
            {"id": "o3-mini", "name": "o3 Mini (Copilot)"},
            {"id": "gemini-2.0-flash-001", "name": "Gemini 2.0 Flash (Copilot)"},
        ],
    },
}


class ListModelsRequest(BaseModel):
    provider: str
    api_key: str = ""
    agent_id: str = ""
    api_base: str = ""


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

    # Custom (OpenAI-compatible) provider: user-supplied base URL, GET {base}/models.
    if provider == "custom":
        api_base = body.api_base
        api_key = body.api_key
        if body.agent_id:
            stored_cfg = agent_config_store.get_config(body.agent_id) or {}
            stored = (stored_cfg.get("providers") or {}).get("custom") or {}
            if not api_base or api_base.startswith("***"):
                api_base = stored.get("api_base") or stored.get("apiBase") or ""
            if not api_key or api_key.startswith("***"):
                api_key = stored.get("api_key") or stored.get("apiKey") or ""
        if not api_base:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Base URL is required for custom provider",
            )
        url = api_base.rstrip("/") + "/models"
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(url, headers=headers)
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
            models = [
                {"id": m["id"], "name": m.get("id", m["id"])}
                for m in sorted(data.get("data", []), key=lambda m: m["id"])
            ]
            return {"provider": "custom", "prefix": "custom", "models": models}
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


@router.get("/api/providers/oauth/{provider}/status")
async def oauth_status(
    provider: str,
    agent_id: str = "",
    _: dict = Depends(get_current_user),
    agent_config_store: AgentConfigStore = Depends(get_agent_config_store),
):
    """Check whether a valid OAuth token exists for a provider.

    When *agent_id* is provided the check looks at the token stored in that
    agent's config (same place API keys live).  Otherwise falls back to the
    global FileTokenStorage used by local/direct runs.
    """
    oauth_cfg = OAUTH_PROVIDER_CONFIGS.get(provider)
    if not oauth_cfg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown OAuth provider: {provider}",
        )

    if agent_id:
        config = agent_config_store.get_config(agent_id) or {}
        token_json = (config.get("providers") or {}).get(provider, {}).get("api_key", "")
        if token_json:
            try:
                data = json.loads(token_json)
                token = OAuthToken(
                    access=data["access"],
                    refresh=data["refresh"],
                    expires=int(data["expires"]),
                    account_id=data.get("account_id"),
                )
                now_ms = int(time.time() * 1000)
                if token.expires - now_ms > 0:
                    return {
                        "provider": provider,
                        "authorized": True,
                        "account_id": token.account_id,
                    }
            except Exception:
                pass
        return {"provider": provider, "authorized": False, "account_id": None}

    try:
        token = await asyncio.to_thread(get_token, oauth_cfg)
        return {"provider": provider, "authorized": True, "account_id": token.account_id}
    except RuntimeError:
        return {"provider": provider, "authorized": False, "account_id": None}


_OAUTH_CALLBACK_TIMEOUT = 300.0  # 5 minutes for the user to complete sign-in in the browser

# Registry of in-flight OAuth flows: state → (code_future, verifier)
# The ephemeral callback container delivers the auth code here via
# POST /api/providers/oauth/internal/deliver.
_active_oauth_flows: dict[str, tuple["asyncio.Future[str]", str]] = {}


# ---------------------------------------------------------------------------
# Internal deliver endpoint — called by the callback container, not the browser
# ---------------------------------------------------------------------------


class _OAuthDeliverRequest(BaseModel):
    code: str
    state: str


@router.post("/api/providers/oauth/internal/deliver")
async def oauth_internal_deliver(body: _OAuthDeliverRequest):
    """Receive the auth code from the ephemeral OAuth callback container.

    The callback container POSTs here after the browser lands on its
    ``/auth/callback`` endpoint.  No user auth required — the ``state`` value
    already acts as a one-time bearer token (PKCE security model).
    """
    entry = _active_oauth_flows.get(body.state)
    if not entry:
        # Flow may have already completed or timed out — ignore silently.
        return {"ok": True}
    code_future, _ = entry
    if not code_future.done():
        loop = asyncio.get_event_loop()
        loop.call_soon_threadsafe(code_future.set_result, body.code)
    return {"ok": True}


# ---------------------------------------------------------------------------
# Docker callback container helpers
# ---------------------------------------------------------------------------


def _get_docker_client():
    """Return a Docker client if the daemon socket is accessible, else None."""
    if _docker_module is None:
        return None
    try:
        client = _docker_module.DockerClient(base_url="unix:///var/run/docker.sock")
        client.ping()
        return client
    except Exception:
        return None


def _spawn_callback_container(
    docker_client,
    redirect_uri: str,
    notify_url: str,
    state: str,
):
    """Start an ephemeral container that listens on the OAuth callback port.

    The container runs ``clawforce.oauth_callback_server``, binds the port
    extracted from *redirect_uri* on ``127.0.0.1`` of the host, and POSTs the
    auth code to *notify_url* once the browser lands on ``/auth/callback``.

    Host resolution strategy (tried in order, first success wins):

    1. ``host.docker.internal`` via ``extra_hosts: host-gateway`` — Docker on Linux
    2. ``host.containers.internal`` without extra_hosts — Podman (auto-injects this)
    3. ``host.docker.internal`` without extra_hosts — Docker Desktop (Mac / Windows,
       auto-injects this hostname)

    Returns the container object, or ``None`` if all attempts fail.
    """
    parsed = urllib.parse.urlparse(redirect_uri)
    port = parsed.port or 1455
    image = os.environ.get("AGENT_IMAGE", "ghcr.io/saolalab/clawforce:latest")
    name = f"clawforce-oauth-cb-{state[:12]}"

    # Attempts: (notify_url_to_use, extra_hosts_dict)
    # host.containers.internal — Podman auto-injects this into every container.
    # host.docker.internal     — Docker Desktop injects this; Docker on Linux needs
    #                            the explicit host-gateway mapping.
    attempts: list[tuple[str, dict]] = [
        (notify_url, {"host.docker.internal": "host-gateway"}),
        (notify_url.replace("host.docker.internal", "host.containers.internal"), {}),
        (notify_url, {}),
    ]

    last_exc: Exception | None = None
    for effective_url, extra_hosts in attempts:
        # Clean up any container left from a failed previous attempt.
        try:
            docker_client.containers.get(name).remove(force=True)
        except Exception:
            pass

        kwargs: dict = {
            "image": image,
            "command": ["python", "-m", "clawforce.oauth_callback_server"],
            "detach": True,
            "name": name,
            "environment": {"OAUTH_NOTIFY_URL": effective_url, "OAUTH_PORT": str(port)},
            "ports": {f"{port}/tcp": ("127.0.0.1", port)},
            "remove": False,
        }
        if extra_hosts:
            kwargs["extra_hosts"] = extra_hosts

        try:
            container = docker_client.containers.run(**kwargs)
            logger.info(
                "OAuth callback container started: {} (port {}, notify→{})",
                name,
                port,
                effective_url,
            )
            return container
        except Exception as exc:
            last_exc = exc
            logger.debug("OAuth container attempt failed ({}): {}", effective_url, exc)

    logger.warning("Could not start OAuth callback container: {}", last_exc)
    return None


def _stop_container(container) -> None:
    try:
        container.stop(timeout=3)
    except Exception:
        pass
    try:
        container.remove()
    except Exception:
        pass


def _build_notify_url(request: Request) -> str:
    """Build the URL the callback container will POST the auth code to.

    Uses ``host.docker.internal`` so the callback container (a sibling
    container on the same Docker host) can reach the clawforce server through
    the host's port mapping.  Falls back to ``localhost`` for non-Docker runs.
    """
    host = request.headers.get("host", "localhost:8080")
    scheme = request.headers.get("x-forwarded-proto") or request.url.scheme
    # Replace 'localhost' with host.docker.internal so sibling containers can
    # reach the clawforce server via the host machine's port mapping.
    container_host = host.replace("localhost", "host.docker.internal")
    return f"{scheme}://{container_host}/api/providers/oauth/internal/deliver"


# ---------------------------------------------------------------------------
# Core PKCE flow
# ---------------------------------------------------------------------------


async def _run_oauth_flow(
    oauth_cfg: OAuthProviderConfig,
    url_ready: "asyncio.Future[str]",
    notify_url: str,
) -> OAuthToken:
    """Run the PKCE OAuth flow using an ephemeral Docker callback container.

    1. Generates a PKCE pair and state token.
    2. Tries to spawn a short-lived Docker container that binds the provider's
       callback port (e.g. 1455) and relays the auth code back via *notify_url*.
    3. Falls back to ``_start_local_server`` when Docker is unavailable (local
       dev without socket access).
    4. Resolves *url_ready* immediately so the endpoint can return the auth URL
       to the frontend, then waits up to 5 minutes for the code to arrive.
    """
    verifier, challenge = _generate_pkce()
    state = _create_state()

    params = {
        "response_type": "code",
        "client_id": oauth_cfg.client_id,
        "redirect_uri": oauth_cfg.redirect_uri,
        "scope": oauth_cfg.scope,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": state,
        "id_token_add_organizations": "true",
        "codex_cli_simplified_flow": "true",
        "originator": oauth_cfg.default_originator,
    }
    auth_url = f"{oauth_cfg.authorize_url}?{urllib.parse.urlencode(params)}"

    loop = asyncio.get_event_loop()
    code_future: asyncio.Future[str] = loop.create_future()
    _active_oauth_flows[state] = (code_future, verifier)

    container = None
    local_server = None

    docker_client = await asyncio.to_thread(_get_docker_client)
    if docker_client is not None:
        container = await asyncio.to_thread(
            _spawn_callback_container,
            docker_client,
            oauth_cfg.redirect_uri,
            notify_url,
            state,
        )

    if container is None:
        # Fallback: start the local server directly on the callback port.
        # Works when clawforce is run directly on the host (not in Docker).
        def _on_code(code: str) -> None:
            if not code_future.done():
                loop.call_soon_threadsafe(code_future.set_result, code)

        local_server, server_error = _start_local_server(state, on_code=_on_code)
        if not local_server:
            raise RuntimeError(
                f"OAuth callback server could not start on port 1455: {server_error}. "
                "Make sure the Docker socket is mounted (-v /var/run/docker.sock:/var/run/docker.sock) "
                "or that port 1455 is not already in use."
            )

    if not url_ready.done():
        url_ready.set_result(auth_url)

    try:
        code = await asyncio.wait_for(code_future, timeout=_OAUTH_CALLBACK_TIMEOUT)
    except asyncio.TimeoutError:
        raise RuntimeError(
            f"OAuth timed out — no browser callback received within "
            f"{int(_OAUTH_CALLBACK_TIMEOUT)}s."
        )
    finally:
        _active_oauth_flows.pop(state, None)
        if container is not None:
            await asyncio.to_thread(_stop_container, container)
        if local_server is not None:
            await asyncio.to_thread(local_server.shutdown)
            local_server.server_close()

    token: OAuthToken = await _exchange_code_for_token_async(code, verifier, oauth_cfg)()
    FileTokenStorage(token_filename=oauth_cfg.token_filename).save(token)
    return token


class OAuthAuthorizeRequest(BaseModel):
    agent_id: str = ""


@router.post("/api/providers/oauth/{provider}/authorize")
async def oauth_authorize(
    provider: str,
    body: OAuthAuthorizeRequest,
    request: Request,
    _: dict = Depends(get_current_user),
    agent_config_store: AgentConfigStore = Depends(get_agent_config_store),
):
    """Start an OAuth browser login flow for a provider.

    Spawns an ephemeral Docker container that binds the provider's callback port
    (e.g. 1455) on the host, builds the authorization URL, and returns it
    immediately so the frontend can open it in a new tab.  Once the user
    completes sign-in the callback container relays the code back, the token is
    saved, and ``GET /api/providers/oauth/{provider}/status`` returns
    ``{"authorized": true}``.

    Falls back to a local port-1455 server when the Docker socket is
    unavailable (direct-run / local development without Docker).
    """
    oauth_cfg = OAUTH_PROVIDER_CONFIGS.get(provider)
    if not oauth_cfg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown OAuth provider: {provider}",
        )

    notify_url = _build_notify_url(request)
    loop = asyncio.get_event_loop()
    url_ready: asyncio.Future[str] = loop.create_future()

    agent_id = body.agent_id

    async def _bg() -> None:
        try:
            tok = await _run_oauth_flow(oauth_cfg, url_ready, notify_url=notify_url)
            logger.info("OAuth [{}] authorized: {}", provider, tok.account_id)

            # Persist token JSON in the agent's config so inject_to_env() delivers
            # it as CLAWFORCE_OPENAI_OAUTH_TOKEN — same pipeline as API keys.
            if agent_id:
                token_json = json.dumps(
                    {
                        "access": tok.access,
                        "refresh": tok.refresh,
                        "expires": tok.expires,
                        "account_id": tok.account_id,
                    }
                )
                providers_update: dict = {
                    provider: {"api_key": token_json},
                }
                # chatgpt and openai_codex share the same OpenAI login — store in both
                sibling = {"chatgpt": "openai_codex", "openai_codex": "chatgpt"}.get(provider)
                if sibling:
                    providers_update[sibling] = {"api_key": token_json}
                agent_config_store.update_config(agent_id, {"providers": providers_update})
                logger.info("OAuth [{}] token saved to agent {}", provider, agent_id)
        except Exception as exc:
            logger.warning("OAuth [{}] error: {}", provider, exc)
            if not url_ready.done():
                url_ready.set_exception(exc)

    asyncio.create_task(_bg())

    try:
        auth_url = await asyncio.wait_for(asyncio.shield(url_ready), timeout=15.0)
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Timed out starting OAuth flow (could not start callback container).",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"OAuth authorization failed: {str(exc)[:200]}",
        )

    return {"auth_url": auth_url}
