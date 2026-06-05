# Nokton

A local-first, voice-activated desktop AI agent. Think JARVIS for your PC — runs entirely on your machine, uses your API keys, controls your desktop.

## What It Does

- **Wake word**: Say "Hey Nokton" to activate (offline, free, OpenWakeWord)
- **Voice I/O**: Local speech-to-text (faster-whisper) + streaming text-to-speech (edge-tts)
- **Any LLM**: OpenCode Zen, OpenRouter, OpenAI, Anthropic, Google, Groq, Ollama, or any OpenAI-compatible endpoint
- **Desktop control**: 29 tools — files, apps, web search, clipboard, terminal, screenshots, OCR, system controls
- **Reasoning**: Off / High / X-High per model (maps to each provider's native params)
- **Vision fallback**: Text-only models "see" via separate vision model
- **Interrupt**: Say "stop" or click cancel — aborts LLM stream, kills running tools
- **Conversations**: Persistent history, search, export (JSON/Markdown)
- **Privacy**: Encrypted API keys (AES-256), audit logs, local-first everything

## Quick Start

```bash
# Windows
scripts\install.bat
scripts\run.bat

# Or manually
pip install -r requirements.txt
cd frontend && npm install && cd ..
# Add your API keys to ~/.nokton/nokton.json
python -m backend.main &
cd frontend && npm start
```

## Configuration

Copy `nokton.json` to `~/.nokton/nokton.json` and add your API keys:

```json
{
  "model": {
    "provider": "opencode",
    "model": "opencode/zen",
    "reasoning_effort": "high"
  },
  "providers": {
    "opencode": { "api_key": "your-zen-key" },
    "openrouter": { "api_key": "your-openrouter-key" },
    "openai": { "api_key": "your-openai-key" },
    "anthropic": { "api_key": "your-anthropic-key" },
    "google": { "api_key": "your-google-key" },
    "groq": { "api_key": "your-groq-key" },
    "ollama": { "base_url": "http://localhost:11434/v1" }
  }
}
```

Or set via environment variables:
- `OPENCODE_API_KEY`, `OPENROUTER_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`, `GROQ_API_KEY`

## Providers Supported

| Provider | Models | Reasoning | Vision | Free Tier |
|----------|--------|-----------|--------|-----------|
| OpenCode | 200+ | Native (Zen) | Yes | Zen plan |
| OpenRouter | 200+ | effort: high/xhigh | Yes | Many `:free` |
| OpenAI | GPT-4o, o3 | effort: high/xhigh | Yes | No |
| Anthropic | Claude 4 | thinking budgets | Yes | No |
| Google | Gemini 2.5 | thinking levels | Yes | Free tier |
| Groq | Llama, Mixtral | effort: high | No | Free tier |
| Ollama | Any local | context scaling | Some | Free |
| Custom | Any OpenAI-compat | Pass-through | Depends | Your infra |

## Tools Included

| Category | Tools |
|----------|-------|
| **Files** | list, read, write, search, create, delete, move, copy |
| **Apps** | launch, close, list processes, kill |
| **System** | CPU/RAM/disk/battery, volume, shutdown, restart |
| **Web** | DuckDuckGo search, fetch page, extract links |
| **Clipboard** | get, set, type text |
| **Screenshots** | capture screen, OCR screen |
| **Terminal** | cmd, PowerShell |
| **Windows** | list, focus, minimize, maximize |

## Architecture

```
┌─────────────┐     WebSocket      ┌─────────────┐
│  Electron   │ ◄────────────────► │   FastAPI   │
│   + React   │   (streaming,      │  + Agent    │
└─────────────┘    tools, voice)   └──────┬──────┘
                                          │
                    ┌─────────────────────┼─────────────────────┐
                    ▼                     ▼                     ▼
             ┌─────────────┐       ┌─────────────┐       ┌─────────────┐
             │  Providers  │       │    Tools    │       │   Voice     │
             │ (8+ LLMs)   │       │  (29 tools) │       │ (STT/TTS/   │
             └─────────────┘       └─────────────┘       │  Wake/VAD)  │
                                                         └─────────────┘
```

## Project Structure

```
nokton/
├── backend/                 # Python FastAPI + Agent
│   ├── main.py             # WebSocket server, REST API
│   ├── config.py           # Config loading (defaults → user → env)
│   ├── agent/              # Agent engine, conversation, compression
│   ├── providers/          # 8 LLM providers + registry
│   ├── tools/              # 29 tools + registry, schema, permissions
│   ├── voice/              # STT, TTS, Wake word, VAD
│   └── util/               # API keys (encrypted), audit log, images
├── frontend/               # Electron + React
│   ├── main.js             # Electron main, backend lifecycle
│   ├── preload.js          # IPC bridge
│   └── src/                # React app (components, hooks, stores)
├── scripts/                # install.bat, run.bat
├── skills/                 # SKILL.md files (extensible)
├── nokton.json             # Default config
└── requirements.txt        # Python deps
```

## Development

```bash
# Backend
cd backend && python -m main

# Frontend (dev mode with hot reload)
cd frontend && npm run dev

# Build frontend
cd frontend && npm run build

# Package Electron app
cd frontend && npm run package
```

## Contributing

1. Fork and clone
2. Create feature branch
3. Make changes (one logical change per commit)
4. Run lint/typecheck: `cd frontend && npm run lint` (add if missing)
5. Test manually: `scripts\run.bat`
6. Submit PR with clear description

**Commit style**: `fix tool confirmation flow` not `Fix: resolved issue with tool confirmation WebSocket handling`

## License

MIT — use freely, contribute back.

## Status

**Alpha** — core scaffold complete, integration in progress. See [PLAN.md](PLAN.md) for roadmap.

## Why Nokton?

Existing options:
- **ChatGPT Desktop**: Cloud-only, no desktop control, no local voice
- **OpenCode**: Great for coding, no desktop automation, no voice
- **OpenClaw**: Desktop automation, no voice, no multi-provider
- **Local LLM UIs**: Chat only, no tools, no voice

Nokton combines: **voice + desktop control + any LLM + local-first + open source**