"""Main DeskBot class for the system tray application."""

import asyncio
import threading
import traceback

import httpx
import keyboard
import pystray

from src.database import DatabaseHandler
from src.llm import LLMHandler
from src import config
from src.voice import VoiceHandler

from .icon import create_icon, get_color_for_state, COLOR_OFFLINE
from .windows import show_chat_window, show_conversations_window, add_chat_message, is_chat_window_focused, show_chat_loading, hide_chat_loading, refresh_chat_window
from .settings import show_settings_window
from .system_prompt import show_system_prompt_window


class DeskBot:
    def __init__(self):
        self.conversation_id = None
        self.selected_mic = None
        self.voice_handler = VoiceHandler(device=self.selected_mic)
        self.database_handler = DatabaseHandler()
        self.running = True
        self.state = "offline"
        self.icon = None
        self.loop = None
        self.cached_conversations = []
        self.cached_microphones = []
        self.cached_service_statuses = {"database": False, "llm": False, "stt": False, "tts": False}
        self.window_refresh_callback = None
        self.text_mode_active = False  # Flag to track if chat window is open
        self._quit_event = None  # Event to signal quit
        self._recording = False  # Flag to track recording state
        self._processing = False  # Flag to track if processing voice input
        self._cancel_requested = False  # Flag to signal cancellation
        self._current_task = None  # Current async processing task

    def update_icon(self, state: str):
        """Update the tray icon to reflect the current state."""
        self.state = state
        color = get_color_for_state(state)
        if self.icon:
            self.icon.icon = create_icon(color)
            self.icon.title = f"DeskBot - {state.title()}"

    def quit_app(self, icon, item):
        """Quit the application."""
        self.running = False
        # Signal the async loop to exit
        if self._quit_event and self.loop:
            self.loop.call_soon_threadsafe(self._quit_event.set)
        icon.stop()

    def select_microphone(self, mic_index):
        """Create callback for microphone selection."""
        def callback(icon, item):
            self.selected_mic = mic_index
            self.voice_handler.set_device(mic_index)
            mic_name = "Default" if mic_index is None else f"Device {mic_index}"
            for mic in self.cached_microphones:
                if mic['index'] == mic_index:
                    mic_name = mic['name']
                    break
            print(f"Microphone changed to: {mic_name}")
        return callback

    def is_mic_selected(self, mic_index):
        """Check if a microphone is currently selected."""
        def check(item):
            return self.selected_mic == mic_index
        return check

    def continue_conversation(self, conv_id):
        """Create callback for continuing a conversation."""
        def callback(icon, item):
            self.conversation_id = conv_id
            print(f"Continuing conversation: {conv_id[:8]}...")
        return callback

    def open_conversation(self, conv_id):
        """Create callback for opening a chat window."""
        def callback(icon, item):
            if self.loop:
                asyncio.run_coroutine_threadsafe(
                    self._show_chat_window(conv_id),
                    self.loop
                )
        return callback

    def delete_conversation(self, conv_id):
        """Create callback for deleting a conversation."""
        def callback(icon, item):
            if self.loop:
                asyncio.run_coroutine_threadsafe(
                    self._delete_conversation(conv_id),
                    self.loop
                )
        return callback

    async def _show_chat_window(self, conv_id, conv_data=None):
        """Load and show a chat in a popup window.

        Args:
            conv_id: The conversation ID
            conv_data: Optional conversation data to skip API fetch
        """
        try:
            def on_back_handler():
                """Handle closing the popup - re-enable TTS/STT."""
                self.text_mode_active = False

            # Disable TTS/STT while popup is open
            self.text_mode_active = True

            if conv_data:
                # We have full data, show immediately
                show_chat_window(
                    conv_data,
                    on_back=on_back_handler,
                    on_send_message=self._send_text_message,
                    loop=self.loop
                )
            else:
                # Show window immediately with cached info (no messages yet)
                # Then load messages in background
                cached_conv = None
                for c in self.cached_conversations:
                    if c['id'] == conv_id:
                        cached_conv = c
                        break

                # Create minimal conv data to show window instantly
                minimal_conv = {
                    'id': conv_id,
                    'title': cached_conv.get('title', 'Loading...') if cached_conv else 'Loading...',
                    'messages': []
                }

                show_chat_window(
                    minimal_conv,
                    on_back=on_back_handler,
                    on_send_message=self._send_text_message,
                    loop=self.loop
                )

                # Load full conversation in background and refresh
                full_conv = await self.database_handler.get_conversation(conv_id)
                if full_conv:
                    refresh_chat_window(conv_id, full_conv)

        except Exception as e:
            print(f"Error loading conversation: {e}")
            self.text_mode_active = False

    async def _send_text_message(self, conv_id: str, message: str) -> str:
        """Send a text message and get AI response (no TTS/STT).

        Args:
            conv_id: The conversation ID
            message: The user's text message

        Returns:
            The assistant's response text
        """
        try:
            print(f'[Text] You: "{message}"')

            # Get conversation history
            conv = await self.database_handler.get_conversation(conv_id)
            history = [
                {"role": m["role"], "content": m["content"]}
                for m in conv.get("messages", [])
            ]

            # Generate AI response (no TTS)
            print("[Text] Generating AI response...")
            llm_handler = LLMHandler()
            response = await llm_handler.generate_response(history, message)
            print(f"[Text] DeskBot: {response}")

            # Save messages to database
            await self.database_handler.save_messages(
                conv_id,
                [
                    {"role": "human", "content": message},
                    {"role": "ai", "content": response}
                ]
            )

            return response

        except Exception as e:
            print(f"Error in _send_text_message: {e}")
            traceback.print_exc()
            raise

    async def _delete_conversation(self, conv_id):
        """Delete a conversation from the database."""
        try:
            success = await self.database_handler.delete_conversation(conv_id)
            if success:
                print(f"Deleted conversation: {conv_id[:8]}...")
                if self.conversation_id == conv_id:
                    self.conversation_id = None
                    print("Current conversation was deleted.")
                await self.refresh_conversations()
            else:
                print(f"Failed to delete conversation: {conv_id[:8]}")
        except Exception as e:
            print(f"Error deleting conversation: {e}")

    async def _rename_conversation(self, conv_id, callback):
        """Generate a new title for a conversation based on its content."""
        try:
            conv = await self.database_handler.get_conversation(conv_id)
            messages = conv.get('messages', [])

            if not messages:
                print("No messages to generate title from")
                return

            # Build a summary of the conversation for title generation
            conversation_text = "\n".join([
                f"{msg['role']}: {msg['content'][:200]}"
                for msg in messages[:6]  # Use first 6 messages max
            ])

            # Generate title using LLM
            llm_handler = LLMHandler()
            prompt = f"Based on this conversation, generate a short, descriptive title (max 50 characters). Reply with ONLY the title, nothing else.\n\nConversation:\n{conversation_text}"

            loop = asyncio.get_event_loop()
            new_title = await loop.run_in_executor(
                None,
                llm_handler.generate_response_sync,
                [],  # empty conversation history
                prompt
            )
            new_title = new_title.strip().strip('"\'')[:50]

            # Update in database
            success = await self.database_handler.update_conversation_title(conv_id, new_title)
            if success:
                print(f"Renamed conversation to: {new_title}")
                await self.refresh_conversations()
                # Call the callback on the main thread to update UI
                if callback:
                    import tkinter as tk
                    # Schedule callback on the tkinter thread
                    callback(new_title)
            else:
                print("Failed to update conversation title")
        except Exception as e:
            print(f"Error renaming conversation: {e}")
            traceback.print_exc()

    def is_current_conversation(self, conv_id):
        """Check if a conversation is the current one."""
        def check(item):
            return self.conversation_id == conv_id
        return check

    def _sync_refresh_conversations(self):
        """Synchronously refresh the conversation list."""
        try:
            with httpx.Client(timeout=5.0) as client:
                r = client.get(f"{config.DATABASE_SERVICE_URL}/conversations")
                if r.status_code == 200:
                    self.cached_conversations = r.json()
        except Exception as e:
            print(f"Error fetching conversations: {e}")

    def _sync_create_conversation(self, title: str = "New Conversation..."):
        """Synchronously create a new conversation."""
        try:
            with httpx.Client(timeout=5.0) as client:
                r = client.post(
                    f"{config.DATABASE_SERVICE_URL}/conversations",
                    json={"title": title}
                )
                if r.status_code == 200:
                    conv = r.json()
                    self.conversation_id = conv['id']
                    self._sync_refresh_conversations()
                    self._notify_window_refresh()
                    return conv
        except Exception as e:
            print(f"Error creating conversation: {e}")
        return None

    def _notify_window_refresh(self):
        """Notify the window to refresh if it's open."""
        if self.window_refresh_callback:
            try:
                self.window_refresh_callback(
                    self.cached_conversations,
                    self.conversation_id
                )
            except Exception:
                # Window might be closed
                self.window_refresh_callback = None

    async def _async_refresh_and_notify(self):
        """Async refresh conversations and notify the window."""
        await self.refresh_conversations()
        self._notify_window_refresh()

    async def _async_check_services_and_notify(self):
        """Async check services and notify the window."""
        new_statuses = await self.check_services()
        if self.window_refresh_callback:
            try:
                self.window_refresh_callback(
                    self.cached_conversations,
                    self.conversation_id,
                    new_statuses
                )
            except Exception:
                self.window_refresh_callback = None

    async def _async_create_conversation(self):
        """Async create a new conversation (without opening)."""
        try:
            conv = await self.database_handler.create_conversation(title="New Conversation...")
            if conv:
                self.conversation_id = conv['id']
                print(f"New conversation created: {conv['id'][:8]}...")
                # Refresh list in background (non-blocking)
                asyncio.create_task(self._async_refresh_and_notify())
        except Exception as e:
            print(f"Error creating conversation: {e}")

    async def _async_create_and_open_conversation(self):
        """Async create a new conversation and open it."""
        try:
            conv = await self.database_handler.create_conversation(title="New Conversation...")
            if conv:
                self.conversation_id = conv['id']
                print(f"New conversation created and opening: {conv['id'][:8]}...")
                # Ensure messages array exists
                conv['messages'] = conv.get('messages', [])
                # Open the chat window immediately (don't wait for refresh)
                await self._show_chat_window(conv['id'], conv_data=conv)
                # Refresh list in background (non-blocking)
                asyncio.create_task(self._async_refresh_and_notify())
        except Exception as e:
            print(f"Error creating conversation: {e}")

    async def refresh_conversations(self):
        """Asynchronously refresh the conversation list."""
        try:
            self.cached_conversations = await self.database_handler.list_conversations()
        except Exception as e:
            print(f"Error fetching conversations: {e}")
            traceback.print_exc()
            self.cached_conversations = []

    def view_all_conversations(self, icon=None, item=None):
        """Show window with all conversations."""
        # Show window immediately with cached data (non-blocking)
        # Then trigger async refresh in background

        def on_continue(conv_id):
            self.conversation_id = conv_id
            print(f"Continuing conversation: {conv_id[:8]}...")

        def on_open(conv_id):
            if self.loop:
                asyncio.run_coroutine_threadsafe(
                    self._show_chat_window(conv_id),
                    self.loop
                )

        def on_delete(conv_id):
            if self.loop:
                asyncio.run_coroutine_threadsafe(
                    self._delete_conversation(conv_id),
                    self.loop
                )

        def on_rename(conv_id, callback):
            if self.loop:
                asyncio.run_coroutine_threadsafe(
                    self._rename_conversation(conv_id, callback),
                    self.loop
                )

        def on_refresh():
            """Trigger async refresh - returns current cached data immediately."""
            # Trigger async refresh in background
            if self.loop:
                asyncio.run_coroutine_threadsafe(
                    self._async_refresh_and_notify(),
                    self.loop
                )
            # Return current cached data immediately
            return self.cached_conversations, self.conversation_id

        def on_refresh_services():
            """Trigger async service check - returns cached data immediately."""
            # Trigger async check in background
            if self.loop:
                asyncio.run_coroutine_threadsafe(
                    self._async_check_services_and_notify(),
                    self.loop
                )
            # Return current cached statuses immediately
            return self.cached_service_statuses

        def on_register_refresh(callback):
            self.window_refresh_callback = callback

        def on_new_conversation():
            """Handle creating a new conversation and opening it from the window."""
            # Run async to avoid blocking UI
            if self.loop:
                asyncio.run_coroutine_threadsafe(
                    self._async_create_and_open_conversation(),
                    self.loop
                )

        show_conversations_window(
            self.cached_conversations,
            self.conversation_id,
            config.PUSH_TO_TALK_KEY,
            config.NEW_CONVERSATION_KEY,
            config.OPEN_CONVERSATION_KEY,
            config.CREATE_AND_OPEN_KEY,
            config.OPEN_CONVERSATIONS_KEY,
            on_continue,
            on_open,
            on_delete,
            on_rename,
            on_refresh,
            on_register_refresh,
            on_new_conversation,
            self.cached_service_statuses,
            on_refresh_services
        )

        # Trigger background refresh after window is shown
        if self.loop:
            asyncio.run_coroutine_threadsafe(
                self._async_refresh_and_notify(),
                self.loop
            )
            asyncio.run_coroutine_threadsafe(
                self._async_check_services_and_notify(),
                self.loop
            )

    def open_settings(self, icon, item):
        """Open the settings window."""
        def on_mic_change(mic_index):
            self.selected_mic = mic_index
            self.voice_handler.set_device(mic_index)
            mic_name = "Default" if mic_index is None else f"Device {mic_index}"
            for mic in self.cached_microphones:
                if mic['index'] == mic_index:
                    mic_name = mic['name']
                    break
            print(f"Microphone changed to: {mic_name}")

        def on_settings_saved():
            """Handle settings save - reload config and re-register hotkeys."""
            hotkey_changes = config.reload_config()

            # Re-register hotkeys if they changed
            old_keys = hotkey_changes['old']
            new_keys = hotkey_changes['new']

            if old_keys != new_keys:
                print("Hotkeys changed, re-registering...")
                self._unregister_hotkeys()
                self._register_hotkeys()
                print(f"Hotkeys re-registered. Push-to-talk: [{config.PUSH_TO_TALK_KEY.upper()}]")
            else:
                print("Settings applied (no hotkey changes)")

            # Refresh conversations window with new service statuses (async, non-blocking)
            if self.window_refresh_callback and self.loop:
                asyncio.run_coroutine_threadsafe(
                    self._async_refresh_and_notify(),
                    self.loop
                )
                asyncio.run_coroutine_threadsafe(
                    self._async_check_services_and_notify(),
                    self.loop
                )

        self.cached_microphones = VoiceHandler.list_microphones()
        show_settings_window(self.selected_mic, on_mic_change, on_settings_saved)

    def open_system_prompt(self, icon, item):
        """Open the system prompt editor."""
        def on_system_prompt_saved():
            """Handle system prompt save - reload config."""
            config.reload_config()
            print("System prompt updated and applied")

        show_system_prompt_window(on_system_prompt_saved)

    def get_menu_items(self):
        """Build the tray menu items."""
        return (
            pystray.MenuItem("Settings", self.open_settings),
            pystray.MenuItem("System Prompt", self.open_system_prompt),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Conversations...", self.view_all_conversations),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", self.quit_app),
        )

    async def check_services(self) -> dict:
        """Check if all services are available.

        Returns:
            Dict with status of each service:
            - database: bool - Database service status
            - llm: bool - LLM service status
            - stt: bool - STT service status
            - tts: bool - TTS service status
        """
        db_status = await DatabaseHandler.check()
        llm_status = await LLMHandler.check()
        stt_status = await VoiceHandler.check_stt()
        tts_status = await VoiceHandler.check_tts()
        self.cached_service_statuses = {
            "database": db_status,
            "llm": llm_status,
            "stt": stt_status,
            "tts": tts_status,
        }
        return self.cached_service_statuses

    async def process_voice(self, audio_bytes):
        """Process voice input: transcribe, generate AI response, speak output."""
        self._processing = True
        self._cancel_requested = False
        self.update_icon("processing")

        try:
            # Check for cancellation
            if self._cancel_requested:
                return

            print("Transcribing audio...")
            text = await self.database_handler.transcribe(audio_bytes)

            if self._cancel_requested:
                return

            if text is None:
                print("STT service is disabled")
                return

            if not text:
                print("No speech detected")
                return

            print(f'You: "{text}"')

            # Show user message in chat window immediately
            if self.text_mode_active and self.conversation_id:
                add_chat_message(self.conversation_id, text, is_user=True)
                show_chat_loading(self.conversation_id)

            print(f"Getting/creating conversation (current ID: {self.conversation_id})")
            if self.conversation_id:
                conv = await self.database_handler.get_conversation(self.conversation_id)
                # Update title if this is the first message (placeholder conversation)
                if not conv.get("messages"):
                    new_title = text[:50]
                    await self.database_handler.update_conversation_title(self.conversation_id, new_title)
                    print(f"Updated conversation title to: {new_title}")
            else:
                conv = await self.database_handler.create_conversation(title=text[:50])
                self.conversation_id = conv["id"]

            if self._cancel_requested:
                return

            print("Building conversation history...")
            history = [
                {"role": m["role"], "content": m["content"]}
                for m in conv.get("messages", [])
            ]

            print("Generating AI response...")
            llm_handler = LLMHandler()
            response = await llm_handler.generate_response(history, text)

            if self._cancel_requested:
                return

            print(f"DeskBot: {response}")

            # Show AI response in chat window
            if self.text_mode_active and self.conversation_id:
                hide_chat_loading(self.conversation_id)
                add_chat_message(self.conversation_id, response, is_user=False)

            print("Saving messages to database...")
            self.conversation_id = await self.database_handler.save_messages(
                self.conversation_id,
                [
                    {"role": "human", "content": text},
                    {"role": "ai", "content": response}
                ]
            )

            if self._cancel_requested:
                return

            # Only play TTS if chat window is not focused
            if not is_chat_window_focused(self.conversation_id):
                print("Synthesizing speech...")
                audio = await self.database_handler.synthesize(response)
                if audio is None:
                    print("TTS service is disabled, skipping speech")
                elif not self._cancel_requested:
                    VoiceHandler.play_audio(audio)
            else:
                print("Chat window focused, skipping TTS playback")

            print("Done!")

        except asyncio.CancelledError:
            print("Voice processing cancelled")
            raise
        except Exception as e:
            print(f"Error in process_voice: {e}")
            traceback.print_exc()
        finally:
            # Always hide loading indicator when done
            if self.conversation_id:
                hide_chat_loading(self.conversation_id)
            self._processing = False

    def _start_recording(self):
        """Start recording when push-to-talk key is pressed."""
        # If currently processing, cancel the operation
        if self._processing:
            print("Cancelling current operation...")
            self._cancel_requested = True
            VoiceHandler.stop_audio()  # Stop any playing audio
            VoiceHandler.play_beep()  # Play cancellation feedback
            # Hide loading indicator immediately
            if self.conversation_id:
                hide_chat_loading(self.conversation_id)
            self.update_icon("ready")
            return

        # Skip if already recording
        if self._recording:
            return

        self._recording = True
        self.update_icon("recording")
        self.voice_handler.start()

    def _stop_and_process(self):
        """Stop recording and process audio when push-to-talk key is released."""
        # Skip if not recording
        if not self._recording:
            return

        self._recording = False
        audio_bytes = self.voice_handler.stop()

        # Minimum ~0.5 seconds at 16kHz, 16-bit mono (16000 bytes + 44 byte header)
        if len(audio_bytes) < 16000:
            print("Recording too short (need at least 0.5 seconds)")
            self.update_icon("ready")
            return

        # Schedule async processing on the event loop
        if self.loop:
            asyncio.run_coroutine_threadsafe(
                self._process_and_update(audio_bytes),
                self.loop
            )

    async def _process_and_update(self, audio_bytes):
        """Process voice and update icon when done."""
        await self.process_voice(audio_bytes)
        self.update_icon("ready")

    # === Hotkey handlers (called from keyboard callbacks) ===

    def _handle_new_conversation(self):
        """Handle new conversation hotkey."""
        if self.loop:
            asyncio.run_coroutine_threadsafe(
                self._async_create_conversation(),
                self.loop
            )

    def _handle_open_conversation(self):
        """Handle open conversation hotkey."""
        if self.conversation_id:
            if self.loop:
                asyncio.run_coroutine_threadsafe(
                    self._show_chat_window(self.conversation_id),
                    self.loop
                )
        else:
            print(f"No current conversation. Press [{config.NEW_CONVERSATION_KEY}] to create one first.")

    def _handle_create_and_open(self):
        """Handle create and open conversation hotkey."""
        if self.loop:
            asyncio.run_coroutine_threadsafe(
                self._async_create_and_open_conversation(),
                self.loop
            )

    def _register_hotkeys(self):
        """Register all hotkeys using event-driven callbacks."""
        keyboard.add_hotkey(config.OPEN_CONVERSATIONS_KEY, self.view_all_conversations)
        keyboard.add_hotkey(config.NEW_CONVERSATION_KEY, self._handle_new_conversation)
        keyboard.add_hotkey(config.OPEN_CONVERSATION_KEY, self._handle_open_conversation)
        keyboard.add_hotkey(config.CREATE_AND_OPEN_KEY, self._handle_create_and_open)

        # Push-to-talk: use add_hotkey for press, hook for release detection
        keyboard.add_hotkey(config.PUSH_TO_TALK_KEY, self._start_recording)

        # For release detection, we monitor the main key (last part of combination)
        main_key = config.PUSH_TO_TALK_KEY.split('+')[-1]
        keyboard.on_release_key(main_key, lambda _: self._stop_and_process(), suppress=False)

    def _unregister_hotkeys(self):
        """Unregister all hotkeys."""
        keyboard.unhook_all()

    async def hotkey_loop(self):
        """Main loop for handling hotkeys (event-driven)."""
        print("Checking services...")
        services = await self.check_services()
        if not services["database"]:
            print("Database service not available!")
            self.update_icon("offline")
            while self.running:
                await asyncio.sleep(5)
                services = await self.check_services()
                if services["database"]:
                    break
            if not self.running:
                return

        await self.refresh_conversations()

        # Show conversations window on startup
        self.view_all_conversations()

        # Register event-driven hotkeys
        self._register_hotkeys()

        # Show STT/TTS service status
        stt_status = "enabled" if config.is_stt_enabled() else "disabled"
        tts_status = "enabled" if config.is_tts_enabled() else "disabled"
        print(f"Voice services: STT={stt_status}, TTS={tts_status}")
        print(f"Ready! Hold [{config.PUSH_TO_TALK_KEY.upper()}] to talk, [{config.NEW_CONVERSATION_KEY.upper()}] new conversation, [{config.OPEN_CONVERSATION_KEY.upper()}] open current, [{config.CREATE_AND_OPEN_KEY.upper()}] new & open, [{config.OPEN_CONVERSATIONS_KEY.upper()}] all conversations.")
        self.update_icon("ready")

        # Wait until quit is requested (no polling needed)
        self._quit_event = asyncio.Event()
        await self._quit_event.wait()

        # Cleanup hotkeys on exit
        self._unregister_hotkeys()

    def run_async_loop(self):
        """Run the async event loop in a separate thread."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self.hotkey_loop())
        finally:
            self.loop.close()

    def run(self):
        """Start the tray application."""
        self.icon = pystray.Icon(
            "DeskBot",
            create_icon(COLOR_OFFLINE),
            "DeskBot - Starting...",
            menu=pystray.Menu(lambda: self.get_menu_items()),
        )

        hotkey_thread = threading.Thread(target=self.run_async_loop, daemon=True)
        hotkey_thread.start()

        self.icon.run()
