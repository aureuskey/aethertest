"""
Nova - Sovereign AI Assistant
Main entry point managing the audio loop.
"""

from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file

import os
import sys
import asyncio
import threading
import pyaudio
from typing import Optional

from stt import DeepgramListener
from tts import ElevenLabsVoice
from brain import get_brain


class Nova:
    """
    Nova's main orchestration class.
    Manages the audio input/output loop with async design.
    """

    def __init__(self):
        self.is_running = False
        self.is_processing = False
        self.is_speaking = False

        # Audio configuration (16kHz, 16-bit PCM, mono - Deepgram optimal)
        self.sample_rate = 16000
        self.channels = 1
        self.format = pyaudio.paInt16
        self.chunk_duration_ms = 20  # 20ms chunks for low latency
        self.chunk_size = int(self.sample_rate * self.chunk_duration_ms / 1000)

        # PyAudio instance
        self.pyaudio: Optional[pyaudio.PyAudio] = None
        self.input_stream: Optional[pyaudio.Stream] = None

        # Components
        self.brain = get_brain()
        self.stt: Optional[DeepgramListener] = None
        self.tts: Optional[ElevenLabsVoice] = None

        # Async event loop
        self.loop: Optional[asyncio.AbstractEventLoop] = None

    def _on_transcript(self, transcript: str):
        """Handle incoming transcript from STT."""
        if not transcript or not transcript.strip():
            return

        if self.is_processing or self.is_speaking:
            print("[Nova] Still processing previous request, ignoring new input...")
            return

        print(f"[Nova] Heard: {transcript}")

        # Process in async loop
        if self.loop:
            asyncio.run_coroutine_threadsafe(
                self._process_request(transcript),
                self.loop
            )

    def _on_speaking_start(self):
        """Callback when TTS starts speaking."""
        self.is_speaking = True
        print("[Nova] Speaking...")

        # Stop listening while speaking to prevent feedback
        if self.stt and self.stt.is_listening:
            asyncio.run_coroutine_threadsafe(
                self._pause_listening(),
                self.loop
            )

    def _on_speaking_end(self):
        """Callback when TTS finishes speaking."""
        self.is_speaking = False
        print("[Nova] Finished speaking. Listening...")

        # Resume listening
        if self.stt:
            asyncio.run_coroutine_threadsafe(
                self._resume_listening(),
                self.loop
            )

    async def _pause_listening(self):
        """Pause audio input to prevent feedback."""
        # We keep the STT connection but don't send audio
        pass  # Actual implementation would mute input

    async def _resume_listening(self):
        """Resume audio input after speaking."""
        pass  # Actual implementation would unmute input

    async def _process_request(self, transcript: str):
        """
        Process user request through brain and speak response.

        Args:
            transcript: The text from user speech
        """
        self.is_processing = True

        try:
            # Get response from brain
            response = await self.brain.process(transcript)

            # Speak the response
            if response and self.tts:
                await self.tts.speak(response)

        except Exception as e:
            print(f"[Nova Error] Request processing failed: {e}")
        finally:
            self.is_processing = False

    async def _audio_input_loop(self):
        """
        Continuously read audio from microphone and send to STT.
        Runs in a separate thread.
        """
        print("[Nova] Audio input loop started")

        while self.is_running:
            try:
                if self.input_stream and self.stt and self.stt.is_listening:
                    # Read audio chunk
                    data = self.input_stream.read(self.chunk_size, exception_on_overflow=False)

                    # Send to Deepgram (only if not speaking to prevent feedback)
                    if not self.is_speaking:
                        await self.stt.send_audio(data)

                await asyncio.sleep(0.001)  # 1ms yield

            except Exception as e:
                print(f"[Nova Audio Error] {e}")
                await asyncio.sleep(0.1)

    def _run_audio_thread(self):
        """Run audio loop in a thread with its own event loop."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._audio_input_loop())

    async def initialize(self):
        """Initialize all components."""
        print("=" * 50)
        print("  NOVA - Sovereign AI Assistant")
        print("  Initializing...")
        print("=" * 50)

        # Initialize PyAudio
        self.pyaudio = pyaudio.PyAudio()

        # Open microphone stream
        self.input_stream = self.pyaudio.open(
            format=self.format,
            channels=self.channels,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=self.chunk_size
        )
        print("[Nova] Microphone initialized")

        # Initialize TTS
        self.tts = ElevenLabsVoice(
            on_speaking_start=self._on_speaking_start,
            on_speaking_end=self._on_speaking_end
        )
        print("[Nova] TTS initialized")

        # Initialize STT with transcript callback
        self.stt = DeepgramListener(transcript_callback=self._on_transcript)
        await self.stt.connect()
        print("[Nova] STT initialized")

        # Store event loop reference
        self.loop = asyncio.get_event_loop()

        print("=" * 50)
        print("  Nova is ready. Speak to interact.")
        print("  Say 'exit' or press Ctrl+C to quit.")
        print("=" * 50)

    async def run(self):
        """Main run loop."""
        await self.initialize()

        self.is_running = True

        # Start audio input in a background thread
        audio_thread = threading.Thread(target=self._run_audio_thread, daemon=True)
        audio_thread.start()

        # Main loop - handle keyboard input and keep alive
        try:
            while self.is_running:
                # Check for exit command via keyboard (optional)
                await asyncio.sleep(0.1)

        except KeyboardInterrupt:
            print("\n[Nova] Shutdown requested...")
        finally:
            await self.shutdown()

    async def shutdown(self):
        """Graceful shutdown."""
        print("[Nova] Shutting down...")
        self.is_running = False

        # Cleanup components
        if self.stt:
            await self.stt.disconnect()

        if self.tts:
            await self.tts.stop()
            self.tts.cleanup()

        if self.input_stream:
            self.input_stream.stop_stream()
            self.input_stream.close()

        if self.pyaudio:
            self.pyaudio.terminate()

        print("[Nova] Goodbye.")


async def main():
    """Entry point."""
    nova = Nova()
    await nova.run()


if __name__ == "__main__":
    # Ensure we're running with Doppler
    if not os.environ.get("DOPPLER_ENVIRONMENT"):
        print("=" * 50)
        print("  WARNING: Doppler environment not detected!")
        print("  Run with: doppler run -- python src/main.py")
        print("=" * 50)
        print()

    # Check required environment variables
    required_vars = ["GROQ_API_KEY", "DEEPGRAM_API_KEY", "ELEVENLABS_API_KEY"]
    missing = [var for var in required_vars if not os.environ.get(var)]
    if missing:
        print(f"[Error] Missing required environment variables: {', '.join(missing)}")
        print("Ensure these are set in Doppler before running.")
        sys.exit(1)

    try:
        asyncio.run(main())
    except Exception as e:
        print(f"[Fatal Error] {e}")
        sys.exit(1)
