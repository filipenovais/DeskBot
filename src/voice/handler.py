"""Voice handler - microphone recording, audio playback, STT, and TTS."""

import io
import wave
import logging
import threading
import numpy as np
import sounddevice as sd
import pygame
import httpx

from src.config import CHANNELS, SAMPLE_RATE
from .client_stt import speech_to_text as stt, check_stt
from .client_tts import text_to_speech as tts, check_tts

logger = logging.getLogger(__name__)

TIMEOUT = httpx.Timeout(120.0, connect=10.0)



class VoiceHandler:
    """Handler for recording audio from microphone, playback, STT, and TTS."""

    def __init__(self, device: int = None):
        self._frames = []
        self._stream = None
        self._recording = False
        self._lock = threading.Lock()
        self._device = device

    def set_device(self, device: int = None):
        self._device = device

    def start(self):
        with self._lock:
            if self._recording:
                return
            self._frames = []
            self._recording = True
            self._stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype="int16",
                callback=self._on_audio,
                blocksize=1024,
                device=self._device,
            )
            self._stream.start()

    def stop(self) -> bytes:
        with self._lock:
            if not self._recording:
                return b""
            self._recording = False
            if self._stream:
                self._stream.stop()
                self._stream.close()
                self._stream = None

        if not self._frames:
            return b""

        audio = np.concatenate(self._frames, axis=0)
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(audio.tobytes())
        return buffer.getvalue()

    def _on_audio(self, indata, frames, time, status):
        if self._recording:
            self._frames.append(indata.copy())

    # === Static methods for audio playback ===

    @staticmethod
    def play_audio(audio_bytes: bytes):
        """Play WAV audio through speakers."""
        if not pygame.mixer.get_init():
            pygame.mixer.init()

        buffer = io.BytesIO(audio_bytes)
        pygame.mixer.music.load(buffer, "wav")
        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy():
            pygame.time.wait(100)

    @staticmethod
    def stop_audio():
        """Stop any currently playing audio."""
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()

    @staticmethod
    def play_beep(frequency: int = 400, duration_ms: int = 150):
        """Play a short beep sound for cancellation feedback.

        Args:
            frequency: Frequency in Hz (default 400)
            duration_ms: Duration in milliseconds (default 150)
        """
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=SAMPLE_RATE)

        # Generate a simple sine wave beep
        duration_samples = int(SAMPLE_RATE * duration_ms / 1000)
        t = np.linspace(0, duration_ms / 1000, duration_samples, dtype=np.float32)
        wave_data = (np.sin(2 * np.pi * frequency * t) * 0.3 * 32767).astype(np.int16)

        # Create stereo sound (pygame requires it for some backends)
        stereo = np.column_stack([wave_data, wave_data])

        # Play through pygame
        sound = pygame.sndarray.make_sound(stereo)
        sound.play()
        pygame.time.wait(duration_ms + 50)

    # === Static method for microphone listing ===
    @staticmethod
    def list_microphones() -> list[dict]:
        """Return list of available input devices."""
        devices = sd.query_devices()
        microphones = []
        for i, device in enumerate(devices):
            if device['max_input_channels'] > 0:
                microphones.append({
                    'index': i,
                    'name': device['name']
                })
        return microphones

    # === Static method for speech-to-text ===
    @staticmethod
    def speech_to_text(audio_data: bytes = None, audio_path: str = None) -> str:
        """
        Convert speech to text using OpenAI-compatible API.

        Args:
            audio_data: Audio bytes (WAV format)
            audio_path: Path to audio file (alternative to audio_data)

        Returns:
            Transcribed text

        Raises:
            STTError: If transcription fails
            STTDisabledError: If STT service is disabled (empty config)
            ValueError: If neither audio_data nor audio_path provided
        """
        return stt(audio_data, audio_path)
    
    # === Static method for text-to-speech ===
    @staticmethod
    def text_to_speech(text: str, output_path: str = None, voice: str = None, model: str = None) -> bytes:
        """
        Convert text to speech using OpenAI-compatible API.

        Args:
            text: The text to convert to speech
            output_path: Optional path to save the audio file
            voice: Voice to use (default: from config TTS_VOICE)
            model: Model to use (default: from config TTS_MODEL)

        Returns:
            Audio bytes in WAV format

        Raises:
            TTSError: If synthesis fails
            TTSDisabledError: If TTS service is disabled (empty config)
            ValueError: If text is empty
        """
        return tts(text, output_path, voice, model)

    # === Static methods for service checks ===
    @staticmethod
    async def check_stt() -> bool:
        """Check if STT service is configured and reachable.

        Returns:
            True if STT is available, False otherwise
        """
        return await check_stt()

    @staticmethod
    async def check_tts() -> bool:
        """Check if TTS service is configured and reachable.

        Returns:
            True if TTS is available, False otherwise
        """
        return await check_tts()