# Nokton — Complete Architecture Document

**Version:** 1.0  
**Date:** 2026-06-05  
**Status:** Design Confirmation  

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Provider & Model Layer](#2-provider--model-layer)
3. [Agent Engine](#3-agent-engine)
4. [Tool System](#4-tool-system)
5. [Voice Pipeline](#5-voice-pipeline)
6. [Desktop Automation](#6-desktop-automation)
7. [Frontend (Electron + React)](#7-frontend-electron--react)
8. [Communication Layer (WebSocket Protocol)](#8-communication-layer-websocket-protocol)
9. [Configuration System](#9-configuration-system)
10. [Security & Permissions](#10-security--permissions)
11. [Storage](#11-storage)
12. [Skills System](#12-skills-system)
13. [Image/Vision Handling](#13-imagevision-handling)
14. [Error Handling & Retry Logic](#14-error-handling--retry-logic)
15. [Latency Budget](#15-latency-budget)
16. [Project Structure](#16-project-structure)

---

## 1. Project Overview

**Nokton** is a Python + Electron desktop AI agent with:
- **Wake word** ("Hey Nokton") activation + push-to-talk
- **Voice I/O** (free, local STT + streaming TTS)
- **Live chat UI** (Electron + React, like ChatGPT)
- **Desktop automation** (files, apps, system, web, clipboard)
- **Multi-provider LLM support** (OpenRouter, DeepSeek, OpenAI, Anthropic, Google, Ollama, Groq, and any OpenAI-compatible endpoint)
- **Function calling / tool use** for agentic desktop workflows
- **Reasoning effort control** (off/high/xhigh per model)
- **Vision fallback** (text-only models can "see" via a separate vision model)
- **Image attachment support** (paste/upload images into chat)
- **Streaming responses** (<2s to first spoken word)
- **Interrupt support** (say "stop" or click cancel to abort any operation)
- **Conversation history** (SQLite persistence)
- **Session management** (multiple conversations, search)

### What we borrow from each project

| Pattern | Source | Adaptation |
|---------|--------|------------|
| Dynamic model catalog + provider abstraction | **OpenCode** | Provider registry with capability-flagged models, remote catalog discovery, lazy SDK loading |
| Tool descriptor system | **OpenClaw** | `@tool` decorator, JSON Schema auto-generation, availability expressions, layered permission policy |
| Tool self-registration | **Hermes Agent** | Tools register themselves at import time via `registry.register()`, `check_fn` for conditional availability |
| Agent loop with streaming | **All three** | While-true loop, SSE streaming, tool execution, interrupt handling |
| Skills/procedural memory | **Hermes Agent** | `SKILL.md` files with YAML frontmatter, progressive disclosure (tier 1/2/3) |
| Context compression | **Hermes Agent** | Summarize middle turns when near context limit, protect first N + last N |
| Reasoning effort routing | **OpenCode** | Variant-per-provider mapping (Anthropic → `thinking`, OpenAI → `reasoningEffort`, OpenRouter → `reasoning.effort`) |
| Image handling | **OpenCode** | Normalization (resize/compress), modality gating, unsupported-part substitution |
| Vision fallback | **opencode-vision plugin** | Detect image → route to vision-capable model → inject text description into text-only model |
| Desktop automation | **OpenClaw Windows Skills** | `pyautogui` + `psutil` + `mss` + `pyperclip` for desktop control |
| Stream as default | **Hermes Agent** | Always prefer streaming, even without display consumers (enables health checking) |
| Error recovery chain | **Hermes Agent** | Classify errors by type, per-type recovery strategies, exponential backoff, fallback activation |

---

## 2. Provider & Model Layer

### 2.1 Architecture

```
Provider Registry
├── Built-in Providers (registered at import)
│   ├── OpenRouterProvider     (200+ models, DeepSeek V4 Flash, free tier)
│   ├── OpenAIProvider         (GPT-4o, GPT-5, o3, etc.)
│   ├── AnthropicProvider      (Claude Opus, Sonnet, Haiku)
│   ├── GoogleProvider         (Gemini 2.5 Pro/Flash, Gemma)
│   ├── DeepSeekProvider       (Direct API, V4 Flash/Pro)
│   ├── OllamaProvider         (Local models)
│   ├── GroqProvider           (Fast inference, Llama, Mixtral)
│   └── CustomProvider         (Any OpenAI-compatible endpoint)
├── Dynamic Discovery
│   ├── Fetch from models.dev (OpenCode's catalog source)
│   ├── Fetch from OpenRouter /models endpoint
│   └── Config overrides in nokton.json
├── Model Router
│   ├── Primary model (user-selected)
│   ├── Small model (for titles, summaries, compression)
│   ├── Vision model (for image description fallback)
│   └── Fallback chain (if primary fails, try next provider)
└── API Key Manager
    ├── Encrypted storage (system keychain or AES-256 encrypted file)
    ├── Validation on save (test endpoint call)
    └── Multiple keys per provider (rotation support)
```

### 2.2 Provider Interface

Every provider implements this abstract base:

```python
class LLMProvider(ABC):
    """Abstract base for all LLM providers."""

    @property
    @abstractmethod
    def id(self) -> str: ...
    """Unique provider ID (e.g., 'openai', 'openrouter')"""

    @property
    @abstractmethod
    def name(self) -> str: ...
    """Display name (e.g., 'OpenAI', 'OpenRouter')"""

    @abstractmethod
    def get_models(self) -> list[ModelInfo]: ...
    """Fetch available models from this provider."""

    @abstractmethod
    def stream_chat(
        self,
        model: str,
        messages: list[Message],
        tools: list[ToolDef] | None = None,
        tool_choice: str = "auto",
        reasoning_effort: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        stop: list[str] | None = None,
    ) -> Generator[StreamEvent, None, None]:
    """Stream chat completion. Yields StreamEvent objects."""
    ...

    @abstractmethod
    def get_model_info(self, model_id: str) -> ModelInfo | None: ...
    """Get capability info for a specific model."""

    @property
    @abstractmethod
    def requires_api_key(self) -> bool: ...
    """Does this provider need an API key?"""

    @abstractmethod
    def validate_api_key(self, key: str) -> bool: ...
    """Test if an API key is valid."""
```

### 2.3 ModelInfo Schema

```python
@dataclass
class ModelInfo:
    id: str                           # e.g., "deepseek/deepseek-v4-flash"
    provider_id: str                  # e.g., "openrouter"
    name: str                         # e.g., "DeepSeek: DeepSeek V4 Flash"
    family: str | None = None         # e.g., "deepseek-flash"
    context_window: int = 128000      # Max total tokens
    max_output: int = 8192            # Max output tokens
    pricing: ModelPricing | None = None
    capabilities: ModelCapabilities = field(default_factory=ModelCapabilities)

@dataclass
class ModelCapabilities:
    vision: bool = False              # Can process image inputs directly
    tool_calling: bool = True         # Supports function/tool calling
    streaming: bool = True            # Supports SSE streaming
    reasoning: bool = False           # Supports reasoning effort control
    json_mode: bool = False           # Supports structured JSON output
    fine_tuning: bool = False         # Can be fine-tuned

@dataclass
class ModelPricing:
    input_per_1m: float = 0.0        # USD per 1M input tokens
    output_per_1m: float = 0.0       # USD per 1M output tokens
    cache_read_per_1m: float | None = None
    is_free: bool = False             # Free tier (OpenRouter :free suffix)
```

### 2.4 Reasoning Effort Mapping

```python
REASONING_MAP: dict[str, dict[str, Any]] = {
    "openrouter": {
        "off":      {},
        "high":     {"reasoning": {"effort": "high"}},
        "xhigh":    {"reasoning": {"effort": "xhigh"}},
    },
    "openai": {
        "off":      {"reasoning_effort": "none"},
        "high":     {"reasoning_effort": "high", "reasoning_summary": "auto"},
        "xhigh":    {"reasoning_effort": "xhigh", "reasoning_summary": "auto"},
    },
    "anthropic": {
        "off":      {},
        "high":     {"thinking": {"type": "enabled", "budget_tokens": 16000}},
        "xhigh":    {"thinking": {"type": "enabled", "budget_tokens": 32000}},
    },
    "deepseek": {
        "off":      {"thinking": {"type": "disabled"}},
        "high":     {"thinking": {"type": "enabled"}, "reasoning_effort": "high"},
        "xhigh":    {"thinking": {"type": "enabled"}, "reasoning_effort": "max"},
    },
    "google": {
        "off":      {},
        "high":     {"thinking_config": {"thinking_level": "medium"}},
        "xhigh":    {"thinking_config": {"thinking_level": "high"}},
    },
    "groq": {
        "off":      {},
        "high":     {"reasoning_effort": "high"},
        "xhigh":    {"reasoning_effort": "high"},  # Groq only supports high
    },
    "ollama": {
        "off":      {},
        "high":     {"options": {"num_ctx": 8192}},
        "xhigh":    {"options": {"num_ctx": 16384}},
    },
}
```

### 2.5 Provider Implementation: OpenRouter

```python
class OpenRouterProvider(LLMProvider):
    id = "openrouter"
    name = "OpenRouter"
    requires_api_key = True
    base_url = "https://openrouter.ai/api/v1"

    def get_models(self) -> list[ModelInfo]:
        """Fetch from OpenRouter's /models endpoint."""
        resp = requests.get(f"{self.base_url}/models", headers=self._headers())
        data = resp.json()
        models = []
        for m in data.get("data", []):
            model_id = m["id"]
            is_free = model_id.endswith(":free")
            models.append(ModelInfo(
                id=model_id,
                provider_id=self.id,
                name=m.get("name", model_id),
                context_window=m.get("context_length", 128000),
                max_output=m.get("top_provider", {}).get("max_completion_tokens", 8192),
                capabilities=ModelCapabilities(
                    vision="image" in m.get("input_modalities", []),
                    tool_calling="tools" in m.get("capabilities", []),
                    streaming=True,
                    reasoning="reasoning" in m.get("capabilities", []),
                ),
                pricing=ModelPricing(
                    input_per_1m=float(m.get("pricing", {}).get("prompt", 0)),
                    output_per_1m=float(m.get("pricing", {}).get("completion", 0)),
                    is_free=is_free,
                ),
            ))
        return models

    def stream_chat(self, model, messages, **kwargs):
        """OpenAI-compatible streaming via SSE."""
        client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        body = {
            "model": model,
            "messages": [m.to_dict() for m in messages],
            "stream": True,
        }
        if kwargs.get("tools"):
            body["tools"] = [t.to_schema() for t in kwargs["tools"]]
            body["tool_choice"] = kwargs.get("tool_choice", "auto")
        if kwargs.get("reasoning_effort"):
            body.update(REASONING_MAP["openrouter"].get(kwargs["reasoning_effort"], {}))

        stream = client.chat.completions.create(**body)
        for chunk in stream:
            yield self._parse_chunk(chunk)
```

---

## 3. Agent Engine

### 3.1 Architecture

```
AgentEngine
├── run_conversation()
│   ├── Pre-turn setup
│   │   ├── Load conversation history
│   │   ├── Build system prompt (identity + tools + skills)
│   │   ├── Estimate token usage
│   │   ├── Check for context overflow → compress if needed
│   │   └── Add memory prefetch context
│   ├── Main while loop
│   │   ├── Check interrupt flag (user said "stop" or clicked cancel)
│   │   ├── Check iteration budget
│   │   ├── Build API messages array
│   │   ├── Call LLM.stream() with streaming
│   │   ├── Process each stream event:
│   │   │   ├── text_delta → emit to UI + buffer for TTS
│   │   │   ├── reasoning_delta → emit to UI (thinking display)
│   │   │   ├── tool_call → parse + execute + feed result back
│   │   │   └── finish → exit loop
│   │   ├── On tool_call:
│   │   │   ├── Check permissions (auto/ask/deny)
│   │   │   ├── If ask → send permission request to UI
│   │   │   ├── Validate arguments
│   │   │   └── Execute tool with timeout
│   │   └── Retry/fallback on error
│   ├── Post-loop
│   │   ├── Persist session
│   │   ├── Run memory nudge
│   │   ├── Run skill creation nudge
│   │   └── Cleanup resources
│   └── Interrupt handler
│       ├── Receive interrupt signal
│       ├── Abort current LLM stream
│       ├── Kill running tool processes
│       └── Reset agent state for next input
```

### 3.2 System Prompt Template

The system prompt is built from multiple sources:

```
# Identity
You are Nokton, a desktop AI assistant...

# Environment
Current OS: Windows 10
Current time: {datetime}
Current user: {username}
Current directory: {cwd}

# Tools
{tool_descriptions}

# Skills (loaded at runtime)
{skill_descriptions}

# Memory (prefetched context)
{memory_context}

# Rules
- Use tools to fulfill user requests.
- For destructive operations (delete, shutdown, etc.), explain what you're doing.
- If the user says "stop" or "cancel", immediately stop what you're doing.
- Be concise in voice responses; be detailed in chat responses.
```

### 3.3 Context Compression

Triggered when `prompt_tokens >= threshold * context_length` (default 50%):

```python
def compress_context(messages: list[Message]) -> list[Message]:
    """Summarize middle turns, protect first N and last N."""
    PROTECT_FIRST_N = 3
    PROTECT_LAST_N = 10

    if len(messages) <= PROTECT_FIRST_N + PROTECT_LAST_N + 2:
        return messages  # Too short to compress

    # Keep first 3 + system messages
    # Protect last 10 user/assistant turns
    # Compress the rest into a single summary message
    middle = messages[PROTECT_FIRST_N:-PROTECT_LAST_N]
    summary = summarize_with_small_model(middle)
    
    compressed = (
        messages[:PROTECT_FIRST_N]
        + [Message(role="user", content=f"[Context summary of previous conversation:\n{summary}\n]")]
        + messages[-PROTECT_LAST_N:]
    )
    return compressed
```

### 3.4 Interrupt Handling

```python
class InterruptManager:
    """Handles user cancellation mid-operation."""

    def __init__(self):
        self._interrupt = threading.Event()
        self._current_task: asyncio.Task | None = None

    def cancel(self):
        """Signal interrupt — called from UI or voice 'stop'."""
        self._interrupt.set()
        if self._current_task and not self._current_task.done():
            self._current_task.cancel()

    def reset(self):
        """Reset after interrupt handled."""
        self._interrupt.clear()
        self._current_task = None

    def check(self):
        """Check if interrupted (call in agent loop)."""
        if self._interrupt.is_set():
            raise InterruptError("Operation cancelled by user.")
```

**Voice interrupt flow:**
1. Wake word listener hears "stop" or user clicks cancel button
2. WebSocket sends `{ type: "cancel" }` to backend
3. Backend calls `InterruptManager.cancel()`
4. Agent loop raises `InterruptError`
5. LLM stream is aborted (close SSE connection)
6. Running tools receive SIGTERM / timeout
7. Backend sends `{ type: "interrupted" }` to UI
8. TTS stops speaking
9. System returns to idle state, ready for next command

---

## 4. Tool System

### 4.1 Architecture

```
ToolRegistry (singleton)
├── @tool decorator → self-registration at import
│   ├── name (unique tool ID)
│   ├── description (for LLM schema)
│   ├── parameters (type hints + docstring → JSON Schema)
│   ├── handler (callable)
│   ├── category (file, app, system, web, clipboard, screenshot)
│   ├── check_fn (optional — returns bool if tool is available)
│   ├── requires_confirm (True for destructive operations)
│   └── timeout (default 30s, override for long operations)
├── Schema generation
│   └── From Python type hints + docstrings → OpenAI JSON Schema
├── Permission checking
│   ├── safe (auto-execute: file read, search, get time)
│   ├── ask (requires user confirm: delete, shutdown, exec)
│   └── disabled (blocked by user config)
└── Execution
    ├── Validate arguments
    ├── Check timeout
    ├── Run handler
    └── Format result → return to agent loop
```

### 4.2 Tool Decorator

```python
# tool_registry.py
_registry: dict[str, ToolDef] = {}

def tool(
    name: str | None = None,
    category: str = "general",
    requires_confirm: bool = False,
    timeout: int = 30,
    check_fn: Callable[[], bool] | None = None,
):
    """Decorator that registers a function as a tool."""
    def decorator(func):
        t = ToolDef(
            id=name or func.__name__,
            description=func.__doc__ or "",
            category=category,
            handler=func,
            parameters=func_to_json_schema(func),
            requires_confirm=requires_confirm,
            timeout=timeout,
            check_fn=check_fn,
        )
        _registry[t.id] = t
        return func
    return decorator
```

### 4.3 Tool Schema Generation

From Python function:
```python
@tool(category="file", requires_confirm=True)
def delete_file(path: str) -> str:
    """Delete a file at the given path.
    
    Args:
        path: Absolute or relative path to the file to delete.
    
    Returns:
        Confirmation message.
    """
    os.remove(path)
    return f"Deleted {path}"
```

Generates JSON Schema:
```json
{
  "name": "delete_file",
  "description": "Delete a file at the given path.",
  "parameters": {
    "type": "object",
    "properties": {
      "path": {
        "type": "string",
        "description": "Absolute or relative path to the file to delete."
      }
    },
    "required": ["path"]
  }
}
```

### 4.4 Tool Availability Expressions

```python
@tool(
    check_fn=lambda: shutil.which("ffmpeg") is not None,
    category="media",
)
def convert_audio(input_path: str, output_format: str) -> str:
    """Convert audio file format using ffmpeg."""
    ...
```

### 4.5 Tool Modules

| Module | Tools | Libraries |
|--------|-------|-----------|
| `tools/file_ops.py` | `list_dir`, `read_file`, `write_file`, `search_files`, `move_file`, `copy_file`, `delete_file`, `create_file` | `os`, `shutil`, `pathlib`, `glob` |
| `tools/app_control.py` | `launch_app`, `close_app`, `list_processes`, `kill_process` | `subprocess`, `psutil` |
| `tools/system_info.py` | `get_cpu`, `get_ram`, `get_battery`, `get_wifi`, `get_volume`, `set_volume`, `shutdown`, `restart` | `psutil`, `wmi` |
| `tools/web_ops.py` | `web_search`, `web_fetch`, `extract_text` | `duckduckgo_search`, `requests`, `bs4` |
| `tools/clipboard_ops.py` | `clipboard_get`, `clipboard_set`, `type_text` | `pyperclip`, `pyautogui` |
| `tools/screenshot.py` | `capture_screen`, `capture_region`, `ocr_screen` | `mss`, `pytesseract`, `PIL` |
| `tools/window_control.py` | `list_windows`, `focus_window`, `minimize_window`, `maximize_window`, `resize_window` | `pygetwindow`, `pywin32` |
| `tools/terminal.py` | `run_command`, `run_powershell`, `run_batch` | `subprocess`, `asyncio` |

### 4.6 Tool Execution & Permission Flow

```
LLM requests tool call
    │
    ▼
Resolve tool from registry
    │
    ▼
Check permission level:
    ├── safe → execute automatically
    ├── ask → send permission request to UI
    │           ├── user approves → execute
    │           └── user denies → return error to LLM
    └── disabled → return "tool disabled" error
    │
    ▼
Validate arguments (type check, bounds check)
    │
    ▼
Execute handler with timeout
    │
    ▼
Format result → return to LLM as tool_result message
```

---

## 5. Voice Pipeline

### 5.1 Architecture

```
VoicePipeline
├── WakeWordDetector (background thread)
│   ├── Model: OpenWakeWord (free, offline) or Porcupine (1 free wake word)
│   ├── Library: pvporcupine or openwakeword
│   ├── Sensitivity: configurable (0.0 - 1.0)
│   └── Emits: "wake" → start recording
├── VoiceActivityDetector (Silero VAD)
│   ├── Model: silero-vad (MIT, runs locally, <10ms inference)
│   ├── Threshold: configurable
│   ├── Min speech duration: 500ms (avoid false triggers)
│   ├── Silence cutoff: 800ms of silence → end recording
│   └── Emits: "speech_start", "speech_end"
├── SpeechToText
│   ├── Primary: faster-whisper (MIT, 4-8x faster than Whisper, local)
│   │   ├── Model size: tiny (~500ms) / small (~1s) / medium (~2s)
│   │   ├── Device: CPU (auto) or CUDA if available
│   │   └── Compute type: int8 (default) or float16
│   ├── Fallback: speech_recognition (Google STT, free, no key)
│   └── Output: transcribed text → agent engine
├── TextToSpeech
│   ├── Primary: edge-tts (free, streaming, natural voices)
│   │   ├── Voices: Microsoft Azure TTS voices (en-US available)
│   │   ├── Streaming: sentence-by-sentence, starts ~500ms after first sentence
│   │   └── Rate: configurable (default normal)
│   ├── Fallback: pyttsx3 (offline, robotic)
│   └── Output: audio stream → system speaker
└── Audio Feedback
    ├── Wake sound: short ascending tone
    ├── Listening: subtle indicator (no sound needed)
    ├── Speaking: (already covered by TTS)
    └── Error: short descending tone
```

### 5.2 Voice Flow (Full Cycle)

```
1. [Background] Wake word detector running (0% CPU, <100MB RAM)
2. User says: "Hey Nokton, what's the weather?"
3. Wake word detected: "Hey Nokton"
   └─ Play wake sound (ascending tone)
   └─ Start recording (buffer audio)
4. VAD detects speech: "what's the weather?"
5. VAD detects silence (800ms) → stop recording
   └─ Send audio to faster-whisper (small model, ~1s)
6. STT result: "what's the weather?"
   └─ Display in chat UI
   └─ Feed into agent engine
7. Agent engine processes:
   └─ LLM streaming starts (~200ms to first token)
   └─ Tool call: web_search("current weather") → result
   └─ LLM produces final response
8. Response text streams to UI
   └─ First sentence buffered → TTS streaming starts (~500ms)
   └─ "The weather today is sunny, 72 degrees..."
9. TTS plays through speakers
10. System returns to idle, wake word listening resumes
```

### 5.3 Voice Interrupt (Barge-in)

If user speaks during TTS playback:
```
1. TTS playing: "The weather today is..."
2. User says: "Stop"
3. Wake word detector hears "Stop" (or VAD detects speech during playback)
4. If wake word confidence > threshold: treat as new command
5. If user says "stop": trigger InterruptManager.cancel()
6. TTS stops, agent loop aborts, system returns to idle
```

---

## 6. Desktop Automation

### 6.1 File Operations (`tools/file_ops.py`)

```python
@tool(category="file")
def list_dir(path: str = ".") -> str:
    """List files and directories at the given path."""

@tool(category="file")
def read_file(path: str) -> str:
    """Read the contents of a text file."""

@tool(category="file")
def write_file(path: str, content: str) -> str:
    """Write content to a file (creates or overwrites)."""

@tool(category="file")
def search_files(query: str, folder: str = ".", max_results: int = 20) -> str:
    """Search for files matching a name pattern."""

@tool(category="file", requires_confirm=True)
def delete_file(path: str) -> str:
    """Permanently delete a file."""

@tool(category="file")
def create_file(path: str, content: str = "") -> str:
    """Create a new file with optional content."""

@tool(category="file", requires_confirm=True)
def move_file(source: str, dest: str) -> str:
    """Move or rename a file."""

@tool(category="file", requires_confirm=True)
def copy_file(source: str, dest: str) -> str:
    """Copy a file to a new location."""
```

### 6.2 App Control (`tools/app_control.py`)

```python
@tool(category="app")
def launch_app(name_or_path: str) -> str:
    """Launch an application by name (searches PATH) or full path."""

@tool(category="app", requires_confirm=True)
def close_app(name: str) -> str:
    """Close an application gracefully."""

@tool(category="app")
def list_processes(filter: str = "") -> str:
    """List running processes, optionally filtered."""

@tool(category="app", requires_confirm=True)
def kill_process(pid: int | str) -> str:
    """Force-kill a process by PID or name."""
```

### 6.3 System Info (`tools/system_info.py`)

```python
@tool(category="system")
def get_system_info() -> str:
    """Get CPU, RAM, disk, battery, WiFi info."""

@tool(category="system")
def get_volume() -> str:
    """Get current system volume level (0-100)."""

@tool(category="system")
def set_volume(level: int) -> str:
    """Set system volume level (0-100)."""

@tool(category="system", requires_confirm=True)
def shutdown(delay_seconds: int = 60) -> str:
    """Shut down the computer after a delay."""

@tool(category="system", requires_confirm=True)
def restart(delay_seconds: int = 60) -> str:
    """Restart the computer after a delay."""
```

### 6.4 Web Operations (`tools/web_ops.py`)

```python
@tool(category="web")
def web_search(query: str, max_results: int = 5) -> str:
    """Search the web using DuckDuckGo (free, no API key)."""

@tool(category="web")
def web_fetch(url: str) -> str:
    """Fetch and extract text content from a web page."""

@tool(category="web")
def extract_links(url: str) -> str:
    """Extract all links from a web page."""
```

### 6.5 Clipboard & Typing (`tools/clipboard_ops.py`)

```python
@tool(category="clipboard")
def clipboard_get() -> str:
    """Get the current clipboard contents."""

@tool(category="clipboard")
def clipboard_set(text: str) -> str:
    """Set clipboard contents."""

@tool(category="clipboard")
def type_text(text: str, interval: float = 0.05) -> str:
    """Type text into the currently focused application."""
```

### 6.6 Screenshot & OCR (`tools/screenshot.py`)

```python
@tool(category="screenshot")
def capture_screen(region: str | None = None) -> str:
    """Capture a screenshot. Optional region: 'full' or 'window'."""
    # Returns: path to saved screenshot image

@tool(category="screenshot")
def ocr_screen(region: str | None = None) -> str:
    """Extract text from screen via OCR."""
```

---

## 7. Frontend (Electron + React)

### 7.1 Electron Main Process (`frontend/main.js`)

```
Main Process
├── Window management
│   ├── Create BrowserWindow (frameless or custom titlebar)
│   ├── System tray icon & menu
│   ├── Minimize to tray on close
│   └── Window state persistence (position, size)
├── IPC Handlers
│   ├── get-settings → read config file
│   ├── save-settings → write config file
│   ├── get-models → request model list from backend
│   ├── get-conversations → list saved conversations
│   ├── export-conversation → export to JSON/MD
│   └── open-external → open URLs in default browser
├── Backend Process Management
│   ├── Spawn Python backend on startup
│   ├── Monitor backend health (heartbeat)
│   └── Kill backend on app quit
└── Auto-updater
    ├── Check GitHub releases
    └── Download and install updates
```

### 7.2 React App (`frontend/src/`)

```
src/
├── App.tsx                    # Main app shell
├── index.tsx                  # Entry point
├── components/
│   ├── Layout/
│   │   ├── Sidebar.tsx        # Conversation list, new chat button
│   │   ├── Titlebar.tsx       # Custom titlebar (drag region)
│   │   └── MainView.tsx       # Chat + input container
│   ├── Chat/
│   │   ├── MessageList.tsx     # Streaming message display
│   │   ├── MessageBubble.tsx   # Single message (user or assistant)
│   │   ├── StreamingText.tsx   # Animated streaming text
│   │   ├── ToolCallCard.tsx    # Shows when agent uses a tool
│   │   ├── InputBar.tsx        # Text input + mic button + send
│   │   ├── ReasoningBlock.tsx  # Shows "thinking..." during reasoning
│   │   └── CodeBlock.tsx       # Syntax-highlighted code
│   ├── Voice/
│   │   ├── VoiceIndicator.tsx  # Status: idle/listening/speaking/thinking
│   │   ├── MicButton.tsx       # Push-to-talk button
│   │   └── Waveform.tsx        # Audio visualization (optional)
│   ├── Settings/
│   │   ├── SettingsPanel.tsx   # Full settings modal
│   │   ├── ProviderSettings.tsx# Per-provider API keys
│   │   ├── ModelSelector.tsx   # Provider + model dropdown
│   │   ├── ToolToggles.tsx     # Enable/disable tool categories
│   │   ├── VoiceSettings.tsx   # STT model, TTS voice, wake word
│   │   └── ReasoningSlider.tsx # Off / High / XHigh
│   └── Common/
│       ├── LoadingSpinner.tsx
│       ├── ConfirmDialog.tsx   # Tool permission confirmation
│       └── ErrorBanner.tsx
├── hooks/
│   ├── useWebSocket.ts        # WebSocket connection management
│   ├── useConversation.ts     # Conversation state & history
│   ├── useSettings.ts         # Settings persistence
│   └── useVoice.ts            # Voice input/output state
├── services/
│   ├── websocket.ts           # WebSocket client implementation
│   ├── api.ts                 # REST API client (settings, models)
│   └── ipc.ts                 # Electron IPC wrapper
├── stores/
│   ├── conversationStore.ts   # Zustand store for chat state
│   ├── settingsStore.ts       # Zustand store for settings
│   └── voiceStore.ts          # Zustand store for voice state
├── types/
│   ├── messages.ts            # Message, ToolCall, Attachment types
│   ├── models.ts              # ModelInfo, ProviderInfo types
│   └── settings.ts            # Config types
└── utils/
    ├── markdown.ts            # Markdown rendering helpers
    └── format.ts              # Date, file size, token format
```

### 7.3 UI States

```
┌─────────────────────────────────────────┐
│  [≡]  Nokton  —  [—] [□] [×]           │ ← Titlebar
├──────────┬──────────────────────────────┤
│ Sidebar  │  Chat Area                   │
│          │                              │
│  ┌─────┐ │  ┌─ User Message ──────────┐ │
│  │Icon │ │  │ What's the weather?      │ │
│  └─────┘ │  └──────────────────────────│ │
│          │  ┌─ Nokton ────────────────┐ │ │
│ Weather  │  │ The weather today is     │ │ │
│ Files    │  │ sunny, 72°F.            │ │ │
│ Settings │  │                          │ │ │
│          │  │[Tool: web_search] ✓     │ │ │
│          │  └──────────────────────────┘ │ │
│          │                              │
│          │  ┌─ Voice Status ──────────┐ │ │
│          │  │ 🎤  Listening...   ●    │ │ │
│          │  └──────────────────────────┘ │ │
│          │  ┌──────────────────────────┐ │ │
│          │  │ Type a message... [🎤][➤]│ │ │
│          │  └──────────────────────────┘ │ │
├──────────┴──────────────────────────────┤
│  System Tray: [🟢 Nokton — Idle]        │
└─────────────────────────────────────────┘
```

### 7.4 WebSocket Client

```typescript
// websocket.ts
class NoktonWebSocket {
    private ws: WebSocket;
    private messageHandler: (event: StreamEvent) => void;

    connect() {
        this.ws = new WebSocket("ws://localhost:8765/ws");
        this.ws.onmessage = (event) => {
            const parsed = JSON.parse(event.data);
            this.messageHandler(parsed);
        };
    }

    sendMessage(text: string, images?: string[]) {
        this.ws.send(JSON.stringify({
            type: "user_message",
            text,
            images,
        }));
    }

    cancel() {
        this.ws.send(JSON.stringify({ type: "cancel" }));
    }

    setSettings(settings: Partial<Settings>) {
        this.ws.send(JSON.stringify({
            type: "settings_update",
            ...settings,
        }));
    }

    confirmTool(callId: string, approved: boolean) {
        this.ws.send(JSON.stringify({
            type: "confirm_tool",
            call_id: callId,
            approved,
        }));
    }
}
```

---

## 8. Communication Layer (WebSocket Protocol)

### 8.1 Connection

```
Client → Server: HTTP Upgrade to WebSocket
Server: ws://localhost:8765/ws
```

### 8.2 Client → Server Messages

```typescript
// Send a user message
{ "type": "user_message", "text": "Hello", "images": ["base64..."] }

// Cancel current operation
{ "type": "cancel" }

// Update a setting
{ "type": "settings_update", "key": "model", "value": "deepseek/deepseek-v4-flash" }

// Confirm or deny a tool call
{ "type": "confirm_tool", "call_id": "call_abc123", "approved": true }

// Set active model
{ "type": "set_model", "provider": "openrouter", "model": "deepseek/deepseek-v4-flash", "reasoning_effort": "high" }

// Request model list
{ "type": "get_models" }

// Voice mode toggle
{ "type": "voice_toggle", "enabled": true }
```

### 8.3 Server → Client Messages

```typescript
// Streaming text delta
{ "type": "assistant_delta", "text": "The weather" }

// Streaming reasoning delta
{ "type": "reasoning_delta", "text": "I need to search for weather..." }

// Stream complete
{ "type": "assistant_done" }

// Tool call request
{ "type": "tool_call", "id": "call_abc123", "name": "web_search", "args": {"query": "weather"}, "requires_confirm": false }

// Tool result
{ "type": "tool_result", "id": "call_abc123", "output": "Sunny, 72°F" }

// Tool error
{ "type": "tool_error", "id": "call_abc123", "error": "Search API unavailable" }

// Voice event
{ "type": "voice_event", "state": "wake" | "listening" | "thinking" | "speaking" | "idle" | "error" }

// Error
{ "type": "error", "code": "API_ERROR", "message": "OpenRouter rate limit exceeded" }

// Agent status
{ "type": "status", "state": "idle" | "thinking" | "executing_tool" | "speaking" | "error" }

// Model list response
{ "type": "models_list", "providers": [{"id": "openrouter", "name": "OpenRouter", "models": [...]}] }

// Settings
{ "type": "settings", ...allSettings }

// Permission request
{ "type": "permission_request", "tool_id": "delete_file", "args": {"path": "C:/file.txt"}, "description": "Delete file C:/file.txt" }
```

### 8.4 REST Endpoints

```
GET  /api/models         → List all available models grouped by provider
GET  /api/models/:id     → Model info and capabilities
GET  /api/settings       → Get current settings
POST /api/settings       → Update settings
GET  /api/conversations  → List conversations
GET  /api/conversations/:id → Get conversation messages
DELETE /api/conversations/:id → Delete conversation
POST /api/conversations/:id/export → Export conversation
```

---

## 9. Configuration System

### 9.1 Config File (`nokton.json`)

```json
{
  "$schema": "https://nokton.local/config.json",
  
  "model": {
    "provider": "openrouter",
    "model": "deepseek/deepseek-v4-flash",
    "small_model": "openrouter/gpt-oss-20b:free",
    "vision_model": "openrouter/google/gemma-3-27b-it:free",
    "reasoning_effort": "high",
    "temperature": 0.7,
    "max_tokens": 4096
  },
  
  "providers": {
    "openrouter": {
      "api_key": "",
      "base_url": "https://openrouter.ai/api/v1"
    },
    "openai": {
      "api_key": "",
      "base_url": "https://api.openai.com/v1"
    },
    "anthropic": {
      "api_key": "",
      "base_url": "https://api.anthropic.com/v1"
    },
    "deepseek": {
      "api_key": "",
      "base_url": "https://api.deepseek.com/v1"
    },
    "groq": {
      "api_key": "",
      "base_url": "https://api.groq.com/openai/v1"
    },
    "ollama": {
      "base_url": "http://localhost:11434/v1"
    }
  },
  
  "tools": {
    "permissions": {
      "safe_categories": ["file_read", "web", "system_read", "clipboard_read"],
      "ask_categories": ["file_write", "app_control", "system_write"],
      "deny_categories": []
    },
    "timeout": 30
  },
  
  "voice": {
    "wake_word": {
      "enabled": true,
      "sensitivity": 0.7,
      "model": "hey_nokton"
    },
    "stt": {
      "engine": "faster-whisper",
      "model_size": "small",
      "device": "cpu"
    },
    "tts": {
      "engine": "edge-tts",
      "voice": "en-US-JennyNeural",
      "rate": "+0%"
    },
    "vad": {
      "threshold": 0.5,
      "silence_duration_ms": 800
    }
  },
  
  "conversation": {
    "max_turns": 100,
    "compress_threshold": 0.5,
    "protect_last_n": 10
  },
  
  "ui": {
    "theme": "dark",
    "font_size": 14,
    "streaming_animation": true,
    "show_reasoning": false,
    "show_tool_calls": true
  }
}
```

### 9.2 Config Loading

```
1. Default config (built-in)
2. ~/.nokton/nokton.json (global user config)
3. ./nokton.json (project config, overrides global)
4. Environment variables (override everything):
   - NOKTON_PROVIDER
   - NOKTON_MODEL
   - OPENROUTER_API_KEY
   - OPENAI_API_KEY
   - ANTHROPIC_API_KEY
   - DEEPSEEK_API_KEY
```

---

## 10. Security & Permissions

### 10.1 Permission Levels

```
┌────────────────┬──────────────────────┬──────────────────────┐
│ Category       │ Default Permission   │ Examples             │
├────────────────┼──────────────────────┼──────────────────────┤
│ File Read      │ Auto                 │ read_file, list_dir  │
│ File Write     │ Ask                  │ write_file, create   │
│ File Destructive│ Ask                 │ delete_file, move    │
│ App Launch     │ Auto                 │ launch_app           │
│ App Control    │ Ask                  │ close_app, kill      │
│ System Read    │ Auto                 │ get_cpu, get_ram     │
│ System Control │ Ask                  │ shutdown, restart    │
│ Web            │ Auto                 │ web_search, fetch    │
│ Clipboard Read │ Auto                 │ clipboard_get        │
│ Clipboard Write│ Auto                 │ clipboard_set, type  │
│ Screenshot     │ Ask                  │ capture_screen       │
│ Terminal       │ Ask                  │ run_command          │
└────────────────┴──────────────────────┴──────────────────────┘
```

### 10.2 API Key Security

```python
class ApiKeyManager:
    """Manages API keys with encryption at rest."""

    def __init__(self, storage_path: str):
        self.storage_path = storage_path
        self._keys: dict[str, str] = {}
        self._load()

    def _load(self):
        """Load encrypted keys from file."""
        try:
            with open(self.storage_path) as f:
                encrypted = f.read()
            # Decrypt using system keychain or AES-256
            self._keys = self._decrypt(encrypted)
        except FileNotFoundError:
            self._keys = {}

    def set_key(self, provider: str, key: str):
        """Store a key (encrypted at rest)."""
        self._keys[provider] = key
        self._save()

    def get_key(self, provider: str) -> str | None:
        """Retrieve a key (decrypted in memory)."""
        return self._keys.get(provider)

    def validate_key(self, provider: str, key: str) -> bool:
        """Test if a key works by making a lightweight API call."""
        ...
```

### 10.3 Audit Logging

```python
class AuditLogger:
    """Logs all tool calls for auditing."""

    def log_tool_call(self, call_id: str, tool: str, args: dict,
                      approved: bool, result: Any, duration: float):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "call_id": call_id,
            "tool": tool,
            "args": sanitize_for_logging(args),
            "approved": approved,
            "success": result.get("success", False),
            "duration_ms": int(duration * 1000),
        }
        self._append_to_log(entry)
```

---

## 11. Storage

### 11.1 Directory Layout

```
~/.nokton/
├── nokton.json              # User config
├── api_keys.enc             # Encrypted API keys
├── conversations/
│   ├── conv_20260605_123456.json  # Per-conversation file
│   └── conv_20260605_123457.json
├── logs/
│   ├── app.log              # Application logs
│   ├── tool_calls.log       # Tool audit trail
│   └── cost.log             # Token usage tracker
├── voice/
│   └── wake_word.ppn        # Wake word model file
└── cache/
    └── model_catalog.json   # Cached model list
```

### 11.2 Conversation Storage

```json
{
  "id": "conv_20260605_123456",
  "title": "Weather discussion",
  "provider": "openrouter",
  "model": "deepseek/deepseek-v4-flash",
  "reasoning_effort": "high",
  "created_at": "2026-06-05T12:34:56Z",
  "updated_at": "2026-06-05T12:35:30Z",
  "messages": [
    {
      "role": "user",
      "content": "What's the weather?",
      "timestamp": "2026-06-05T12:34:56Z"
    },
    {
      "role": "assistant",
      "content": "The weather today is sunny, 72°F.",
      "reasoning": "I need to search for current weather...",
      "tool_calls": [
        {
          "id": "call_abc",
          "name": "web_search",
          "args": {"query": "current weather"},
          "result": "Sunny, 72°F",
          "duration_ms": 1200
        }
      ],
      "timestamp": "2026-06-05T12:35:30Z",
      "tokens_used": {
        "input": 150,
        "output": 20,
        "reasoning": 80
      }
    }
  ],
  "stats": {
    "total_tokens_input": 150,
    "total_tokens_output": 20,
    "total_cost_usd": 0.00002
  }
}
```

### 11.3 Token & Cost Tracking

```python
class CostTracker:
    """Tracks token usage and estimates cost per session."""

    def __init__(self):
        self.session_input = 0
        self.session_output = 0
        self.session_reasoning = 0
        self.total_input = 0
        self.total_output = 0
        self.total_cost = 0.0

    def add_usage(self, provider: str, model: str, input_tokens: int,
                  output_tokens: int, reasoning_tokens: int = 0):
        pricing = self._get_pricing(provider, model)
        cost = (input_tokens * pricing.input_per_1m / 1_000_000 +
                output_tokens * pricing.output_per_1m / 1_000_000)
        
        self.session_input += input_tokens
        self.session_output += output_tokens
        self.session_reasoning += reasoning_tokens
        self.total_input += input_tokens
        self.total_output += output_tokens
        self.total_cost += cost
        self._log_usage(provider, model, input_tokens, output_tokens, cost)
```

---

## 12. Skills System

### 12.1 SKILL.md Format

Borrowed from Hermes Agent's format:

```markdown
---
name: file-management
description: Advanced file management operations
version: 1.0.0
platforms: [windows]
required_environment_variables: []
---

# File Management Skill

## Overview
I can help manage files and folders on your Windows system.

## Commands
- "organize my downloads folder by file type"
- "find all large files over 100MB"
- "create a new project folder structure"

## Instructions
When the user asks about file organization:
1. First list the contents of the target folder
2. Identify files by extension/category
3. Create category subfolders
4. Move files into appropriate folders

## Notes
- Always ask before moving more than 10 files
- Don't modify system directories
```

### 12.2 Skill Discovery

```python
class SkillManager:
    """Manages skills from ~/.nokton/skills/ directory."""

    def __init__(self, skills_dir: str):
        self.skills_dir = Path(skills_dir)
        self.skills: dict[str, Skill] = {}
        self._discover()

    def _discover(self):
        """Scan skills directory for SKILL.md files."""
        for skill_dir in self.skills_dir.iterdir():
            if skill_dir.is_dir():
                skill_file = skill_dir / "SKILL.md"
                if skill_file.exists():
                    skill = self._parse_skill(skill_file)
                    self.skills[skill.name] = skill

    def get_skill_descriptions(self) -> str:
        """Return tier-1 descriptions (name + description only)."""
        lines = []
        for skill in self.skills.values():
            lines.append(f"- {skill.name}: {skill.description}")
        return "\n".join(lines)

    def get_skill_content(self, name: str) -> str | None:
        """Return tier-2 full instructions."""
        skill = self.skills.get(name)
        return skill.content if skill else None
```

---

## 13. Image/Vision Handling

### 13.1 Architecture (Borrowed from OpenCode)

```
User pastes/attaches image
    │
    ▼
ImageNormalizer
    ├── Resize (max 2000x2000)
    ├── Compress (max 5MB base64)
    └── Format (JPEG preferred for base64)
    │
    ▼
ModelCapabilityChecker
    ├── Does the current model support vision?
    │   ├── Yes → Send image directly as base64 content part
    │   └── No → Route to VisionFallback
    │
    ▼
VisionFallback (for text-only models like DeepSeek V4 Flash)
    ├── Send image to vision-capable model:
    │   ├── Primary: google/gemma-3-27b-it:free (free on OpenRouter)
    │   ├── Backup: openrouter/google/gemini-2.5-flash
    │   └── Prompt: "Describe this image in detail."
    ├── Get text description
    └── Inject description into DeepSeek's context as:
        "[User attached an image. Description: {description}]"
```

### 13.2 Screenshot → Vision Pipeline

```python
class VisionFallback:
    """Handles image understanding for text-only models."""

    def __init__(self, provider: LLMProvider, model_id: str):
        self.provider = provider
        self.model_id = model_id

    def describe_image(self, image_base64: str) -> str:
        """Send image to vision model, get text description."""
        messages = [
            Message(role="user", content=[
                ContentText("Describe this image in detail."),
                ContentImage(base64=image_base64),
            ])
        ]
        result = []
        for event in self.provider.stream_chat(
            model=self.model_id,
            messages=messages,
            max_tokens=1024,
        ):
            if event.type == "text_delta":
                result.append(event.text)
        return "".join(result)

    def handle_image_in_input(self, image_base64: str) -> ContentText:
        """Replace image with text description for text-only models."""
        description = self.describe_image(image_base64)
        return ContentText(f"[User attached an image. Description: {description}]")
```

### 13.3 Screenshot Tool with OCR

```python
@tool(category="screenshot")
def capture_and_describe() -> str:
    """Take a screenshot and return a text description of what's on screen."""
    # 1. Capture screenshot
    screenshot = mss.mss().shot(output="screenshots/latest.png")
    
    # 2. OCR the screenshot
    text = pytesseract.image_to_string(screenshot)
    
    # 3. If vision model available, also get semantic description
    if vision_provider:
        with open(screenshot, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        description = vision_fallback.describe_image(b64)
    else:
        description = "OCR text extracted from screen."
    
    return f"Screenshot captured. OCR text: {text}\nVisual description: {description}"
```

---

## 14. Error Handling & Retry Logic

### 14.1 Error Classification

```python
class APIError(Exception):
    """Base class for API errors."""

class RateLimitError(APIError): ...
class QuotaExceededError(APIError): ...
class AuthError(APIError): ...
class TimeoutError(APIError): ...
class ServerError(APIError): ...
class InvalidRequestError(APIError): ...
class ContextLengthError(APIError): ...
class EmptyResponseError(APIError): ...

def classify_api_error(exception: Exception, response_body: str | None) -> APIError:
    """Classify an API error for appropriate recovery."""
    if "rate_limit" in str(exception).lower() or "429" in str(exception):
        return RateLimitError("Rate limit exceeded")
    if "quota" in str(exception).lower() or "402" in str(exception):
        return QuotaExceededError("Quota exceeded")
    if "auth" in str(exception).lower() or "401" in str(exception):
        return AuthError("Authentication failed")
    if "timeout" in str(exception).lower():
        return TimeoutError("Request timed out")
    if "5" in str(exception)[:3] or "server_error" in str(exception).lower():
        return ServerError("Server error")
    if "context_length" in str(exception).lower() or "too long" in str(exception).lower():
        return ContextLengthError("Context too long")
    return APIError(str(exception))
```

### 14.2 Retry Strategy

```python
class RetryStrategy:
    """Per-error-type retry with configurable backoff."""

    STRATEGIES = {
        RateLimitError:      {"retry": True,  "backoff": "exponential", "base_s": 5,  "max_s": 120},
        QuotaExceededError:  {"retry": False, "fallback": True},
        AuthError:           {"retry": False, "notify": True},
        TimeoutError:        {"retry": True,  "backoff": "linear",      "base_s": 2,  "max_s": 30},
        ServerError:         {"retry": True,  "backoff": "exponential", "base_s": 2,  "max_s": 60},
        ContextLengthError:  {"retry": True,  "action": "compress"},
        EmptyResponseError:  {"retry": True,  "backoff": "linear",      "base_s": 1,  "max_s": 10},
    }

    def should_retry(self, error: APIError, attempt: int) -> bool:
        strategy = self.STRATEGIES.get(type(error))
        if not strategy or not strategy["retry"]:
            return False
        max_attempts = 3
        return attempt < max_attempts

    def get_delay(self, error: APIError, attempt: int) -> float:
        strategy = self.STRATEGIES.get(type(error), {})
        backoff = strategy.get("backoff", "linear")
        base = strategy.get("base_s", 2)
        max_s = strategy.get("max_s", 60)
        
        if backoff == "exponential":
            delay = base * (2 ** attempt)
        else:  # linear
            delay = base * (attempt + 1)
        
        return min(delay, max_s)
```

### 14.3 Fallback Chain

```python
class FallbackManager:
    """If primary provider fails, try fallback providers."""

    def __init__(self, primary: str, fallbacks: list[str]):
        self.primary = primary
        self.fallbacks = fallbacks
        self.current = primary
        self.attempts = 0

    def get_next(self) -> str | None:
        """Get next provider in fallback chain."""
        self.attempts += 1
        if self.current == self.primary and self.fallbacks:
            self.current = self.fallbacks[0]
            return self.current
        idx = self.fallbacks.index(self.current) + 1 if self.current in self.fallbacks else 0
        if idx < len(self.fallbacks):
            self.current = self.fallbacks[idx]
            return self.current
        return None  # No more fallbacks

    def reset(self):
        self.current = self.primary
        self.attempts = 0
```

---

## 15. Latency Budget

### 15.1 Targets

| Stage | Target Latency | Technique |
|-------|---------------|-----------|
| Wake word detection | <200ms | Local model (OpenWakeWord) |
| Speech recording stop | <100ms | Silero VAD, 800ms silence cutoff |
| STT transcription | ~1s (small model) | faster-whisper, int8 quantization |
| LLM first token | ~300ms | Streaming SSE, model < 50ms TTFT |
| TTS first audio | ~500ms | edge-tts, sentence buffering |
| **Total voice → first response** | **~2-3s** | Streaming pipeline |
| UI first text | ~300ms | SSE streaming, immediate display |

### 15.2 Optimization Techniques

1. **Streaming everywhere**: Never wait for complete results
2. **Parallel pipelines**: TTS can start on first sentence while LLM continues generating
3. **Sentence boundary detection**: Start TTS after first `.` `?` `!` or `\n`
4. **Small STT model**: `faster-whisper small` offers best speed/accuracy tradeoff
5. **Cached model catalog**: `model_catalog.json` cached locally, refreshed every 5 min
6. **Keepalive connections**: Persistent connections to OpenRouter/API endpoints
7. **Prompt caching**: Reuse system prompt across turns (OpenRouter supports this)
8. **Eager tool execution**: Start executing tools as soon as the LLM requests them
9. **TTSCache**: Cache common TTS phrases locally

### 15.3 Pipeline Diagram

```
Voice Pipeline (streaming):
  Mic → [Wake Word] → [VAD] → [STT] ──┐
                                       ▼
                                    [Agent Loop]
                                       │
                  ┌────────────────────┼────────────────────┐
                  ▼                    ▼                    ▼
              [UI Text]           [Tool Exec]          [TTS Stream]
              (immediate)         (parallel)           (sentence 1)
                                                          │
                                                     [Speaker]
                                                   (~1.5-2s total)
```

---

## 16. Project Structure

```
nokton/
├── CONFIRM.md                           # This document
├── README.md                            # Project overview
├── requirements.txt                     # Python dependencies
├── nokton.json                          # Default config
│
├── backend/
│   ├── main.py                          # FastAPI + WebSocket server
│   ├── config.py                        # Config loader
│   │
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── engine.py                    # Agent loop (orchestrator)
│   │   ├── system_prompt.py            # System prompt builder
│   │   ├── conversation_manager.py     # Session persistence
│   │   ├── context_compressor.py       # Context window management
│   │   ├── interrupt_manager.py        # Cancel/stop handling
│   │   └── cost_tracker.py            # Token & cost tracking
│   │
│   ├── providers/
│   │   ├── __init__.py                  # Provider registry
│   │   ├── base.py                     # LLMProvider ABC
│   │   ├── openrouter.py               # OpenRouter implementation
│   │   ├── openai.py                   # OpenAI implementation
│   │   ├── anthropic.py                # Anthropic implementation
│   │   ├── deepseek.py                 # Direct DeepSeek API
│   │   ├── google.py                   # Google Gemini API
│   │   ├── groq.py                     # Groq implementation
│   │   ├── ollama.py                   # Local Ollama
│   │   ├── custom.py                   # Generic OpenAI-compatible
│   │   └── model_catalog.py            # Model discovery & caching
│   │
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── registry.py                 # ToolRegistry, @tool decorator
│   │   ├── schema.py                   # Type hints → JSON Schema gen
│   │   ├── permission.py              # Permission checking
│   │   ├── file_ops.py                 # File operations
│   │   ├── app_control.py             # Application control
│   │   ├── system_info.py             # System info & control
│   │   ├── web_ops.py                 # Web search & fetch
│   │   ├── clipboard_ops.py           # Clipboard & typing
│   │   ├── screenshot.py              # Screen capture & OCR
│   │   ├── window_control.py          # Window management
│   │   └── terminal.py                # Shell command execution
│   │
│   ├── voice/
│   │   ├── __init__.py
│   │   ├── wake_word.py                # Wake word detection
│   │   ├── stt.py                      # Speech-to-text (faster-whisper)
│   │   ├── tts.py                      # Text-to-speech (edge-tts)
│   │   └── vad.py                      # Voice activity detection (Silero)
│   │
│   └── util/
│       ├── api_key_manager.py          # Encrypted key storage
│       ├── audit_logger.py             # Tool audit logging
│       └── image_handler.py            # Image normalization & vision fallback
│
├── frontend/
│   ├── package.json
│   ├── forge.config.js                 # Electron Forge config
│   ├── main.js                         # Electron main process
│   ├── preload.js                      # Preload script (IPC bridge)
│   │
│   └── src/
│       ├── index.html
│       ├── index.tsx                   # React entry
│       ├── App.tsx                     # App shell
│       │
│       ├── components/
│       │   ├── Layout/
│       │   │   ├── Sidebar.tsx
│       │   │   ├── Titlebar.tsx
│       │   │   └── MainView.tsx
│       │   ├── Chat/
│       │   │   ├── MessageList.tsx
│       │   │   ├── MessageBubble.tsx
│       │   │   ├── StreamingText.tsx
│       │   │   ├── ToolCallCard.tsx
│       │   │   ├── InputBar.tsx
│       │   │   ├── ReasoningBlock.tsx
│       │   │   └── CodeBlock.tsx
│       │   ├── Voice/
│       │   │   ├── VoiceIndicator.tsx
│       │   │   └── MicButton.tsx
│       │   ├── Settings/
│       │   │   ├── SettingsPanel.tsx
│       │   │   ├── ModelSelector.tsx
│       │   │   ├── ProviderSettings.tsx
│       │   │   ├── ToolToggles.tsx
│       │   │   ├── VoiceSettings.tsx
│       │   │   └── ReasoningSlider.tsx
│       │   └── Common/
│       │       ├── ConfirmDialog.tsx
│       │       └── ErrorBanner.tsx
│       │
│       ├── hooks/
│       │   ├── useWebSocket.ts
│       │   ├── useConversation.ts
│       │   ├── useSettings.ts
│       │   └── useVoice.ts
│       │
│       ├── services/
│       │   ├── websocket.ts
│       │   ├── api.ts
│       │   └── ipc.ts
│       │
│       ├── stores/
│       │   ├── conversationStore.ts
│       │   ├── settingsStore.ts
│       │   └── voiceStore.ts
│       │
│       ├── types/
│       │   ├── messages.ts
│       │   ├── models.ts
│       │   └── settings.ts
│       │
│       └── styles/
│           ├── global.css
│           ├── chat.css
│           └── settings.css
│
├── scripts/
│   ├── run.bat                          # Windows launch script
│   └── install.bat                      # Windows dependency install
│
└── skills/                              # Built-in skills
    └── file-management/
        └── SKILL.md
```

---

## Key Decisions Summary

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | **Python backend, not TypeScript** | Best ecosystem for audio processing (pyaudio, faster-whisper, silero-vad), desktop automation (pyautogui, psutil), and ML inference |
| 2 | **WebSocket for real-time comms** | Bidirectional streaming, lower latency than HTTP polling, native browser support |
| 3 | **faster-whisper local STT** | Free, MIT license, 4-8x faster than Whisper, no API key, runs locally |
| 4 | **edge-tts for voice** | Free, streaming, natural quality, Microsoft voices, no API key |
| 5 | **OpenWakeWord for wake word** | Free, offline, customizable wake word ("Hey Nokton") |
| 6 | **Provider registry pattern** | Borrowed from OpenCode — any provider can be added via same interface |
| 7 | **Dynamic model catalog** | Fetch models from OpenRouter `/models` endpoint on startup + cache locally |
| 8 | **Vision fallback for text models** | Route images to free vision model (Gemma 3 27B) for description → inject into text-only model |
| 9 | **Per-provider reasoning mapping** | Each provider maps reasoning effort differently — we abstract this via provider-level config |
| 10 | **Layered permissions** | Safe auto-execute / ask confirmation / disabled, per tool category |
| 11 | **Model-level capability flags** | Every model declares what it supports (vision, tools, reasoning, streaming) — features gate automatically |
| 12 | **Session persistence in JSON** | Simple, human-readable, easy to export and debug |
| 13 | **Streaming as default** | Always stream LLM responses, even if UI is minimized — enables health monitoring |
| 14 | **Interrupt on any operation** | "Stop" word in wake listener + cancel button in UI → abort agent loop + kill tools |
| 15 | **Cross-platform target** | Windows primary (user's OS), macOS/Linux as secondary targets |

---

## Questions for Discussion

1. **Should we support plugin hooks** (like OpenClaw's plugin lifecycle) from day 1, or add later?
2. **Should the LLM streaming include reasoning tokens** in the UI, or hide them by default?
3. **Do we want bundled skills** to ship with the app, or just the system + user skills?
4. **For the vision fallback** — should we use `openrouter/google/gemma-3-27b-it:free` or pick a different free vision model?
5. **Should conversations sync across devices** (cloud backup) or stay purely local?
6. **MCP support** — should we support MCP server connections (like OpenClaw/OpenCode) for extensibility?
