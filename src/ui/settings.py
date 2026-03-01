"""Settings window for editing .env configuration and microphone selection."""

import os
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from src.voice import VoiceHandler
from .theme import (
    BG_DEEP, BG_MID, BG_CARD, BG_LIGHT,
    CRIMSON, BURGUNDY, GOLD, PLUM,
    TEXT_BRIGHT, TEXT_DIM, TEXT_DARK,
    BORDER
)


def get_env_path() -> str:
    """Get the path to the .env file."""
    src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    project_root = os.path.dirname(src_dir)
    return os.path.join(project_root, ".env")


def load_env_vars() -> dict:
    """Load variables from .env file."""
    env_path = get_env_path()
    env_vars = {}

    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()

    return env_vars


def save_env_vars(env_vars: dict) -> bool:
    """Save variables to .env file, preserving comments."""
    env_path = get_env_path()

    try:
        lines = []
        if os.path.exists(env_path):
            with open(env_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

        updated_keys = set()
        new_lines = []

        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith('#') and '=' in stripped:
                key = stripped.split('=', 1)[0].strip()
                if key in env_vars:
                    new_lines.append(f"{key}={env_vars[key]}\n")
                    updated_keys.add(key)
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)

        for key, value in env_vars.items():
            if key not in updated_keys:
                new_lines.append(f"{key}={value}\n")

        with open(env_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)

        return True
    except Exception as e:
        print(f"Error saving .env file: {e}")
        return False


def show_settings_window(selected_mic, on_mic_change: callable, on_settings_saved: callable = None):
    """Show the settings window for editing .env variables and microphone.

    Args:
        selected_mic: Currently selected microphone index
        on_mic_change: Callback when microphone selection changes
        on_settings_saved: Callback when settings are saved (for hot-reload)
    """
    env_vars = load_env_vars()
    microphones = VoiceHandler.list_microphones()

    def show_window():
        root = tk.Tk()
        root.title("Settings")
        root.geometry("600x500")
        root.resizable(True, True)
        root.configure(bg=BG_DEEP)

        entries = {}

        mic_names = ["Default"] + [mic['name'][:50] for mic in microphones]
        mic_indices = [None] + [mic['index'] for mic in microphones]

        current_mic_idx = 0
        if selected_mic is not None:
            for i, idx in enumerate(mic_indices):
                if idx == selected_mic:
                    current_mic_idx = i
                    break

        mic_var = tk.StringVar(master=root, value=mic_names[current_mic_idx])

        def on_save():
            new_vars = {}
            for key, widget in entries.items():
                new_vars[key] = widget.get().strip()  # Save all values including empty

            # Always preserve SYSTEM_PROMPT
            if "SYSTEM_PROMPT" in env_vars:
                new_vars["SYSTEM_PROMPT"] = env_vars["SYSTEM_PROMPT"]

            selected_name = mic_var.get()
            new_mic_index = None
            for i, name in enumerate(mic_names):
                if name == selected_name:
                    new_mic_index = mic_indices[i]
                    break

            on_mic_change(new_mic_index)

            if save_env_vars(new_vars):
                # Call the hot-reload callback if provided
                if on_settings_saved:
                    on_settings_saved()
                messagebox.showinfo("Settings", "Settings saved and applied!")
                root.destroy()
            else:
                messagebox.showerror("Error", "Failed to save settings.")

        def on_cancel():
            root.destroy()

        root.protocol("WM_DELETE_WINDOW", on_cancel)

        # === BUTTONS AT BOTTOM ===
        btn_frame = tk.Frame(root, bg=BG_DEEP)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=15, pady=15)

        btn_style = {'font': ('Consolas', 9), 'width': 12, 'cursor': 'hand2',
                     'relief': 'flat', 'activebackground': GOLD}
        tk.Button(btn_frame, text="Save", command=on_save, bg=CRIMSON, fg='white', **btn_style).pack(side=tk.LEFT, padx=5, expand=True)
        tk.Button(btn_frame, text="Cancel", command=on_cancel, bg=BG_CARD, fg=TEXT_DIM, **btn_style).pack(side=tk.LEFT, padx=5, expand=True)

        # === SCROLLABLE CONTENT ===
        canvas = tk.Canvas(root, bg=BG_DEEP, highlightthickness=0)
        scrollbar = tk.Scrollbar(root, orient="vertical", command=canvas.yview,
                                bg=BG_MID, troughcolor=BG_DEEP,
                                activebackground=CRIMSON, highlightthickness=0,
                                bd=0, width=12)
        scrollable_frame = tk.Frame(canvas, bg=BG_DEEP)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Mouse wheel scrolling
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", on_mousewheel)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(15, 0), pady=(10, 0))
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=(10, 0))

        # Helper functions
        def create_section(parent, title):
            """Create a section frame with title."""
            frame = tk.Frame(parent, bg=BG_CARD, relief=tk.FLAT,
                           highlightbackground=BORDER, highlightthickness=1)
            frame.pack(fill=tk.X, pady=(0, 10))

            title_label = tk.Label(
                frame,
                text=title,
                font=("Consolas", 10, "bold"),
                bg=BG_CARD,
                fg=CRIMSON,
                anchor='w'
            )
            title_label.pack(fill=tk.X, padx=10, pady=(8, 5))

            content = tk.Frame(frame, bg=BG_CARD)
            content.pack(fill=tk.X, padx=10, pady=(0, 10))
            return content

        def create_field(parent, label, key, default="", show=None, width=75):
            """Create a labeled entry field."""
            tk.Label(
                parent,
                text=label,
                font=("Consolas", 9),
                bg=BG_CARD,
                fg=TEXT_DIM,
                anchor='w'
            ).pack(fill=tk.X, pady=(5, 2))

            entry = tk.Entry(parent, width=width, font=("Consolas", 9),
                           bg=BG_MID, fg=TEXT_BRIGHT, insertbackground=CRIMSON,
                           relief='flat', highlightbackground=BORDER,
                           highlightthickness=1, highlightcolor=CRIMSON)
            if show:
                entry.config(show=show)
            entry.insert(0, env_vars.get(key, default))
            entry.pack(fill=tk.X, pady=(0, 3), ipady=3)
            entries[key] = entry
            return entry

        def create_combo(parent, label, var, values, width=70):
            """Create a labeled combobox."""
            tk.Label(
                parent,
                text=label,
                font=("Consolas", 9),
                bg=BG_CARD,
                fg=TEXT_DIM,
                anchor='w'
            ).pack(fill=tk.X, pady=(5, 2))

            combo = ttk.Combobox(parent, textvariable=var, values=values, state="readonly", width=width,
                                font=("Consolas", 9))
            combo.pack(fill=tk.X, pady=(0, 3))
            return combo

        # === HOTKEYS SECTION ===
        hotkey_section = create_section(scrollable_frame, "Hotkeys")
        create_field(hotkey_section, "Open Conversations Window", "OPEN_CONVERSATIONS_KEY", width=10)
        create_field(hotkey_section, "Create & Open New Conversation", "CREATE_AND_OPEN_KEY", width=10)
        create_field(hotkey_section, "Open Current Conversation", "OPEN_CONVERSATION_KEY", width=10)
        create_field(hotkey_section, "Create New Conversation", "NEW_CONVERSATION_KEY", width=10)
        create_field(hotkey_section, "Hold to Talk", "PUSH_TO_TALK_KEY", width=10)
        
        # === AUDIO SECTION ===
        audio_section = create_section(scrollable_frame, "Audio")
        create_combo(audio_section, "Microphone", mic_var, mic_names)
        
        # === DATABASE SECTION ===
        db_section = create_section(scrollable_frame, "Database")
        create_field(db_section, "Service URL", "DATABASE_SERVICE_URL")

        # === LLM SECTION ===
        llm_section = create_section(scrollable_frame, "Language Model")
        create_field(llm_section, "Provider (groq, openai, anthropic, ollama)", "LLM_PROVIDER")
        create_field(llm_section, "API Base URL", "LLM_API_BASE_URL")
        create_field(llm_section, "API Key", "LLM_API_KEY", show="*")
        create_field(llm_section, "Model", "LLM_MODEL")

        # === STT SECTION ===
        stt_section = create_section(scrollable_frame, "Speech-to-Text")
        create_field(stt_section, "API Base URL (disabled if empty)", "STT_API_BASE_URL")
        create_field(stt_section, "API Key", "STT_API_KEY", show="*")
        create_field(stt_section, "Model", "STT_MODEL")

        # === TTS SECTION ===
        tts_section = create_section(scrollable_frame, "Text-to-Speech")
        create_field(tts_section, "API Base URL (disabled if empty)", "TTS_API_BASE_URL")
        create_field(tts_section, "API Key", "TTS_API_KEY", show="*")
        create_field(tts_section, "Model", "TTS_MODEL")
        create_field(tts_section, "Voice", "TTS_VOICE")

        # Update canvas scroll region after all content is added
        scrollable_frame.update_idletasks()
        canvas.configure(scrollregion=canvas.bbox("all"))

        root.mainloop()

    threading.Thread(target=show_window, daemon=True).start()
