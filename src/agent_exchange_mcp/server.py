"""MCP server that lets a client talk to other AI models (Anthropic, OpenAI, xAI, ...)."""

import asyncio
import uuid
from typing import Literal

from mcp.server.fastmcp import Context, FastMCP
from pydantic import Field, create_model

from . import providers
from .config import Config, load_config
from .store import Conversation, Store

mcp = FastMCP("agent-exchange")
_config: Config | None = None


_store: Store | None = None


def _cfg() -> Config:
    global _config
    if _config is None:
        _config = load_config()
    return _config


def _conversations() -> Store:
    global _store
    if _store is None:
        _store = Store(_cfg().data_dir)
    return _store


ProviderName = Literal["anthropic", "openai", "xai"]  # shown as a choice list by clients


async def _pick_provider(ctx: Context, cfg: Config) -> str:
    """Resolve the provider for a new conversation, asking the user via the client UI."""
    ready = [n for n, p in cfg.providers.items() if p.api_key]
    if len(ready) <= 1:
        return cfg.default_provider
    choice = create_model(
        "ProviderChoice",
        provider=(
            Literal[tuple(ready)],  # type: ignore[valid-type]
            Field(description="Which AI provider should answer?"),
        ),
    )
    try:
        result = await ctx.elicit("Which AI provider should answer this conversation?", choice)
    except Exception:
        return cfg.default_provider  # client doesn't support elicitation
    if result.action != "accept":
        raise ValueError("Provider selection was declined or cancelled.")
    return result.data.provider


@mcp.tool()
async def chat(
    message: str,
    ctx: Context,
    conversation_id: str | None = None,
    provider: ProviderName | None = None,
    model: str | None = None,
    system: str | None = None,
    max_tokens: int = 16000,
    effort: Literal["low", "medium", "high", "xhigh", "max"] = "medium",
) -> dict:
    """Send a message to another AI model and get its reply.

    Omit conversation_id to start a new conversation; pass the returned
    conversation_id to continue it (history is saved to disk, and you may switch
    provider between turns).

    Args:
        message: The user message.
        conversation_id: Continue an existing conversation.
        provider: Provider to use. If omitted: a continued conversation keeps its last
            provider; a new one asks the user to choose (via the client UI when supported).
        model: Model ID override for this turn.
        system: System prompt (only applied when starting a conversation).
        max_tokens: Maximum tokens in the reply.
        effort: Thinking effort (Anthropic only; ignored by other providers).
    """
    cfg = _cfg()
    store = _conversations()
    if conversation_id:
        convo = store.load(conversation_id)
    else:
        conversation_id = uuid.uuid4().hex[:12]
        convo = Conversation(system=system)

    name = provider or convo.provider or await _pick_provider(ctx, cfg)
    if name not in cfg.providers:
        raise ValueError(f"Unknown provider '{name}'. Available: {sorted(cfg.providers)}")
    p = cfg.providers[name]

    used_model = model or p.model
    history = convo.messages + [{"role": "user", "content": message}]
    reply = await asyncio.to_thread(
        providers.complete, p, used_model, convo.system, history, max_tokens, effort
    )
    # Only commit the turn once the call succeeded, so failures leave history intact.
    convo.messages = history + [{"role": "assistant", "content": reply}]
    convo.provider = name
    store.save(conversation_id, convo)
    return {"conversation_id": conversation_id, "provider": name, "model": used_model, "reply": reply}


@mcp.tool()
def list_providers() -> list[dict]:
    """List configured providers, their default models, and whether an API key is set."""
    cfg = _cfg()
    return [
        {"name": n, "model": p.model, "kind": p.kind,
         "has_api_key": bool(p.api_key), "default": n == cfg.default_provider}
        for n, p in cfg.providers.items()
    ]


@mcp.tool()
def list_conversations() -> list[dict]:
    """List active conversations (id, turn count, system prompt)."""
    store = _conversations()
    out = []
    for cid in store.list_ids():
        c = store.load(cid)
        out.append({"conversation_id": cid, "turns": len(c.messages) // 2, "system": c.system})
    return out


@mcp.tool()
def reset_conversation(conversation_id: str) -> str:
    """Delete a conversation and its history."""
    _conversations().delete(conversation_id)
    return "deleted"


def main() -> None:
    mcp.run()  # stdio transport


if __name__ == "__main__":
    main()
