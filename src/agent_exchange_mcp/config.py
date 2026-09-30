"""Provider configuration: TOML file plus environment-variable fallbacks."""

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

DEFAULT_CONFIG_PATH = Path.home() / ".config" / "agent-exchange" / "config.toml"

# kind: "anthropic" uses the Anthropic SDK; "openai" means an OpenAI-compatible API.
BUILTIN = {
    "anthropic": {
        "kind": "anthropic",
        "api_key_env": "ANTHROPIC_API_KEY",
        "model": "claude-opus-5-5",
    },
    "openai": {
        "kind": "openai",
        "api_key_env": "OPENAI_API_KEY",
        "model": "gpt-5",
    },
    "xai": {
        "kind": "openai",
        "api_key_env": "XAI_API_KEY",
        "base_url": "https://api.x.ai/v1",
        "model": "grok-4",
    },
}


@dataclass
class Provider:
    name: str
    kind: str
    model: str
    api_key: str | None
    base_url: str | None = None


@dataclass
class Config:
    default_provider: str
    providers: dict[str, Provider]


def load_config() -> Config:
    path = Path(os.environ.get("AGENT_EXCHANGE_CONFIG", DEFAULT_CONFIG_PATH))
    raw: dict = {}
    if path.is_file():
        with path.open("rb") as f:
            raw = tomllib.load(f)

    merged = {name: dict(spec) for name, spec in BUILTIN.items()}
    for name, spec in raw.get("providers", {}).items():
        merged.setdefault(name, {}).update(spec)

    providers = {}
    for name, spec in merged.items():
        # An inline `api_key` wins; otherwise read the env var named by `api_key_env`.
        key = spec.get("api_key") or os.environ.get(spec.get("api_key_env", ""))
        if "kind" not in spec or "model" not in spec:
            raise ValueError(f"Provider '{name}' needs 'kind' and 'model' in {path}")
        providers[name] = Provider(
            name=name,
            kind=spec["kind"],
            model=spec["model"],
            api_key=key,
            base_url=spec.get("base_url"),
        )

    default = os.environ.get("AGENT_EXCHANGE_PROVIDER") or raw.get(
        "default_provider", "anthropic"
    )
    if default not in providers:
        raise ValueError(f"default_provider '{default}' is not a configured provider")
    return Config(default_provider=default, providers=providers)
