"""MCP server exposing Claude (via the Anthropic API) as a tool."""

import os
from typing import Literal

import anthropic
from mcp.server.fastmcp import FastMCP

DEFAULT_MODEL = os.environ.get("AGENT_EXCHANGE_MODEL", "claude-opus-5-5")

mcp = FastMCP("agent-exchange")
_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    # Credentials resolve from ANTHROPIC_API_KEY (or an `ant auth login` profile).
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


@mcp.tool()
def ask_claude(
    prompt: str,
    system: str | None = None,
    model: str | None = None,
    max_tokens: int = 16000,
    effort: Literal["low", "medium", "high", "xhigh", "max"] = "medium",
) -> str:
    """Send a prompt to another Claude model and return its text reply.

    Args:
        prompt: The message to send.
        system: Optional system prompt.
        model: Model ID (defaults to AGENT_EXCHANGE_MODEL or claude-opus-5-5).
        max_tokens: Maximum tokens in the reply.
        effort: How much thinking/effort the model should spend.
    """
    kwargs = {}
    if system:
        kwargs["system"] = system
    try:
        with _get_client().messages.stream(
            model=model or DEFAULT_MODEL,
            max_tokens=max_tokens,
            thinking={"type": "adaptive"},
            output_config={"effort": effort},
            messages=[{"role": "user", "content": prompt}],
            **kwargs,
        ) as stream:
            response = stream.get_final_message()
    except anthropic.RateLimitError:
        raise RuntimeError("Anthropic API rate limit hit; retry shortly.")
    except anthropic.APIStatusError as e:
        raise RuntimeError(f"Anthropic API error {e.status_code}: {e.message}")
    except anthropic.APIConnectionError as e:
        raise RuntimeError(f"Could not reach the Anthropic API: {e}")

    if response.stop_reason == "refusal":
        raise RuntimeError("The model declined to answer this request.")
    text = "".join(b.text for b in response.content if b.type == "text")
    if response.stop_reason == "max_tokens":
        text += "\n\n[truncated: max_tokens reached]"
    return text


def main() -> None:
    mcp.run()  # stdio transport


if __name__ == "__main__":
    main()
