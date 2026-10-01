# Agent_Exchange_MCP

An [MCP](https://modelcontextprotocol.io) server that lets an AI client (Claude Code, Claude Desktop, …) talk to *other* AI models through their APIs. Supports Anthropic, OpenAI and xAI, with multi-turn conversations saved to disk.

## Features

- **Multiple providers** — Anthropic (Claude), OpenAI, xAI (Grok). Choose the provider from the client UI, and switch it per call, even mid-conversation.
- **Multi-turn conversations** — history is kept per `conversation_id`.
- **Persistent** — each conversation is a JSON file on disk and survives server restarts.
- **Simple config** — API keys and models live in a `.env` file.

## Installation

Requires Python 3.11+.

```bash
git clone https://github.com/cat-people-82/Agent_Exchange_MCP.git
cd Agent_Exchange_MCP
pip install -e .
cp .env.example .env    # then add your API keys
```

## Configuration

Settings are read from `.env` in the project root (or the current directory, or the file named by `AGENT_EXCHANGE_ENV_FILE`). Real environment variables take precedence over `.env`. `.env` is git-ignored — never commit it.

| Variable | Default | Purpose |
|---|---|---|
| `AGENT_EXCHANGE_DATA_DIR` | `~/.local/share/agent-exchange/conversations` | Where conversations are saved |
| `ANTHROPIC_API_KEY` / `ANTHROPIC_MODEL` | – / `claude-opus-5-5` | Anthropic credentials and default model |
| `OPENAI_API_KEY` / `OPENAI_MODEL` / `OPENAI_BASE_URL` | – / `gpt-5` / OpenAI | OpenAI settings |
| `XAI_API_KEY` / `XAI_MODEL` / `XAI_BASE_URL` | – / `grok-4` / `https://api.x.ai/v1` | xAI settings |

Provider selection is *not* configured here — it happens in the client (see below). `.env` only holds API keys, models and the data directory. You only need keys for the providers you use. Adjust the default OpenAI/xAI model IDs to whatever your account offers.

## Register with an MCP client

Claude Code:

```bash
claude mcp add agent-exchange -- agent-exchange-mcp
```

Claude Desktop — edit `claude_desktop_config.json` (Settings → Developer → Edit Config). `command` must be an **executable** (not the path to `server.py`), so point it at the Python interpreter of the environment where you ran `pip install -e .` and run the package as a module:

```json
{
  "mcpServers": {
    "agent-exchange": {
      "command": "/absolute/path/to/Agent_Exchange_MCP/.venv/bin/python",
      "args": ["-m", "agent_exchange_mcp"]
    }
  }
}
```

Tips:
- Create the environment first: `python3 -m venv .venv && .venv/bin/pip install -e .` (find an existing interpreter's path with `which python` while its environment is active).
- Claude Desktop doesn't inherit your shell environment; keys are read from the project's `.env`, or pass them via an `"env": { "ANTHROPIC_API_KEY": "..." }` entry.
- Fully quit and reopen Claude Desktop after editing the config. Logs are in `~/Library/Logs/Claude/mcp-server-agent-exchange.log`.

## Tools

| Tool | Description |
|---|---|
| `chat(message, conversation_id?, provider?, model?, system?, max_tokens?, effort?)` | Send a message and get the reply. Omit `conversation_id` to start a new conversation; pass the returned id to continue it. `system` applies only when starting a conversation. `effort` (`low`…`max`) applies to Anthropic only. |
| `list_providers()` | Configured providers, default models, and whether a key is set. |
| `server_info()` | Diagnose config: which `.env` files were checked/found, data dir, and which providers have a key. |
| `list_conversations()` | Saved conversations (id, turns, system prompt). |
| `reset_conversation(conversation_id)` | Delete a conversation. |

`chat` returns `{conversation_id, provider, model, reply}`.

Example flow: ask Claude a question, then continue the same conversation with `provider: "xai"` to get Grok's take with the full history.

## Choosing a provider

The provider is picked in your MCP client, not in config:

- `chat` has a `provider` parameter (`anthropic` | `openai` | `xai`), which clients show as a choice list and which the calling model or you can set.
- If it is omitted when **starting** a conversation and more than one provider has an API key, the server asks you to choose through the client's prompt (MCP *elicitation*, supported by clients such as Claude Code).
- If the client doesn't support elicitation, or only one provider has a key, the first provider with a key is used.
- A **continued** conversation keeps its last provider unless you pass a different one.

## Storage

Conversations are stored as `<conversation_id>.json` (system prompt + message list) in the data directory. Files are plain text and contain your prompts and replies, so protect the directory accordingly. Delete a conversation with `reset_conversation` or by removing its file.

## Notes

- If a provider call fails, the turn is not saved, so history stays consistent.
- Anthropic calls use adaptive thinking and streaming; OpenAI and xAI use the Chat Completions API.
