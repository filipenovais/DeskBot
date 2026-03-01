# DeskBot

![Python](https://img.shields.io/badge/Python-3.10.11-3776AB?style=flat&logo=python&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat&logo=docker&logoColor=white)
![Conda](https://img.shields.io/badge/Conda-44A833?style=flat&logo=anaconda&logoColor=white)

A local-first, voice-activated AI assistant that lives on your desktop.

**Voice:** Hold a hotkey, speak, release.
**Text:** Press a hotkey, window opens, start typing.
That's it.

Minimal dependencies, lightweight stack, modular and free. Easy setup on Windows and Linux with a settings menu for hotkeys, microphone, and API providers. Fork it, tweak it, make it your own.

![DeskBot](DeskBot.gif)


## Why DeskBot?

- **Not locked into one provider** — Swap LLMs via base URL: Groq, OpenAI, Anthropic, Ollama
- **Full privacy option** — Run completely local with Ollama, no API keys required
- **Better models on demand** — Bring your own from any provider via API key, or use Groq's free tier
- **Customizable personality** — Change the system prompt to match your workflow
- **Persistent conversations** — All chats saved in a local Docker container
- **Smart organization** — Auto-generated titles and context-aware replies
- **Voice support** — Pluggable TTS/STT with Groq's free tier
- **Live information** — Web search support (model-dependent)
- **Minimal footprint** — Sits in your system tray, ready when you are

## Features

### Input Modes
- **Voice** — Hold a configurable hotkey, speak, release. Uses Whisper for speech-to-text.
- **Text** — Press a hotkey to open a chat window for typed queries.

### LLM Providers
Swap providers via base URL configuration:
- Groq (free tier available)
- OpenAI
- Anthropic
- Ollama (fully local, no API key required)

### Conversation Management
- All conversations stored locally in a Dockerized SQLite database
- Auto-generated titles based on conversation context
- Resume previous conversations at any time

### Speech Services
- **STT** — Whisper-based transcription via Groq or local instance
- **TTS** — Pluggable text-to-speech with multiple provider options

### Additional
- Web search support for live information retrieval (model-dependent)
- System tray integration for minimal desktop footprint
- Configurable system prompts to customize assistant behavior

## Quick Start

```bash
# Clone the repository
git clone https://github.com/your-username/deskbot.git
cd deskbot

# Run the installer (Git Bash on Windows, Terminal on macOS/Linux)
chmod +x install.sh
./install.sh

# For fully local setup with Ollama
./install.sh --ollama

# Start DeskBot
conda activate deskbot_env
python run.py
```

For detailed instructions, see the **[Setup Guide](docs/setup.html)**.

## Tech Stack

| Component | Technology | Description |
|-----------|------------|-------------|
| Application | Python, Tkinter | Desktop app with system tray integration |
| Database | SQLite | Lightweight persistence running in Docker container |
| Speech-to-Text | Whisper | Transcription via Groq API or local deployment |
| Text-to-Speech | Configurable | Multiple TTS providers supported |
| LLM Interface | OpenAI-compatible | Standard API format for provider flexibility |

## Default Hotkeys

| Key | Action |
|-----|--------|
| `Shift+F12` | Hold to talk (push-to-talk) |
| `Shift+F2` | Create & open new conversation |
| `Shift+F3` | Open current conversation |
| `Shift+F11` | Create new conversation |
| `Shift+F1` | Open conversations window |
