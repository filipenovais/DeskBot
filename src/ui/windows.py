"""Tkinter popup windows for viewing conversations."""

import asyncio
import re
import threading
import tkinter as tk
import webbrowser

from .theme import (
    BG_DEEP, BG_MID, BG_CARD, BG_LIGHT,
    CRIMSON, BURGUNDY, GOLD, PLUM,
    TEXT_BRIGHT, TEXT_DIM, TEXT_DARK,
    BORDER, SELECTION,
    STATUS_READY, STATUS_RECORDING, STATUS_PROCESSING, STATUS_OFFLINE
)

# Status colors (matching icon.py)
COLOR_READY = STATUS_READY
COLOR_RECORDING = STATUS_RECORDING
COLOR_PROCESSING = STATUS_PROCESSING
COLOR_OFFLINE = STATUS_OFFLINE

# Track active window instances to prevent duplicates
_chat_windows = {}  # {conv_id: root}
_chat_window_refreshers = {}  # {conv_id: refresh_callback}
_chat_window_message_adders = {}  # {conv_id: add_message_callback}
_chat_window_input_boxes = {}  # {conv_id: input_box}
_chat_window_loading_show = {}  # {conv_id: show_loading_callback}
_chat_window_loading_hide = {}  # {conv_id: hide_loading_callback}

# URL regex pattern (compiled once at module level for performance)
_url_pattern = re.compile(
    r'(https?://[^\s<>"\')\]]+|www\.[^\s<>"\')\]]+)',
    re.IGNORECASE
)


def refresh_chat_window(conv_id: str, conv: dict):
    """Refresh an open chat window with new conversation data.

    Args:
        conv_id: The conversation ID
        conv: The updated conversation data with messages
    """
    if conv_id in _chat_window_refreshers:
        try:
            _chat_window_refreshers[conv_id](conv)
        except Exception:
            # Window might be closed or callback invalid
            if conv_id in _chat_window_refreshers:
                del _chat_window_refreshers[conv_id]


def add_chat_message(conv_id: str, content: str, is_user: bool):
    """Add a single message bubble to an open chat window.

    Args:
        conv_id: The conversation ID
        content: The message content
        is_user: True for user message, False for AI response
    """
    if conv_id in _chat_window_message_adders:
        try:
            _chat_window_message_adders[conv_id](content, is_user)
        except Exception:
            # Window might be closed or callback invalid
            if conv_id in _chat_window_message_adders:
                del _chat_window_message_adders[conv_id]


def show_chat_loading(conv_id: str):
    """Show loading indicator in the chat window.

    Args:
        conv_id: The conversation ID
    """
    if conv_id in _chat_window_loading_show:
        try:
            _chat_window_loading_show[conv_id]()
        except Exception:
            # Window might be closed or callback invalid
            if conv_id in _chat_window_loading_show:
                del _chat_window_loading_show[conv_id]


def hide_chat_loading(conv_id: str):
    """Hide loading indicator in the chat window.

    Args:
        conv_id: The conversation ID
    """
    if conv_id in _chat_window_loading_hide:
        try:
            _chat_window_loading_hide[conv_id]()
        except Exception:
            # Window might be closed or callback invalid
            if conv_id in _chat_window_loading_hide:
                del _chat_window_loading_hide[conv_id]


def is_chat_window_focused(conv_id: str) -> bool:
    """Check if the chat window for a conversation is focused.

    Args:
        conv_id: The conversation ID

    Returns:
        True if the window exists and has focus, False otherwise
    """
    if conv_id not in _chat_windows:
        return False
    try:
        root = _chat_windows[conv_id]
        return root.focus_displayof() is not None
    except tk.TclError:
        # Window was destroyed
        if conv_id in _chat_windows:
            del _chat_windows[conv_id]
        return False


def show_chat_window(
    conv: dict,
    on_back: callable = None,
    on_send_message: callable = None,
    loop: asyncio.AbstractEventLoop = None
):
    """Show a popup window displaying a conversation with interactive chat.

    Args:
        conv: Conversation dictionary with id, title, and messages
        on_back: Callback when user closes the window
        on_send_message: Async callback(conv_id, message_text) -> response_text
        loop: Asyncio event loop for running async operations
    """
    conv_id = conv.get('id')

    # If window for this conversation already exists, bring it to front
    if conv_id in _chat_windows:
        try:
            _chat_windows[conv_id].lift()
            _chat_windows[conv_id].focus_force()
            # Focus the input box so user can start typing immediately
            if conv_id in _chat_window_input_boxes:
                _chat_window_input_boxes[conv_id].focus_set()
            return
        except tk.TclError:
            # Window was destroyed, continue to create new one
            del _chat_windows[conv_id]
            if conv_id in _chat_window_input_boxes:
                del _chat_window_input_boxes[conv_id]

    def show_popup():
        root = tk.Tk()
        root.title(f"{conv.get('title', 'Untitled')[:50]}")
        root.geometry("600x500")
        root.configure(bg=BG_LIGHT)

        # Bring window to front on Windows
        root.lift()
        root.attributes('-topmost', True)
        root.focus_force()

        # Store window instance
        _chat_windows[conv_id] = root

        is_sending = [False]  # Use list to allow modification in nested function

        def handle_back():
            if conv_id in _chat_windows:
                del _chat_windows[conv_id]
            if conv_id in _chat_window_refreshers:
                del _chat_window_refreshers[conv_id]
            if conv_id in _chat_window_message_adders:
                del _chat_window_message_adders[conv_id]
            if conv_id in _chat_window_input_boxes:
                del _chat_window_input_boxes[conv_id]
            if conv_id in _chat_window_loading_show:
                del _chat_window_loading_show[conv_id]
            if conv_id in _chat_window_loading_hide:
                del _chat_window_loading_hide[conv_id]
            root.destroy()
            if on_back:
                on_back()

        root.protocol("WM_DELETE_WINDOW", handle_back)

        # Input area - pack at bottom
        input_frame = tk.Frame(root, bg=BG_LIGHT)
        input_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0, 10))

        input_label = tk.Label(input_frame, text="Message:", font=("Consolas", 9, "bold"),
                               bg=BG_LIGHT, fg=CRIMSON)
        input_label.pack(anchor=tk.W, pady=(0, 2))

        input_container = tk.Frame(input_frame, bg=CRIMSON)
        input_container.pack(fill=tk.X)

        input_box = tk.Text(input_container, font=("Consolas", 10), height=3,
                           bg='#faf5f5', fg=TEXT_DARK, insertbackground=BURGUNDY,
                           relief='flat', padx=8, pady=5)
        input_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=2, pady=2)

        # Store input box reference for focus management
        _chat_window_input_boxes[conv_id] = input_box

        # Content - Scrollable message area with bubbles
        chat_container = tk.Frame(root, bg='#faf5f5', relief='flat')
        chat_container.pack(expand=True, fill='both', padx=10, pady=(10, 0))

        canvas = tk.Canvas(chat_container, bg='#faf5f5', highlightthickness=0)
        scrollbar = tk.Scrollbar(chat_container, orient="vertical", command=canvas.yview)
        msg_frame = tk.Frame(canvas, bg='#faf5f5')

        msg_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas_window = canvas.create_window((0, 0), window=msg_frame, anchor="nw")

        # Make msg_frame expand to canvas width
        def on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)
        canvas.bind("<Configure>", on_canvas_configure)

        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill='both', expand=True)
        scrollbar.pack(side=tk.RIGHT, fill='y')

        # Mouse wheel scrolling
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", on_mousewheel)

        # Loading animation state
        loading_bubble_ref = [None]  # Reference to current loading bubble
        loading_animation_id = [None]  # Reference to animation after() id

        def create_loading_bubble(parent):
            """Create a loading indicator bubble with pulsating dots."""
            row = tk.Frame(parent, bg='#faf5f5')
            row.pack(fill='x', pady=4, padx=10)

            bubble_bg = '#f0e8e8'
            bubble_fg = TEXT_DARK

            # Create bubble frame
            bubble = tk.Frame(row, bg=bubble_bg, padx=12, pady=8)
            bubble.pack(anchor='w')

            # Create three dot labels
            dots = []
            for i in range(3):
                dot = tk.Label(
                    bubble,
                    text="●",
                    font=("Consolas", 14),
                    bg=bubble_bg,
                    fg=TEXT_DIM
                )
                dot.pack(side=tk.LEFT, padx=2)
                dots.append(dot)

            # Animation state
            animation_step = [0]

            def animate_dots():
                """Animate the dots with pulsating effect."""
                if not row.winfo_exists():
                    return

                step = animation_step[0] % 6
                for i, dot in enumerate(dots):
                    # Create a wave effect - each dot lights up in sequence
                    if step == i * 2 or step == i * 2 + 1:
                        dot.config(fg=CRIMSON)
                    else:
                        dot.config(fg=TEXT_DIM)

                animation_step[0] += 1
                # Store animation id so we can cancel it
                loading_animation_id[0] = root.after(100, animate_dots)

            # Start animation
            animate_dots()

            return row

        def remove_loading_bubble():
            """Remove the loading bubble and stop animation."""
            if loading_animation_id[0]:
                try:
                    root.after_cancel(loading_animation_id[0])
                except:
                    pass
                loading_animation_id[0] = None

            if loading_bubble_ref[0]:
                try:
                    loading_bubble_ref[0].destroy()
                except:
                    pass
                loading_bubble_ref[0] = None

        def create_bubble(parent, text, is_user, is_cancelled=False, is_error=False):
            """Create a message bubble with selectable/copyable text and clickable links."""
            row = tk.Frame(parent, bg='#faf5f5')
            row.pack(fill='x', pady=4, padx=10)

            if is_cancelled:
                bubble_bg = '#8B4513'  # Brown for cancelled
                bubble_fg = '#FFE4B5'  # Light text
                anchor = 'w'
            elif is_error:
                bubble_bg = '#f0e8e8'  # Light background like AI bubble
                bubble_fg = '#CC0000'  # Red text for errors
                anchor = 'e'  # Right side for errors
            elif is_user:
                bubble_bg = CRIMSON
                bubble_fg = 'white'
                anchor = 'e'
            else:
                bubble_bg = '#f0e8e8'
                bubble_fg = TEXT_DARK
                anchor = 'w'

            # Use Text widget for selectable/copyable content
            bubble = tk.Text(
                row, font=("Consolas", 10),
                bg=bubble_bg, fg=bubble_fg,
                padx=12, pady=8,
                wrap='word', width=50, height=1,
                relief='flat', borderwidth=0,
                selectbackground=GOLD if is_user else CRIMSON,
                selectforeground='white' if not is_user else TEXT_DARK,
                cursor='arrow'
            )

            # Configure link tag style
            link_color = '#4da6ff' if is_user else '#0066cc'  # Lighter blue for dark bg, darker for light bg
            bubble.tag_configure('link', foreground=link_color, underline=True)

            # Insert text and find links
            bubble.insert('1.0', text)

            # Find and tag all URLs
            for match in _url_pattern.finditer(text):
                start_idx = f"1.0+{match.start()}c"
                end_idx = f"1.0+{match.end()}c"
                url = match.group(0)
                tag_name = f"link_{match.start()}"

                bubble.tag_add('link', start_idx, end_idx)
                bubble.tag_add(tag_name, start_idx, end_idx)

                # Bind click event to open URL
                def make_click_handler(url_to_open):
                    def handler(event):
                        # Add http:// if missing
                        full_url = url_to_open if url_to_open.startswith('http') else f'http://{url_to_open}'
                        webbrowser.open(full_url)
                    return handler

                bubble.tag_bind(tag_name, '<Button-1>', make_click_handler(url))
                bubble.tag_bind(tag_name, '<Enter>', lambda e: bubble.config(cursor='hand2'))
                bubble.tag_bind(tag_name, '<Leave>', lambda e: bubble.config(cursor='arrow'))

            # Auto-resize height based on content
            lines = text.count('\n') + 1
            char_width = 50  # approximate chars per line
            wrapped_lines = max(1, len(text) // char_width + lines)
            bubble.config(height=min(wrapped_lines + 1, 20))  # Cap at 20 lines

            # Make read-only but selectable
            bubble.config(state=tk.DISABLED)

            bubble.pack(anchor=anchor)
            return row

        def update_conversation_display(new_conv=None):
            """Update the message area with current messages.

            Args:
                new_conv: Optional new conversation data to update from.
            """
            # Update conv data if provided
            if new_conv is not None:
                conv['messages'] = new_conv.get('messages', [])
                conv['title'] = new_conv.get('title', conv.get('title'))

            # Clear existing bubbles
            for widget in msg_frame.winfo_children():
                widget.destroy()

            messages = conv.get('messages', [])
            for msg in messages:
                is_user = msg['role'] == 'human'
                create_bubble(msg_frame, msg['content'].lstrip(), is_user)

            # Scroll to bottom after update
            root.after(50, lambda: canvas.yview_moveto(1.0))

        def external_refresh(new_conv):
            """Called from outside to refresh the chat window with new data."""
            try:
                root.after(0, lambda: update_conversation_display(new_conv))
            except tk.TclError:
                pass  # Window was destroyed

        def external_add_message(content, is_user):
            """Called from outside to add a single message bubble."""
            def add():
                create_bubble(msg_frame, content.lstrip(), is_user)
                # Also add to conv messages to keep in sync
                role = 'human' if is_user else 'ai'
                conv['messages'].append({'role': role, 'content': content})
                canvas.update_idletasks()
                canvas.yview_moveto(1.0)
            try:
                root.after(0, add)
            except tk.TclError:
                pass  # Window was destroyed

        def external_show_loading():
            """Called from outside to show loading indicator."""
            def show():
                # Only show if not already showing
                if loading_bubble_ref[0] is None:
                    loading_bubble_ref[0] = create_loading_bubble(msg_frame)
                    canvas.update_idletasks()
                    canvas.yview_moveto(1.0)
            try:
                root.after(0, show)
            except tk.TclError:
                pass  # Window was destroyed

        def external_hide_loading():
            """Called from outside to hide loading indicator."""
            try:
                root.after(0, remove_loading_bubble)
            except tk.TclError:
                pass  # Window was destroyed

        # Store the refresh callback
        _chat_window_refreshers[conv_id] = external_refresh
        _chat_window_message_adders[conv_id] = external_add_message
        _chat_window_loading_show[conv_id] = external_show_loading
        _chat_window_loading_hide[conv_id] = external_hide_loading

        def handle_send():
            """Handle sending a message."""
            if is_sending[0] or not on_send_message or not loop:
                return

            message = input_box.get("1.0", tk.END).strip()
            if not message:
                return

            # Clear input and disable controls
            input_box.delete("1.0", tk.END)
            input_box.config(state=tk.DISABLED)
            is_sending[0] = True

            # Add user message to display immediately
            create_bubble(msg_frame, message, True)
            canvas.update_idletasks()
            canvas.yview_moveto(1.0)

            # Show loading bubble while waiting for response
            loading_bubble_ref[0] = create_loading_bubble(msg_frame)
            canvas.update_idletasks()
            canvas.yview_moveto(1.0)

            # Run async send operation
            def on_complete(future):
                try:
                    response = future.result()
                    # Update display with assistant response
                    root.after(0, lambda: add_assistant_response(response, is_error=False))
                except Exception as e:
                    error_msg = f"Error: {str(e)}"
                    root.after(0, lambda: add_assistant_response(error_msg, is_error=True))
                finally:
                    # Re-enable controls
                    root.after(0, lambda: finish_send())

            def add_assistant_response(response, is_error=False):
                """Add assistant response to display."""
                # Remove loading bubble first
                remove_loading_bubble()

                # Always add the user message to conversation history
                conv['messages'].append({"role": "human", "content": message})

                # Only add AI response if not an error
                if not is_error:
                    conv['messages'].append({"role": "ai", "content": response})

                create_bubble(msg_frame, response, is_user=False, is_error=is_error)
                canvas.update_idletasks()
                canvas.yview_moveto(1.0)

                # If error, restore focus to chat window after a brief delay
                if is_error:
                    root.after(100, lambda: root.lift())
                    root.after(150, lambda: root.focus_force())
                    root.after(200, lambda: input_box.focus_set())

            def finish_send():
                """Re-enable controls after send."""
                input_box.config(state=tk.NORMAL)
                is_sending[0] = False
                input_box.focus()

            # Schedule async operation
            future = asyncio.run_coroutine_threadsafe(
                on_send_message(conv_id, message),
                loop
            )
            future.add_done_callback(on_complete)

        # Bind Enter key to send
        def on_enter(event):
            if event.state & 0x0001:  # Shift pressed
                return  # allow newline
            else:
                handle_send()
                return "break"  # prevent newline when sending

        input_box.bind("<Return>", on_enter)

        # Initial display
        update_conversation_display()

        # Focus input box after window is fully ready
        def set_focus():
            root.attributes('-topmost', False)
            input_box.focus_set()
        root.after(100, set_focus)

        root.mainloop()

    threading.Thread(target=show_popup, daemon=True).start()


def _create_status_dot(parent, color, size=12):
    """Create a colored circle canvas."""
    canvas = tk.Canvas(parent, width=size, height=size, highlightthickness=0, bg=parent.cget('bg'))
    margin = 1
    canvas.create_oval(margin, margin, size - margin, size - margin, fill=color, outline="")
    return canvas


_conversations_window_instance = [None]  # Track active window instance

def show_conversations_window(
    cached_conversations: list,
    current_conversation_id: str,
    hotkey: str,
    new_conv_key: str,
    open_conv_key: str,
    create_and_open_key: str,
    open_conversations_key: str,
    on_continue: callable,
    on_open: callable,
    on_delete: callable,
    on_rename: callable,
    on_refresh: callable,
    on_register_refresh: callable,
    on_new_conversation: callable = None,
    service_statuses: dict = None,
    on_refresh_services: callable = None
):
    """Show a window listing all conversations with actions."""
    # If window already exists, bring it to front
    if _conversations_window_instance[0] is not None:
        try:
            _conversations_window_instance[0].lift()
            _conversations_window_instance[0].focus_force()
            return
        except tk.TclError:
            # Window was destroyed, continue to create new one
            _conversations_window_instance[0] = None

    def show_window():
        root = tk.Tk()
        root.title("DeskBot")
        root.geometry("600x500")
        root.configure(bg=BG_DEEP)

        # Load icon with error handling
        try:
            icon = tk.PhotoImage(file="./src/icon.png")
            root.iconphoto(True, icon)
        except Exception as e:
            print(f"Could not load icon: {e}")

        # Store window instance
        _conversations_window_instance[0] = root

        # Bring window to front on Windows
        root.lift()
        root.attributes('-topmost', True)
        root.focus_force()
        # Reset topmost after window is shown so other windows can come to front
        root.after(100, lambda: root.attributes('-topmost', False))

        conversations = list(cached_conversations)  # Local mutable copy
        conv_map = {}
        current_idx = [None]  # Use list to allow modification in nested function
        current_conv_id = [current_conversation_id]  # Track current conv id

        def on_close():
            if on_register_refresh:
                on_register_refresh(None)  # Unregister callback
            _conversations_window_instance[0] = None
            root.destroy()

        root.protocol("WM_DELETE_WINDOW", on_close)

        # === INFO PANEL AT TOP ===
        info_frame = tk.Frame(root, bg=BG_DEEP, relief=tk.FLAT, bd=0)
        info_frame.pack(fill=tk.X, padx=10, pady=(10, 5))

        # Inner frame with rounded appearance
        inner_frame = tk.Frame(info_frame, bg=BG_CARD, relief=tk.FLAT, bd=0,
                               highlightbackground=BORDER, highlightthickness=1)
        inner_frame.pack(fill=tk.X, padx=2, pady=2)

        # Status row - compact horizontal layout showing service statuses
        status_row = tk.Frame(inner_frame, bg=BG_CARD)
        status_row.pack(fill=tk.X, padx=12, pady=(10, 8))

        tk.Label(
            status_row,
            text="Services:",
            font=("Consolas", 9, "bold"),
            bg=BG_CARD,
            fg=CRIMSON
        ).pack(side=tk.LEFT, padx=(0, 12))

        # Get service statuses (default to all False if not provided)
        statuses = service_statuses or {}
        service_keys = ["database", "llm", "stt", "tts"]
        service_labels = ["Database", "LLM", "STT", "TTS"]
        status_dots = {}  # Store references to dots for updating

        for key, label in zip(service_keys, service_labels):
            is_available = statuses.get(key, False)
            color = COLOR_READY if is_available else COLOR_OFFLINE
            dot = _create_status_dot(status_row, color, size=10)
            dot.configure(bg=BG_CARD)
            dot.pack(side=tk.LEFT, padx=(0, 3))
            status_dots[key] = dot
            tk.Label(
                status_row,
                text=label,
                font=("Consolas", 8),
                bg=BG_CARD,
                fg=TEXT_DIM
            ).pack(side=tk.LEFT, padx=(0, 12))

        def update_service_statuses(new_statuses: dict):
            """Update the service status dots with new values."""
            for key, dot in status_dots.items():
                is_available = new_statuses.get(key, False)
                color = COLOR_READY if is_available else COLOR_OFFLINE
                dot.delete("all")
                margin = 1
                dot.create_oval(margin, margin, 10 - margin, 10 - margin, fill=color, outline="")

        # Separator
        tk.Frame(inner_frame, height=1, bg=BORDER).pack(fill=tk.X, padx=12)

        # Hotkeys section
        hotkey_section = tk.Frame(inner_frame, bg=BG_CARD)
        hotkey_section.pack(fill=tk.X, padx=12, pady=(8, 10))

        tk.Label(
            hotkey_section,
            text="Hotkeys:",
            font=("Consolas", 9, "bold"),
            bg=BG_CARD,
            fg=CRIMSON
        ).pack(anchor=tk.W, pady=(0, 6))

        # Hotkey grid
        keys_grid = tk.Frame(hotkey_section, bg=BG_CARD)
        keys_grid.pack(fill=tk.X)

        hotkeys_data = [
            (open_conversations_key.upper(), "Open Conversations window", "Press"),
            (create_and_open_key.upper(), "Create & Open New conversation", "Press"),
            (open_conv_key.upper(), "Open Current conversation", "Press"),
            (new_conv_key.upper(), "Create New conversation", "Press"),
            (hotkey.upper(), "Talk", "Hold"),
        ]

        for i, (key, desc, action) in enumerate(hotkeys_data):
            row = tk.Frame(keys_grid, bg=BG_CARD)
            row.pack(fill=tk.X, pady=1)

            # Key badge
            key_label = tk.Label(
                row,
                text=f" {key} ",
                font=("Consolas", 8, "bold"),
                bg=BURGUNDY,
                fg=TEXT_BRIGHT,
                relief=tk.FLAT
            )
            key_label.pack(side=tk.LEFT, padx=(0, 8))

            # Action + description
            tk.Label(
                row,
                text=f"{action} to {desc.lower()}",
                font=("Consolas", 8),
                bg=BG_CARD,
                fg=TEXT_DIM,
                anchor=tk.W
            ).pack(side=tk.LEFT)

        # === BUTTONS AT BOTTOM ===
        btn_frame = tk.Frame(root, bg=BG_DEEP)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)

        btn_style = {'font': ('Consolas', 9), 'width': 9, 'cursor': 'hand2',
                     'bg': CRIMSON, 'fg': 'white', 'activebackground': GOLD,
                     'relief': 'flat'}

        def highlight_current():
            """Update highlighting to show current conversation."""
            for i in range(listbox.size()):
                if i == current_idx[0]:
                    listbox.itemconfig(i, bg=SELECTION, fg=TEXT_BRIGHT)
                else:
                    listbox.itemconfig(i, bg=BG_MID, fg=TEXT_BRIGHT)

        def update_title_prefix(idx, is_current):
            """Update the title prefix for an item."""
            conv = conv_map[idx]
            title = conv.get('title', 'Untitled')[:42]
            prefix = "\u2713 " if is_current else "   "
            listbox.delete(idx)
            listbox.insert(idx, prefix + title)
            conv_map[idx] = conv

        def handle_open():
            selection = listbox.curselection()
            if selection:
                conv = conv_map[selection[0]]
                conv_id = conv['id']
                on_open(conv_id)

        def handle_select():
            selection = listbox.curselection()
            if selection:
                idx = selection[0]
                conv = conv_map[idx]
                # Remove checkmark from old current
                if current_idx[0] is not None and current_idx[0] != idx:
                    update_title_prefix(current_idx[0], False)
                # Add checkmark to new current
                update_title_prefix(idx, True)
                current_idx[0] = idx
                highlight_current()
                listbox.selection_set(idx)
                on_continue(conv['id'])

        def handle_delete():
            selection = listbox.curselection()
            if selection:
                deleted_idx = selection[0]
                conv = conv_map[deleted_idx]
                conv_id = conv['id']
                listbox.delete(deleted_idx)
                new_map = {}
                idx = 0
                for old_idx, c in conv_map.items():
                    if old_idx != deleted_idx:
                        new_map[idx] = c
                        idx += 1
                conv_map.clear()
                conv_map.update(new_map)
                # Update current_idx if needed
                if current_idx[0] is not None:
                    if current_idx[0] == deleted_idx:
                        current_idx[0] = None
                    elif current_idx[0] > deleted_idx:
                        current_idx[0] -= 1
                highlight_current()
                on_delete(conv_id)

        def handle_rename():
            selection = listbox.curselection()
            if selection and on_rename:
                idx = selection[0]
                conv = conv_map[idx]
                on_rename(conv['id'], lambda new_title: root.after(0, lambda: update_list_title(idx, new_title)))

        def refresh_list(new_conversations, new_current_id):
            """Refresh the list with new data."""
            current_conv_id[0] = new_current_id
            listbox.delete(0, tk.END)
            conv_map.clear()
            current_idx[0] = None
            for i, conv in enumerate(new_conversations):
                title = conv.get('title', 'Untitled')[:42]
                if conv['id'] == new_current_id:
                    title = f"\u2713 {title}"
                    current_idx[0] = i
                else:
                    title = f"   {title}"
                listbox.insert(tk.END, title)
                conv_map[i] = conv
            highlight_current()
            # Select the current conversation
            if current_idx[0] is not None:
                listbox.selection_clear(0, tk.END)
                listbox.selection_set(current_idx[0])
                listbox.see(current_idx[0])

        def handle_refresh():
            if on_refresh:
                new_conversations, new_current_id = on_refresh()
                if new_conversations is not None:
                    refresh_list(new_conversations, new_current_id)
            # Also refresh service statuses
            if on_refresh_services:
                new_statuses = on_refresh_services()
                if new_statuses is not None:
                    update_service_statuses(new_statuses)

        def external_refresh(new_conversations, new_current_id, new_service_statuses=None):
            """Called from outside to refresh the window."""
            try:
                root.after(0, lambda: refresh_list(new_conversations, new_current_id))
                if new_service_statuses is not None:
                    root.after(0, lambda: update_service_statuses(new_service_statuses))
            except tk.TclError:
                pass  # Window was destroyed

        def update_list_title(idx, new_title):
            """Update the title in the listbox after rename."""
            if idx in conv_map:
                conv_map[idx]['title'] = new_title
                is_current = idx == current_idx[0]
                prefix = "\u2713 " if is_current else "   "
                listbox.delete(idx)
                listbox.insert(idx, prefix + new_title[:42])
                highlight_current()
                listbox.selection_set(idx)

        def handle_new():
            """Handle creating a new conversation and opening it."""
            if on_new_conversation:
                on_new_conversation()

        tk.Button(btn_frame, text="New", command=handle_new, **btn_style).pack(side=tk.LEFT, padx=3, expand=True)
        tk.Button(btn_frame, text="Open", command=handle_open, **btn_style).pack(side=tk.LEFT, padx=3, expand=True)
        tk.Button(btn_frame, text="Rename", command=handle_rename, **btn_style).pack(side=tk.LEFT, padx=3, expand=True)
        tk.Button(btn_frame, text="Delete", command=handle_delete, **btn_style).pack(side=tk.LEFT, padx=3, expand=True)
        tk.Button(btn_frame, text="Refresh", command=handle_refresh, **btn_style).pack(side=tk.LEFT, padx=3, expand=True)

        # === CONVERSATIONS LIST ===
        list_label = tk.Label(
            root,
            text="Conversations",
            font=("Consolas", 10, "bold"),
            bg=BG_DEEP,
            fg=CRIMSON,
            anchor=tk.W
        )
        list_label.pack(fill=tk.X, padx=12, pady=(8, 2))

        frame = tk.Frame(root, bg=BG_DEEP)
        frame.pack(expand=True, fill='both', padx=10, pady=(0, 5))

        scrollbar = tk.Scrollbar(frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        listbox = tk.Listbox(
            frame,
            yscrollcommand=scrollbar.set,
            font=("Consolas", 10),
            bg=BG_MID,
            fg=TEXT_BRIGHT,
            selectbackground=CRIMSON,
            selectforeground='white',
            activestyle='none',
            relief=tk.FLAT,
            bd=0,
            highlightthickness=1,
            highlightcolor=BORDER
        )
        listbox.pack(expand=True, fill='both')
        scrollbar.config(command=listbox.yview)

        for i, conv in enumerate(conversations):
            title = conv.get('title', 'Untitled')[:42]
            if conv['id'] == current_conv_id[0]:
                title = f"\u2713 {title}"
                current_idx[0] = i
            else:
                title = f"   {title}"
            listbox.insert(tk.END, title)
            conv_map[i] = conv

        highlight_current()

        # Select the current conversation
        if current_idx[0] is not None:
            listbox.selection_set(current_idx[0])
            listbox.see(current_idx[0])

        # Bind single-click to select conversation
        def on_single_click(event):
            """Handle single click - select the conversation."""
            # Small delay to let the selection happen first
            root.after(50, handle_select)

        # Bind double-click to open conversation
        def on_double_click(event):
            """Handle double click - open the conversation."""
            handle_open()

        listbox.bind('<ButtonRelease-1>', on_single_click)
        listbox.bind('<Double-Button-1>', on_double_click)

        # Register the external refresh callback
        if on_register_refresh:
            on_register_refresh(external_refresh)

        root.mainloop()

    threading.Thread(target=show_window, daemon=True).start()
