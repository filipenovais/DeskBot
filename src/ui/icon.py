"""Icon creation and color constants for the system tray."""

from PIL import Image, ImageDraw

from .theme import STATUS_READY, STATUS_RECORDING, STATUS_PROCESSING, STATUS_OFFLINE

COLOR_READY = STATUS_READY
COLOR_RECORDING = STATUS_RECORDING
COLOR_PROCESSING = STATUS_PROCESSING
COLOR_OFFLINE = STATUS_OFFLINE


def create_icon(color: str) -> Image.Image:
    """Create a circular tray icon with the given color."""
    size = 64
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    margin = 4
    draw.ellipse([margin, margin, size - margin, size - margin], fill=color)
    return img


def get_color_for_state(state: str) -> str:
    """Get the icon color for a given state."""
    colors = {
        "ready": COLOR_READY,
        "recording": COLOR_RECORDING,
        "processing": COLOR_PROCESSING,
        "offline": COLOR_OFFLINE,
    }
    return colors.get(state, COLOR_OFFLINE)
