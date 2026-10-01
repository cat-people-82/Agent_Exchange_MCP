"""Thin wrappers that send a message history to a provider and return text."""

import os

import anthropic
import certifi
import openai

from .config import Provider

Messages = list[dict[str, str]]


class ProviderError(RuntimeError):
    pass


def _cause(exc: BaseException, depth: int = 4) -> str:
    """Render an exception with its chained causes, for diagnosable errors."""
    parts, seen = [], set()
    e: BaseException | None = exc
    while e is not None and len(parts) < depth and id(e) not in seen:
        seen.add(id(e))
        text = str(e).strip()
        parts.append(f"{type(e).__name__}: {text}" if text else type(e).__name__)
        e = e.__cause__ or e.__context__
    return " <- ".join(parts)


def _ca_bundle() -> str:
    """CA bundle to verify TLS against.

    The SDKs' default client verifies through the OS trust store (httpx 2.x uses
    truststore, which on macOS calls the Security framework and can fail with a
    bare OSStatus error even for a valid public certificate). Verifying against
    certifi instead is deterministic and works for the public endpoints used here.
    Set AGENT_EXCHANGE_CA_BUNDLE to use a different bundle, e.g. behind a TLS
    terminating corporate proxy whose CA is not in certifi.
    """
    return os.environ.get("AGENT_EXCHANGE_CA_BUNDLE") or certifi.where()


def _http_kwargs(ignore_proxy: bool) -> dict:
    # trust_env=False makes the HTTP client ignore ALL_PROXY/HTTPS_PROXY/etc.
    kwargs: dict = {"verify": _ca_bundle()}
    if ignore_proxy:
        kwargs["trust_env"] = False
    return kwargs


def _anthropic_client(p: Provider, ignore_proxy: bool) -> anthropic.Anthropic:
    http = anthropic.DefaultHttpxClient(**_http_kwargs(ignore_proxy))
    return anthropic.Anthropic(api_key=p.api_key, base_url=p.base_url, http_client=http)


def _openai_client(p: Provider, ignore_proxy: bool) -> openai.OpenAI:
    http = openai.DefaultHttpxClient(**_http_kwargs(ignore_proxy))
    return openai.OpenAI(api_key=p.api_key, base_url=p.base_url, http_client=http)


def complete(p: Provider, model: str, system: str | None, messages: Messages,
             max_tokens: int, effort: str, ignore_proxy: bool = False) -> str:
    if not p.api_key:
        raise ProviderError(
            f"No API key for provider '{p.name}'. Set {p.name.upper()}_API_KEY in "
            "the .env file or the client's environment-variable settings, then reconnect "
            "the server (config is read at startup). Call server_info to see where it looked."
        )
    if p.kind == "anthropic":
        return _anthropic(p, model, system, messages, max_tokens, effort, ignore_proxy)
    if p.kind == "openai":
        return _openai(p, model, system, messages, max_tokens, ignore_proxy)
    raise ProviderError(f"Unknown provider kind '{p.kind}'")


def _anthropic(p, model, system, messages, max_tokens, effort, ignore_proxy) -> str:
    kwargs = {"system": system} if system else {}
    try:
        with _anthropic_client(p, ignore_proxy).messages.stream(
            model=model,
            max_tokens=max_tokens,
            thinking={"type": "adaptive"},
            output_config={"effort": effort},
            messages=messages,
            **kwargs,
        ) as stream:
            response = stream.get_final_message()
    except anthropic.RateLimitError:
        raise ProviderError("Anthropic rate limit hit; retry shortly.")
    except anthropic.APIStatusError as e:
        raise ProviderError(f"Anthropic API error {e.status_code}: {e.message}")
    except anthropic.APIConnectionError as e:
        raise ProviderError(f"Could not reach the Anthropic API: {e}")

    if response.stop_reason == "refusal":
        raise ProviderError("The model declined to answer this request.")
    text = "".join(b.text for b in response.content if b.type == "text")
    if response.stop_reason == "max_tokens":
        text += "\n\n[truncated: max_tokens reached]"
    return text


def _openai(p, model, system, messages, max_tokens, ignore_proxy) -> str:
    msgs = ([{"role": "system", "content": system}] if system else []) + messages
    # OpenAI proper wants max_completion_tokens; other compatible APIs (xAI) use max_tokens.
    limit = "max_completion_tokens" if p.name == "openai" else "max_tokens"
    try:
        resp = _openai_client(p, ignore_proxy).chat.completions.create(
            model=model, messages=msgs, **{limit: max_tokens}
        )
    except openai.RateLimitError:
        raise ProviderError(f"{p.name} rate limit hit; retry shortly.")
    except openai.APIStatusError as e:
        raise ProviderError(f"{p.name} API error {e.status_code}: {e.message}")
    except openai.APIConnectionError as e:
        # The SDK's own message is a bare "Connection error."; the useful detail
        # (proxy refusal, DNS failure, TLS error) is on the chained cause.
        raise ProviderError(f"Could not reach the {p.name} API: {_cause(e)}")

    choice = resp.choices[0]
    text = choice.message.content or ""
    if choice.finish_reason == "length":
        text += "\n\n[truncated: max_tokens reached]"
    return text
