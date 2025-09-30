from __future__ import annotations

import asyncio
import json
import time
from typing import Optional

import numpy as np
from aiortc import RTCPeerConnection, RTCSessionDescription, MediaStreamTrack
from aiortc.mediastreams import AudioStreamTrack

from asr import ASRTranscriber
from audio import frame_to_pcm16, pcm16_to_frame
from config import settings
from llm import infer
from tts import synthesize_stream
from vad import SileroVAD
from visemes import phoneme_events_to_visemes


class BotAudioTrack(AudioStreamTrack):
    kind = "audio"

    def __init__(self, sample_rate: int) -> None:
        super().__init__()
        self.sample_rate = sample_rate
        self._queue: asyncio.Queue = asyncio.Queue()
        self._stop_event = asyncio.Event()

    async def recv(self):  # type: ignore[override]
        frame = await self._queue.get()
        return frame

    def clear(self) -> None:
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break

    async def push(self, pcm: np.ndarray) -> None:
        frame = pcm16_to_frame(pcm, self.sample_rate)
        await self._queue.put(frame)


async def create_pc_and_tracks(offer_sdp: str) -> str:
    pc = RTCPeerConnection()
    bot_track = BotAudioTrack(sample_rate=settings.TTS_SAMPLE_RATE)
    pc.addTrack(bot_track)
    asr = ASRTranscriber()
    vad = SileroVAD(sample_rate=24000)
    tts_lock = asyncio.Lock()
    current_tts: Optional[asyncio.Task] = None
    viseme_channel = pc.createDataChannel("visemes")

    def cancel_tts():
        nonlocal current_tts
        if current_tts and not current_tts.done():
            current_tts.cancel()
        bot_track.clear()
        if viseme_channel.readyState == "open":
            viseme_channel.send(json.dumps({"type": "clear"}))

    @pc.on("datachannel")
    def on_datachannel(channel):
        nonlocal viseme_channel
        if channel.label == "visemes":
            viseme_channel = channel

    @pc.on("track")
    def on_track(track: MediaStreamTrack) -> None:
        if track.kind != "audio":
            return

        async def _reader() -> None:
            while True:
                frame = await track.recv()
                pcm = frame_to_pcm16(frame)
                vad.push(pcm, time.time())

        async def _utterance_worker() -> None:
            nonlocal current_tts
            while True:
                utterance = await vad.get_utterance()
                cancel_tts()
                text, tokens, confidence = asr.transcribe(utterance.samples, utterance.sample_rate)
                if not text:
                    continue
                if settings.DEBUG_LATENCY:
                    print(f"ASR text='{text}' conf={confidence:.2f}")
                reply = await infer(text)
                full_text = " ".join(filter(None, [reply["first"], reply["rest"]]))
                if viseme_channel.readyState == "open":
                    viseme_channel.send(json.dumps({"type": "caption", "text": full_text}))

                async def _speak(message: str) -> None:
                    start_time = time.time()
                    async with tts_lock:
                        for audio_chunk, alignment_events in synthesize_stream(message):
                            pcm16 = np.clip(audio_chunk, -1.0, 1.0)
                            pcm16 = (pcm16 * 32767).astype(np.int16)
                            await bot_track.push(pcm16)
                            visemes = phoneme_events_to_visemes(alignment_events)
                            if viseme_channel.readyState == "open" and visemes:
                                payload = {
                                    "type": "visemes",
                                    "events": [
                                        {
                                            "t": round(event.t, 4),
                                            "viseme": event.viseme,
                                            "weight": event.weight,
                                            "blendshapes": event.blendshapes,
                                        }
                                        for event in visemes
                                    ],
                                }
                                viseme_channel.send(json.dumps(payload))
                    if settings.DEBUG_LATENCY:
                        print(f"TTS duration={time.time() - start_time:.2f}s for '{message}'")

                current_tts = asyncio.create_task(_speak(full_text))

        asyncio.create_task(_reader())
        asyncio.create_task(_utterance_worker())

    offer = RTCSessionDescription(sdp=offer_sdp, type="offer")
    await pc.setRemoteDescription(offer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)
    return pc.localDescription.sdp


__all__ = ["create_pc_and_tracks"]
