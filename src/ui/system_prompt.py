"""System prompt editor window."""

import threading
import tkinter as tk
from tkinter import messagebox, ttk

from .settings import load_env_vars, save_env_vars
from .theme import (
    BG_DEEP, BG_MID, BG_CARD, BG_LIGHT,
    CRIMSON, BURGUNDY, GOLD,
    TEXT_BRIGHT, TEXT_DIM, TEXT_DARK,
    BORDER
)

# Preset system prompts
SYSTEM_PROMPTS = {
    "The Straight-Shooter": "You are DeskBot, a sharp and efficient desk assistant. Respond in one or two short sentences only. Be blunt, clear, and practical. No markdown, no lists, no fluff.",
    "The Chill Tech Friend": "You are DeskBot, a laid-back but smart desk buddy. Keep replies to one or two short sentences. Sound relaxed and friendly, like a calm developer friend explaining something quickly. No markdown or formatting.",
    "The Motivator": "You are DeskBot, an upbeat and encouraging desk companion. Answer in one or two short sentences with positive energy. Keep it direct, simple, and conversational with no markdown or lists.",
    "The Analytical Thinker": "You are DeskBot, a logical and thoughtful desk assistant. Reply in one or two concise sentences. Be precise, structured in thought, and minimal in wording. No markdown or lists.",
    "Custom": ""
}


def show_system_prompt_window(on_saved: callable = None):
    """Show a window for editing the system prompt.

    Args:
        on_saved: Optional callback when system prompt is saved (for hot-reload)
    """
    # Load data before starting the thread
    env_vars = load_env_vars()

    def show_window():
        root = tk.Tk()
        root.title("System Prompt")
        root.geometry("600x450")
        root.resizable(True, True)
        root.configure(bg=BG_LIGHT)

        current_prompt = env_vars.get("SYSTEM_PROMPT", "")

        # Determine which preset is currently selected (if any)
        selected_preset = "Custom"
        custom_prompt_text = [current_prompt]  # Use list to make it mutable in closure
        for preset_name, preset_text in SYSTEM_PROMPTS.items():
            if preset_name != "Custom" and preset_text == current_prompt:
                selected_preset = preset_name
                break

        def on_save():
            selected = preset_var.get()

            if selected == "Custom":
                # Save the custom prompt
                new_prompt = text_widget.get("1.0", "end-1c").strip()
                if not new_prompt:
                    messagebox.showwarning("Warning", "Custom prompt cannot be empty!")
                    return
                env_vars["SYSTEM_PROMPT"] = new_prompt
            else:
                # Save the selected preset
                preset_text = SYSTEM_PROMPTS.get(selected, "")
                env_vars["SYSTEM_PROMPT"] = preset_text

            if save_env_vars(env_vars):
                if on_saved:
                    on_saved()
                messagebox.showinfo("System Prompt", "System prompt saved and applied!")
                root.destroy()
            else:
                messagebox.showerror("Error", "Failed to save system prompt.")

        def on_cancel():
            root.destroy()

        root.protocol("WM_DELETE_WINDOW", on_cancel)

        # Buttons at bottom - pack FIRST
        btn_frame = tk.Frame(root, bg=BG_LIGHT)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=15)
        tk.Button(btn_frame, text="Save", command=on_save, width=12,
                 font=("Consolas", 9), bg=CRIMSON, fg='white',
                 activebackground=GOLD, relief='flat', cursor='hand2').pack(side=tk.LEFT, padx=5, expand=True)
        tk.Button(btn_frame, text="Cancel", command=on_cancel, width=12,
                 font=("Consolas", 9), bg=TEXT_DIM, fg='white',
                 relief='flat', cursor='hand2').pack(side=tk.LEFT, padx=5, expand=True)

        # Content - pack AFTER buttons
        main_frame = tk.Frame(root, bg=BG_LIGHT)
        main_frame.pack(expand=True, fill='both', padx=15, pady=(10, 0))

        label = tk.Label(main_frame, text="System Prompt", font=("Consolas", 12, "bold"),
                        fg=CRIMSON, bg=BG_LIGHT, anchor="w")
        label.pack(anchor="w", pady=(0, 5))

        hint = tk.Label(main_frame, text="This prompt defines the assistant's personality and behavior.",
                       font=("Consolas", 9), fg=TEXT_DIM, bg=BG_LIGHT, anchor="w")
        hint.pack(anchor="w", pady=(0, 10))

        # Preset selector
        preset_frame = tk.Frame(main_frame, bg=BG_LIGHT)
        preset_frame.pack(anchor="w", fill='x', pady=(0, 10))

        preset_label = tk.Label(preset_frame, text="Style:", font=("Consolas", 9),
                               fg=TEXT_DARK, bg=BG_LIGHT)
        preset_label.pack(side=tk.LEFT, padx=(0, 10))

        preset_var = tk.StringVar(master=root, value=selected_preset)

        preset_combo = ttk.Combobox(preset_frame, textvariable=preset_var,
                                   values=list(SYSTEM_PROMPTS.keys()),
                                   state="readonly", width=25, font=("Consolas", 9))
        preset_combo.pack(side=tk.LEFT)

        # Style the combobox
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TCombobox',
                       fieldbackground='#faf5f5',
                       background=CRIMSON,
                       foreground=TEXT_DARK,
                       arrowcolor=CRIMSON,
                       bordercolor=CRIMSON,
                       lightcolor=BG_LIGHT,
                       darkcolor=BG_LIGHT)

        # Editor with crimson border
        text_outer = tk.Frame(main_frame, bg=CRIMSON)
        text_outer.pack(expand=True, fill='both')

        text_frame = tk.Frame(text_outer, bg='#faf5f5')
        text_frame.pack(expand=True, fill='both', padx=2, pady=2)

        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        text_widget = tk.Text(text_frame, wrap=tk.WORD, font=("Consolas", 10),
                             bg='#faf5f5', fg=TEXT_DARK, insertbackground=BURGUNDY,
                             relief='flat', padx=10, pady=10,
                             yscrollcommand=scrollbar.set)
        text_widget.pack(expand=True, fill='both')
        scrollbar.config(command=text_widget.yview)

        # Set initial text and state
        text_widget.insert("1.0", current_prompt)
        if selected_preset != "Custom":
            text_widget.config(state=tk.DISABLED)  # Read-only for presets

        # Define preset change handler AFTER text_widget is created
        def on_preset_change(*args):
            """Handle preset selection change."""
            selected = preset_var.get()

            # Get the prompt text for the selected preset
            if selected == "Custom":
                new_text = custom_prompt_text[0] if custom_prompt_text[0] else ""
            else:
                new_text = SYSTEM_PROMPTS.get(selected, "")

            # Always enable first to allow modifications
            text_widget.config(state=tk.NORMAL)

            # Clear current content and insert new
            text_widget.delete("1.0", tk.END)
            text_widget.insert("1.0", new_text)

            # Scroll to top
            text_widget.see("1.0")

            # Disable for presets, keep enabled for Custom
            if selected != "Custom":
                text_widget.config(state=tk.DISABLED)

        # Trace variable changes - triggers when combobox selection changes
        preset_var.trace_add("write", on_preset_change)

        root.mainloop()

    threading.Thread(target=show_window, daemon=True).start()
