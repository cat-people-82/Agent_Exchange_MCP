"""Thin wrappers that send a message history to a provider and return text."""

import anthropic
import openai

from .config import Provider

Messages = list[dict[str, str]]


class ProviderError(RuntimeError):
    pass


def complete(p: Provider, model: str, system: str | None, messages: Messages,
             max_tokens: int, effort: str) -> str:
    if not p.api_key:
        raise ProviderError(
            f"No API key for provider '{p.name}'. Set {p.name.upper()}_API_KEY in "
            "the .env file (or the client's env settings)."
        )
    if p.kind == "anthropic":
        return _anthropic(p, model, system, messages, max_tokens, effort)
    if p.kind == "openai":
        return _openai(p, model, system, messages, max_tokens)
    raise ProviderError(f"Unknown provider kind '{p.kind}'")


def _anthropic(p, model, system, messages, max_tokens, effort) -> str:
    kwargs = {"system": system} if system else {}
    try:
        with anthropic.Anthropic(api_key=p.api_key, base_url=p.base_url).messages.stream(
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


def _openai(p, model, system, messages, max_tokens) -> str:
    msgs = ([{"role": "system", "content": system}] if system else []) + messages
    # OpenAI proper wants max_completion_tokens; other compatible APIs (xAI) use max_tokens.
    limit = "max_completion_tokens" if p.name == "openai" else "max_tokens"
    try:
        resp = openai.OpenAI(api_key=p.api_key, base_url=p.base_url).chat.completions.create(
            model=model, messages=msgs, **{limit: max_tokens}
        )
    except openai.RateLimitError:
        raise ProviderError(f"{p.name} rate limit hit; retry shortly.")
    except openai.APIStatusError as e:
        raise ProviderError(f"{p.name} API error {e.status_code}: {e.message}")
    except openai.APIConnectionError as e:
        raise ProviderError(f"Could not reach the {p.name} API: {e}")

    choice = resp.choices[0]
    text = choice.message.content or ""
    if choice.finish_reason == "length":
        text += "\n\n[truncated: max_tokens reached]"
    return text
