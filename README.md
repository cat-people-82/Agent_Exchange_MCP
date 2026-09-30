# Agent_Exchange_MCP

MCP server that lets an MCP client (Claude Code, Claude Desktop, ...) call a Claude model through the Anthropic API.

## Tool

- `ask_claude(prompt, system?, model?, max_tokens?, effort?)` — returns the model's text reply.

## Setup

```bash
pip install -e .
export ANTHROPIC_API_KEY=sk-ant-...
agent-exchange-mcp        # runs over stdio
```

Optional: `AGENT_EXCHANGE_MODEL` overrides the default model (`claude-opus-5-5`).

## Register with Claude Code

```bash
claude mcp add agent-exchange -e ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY -- agent-exchange-mcp
```
