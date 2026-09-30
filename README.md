# Agent_Exchange_MCP

MCP server that lets an MCP client (Claude Code, Claude Desktop, ...) call a Claude model through the Anthropic API.

## Tools

- `chat(message, conversation_id?, provider?, model?, system?, max_tokens?, effort?)` — send a message to Anthropic, OpenAI, xAI (or any configured OpenAI-compatible provider). Omit `conversation_id` to start a conversation; pass the returned id to continue it. You can switch provider between turns.
- `list_providers()` — configured providers, default models, whether a key is set.
- `list_conversations()` / `reset_conversation(id)` — manage in-memory conversations (lost when the server restarts).

## Setup

```bash
pip install -e .
export ANTHROPIC_API_KEY=... OPENAI_API_KEY=... XAI_API_KEY=...
agent-exchange-mcp        # runs over stdio
```

## Configuration

API keys come from environment variables by default. To change the default provider, models, or add providers, copy `config.example.toml` to `~/.config/agent-exchange/config.toml` (or set `AGENT_EXCHANGE_CONFIG`). Keys may be set inline with `api_key` or via `api_key_env`. `AGENT_EXCHANGE_PROVIDER` overrides the default provider.

Model IDs for OpenAI/xAI are defaults you should adjust to what your account offers.

## Register with Claude Code

```bash
claude mcp add agent-exchange -e ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY -e OPENAI_API_KEY=$OPENAI_API_KEY -e XAI_API_KEY=$XAI_API_KEY -- agent-exchange-mcp
```
