"""Configuration - loads settings from .env file."""

import os
from pathlib import Path
from dotenv import load_dotenv

def _get_env_path():
    """Get the path to the .env file."""
    env_paths = [
        Path(__file__).parent.parent / ".env",  # ../.env (project root)
        Path.cwd() / ".env",
    ]
    for env_path in env_paths:
        if env_path.exists():
            return env_path
    return None

def _load_config():
    """Load configuration from .env file."""
    env_path = _get_env_path()
    if env_path:
        # Force reload by clearing cached env vars first
        load_dotenv(env_path, override=True)

# Initial load
_load_config()

# Service URLs
DATABASE_SERVICE_URL = os.getenv("DATABASE_SERVICE_URL", "")

# LLM Configuration
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "")  # groq, openai, anthropic, ollama
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_API_BASE_URL = os.getenv("LLM_API_BASE_URL", "")
LLM_MODEL = os.getenv("LLM_MODEL", "")

# STT Configuration (defaults to LLM settings)
STT_API_KEY = os.getenv("STT_API_KEY", "")
STT_API_BASE_URL = os.getenv("STT_API_BASE_URL", "")
STT_MODEL = os.getenv("STT_MODEL", "")

# TTS Configuration (defaults to LLM settings)
TTS_API_KEY = os.getenv("TTS_API_KEY", "")
TTS_API_BASE_URL = os.getenv("TTS_API_BASE_URL", "")
TTS_MODEL = os.getenv("TTS_MODEL", "")
TTS_VOICE = os.getenv("TTS_VOICE", "")

SYSTEM_PROMPT = os.getenv("SYSTEM_PROMPT", "")

# Hotkeys
OPEN_CONVERSATIONS_KEY = os.getenv("OPEN_CONVERSATIONS_KEY", "shift+f1")
CREATE_AND_OPEN_KEY = os.getenv("CREATE_AND_OPEN_KEY", "shift+f2")
OPEN_CONVERSATION_KEY = os.getenv("OPEN_CONVERSATION_KEY", "shift+f3")
NEW_CONVERSATION_KEY = os.getenv("NEW_CONVERSATION_KEY", "shift+f11")
PUSH_TO_TALK_KEY = os.getenv("PUSH_TO_TALK_KEY", "shift+f12")

# Audio settings
SAMPLE_RATE = 16000
CHANNELS = 1


def is_stt_enabled() -> bool:
    """Check if STT service is enabled (base URL is set)."""
    return bool(STT_API_BASE_URL)


def is_tts_enabled() -> bool:
    """Check if TTS service is enabled (base URL is set)."""
    return bool(TTS_API_BASE_URL)


def reload_config():
    """Reload all configuration from .env file.

    Updates all module-level variables with fresh values from .env.
    Returns a dict with the old and new hotkey values for re-registration.
    """
    global DATABASE_SERVICE_URL, LLM_PROVIDER, LLM_API_KEY, LLM_API_BASE_URL, LLM_MODEL
    global STT_API_KEY, STT_API_BASE_URL, STT_MODEL
    global TTS_API_KEY, TTS_API_BASE_URL, TTS_MODEL, TTS_VOICE
    global SYSTEM_PROMPT
    global OPEN_CONVERSATIONS_KEY, CREATE_AND_OPEN_KEY, OPEN_CONVERSATION_KEY
    global NEW_CONVERSATION_KEY, PUSH_TO_TALK_KEY

    # Store old hotkeys for comparison
    old_hotkeys = {
        'OPEN_CONVERSATIONS_KEY': OPEN_CONVERSATIONS_KEY,
        'CREATE_AND_OPEN_KEY': CREATE_AND_OPEN_KEY,
        'OPEN_CONVERSATION_KEY': OPEN_CONVERSATION_KEY,
        'NEW_CONVERSATION_KEY': NEW_CONVERSATION_KEY,
        'PUSH_TO_TALK_KEY': PUSH_TO_TALK_KEY,
    }

    # Reload from .env
    _load_config()

    # Update all variables
    DATABASE_SERVICE_URL = os.getenv("DATABASE_SERVICE_URL", "")
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "")
    LLM_API_KEY = os.getenv("LLM_API_KEY", "")
    LLM_API_BASE_URL = os.getenv("LLM_API_BASE_URL", "")
    LLM_MODEL = os.getenv("LLM_MODEL", "")
    STT_API_KEY = os.getenv("STT_API_KEY", "")
    STT_API_BASE_URL = os.getenv("STT_API_BASE_URL", "")
    STT_MODEL = os.getenv("STT_MODEL", "")
    TTS_API_KEY = os.getenv("TTS_API_KEY", "")
    TTS_API_BASE_URL = os.getenv("TTS_API_BASE_URL", "")
    TTS_MODEL = os.getenv("TTS_MODEL", "")
    TTS_VOICE = os.getenv("TTS_VOICE", "")
    SYSTEM_PROMPT = os.getenv("SYSTEM_PROMPT", "")
    OPEN_CONVERSATIONS_KEY = os.getenv("OPEN_CONVERSATIONS_KEY", "shift+f1")
    CREATE_AND_OPEN_KEY = os.getenv("CREATE_AND_OPEN_KEY", "shift+f2")
    OPEN_CONVERSATION_KEY = os.getenv("OPEN_CONVERSATION_KEY", "shift+f3")
    NEW_CONVERSATION_KEY = os.getenv("NEW_CONVERSATION_KEY", "shift+f11")
    PUSH_TO_TALK_KEY = os.getenv("PUSH_TO_TALK_KEY", "shift+f12")

    new_hotkeys = {
        'OPEN_CONVERSATIONS_KEY': OPEN_CONVERSATIONS_KEY,
        'CREATE_AND_OPEN_KEY': CREATE_AND_OPEN_KEY,
        'OPEN_CONVERSATION_KEY': OPEN_CONVERSATION_KEY,
        'NEW_CONVERSATION_KEY': NEW_CONVERSATION_KEY,
        'PUSH_TO_TALK_KEY': PUSH_TO_TALK_KEY,
    }

    return {'old': old_hotkeys, 'new': new_hotkeys}