"""
Nova's Ears Module
Deepgram WebSocket integration for real-time streaming Speech-to-Text.
"""

import os
import asyncio
import json
from typing import Callable, Optional
from deepgram import (
    DeepgramClient,
    DeepgramClientOptions,
    LiveTranscriptionEvents,
    LiveOptions,
)


class DeepgramListener:
    """
    Handles real-time audio transcription via Deepgram WebSockets.
    """

    def __init__(self, transcript_callback: Callable[[str], None]):
        """
        Initialize the Deepgram listener.

        Args:
            transcript_callback: Function to call when a final transcript is received
        """
        self.api_key = os.environ.get("DEEPGRAM_API_KEY")
        if not self.api_key:
            raise ValueError("DEEPGRAM_API_KEY environment variable not set. Ensure Doppler has injected it.")

        self.transcript_callback = transcript_callback
        self.dg_connection: Optional[any] = None
        self.is_listening = False
        self._current_interim = ""

        # Configure Deepgram client
        config = DeepgramClientOptions(
            verbose=logging.WARNING,
            options={"keepalive": "true"}
        )
        self.deepgram = DeepgramClient(self.api_key, config)

    async def connect(self):
        """Establish WebSocket connection to Deepgram."""
        try:
            self.dg_connection = self.deepgram.listen.websocket.v("1")

            # Set up event handlers
            self.dg_connection.on(LiveTranscriptionEvents.OPEN, self._on_open)
            self.dg_connection.on(LiveTranscriptionEvents.TRANSCRIPT_RECEIVED, self._on_transcript)
            self.dg_connection.on(LiveTranscriptionEvents.CLOSE, self._on_close)
            self.dg_connection.on(LiveTranscriptionEvents.ERROR, self._on_error)
            self.dg_connection.on(LiveTranscriptionEvents.SPEECH_STARTED, self._on_speech_started)
            self.dg_connection.on(LiveTranscriptionEvents.SPEECH_FINISHED, self._on_speech_finished)

            # Configure live transcription options
            options = LiveOptions(
                model="nova-2-general",
                language="en-GB",  # British English for Nova's persona
                smart_format=True,
                interim_results=True,
                utterance_end_ms="1000",
                vad_events=True,
                endpointing=300,  # 300ms of silence triggers final transcript
            )

            # Start the connection
            if self.dg_connection.start(options):
                self.is_listening = True
                print("[STT] Deepgram connection established. Listening...")
            else:
                print("[STT] Failed to start Deepgram connection")

        except Exception as e:
            print(f"[STT Error] Failed to connect: {e}")
            raise

    def _on_open(self, client, *args, **kwargs):
        """Handler for WebSocket open event."""
        print("[STT] WebSocket connection opened")

    def _on_transcript(self, client, result, **kwargs):
        """Handler for transcript received event."""
        transcript = result.channel.alternatives[0].transcript
        is_final = result.is_final
        speech_final = result.speech_final

        if not transcript:
            return

        if is_final:
            print(f"[STT] Final (segment): {transcript}")
            if speech_final:
                # Complete utterance received
                print(f"[STT] Complete utterance: {transcript}")
                self.transcript_callback(transcript)
        else:
            # Interim results - for UI feedback
            self._current_interim = transcript
            # print(f"[STT] Interim: {transcript}")  # Uncomment for debugging

    def _on_speech_started(self, client, *args, **kwargs):
        """Handler for speech detection start."""
        print("[STT] Speech detected...")

    def _on_speech_finished(self, client, *args, **kwargs):
        """Handler for speech detection end."""
        print("[STT] Speech ended.")

    def _on_close(self, client, *args, **kwargs):
        """Handler for WebSocket close event."""
        print("[STT] WebSocket connection closed")
        self.is_listening = False

    def _on_error(self, client, error, **kwargs):
        """Handler for WebSocket error event."""
        print(f"[STT Error] {error}")

    async def send_audio(self, audio_chunk: bytes):
        """
        Send audio data to Deepgram.

        Args:
            audio_chunk: Raw audio bytes (PCM 16-bit, 16kHz, mono)
        """
        if self.is_listening and self.dg_connection:
            try:
                self.dg_connection.send(audio_chunk)
            except Exception as e:
                print(f"[STT Error] Failed to send audio: {e}")

    async def disconnect(self):
        """Close the WebSocket connection."""
        if self.dg_connection:
            self.dg_connection.finish()
            self.is_listening = False
            print("[STT] Disconnected from Deepgram")

    def finalize(self):
        """Force finalize any pending transcripts."""
        if self.dg_connection:
            self.dg_connection.finish()


import logging
logging.basicConfig(level=logging.INFO)
