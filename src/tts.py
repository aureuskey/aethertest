"""
Nova's Voice Module
ElevenLabs integration for high-fidelity Text-to-Speech.
"""

import os
import asyncio
import threading
import queue
from typing import Optional, Callable
from elevenlabs import ElevenLabs, VoiceSettings
from elevenlabs.types import Voice
import pyaudio


class ElevenLabsVoice:
    """
    Handles text-to-speech synthesis and audio playback via ElevenLabs.
    """

    def __init__(self, on_speaking_start: Optional[Callable] = None, on_speaking_end: Optional[Callable] = None):
        """
        Initialize the ElevenLabs voice.

        Args:
            on_speaking_start: Callback when speech starts
            on_speaking_end: Callback when speech ends
        """
        self.api_key = os.environ.get("ELEVENLABS_API_KEY")
        if not self.api_key:
            raise ValueError("ELEVENLABS_API_KEY environment variable not set. Ensure Doppler has injected it.")

        self.on_speaking_start = on_speaking_start
        self.on_speaking_end = on_speaking_end

        # Initialize ElevenLabs client
        self.client = ElevenLabs(api_key=self.api_key)

        # Voice configuration - using 'Adam' as a base, can be customized
        self.voice_id = os.environ.get("ELEVENLABS_VOICE_ID", "pNInz6obpgDQGcFmaJgB")  # Default: Adam
        self.voice_settings = VoiceSettings(
            stability=0.5,
            similarity_boost=0.75,
            style=0.0,
            use_speaker_boost=True
        )

        # Audio playback setup
        self.audio_queue: queue.Queue[Optional[bytes]] = queue.Queue()
        self.is_speaking = False
        self._stop_event = threading.Event()
        self._audio_thread: Optional[threading.Thread] = None

        # PyAudio setup (16kHz, mono, 16-bit PCM - matches Deepgram input)
        self.audio_format = pyaudio.paInt16
        self.channels = 1
        self.rate = 24000  # ElevenLabs default output rate
        self.chunk_size = 1024

        self._init_audio()

    def _init_audio(self):
        """Initialize PyAudio."""
        try:
            self.pyaudio = pyaudio.PyAudio()
            self.stream: Optional[pyaudio.Stream] = None
        except Exception as e:
            print(f"[TTS Error] Failed to initialize PyAudio: {e}")
            raise

    def _get_voice_id(self) -> str:
        """Get the appropriate voice ID for Nova's British persona."""
        # Try to find a British voice, fallback to default
        try:
            voices = self.client.voices.get_all()
            for voice in voices.voices:
                # Look for British/UK voices
                if any(term in voice.name.lower() for term in ['british', 'uk', 'english']):
                    print(f"[TTS] Selected British voice: {voice.name}")
                    return voice.voice_id
        except Exception as e:
            print(f"[TTS] Could not fetch voices: {e}")

        # Fallback to default
        return self.voice_id

    async def speak(self, text: str):
        """
        Convert text to speech and play it.

        Args:
            text: The text to synthesize and speak
        """
        if not text or not text.strip():
            return

        print(f"[TTS] Speaking: {text[:100]}...")

        # Trigger speaking start callback
        if self.on_speaking_start:
            self.on_speaking_start()

        self.is_speaking = True

        try:
            # Generate audio stream from ElevenLabs
            audio_stream = self.client.text_to_speech.convert_as_stream(
                text=text,
                voice_id=self.voice_id,
                voice_settings=self.voice_settings,
                model_id="eleven_turbo_v2_5",  # Fastest model for low latency
                output_format="pcm_24000",  # 24kHz PCM
            )

            # Play audio in a separate thread to avoid blocking
            await asyncio.get_event_loop().run_in_executor(
                None, self._play_audio_stream, audio_stream
            )

        except Exception as e:
            print(f"[TTS Error] Failed to synthesize speech: {e}")
        finally:
            self.is_speaking = False
            if self.on_speaking_end:
                self.on_speaking_end()

    def _play_audio_stream(self, audio_stream):
        """Play audio stream from ElevenLabs."""
        try:
            # Open PyAudio stream
            self.stream = self.pyaudio.open(
                format=self.audio_format,
                channels=self.channels,
                rate=self.rate,
                output=True,
                frames_per_buffer=self.chunk_size
            )

            # Stream audio chunks
            for chunk in audio_stream:
                if chunk:
                    self.stream.write(chunk)

            # Close stream
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None

        except Exception as e:
            print(f"[TTS Error] Failed to play audio: {e}")

    async def stop(self):
        """Stop current speech playback."""
        if self.is_speaking and self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
                self.stream = None
            except Exception as e:
                print(f"[TTS Error] Failed to stop audio: {e}")
        self.is_speaking = False

    def cleanup(self):
        """Clean up audio resources."""
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except:
                pass
        if self.pyaudio:
            self.pyaudio.terminate()
        print("[TTS] Audio resources cleaned up")
