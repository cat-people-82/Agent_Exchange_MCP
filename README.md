# Agent_Exchange_MCP

An [MCP](https://modelcontextprotocol.io) server that lets an AI client (Claude Code, Claude Desktop, …) talk to *other* AI models through their APIs. Supports Anthropic, OpenAI and xAI, with multi-turn conversations saved to disk.

## Features

- **Multiple providers** — Anthropic (Claude), OpenAI, xAI (Grok). Switch provider per call, even mid-conversation.
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
| `AGENT_EXCHANGE_PROVIDER` | `anthropic` | Provider used when `chat` gets no `provider` (`anthropic`, `openai`, `xai`) |
| `AGENT_EXCHANGE_DATA_DIR` | `~/.local/share/agent-exchange/conversations` | Where conversations are saved |
| `ANTHROPIC_API_KEY` / `ANTHROPIC_MODEL` | – / `claude-opus-5-5` | Anthropic credentials and default model |
| `OPENAI_API_KEY` / `OPENAI_MODEL` / `OPENAI_BASE_URL` | – / `gpt-5` / OpenAI | OpenAI settings |
| `XAI_API_KEY` / `XAI_MODEL` / `XAI_BASE_URL` | – / `grok-4` / `https://api.x.ai/v1` | xAI settings |

You only need keys for the providers you use. Adjust the default OpenAI/xAI model IDs to whatever your account offers.

## Register with an MCP client

Claude Code:

```bash
claude mcp add agent-exchange -- agent-exchange-mcp
```

Claude Desktop (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "agent-exchange": { "command": "agent-exchange-mcp" }
  }
}
```

Use the full path to the `agent-exchange-mcp` executable if it isn't on the client's `PATH` (e.g. when installed in a virtualenv). Keys are picked up from the project's `.env`, or you can pass them via the client's `env` setting.

## Tools

| Tool | Description |
|---|---|
| `chat(message, conversation_id?, provider?, model?, system?, max_tokens?, effort?)` | Send a message and get the reply. Omit `conversation_id` to start a new conversation; pass the returned id to continue it. `system` applies only when starting a conversation. `effort` (`low`…`max`) applies to Anthropic only. |
| `list_providers()` | Configured providers, default models, and whether a key is set. |
| `list_conversations()` | Saved conversations (id, turns, system prompt). |
| `reset_conversation(conversation_id)` | Delete a conversation. |

`chat` returns `{conversation_id, provider, model, reply}`.

Example flow: ask Claude a question, then continue the same conversation with `provider: "xai"` to get Grok's take with the full history.

## Storage

Conversations are stored as `<conversation_id>.json` (system prompt + message list) in the data directory. Files are plain text and contain your prompts and replies, so protect the directory accordingly. Delete a conversation with `reset_conversation` or by removing its file.

## Notes

- If a provider call fails, the turn is not saved, so history stays consistent.
- Anthropic calls use adaptive thinking and streaming; OpenAI and xAI use the Chat Completions API.
