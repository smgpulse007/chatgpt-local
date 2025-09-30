from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Callable, List, Optional

import numpy as np
import torch

from config import settings


@dataclass
class Utterance:
    samples: np.ndarray
    sample_rate: int
    started_at: float
    ended_at: float


class SileroVAD:
    """Wrapper around the Silero Voice Activity Detector.

    Audio pushed to :meth:`push` must be PCM16 mono @ 24 kHz. Detected
    utterances are emitted via ``on_utterance`` callback or can be awaited via
    :meth:`get_utterance`.
    """

    def __init__(self, sample_rate: int = 24000) -> None:
        self.sample_rate = sample_rate
        self._model, utils = torch.hub.load(
            repo_or_dir="snakers4/silero-vad",
            model="silero_vad",
            verbose=False,
        )
        (_, self._get_speech_timestamps, _, self._collect_chunks) = utils
        self._buffer: List[np.ndarray] = []
        self._current_start: Optional[float] = None
        self._loop = asyncio.get_event_loop()
        self._queue: asyncio.Queue[Utterance] = asyncio.Queue()
        self._on_utterance: Optional[Callable[[Utterance], None]] = None
        self._frame_samples = int(self.sample_rate * settings.VAD_FRAME_MS / 1000)
        self._silence_samples = int(self.sample_rate * settings.VAD_SILENCE_MS / 1000)

    def on_utterance(self, callback: Callable[[Utterance], None]) -> None:
        self._on_utterance = callback

    async def get_utterance(self) -> Utterance:
        return await self._queue.get()

    def push(self, pcm16: np.ndarray, timestamp: float) -> None:
        if pcm16.dtype != np.int16:
            raise ValueError("VAD expects PCM16 audio")
        self._buffer.append(pcm16)
        self._process(timestamp)

    def _process(self, timestamp: float) -> None:
        if not self._buffer:
            return
        audio = np.concatenate(self._buffer)
        speech_segments = self._get_speech_timestamps(
            audio,
            self._model,
            sampling_rate=self.sample_rate,
            threshold=settings.VAD_ENERGY_THRESHOLD,
            min_silence_duration_ms=settings.VAD_SILENCE_MS,
            min_speech_duration_ms=settings.VAD_FRAME_MS * 2,
        )
        if not speech_segments:
            # no speech detected yet
            return

        for segment in speech_segments:
            start_sample = segment["start"]
            end_sample = segment["end"]
            utterance_audio = audio[start_sample:end_sample]
            if utterance_audio.size == 0:
                continue
            started_at = timestamp - (audio.size - start_sample) / self.sample_rate
            ended_at = started_at + utterance_audio.size / self.sample_rate
            utterance = Utterance(
                samples=utterance_audio.copy(),
                sample_rate=self.sample_rate,
                started_at=started_at,
                ended_at=ended_at,
            )
            if self._on_utterance:
                self._on_utterance(utterance)
            try:
                self._queue.put_nowait(utterance)
            except asyncio.QueueFull:
                pass
        # clear buffer when first silence is detected beyond last segment
        last_end = speech_segments[-1]["end"]
        if audio.size - last_end > self._silence_samples:
            self._buffer = [audio[last_end:]]
        else:
            self._buffer = [audio[last_end:]]


__all__ = ["SileroVAD", "Utterance"]
