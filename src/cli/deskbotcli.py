"""DeskBot CLI - Command Line Interface for DeskBot."""

import asyncio
import sys
import threading
from datetime import datetime

from src.database import DatabaseHandler
from src.llm import LLMHandler
from src.voice import VoiceHandler
from src import config
from src.config import PUSH_TO_TALK_KEY
from src.ui import theme


# ANSI color codes matching the Crimson Dusk theme
class Colors:
    """ANSI colors matching the UI theme."""
    # Text colors
    CRIMSON = '\033[38;2;220;53;69m'      # Accent/highlight
    BURGUNDY = '\033[38;2;139;41;66m'     # Secondary accent
    GOLD = '\033[38;2;240;192;64m'        # Tertiary/active
    PLUM = '\033[38;2;155;77;150m'        # Subtle accent
    BRIGHT = '\033[38;2;248;240;240m'     # Primary text
    DIM = '\033[38;2;160;136;152m'        # Muted text
    GREEN = '\033[38;2;80;200;120m'       # Success/ready

    # Styles
    BOLD = '\033[1m'
    DIM_STYLE = '\033[2m'
    RESET = '\033[0m'

    # Background colors
    BG_DEEP = '\033[48;2;26;18;24m'
    BG_MID = '\033[48;2;42;31;40m'

    @staticmethod
    def crimson(text):
        return f"{Colors.CRIMSON}{text}{Colors.RESET}"

    @staticmethod
    def gold(text):
        return f"{Colors.GOLD}{text}{Colors.RESET}"

    @staticmethod
    def bright(text):
        return f"{Colors.BRIGHT}{text}{Colors.RESET}"

    @staticmethod
    def dim(text):
        return f"{Colors.DIM}{text}{Colors.RESET}"

    @staticmethod
    def green(text):
        return f"{Colors.GREEN}{text}{Colors.RESET}"

    @staticmethod
    def bold(text):
        return f"{Colors.BOLD}{text}{Colors.RESET}"

    @staticmethod
    def burgundy(text):
        return f"{Colors.BURGUNDY}{text}{Colors.RESET}"

    @staticmethod
    def plum(text):
        return f"{Colors.PLUM}{text}{Colors.RESET}"


class DeskBotCLI:
    """Command-line interface for DeskBot voice assistant."""

    def __init__(self):
        self.database_handler = DatabaseHandler()
        self.voice_handler = VoiceHandler()
        self.conversation_id = None

    def print_header(self, text: str):
        """Print a styled header."""
        print(f"\n{Colors.CRIMSON}{'═' * 70}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.GOLD}{text:^70}{Colors.RESET}")
        print(f"{Colors.CRIMSON}{'═' * 70}{Colors.RESET}\n")

    def print_separator(self):
        """Print a separator line."""
        print(f"{Colors.DIM}{'─' * 70}{Colors.RESET}")

    def print_dots(self):
        """Print a dot separator line."""
        print(f"{Colors.DIM}{'·' * 70}{Colors.RESET}")

    async def process_voice(self, audio_bytes: bytes) -> str:
        """Process voice input: transcribe, generate AI response, speak output.

        Args:
            audio_bytes: Audio data in WAV format

        Returns:
            The conversation ID (new or existing)
        """
        # 1. Transcribe audio to text
        print(f"{Colors.plum('🎤 Transcribing...')}", end='\r')
        text = await self.database_handler.transcribe(audio_bytes)
        print(' ' * 20, end='\r')  # Clear the "Transcribing..." message

        if text is None:
            print(f"{Colors.dim('STT service is disabled.')}")
            self.print_dots()
            return self.conversation_id
        if not text:
            print(f"{Colors.dim('No speech detected.')}")
            self.print_dots()
            return self.conversation_id

        print(f'{Colors.bright("You:")} {text.lstrip()}')
        self.print_dots()

        # 2. Get or create conversation
        if self.conversation_id:
            conv = await self.database_handler.get_conversation(self.conversation_id)
        else:
            conv = await self.database_handler.create_conversation(title=text[:50])
            self.conversation_id = conv["id"]

        # 3. Build conversation history from messages
        history = [
            {"role": m["role"], "content": m["content"]}
            for m in conv.get("messages", [])
        ]

        # 4. Generate AI response using LLM
        print(f"{Colors.plum('🤔 Thinking...')}", end='\r')
        llm_handler = LLMHandler()
        response = await llm_handler.generate_response(history, text)
        print(' ' * 20, end='\r')  # Clear the "Thinking..." message
        print(f"{Colors.crimson('DeskBot:')} {response}")
        self.print_dots()

        # 5. Save messages to database
        self.conversation_id = await self.database_handler.save_messages(
            self.conversation_id,
            [
                {"role": "human", "content": text},
                {"role": "ai", "content": response}
            ]
        )

        # 6. Synthesize and play response (if TTS is enabled)
        audio = await self.database_handler.synthesize(response)
        if audio is not None:
            print(f"{Colors.gold('🔊 Speaking...')}", end='\r')
            VoiceHandler.play_audio(audio)
            print(' ' * 20, end='\r')  # Clear the "Speaking..." message

        return self.conversation_id

    async def process_text(self, text: str) -> str:
        """Process text input: generate AI response, speak output."""
        # Clear the input line (move up and clear)
        print('\033[A\033[K', end='')
        print(f'{Colors.bright("You:")} {text}')
        self.print_dots()

        # Get or create conversation
        if self.conversation_id:
            conv = await self.database_handler.get_conversation(self.conversation_id)
        else:
            conv = await self.database_handler.create_conversation(title=text[:50])
            self.conversation_id = conv["id"]

        # Build conversation history
        history = [
            {"role": m["role"], "content": m["content"]}
            for m in conv.get("messages", [])
        ]

        # Generate AI response
        print(f"{Colors.plum('🤔 Thinking...')}", end='\r')
        llm_handler = LLMHandler()
        response = await llm_handler.generate_response(history, text)
        print(' ' * 20, end='\r')  # Clear the "Thinking..." message
        print(f"{Colors.crimson('DeskBot:')} {response}")
        self.print_dots()

        # Save messages
        self.conversation_id = await self.database_handler.save_messages(
            self.conversation_id,
            [
                {"role": "human", "content": text},
                {"role": "ai", "content": response}
            ]
        )

        return self.conversation_id

    async def run_loop(self, conversation_id: str = None):
        """Main loop for CLI mode."""
        import keyboard

        # Show beautiful header
        self.print_header("DeskBot CLI")

        print(f"{Colors.plum('⚙  Checking services...')}")
        db_ready = await self.database_handler.check()
        if not db_ready:
            print(f"\n{Colors.CRIMSON}✗ ERROR:{Colors.RESET} Database service not running.")
            print(f"{Colors.dim('Start with: docker-compose up')}\n")
            return

        # Show STT/TTS service status
        stt_status = Colors.green("✓ enabled") if config.is_stt_enabled() else Colors.dim("✗ disabled")
        tts_status = Colors.green("✓ enabled") if config.is_tts_enabled() else Colors.dim("✗ disabled")
        print(f"{Colors.green('✓ Services ready!')}")
        print(f"  {Colors.dim('STT:')} {stt_status}")
        print(f"  {Colors.dim('TTS:')} {tts_status}\n")

        # Handle partial conversation ID matching
        if conversation_id:
            conversations = await self.database_handler.list_conversations()
            matched_conv = None

            for c in conversations:
                if c['id'].startswith(conversation_id) or c['id'] == conversation_id:
                    matched_conv = c
                    break

            if matched_conv:
                self.conversation_id = matched_conv['id']
                conv = await self.database_handler.get_conversation(self.conversation_id)
                msg_count = len(conv.get("messages", []))
                print(f"{Colors.gold('📖 Opened conversation:')}")
                print(f"  {Colors.dim('ID:')} {Colors.bright(self.conversation_id[:12])}...")
                print(f"  {Colors.dim('Title:')} {Colors.bright(conv.get('title', 'Untitled')[:50])}")
                print(f"  {Colors.dim('Messages:')} {Colors.bright(str(msg_count))}")

                # Display recent messages
                messages = conv.get("messages", [])
                if messages:
                    print(f"\n{Colors.burgundy('Recent messages:')}")
                    recent = messages[-4:] if len(messages) > 4 else messages
                    for msg in recent:
                        role = msg.get("role", "unknown")
                        content = msg.get("content", "")[:60] + "..." if len(msg.get("content", "")) > 60 else msg.get("content", "")

                        if role == "human":
                            print(f"  {Colors.dim('You:')} {Colors.dim(content)}")
                        elif role == "ai":
                            print(f"  {Colors.crimson('AI:')} {Colors.dim(content)}")
            else:
                print(f"{Colors.CRIMSON}✗ Conversation not found:{Colors.RESET} {Colors.dim(conversation_id)}")
                print(f"{Colors.dim('Starting new conversation instead...')}")
                self.conversation_id = None
        else:
            self.conversation_id = None

        if not self.conversation_id:
            print(f"{Colors.gold('✨ Chat Mode')}")
            print(f"{Colors.dim('Type or speak to start a new conversation')}")

        print(f"\n{Colors.burgundy('Commands:')}")
        print(f"  {Colors.bright('/list')}        - List all conversations")
        print(f"  {Colors.bright('/new')}         - Start a new conversation")
        print(f"  {Colors.bright('/open <id>')}   - Open a conversation by ID")
        print(f"  {Colors.bright('/delete <id>')} - Delete a conversation by ID")
        print(f"  {Colors.bright('/quit')}        - Exit CLI")

        print(f"\n{Colors.burgundy('Chat:')}")
        print(f"  Type message + {Colors.gold('Enter')}, or hold {Colors.gold('[' + PUSH_TO_TALK_KEY.upper() + ']')} to talk")
        print(f"  {Colors.dim('Press Ctrl+C to quit')}\n")

        self.print_separator()

        # Background thread for text input
        pending_input = []
        input_lock = threading.Lock()

        def input_thread():
            while True:
                try:
                    line = sys.stdin.readline()
                    if line:
                        with input_lock:
                            pending_input.append(line.strip())
                except:
                    break

        threading.Thread(target=input_thread, daemon=True).start()

        try:
            while True:
                # Check for voice input (PTT key)
                if keyboard.is_pressed(PUSH_TO_TALK_KEY):
                    self.voice_handler.start()
                    while keyboard.is_pressed(PUSH_TO_TALK_KEY):
                        await asyncio.sleep(0.05)

                    audio_bytes = self.voice_handler.stop()
                    if len(audio_bytes) < 1000:
                        print(f"{Colors.dim('Recording too short.')}")
                        self.print_dots()
                    else:
                        await self.process_voice(audio_bytes)
                    continue

                # Check for text input
                with input_lock:
                    if pending_input:
                        text = pending_input.pop(0).strip()
                        if text:
                            # Handle commands (starting with /)
                            if text.lower() == "/list":
                                await self.list_conversations()
                            elif text.lower().startswith("/open "):
                                conv_id = text[6:].strip()
                                await self.open_conversation(conv_id)
                            elif text.lower().startswith("/delete "):
                                conv_id = text[8:].strip()
                                await self.delete_conversation(conv_id)
                            elif text.lower() == "/new":
                                # Start a new conversation
                                if self.conversation_id:
                                    print(f"{Colors.gold('✨ Starting new conversation')}")
                                    print(f"{Colors.dim('Previous conversation saved:')} {Colors.bright(self.conversation_id[:12])}...")
                                    self.print_dots()
                                else:
                                    print(f"{Colors.gold('✨ New conversation')}")
                                    self.print_dots()
                                self.conversation_id = None
                            elif text.lower() in ["/quit", "/exit", "/q"]:
                                print(f"\n{Colors.gold('👋 Goodbye!')}")
                                if self.conversation_id:
                                    print(f"{Colors.dim('Conversation saved:')} {Colors.bright(self.conversation_id[:12])}...\n")
                                return
                            else:
                                # Regular chat message
                                await self.process_text(text)

                await asyncio.sleep(0.05)

        except KeyboardInterrupt:
            print(f"\n\n{Colors.gold('👋 Goodbye!')}")
            if self.conversation_id:
                print(f"{Colors.dim('Conversation saved:')} {Colors.bright(self.conversation_id[:12])}...\n")

    async def list_conversations(self):
        """List all conversations with beautiful formatting."""
        conversations = await self.database_handler.list_conversations()
        if not conversations:
            print(f"\n{Colors.dim('📭 No conversations yet.')}")
            print(f"{Colors.dim('Start chatting to create your first conversation!')}\n")
            return

        print(f"\n{Colors.BOLD}{Colors.CRIMSON}📚 Conversations{Colors.RESET}\n")

        # Header
        print(f"{Colors.burgundy('─' * 70)}")
        print(f"{Colors.DIM}{'ID':<10} {'Title':<40} {'Messages':>8}{Colors.RESET}")
        print(f"{Colors.burgundy('─' * 70)}")

        # List conversations
        for i, c in enumerate(conversations):
            conv_id_short = c['id'][:8]
            title = c['title'][:38] + "..." if len(c['title']) > 38 else c['title']
            msg_count = c['message_count']

            # Alternate row colors for readability
            if i % 2 == 0:
                id_color = Colors.gold
                title_color = Colors.bright
            else:
                id_color = Colors.plum
                title_color = Colors.dim

            print(f"{id_color(conv_id_short):<18} {title_color(title):<48} {Colors.green(str(msg_count)):>8}")

        print(f"{Colors.burgundy('─' * 70)}")
        print(f"{Colors.dim(f'Total: {len(conversations)} conversation(s)')}\n")
        print(f"{Colors.dim('💡 Use')} {Colors.bright('/open <id>')} {Colors.dim('to continue a conversation')}")

    async def open_conversation(self, conversation_id: str):
        """Open and display a conversation."""
        # Try to find conversation by partial ID
        conversations = await self.database_handler.list_conversations()
        matched_conv = None

        for c in conversations:
            if c['id'].startswith(conversation_id):
                matched_conv = c
                break

        if not matched_conv:
            print(f"\n{Colors.CRIMSON}✗ Conversation not found:{Colors.RESET} {Colors.dim(conversation_id)}")
            print(f"{Colors.dim('Use')} {Colors.bright('/list')} {Colors.dim('to see all conversations')}\n")
            return

        # Load full conversation
        conv = await self.database_handler.get_conversation(matched_conv['id'])
        self.conversation_id = matched_conv['id']

        print(f"\n{Colors.BOLD}{Colors.CRIMSON}📖 Opening Conversation{Colors.RESET}\n")
        print(f"{Colors.dim('ID:')} {Colors.bright(matched_conv['id'][:12])}...")
        print(f"{Colors.dim('Title:')} {Colors.bright(conv.get('title', 'Untitled'))}")
        print(f"{Colors.dim('Messages:')} {Colors.green(str(len(conv.get('messages', []))))}\n")

        # Display conversation history
        messages = conv.get("messages", [])
        if messages:
            print(f"{Colors.burgundy('─' * 70)}")
            for msg in messages:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")

                if role == "human":
                    print(f"{Colors.bright('You:')} {content}")
                elif role == "ai":
                    print(f"{Colors.crimson('DeskBot:')} {content}")

                self.print_dots()

    async def delete_conversation(self, conversation_id: str):
        """Delete a conversation by ID (supports partial ID matching)."""
        # Try to find conversation by partial ID
        conversations = await self.database_handler.list_conversations()
        matched_conv = None

        for c in conversations:
            if c['id'].startswith(conversation_id):
                matched_conv = c
                break

        if not matched_conv:
            print(f"\n{Colors.CRIMSON}✗ Conversation not found:{Colors.RESET} {Colors.dim(conversation_id)}")
            print(f"{Colors.dim('Use')} {Colors.bright('/list')} {Colors.dim('to see all conversations')}\n")
            return

        # Delete the matched conversation
        if await self.database_handler.delete_conversation(matched_conv['id']):
            print(f"\n{Colors.green('✓ Deleted:')} {Colors.bright(matched_conv['title'][:50])}")
            print(f"{Colors.dim('ID:')} {Colors.dim(matched_conv['id'][:12])}...\n")

            # If we deleted the current conversation, reset it
            if self.conversation_id == matched_conv['id']:
                self.conversation_id = None
                print(f"{Colors.gold('✨ Starting new conversation')}\n")
        else:
            print(f"\n{Colors.CRIMSON}✗ Failed to delete:{Colors.RESET} {Colors.dim(matched_conv['id'])}\n")
