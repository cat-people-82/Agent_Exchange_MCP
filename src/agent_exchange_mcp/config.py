"""Provider configuration, read from environment variables (optionally via a .env file)."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# kind: "anthropic" uses the Anthropic SDK; "openai" means an OpenAI-compatible API.
# Each provider is configured by <NAME>_API_KEY, <NAME>_MODEL and <NAME>_BASE_URL.
PROVIDERS = {
    "anthropic": {"kind": "anthropic", "model": "claude-opus-5-5", "base_url": None},
    "openai": {"kind": "openai", "model": "gpt-5", "base_url": None},
    "xai": {"kind": "openai", "model": "grok-4", "base_url": "https://api.x.ai/v1"},
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
    data_dir: Path
    env_files: list[tuple[str, bool]]  # (.env path checked, found?)


def load_config() -> Config:
    # Existing environment variables win over .env values (override=False).
    explicit = os.environ.get("AGENT_EXCHANGE_ENV_FILE")
    candidates = [Path(explicit)] if explicit else [PROJECT_ROOT / ".env", Path.cwd() / ".env"]
    env_files = []
    for path in candidates:
        try:
            found = path.is_file()
            if found:
                load_dotenv(path)
        except OSError:  # e.g. blocked by an app sandbox
            found = False
        env_files.append((str(path), found))

    providers = {}
    for name, spec in PROVIDERS.items():
        prefix = name.upper()
        providers[name] = Provider(
            name=name,
            kind=spec["kind"],
            model=os.environ.get(f"{prefix}_MODEL") or spec["model"],
            api_key=os.environ.get(f"{prefix}_API_KEY") or None,
            base_url=os.environ.get(f"{prefix}_BASE_URL") or spec["base_url"],
        )

    # Fallback when the client doesn't pick a provider: the first one with a key.
    default = next((n for n, p in providers.items() if p.api_key), "anthropic")
    data_dir = Path(
        os.environ.get("AGENT_EXCHANGE_DATA_DIR")
        or Path.home() / ".local" / "share" / "agent-exchange" / "conversations"
    ).expanduser()
    return Config(default_provider=default, providers=providers, data_dir=data_dir, env_files=env_files)
