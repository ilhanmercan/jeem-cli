# jeem-cli

Unofficial CLI for [jeem.ai](https://jeem.ai) — a conversational search engine. Ask questions and get streaming answers directly in your terminal.

## Disclaimer

This is **not an official jeem.ai product**. The API endpoint used is public and undocumented. It may change or become rate-limited at any time without notice. This tool is not affiliated with, endorsed by, or associated with jeem.ai.

## Install

Requires Python 3.10+.

```bash
git clone https://github.com/YOUR_USERNAME/jeem-cli.git
cd jeem-cli
uv tool install --editable .
```

Or with pip:

```bash
pipx install --editable .
```

## Usage

### Single question

```bash
jeem ask "what is the capital of France?"
```

Streams the answer in real-time as tokens arrive.

### Buffer mode

```bash
jeem ask "explain quantum computing" --no-stream
```

Waits for the full response, then prints it at once.

### Multi-turn conversations

```bash
jeem ask "my name is Alice" --session chat_name
jeem ask "what is my name?" --session chat_name
```

Sessions persist to `~/.jeem/sessions/` and survive restarts.

### Raw JSON output

```bash
jeem ask "hi" --json
```

Emits each SSE event as a JSON line — useful for piping or debugging.

### Session management

```bash
jeem session list             # list all sessions
jeem session show <name>      # show messages in a session
jeem session delete <name>    # delete a session
jeem session delete --all     # delete all sessions
```
