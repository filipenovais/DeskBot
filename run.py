"""DeskBot - Main Entry Point

Usage:
    python run.py              # Start tray application (default)
    python run.py --cli        # Start CLI mode (chat)

CLI Commands (in chat mode):
    /list       - List all conversations
    /open <id>  - Open a conversation by ID (partial ID works)
    /new        - Start a new conversation
    /quit       - Exit CLI mode

Icon colors (tray mode):
  - Green  = Ready (waiting for hotkey)
  - Red    = Recording (hotkey held)
  - Yellow = Processing (transcribing/thinking/speaking)
  - Gray   = Offline (services not available)
"""

import argparse
import asyncio

from src.ui import DeskBot
from src.cli import DeskBotCLI


def run_tray():
    """Start the tray application."""
    print("Starting DeskBot...")
    print("Look for the icon in your system tray!")
    app = DeskBot()
    app.run()
    print("Goodbye!")


def run_cli():
    """Start the CLI application."""
    cli = DeskBotCLI()
    asyncio.run(cli.run_loop(None))


def main():
    parser = argparse.ArgumentParser(description="DeskBot")
    parser.add_argument("--cli", action="store_true", help="Run in CLI mode instead of tray mode")

    args = parser.parse_args()

    if args.cli:
        run_cli()
    else:
        run_tray()


if __name__ == "__main__":
    main()
