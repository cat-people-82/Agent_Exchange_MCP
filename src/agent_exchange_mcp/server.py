"""MCP server that lets a client talk to other AI models (Anthropic, OpenAI, xAI, ...)."""

import uuid
from dataclasses import dataclass, field
from typing import Literal

from mcp.server.fastmcp import FastMCP

from . import providers
from .config import Config, load_config

mcp = FastMCP("agent-exchange")
_config: Config | None = None


@dataclass
class Conversation:
    system: str | None = None
    messages: list[dict[str, str]] = field(default_factory=list)


# In-memory only: conversations last as long as the server process.
_conversations: dict[str, Conversation] = {}


def _cfg() -> Config:
    global _config
    if _config is None:
        _config = load_config()
    return _config


@mcp.tool()
def chat(
    message: str,
    conversation_id: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    system: str | None = None,
    max_tokens: int = 16000,
    effort: Literal["low", "medium", "high", "xhigh", "max"] = "medium",
) -> dict:
    """Send a message to another AI model and get its reply.

    Omit conversation_id to start a new conversation; pass the returned
    conversation_id to continue it (history is kept, and you may switch
    provider between turns).

    Args:
        message: The user message.
        conversation_id: Continue an existing conversation.
        provider: Provider name (see list_providers); defaults to the configured default.
        model: Model ID override for this turn.
        system: System prompt (only applied when starting a conversation).
        max_tokens: Maximum tokens in the reply.
        effort: Thinking effort (Anthropic only; ignored by other providers).
    """
    cfg = _cfg()
    name = provider or cfg.default_provider
    if name not in cfg.providers:
        raise ValueError(f"Unknown provider '{name}'. Available: {sorted(cfg.providers)}")
    p = cfg.providers[name]

    if conversation_id:
        if conversation_id not in _conversations:
            raise ValueError(f"Unknown conversation_id '{conversation_id}'")
        convo = _conversations[conversation_id]
    else:
        conversation_id = uuid.uuid4().hex[:12]
        convo = _conversations[conversation_id] = Conversation(system=system)

    used_model = model or p.model
    history = convo.messages + [{"role": "user", "content": message}]
    reply = providers.complete(p, used_model, convo.system, history, max_tokens, effort)
    # Only commit the turn once the call succeeded, so failures leave history intact.
    convo.messages = history + [{"role": "assistant", "content": reply}]
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
    return [
        {"conversation_id": cid, "turns": len(c.messages) // 2, "system": c.system}
        for cid, c in _conversations.items()
    ]


@mcp.tool()
def reset_conversation(conversation_id: str) -> str:
    """Delete a conversation and its history."""
    if _conversations.pop(conversation_id, None) is None:
        raise ValueError(f"Unknown conversation_id '{conversation_id}'")
    return "deleted"


def main() -> None:
    mcp.run()  # stdio transport


if __name__ == "__main__":
    main()
