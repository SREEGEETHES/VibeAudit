# VibeAudit 🔍

AI-generated code reviewer for vibe coders. Local. Private. No cloud.

## The Problem

You vibe-coded 3,000 lines using Cursor/Claude. It works in testing.
But no one reviewed it. Is there a race condition? An injection hole? A logic bomb?
You don't know. You ship anyway.

VibeAudit gives you an honest senior engineer review — in 30 seconds, locally.

## Features

### What it reviews
- **Security** — injection, auth issues, exposed secrets, input validation
- **Logic** — wrong assumptions, race conditions, null errors, edge cases
- **Scalability** — N+1 queries, memory leaks, unbounded loops, missing pagination
- **Code Quality** — missing error handling, hardcoded values, dead code

### Second Brain
- **Persistent storage** — All audits saved to local SQLite database
- **Test Cases** — Save reusable test case templates
- **Criteria** — Custom review criteria checklists
- **Obsidian Sync** — Export audits to your Obsidian vault

### Privacy
- **100% local** with Ollama — code never leaves your machine
- **Cloud options** available: Anthropic, OpenAI, Kimi, MiniMax

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py
```

Go to **Settings** → configure your AI provider → go to **Audit** → paste code → Run

## AI Providers

| Provider | Cost | Privacy | Setup |
|----------|------|---------|-------|
| Ollama (recommended) | Free | 100% local | Install from ollama.ai, run `ollama serve`, pull a model |
| Anthropic Claude | Paid | API call | Get key at console.anthropic.com |
| OpenAI GPT-4o | Paid | API call | Get key at platform.openai.com |
| Kimi (Moonshot) | Free tier | API call | Get key at platform.moonshot.cn |
| MiniMax | Free tier | API call | Get key at platform.minimax.chat |

## Recommended Ollama Models

```bash
# Best for code understanding
ollama pull deepseek-coder

# General code review
ollama pull codellama

# Balanced option
ollama pull llama3
```

## Supported Languages

Python, JavaScript, TypeScript, React, Go, Rust, Java, Ruby, PHP,
C, C++, C#, Swift, Kotlin, SQL, Shell, YAML, JSON, HTML, CSS

## Second Brain Usage

1. **Save audits** — After each review, click "Save to Second Brain"
2. **View history** — Go to Brain page to see all past audits
3. **Add test cases** — Save templates for common testing scenarios
4. **Add criteria** — Create custom review checklists
5. **Export to Obsidian** — Set your vault path in Settings, then export

## Config Location

Settings are stored in: `~/.vibeaudit/config.json`
Brain database is at: `~/.vibeaudit/brain.db`

## License

MIT — free for everyone