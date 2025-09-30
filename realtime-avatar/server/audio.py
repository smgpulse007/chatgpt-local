from __future__ import annotations

from typing import Iterable, Tuple

import numpy as np
from aiortc.mediastreams import AudioFrame


def pcm16_to_frame(pcm: np.ndarray, sample_rate: int) -> AudioFrame:
    if pcm.dtype != np.int16:
        pcm = pcm.astype(np.int16)
    frame = AudioFrame(format="s16", layout="mono", samples=len(pcm))
    frame.planes[0].update(pcm.tobytes())
    frame.sample_rate = sample_rate
    return frame


def frame_to_pcm16(frame: AudioFrame) -> np.ndarray:
    pcm = np.frombuffer(frame.planes[0].to_bytes(), dtype=np.int16)
    return pcm.copy()


def chunk_audio(pcm: np.ndarray, sample_rate: int, chunk_duration: float) -> Iterable[np.ndarray]:
    chunk_size = int(sample_rate * chunk_duration)
    for start in range(0, len(pcm), chunk_size):
        yield pcm[start : start + chunk_size]


__all__ = ["pcm16_to_frame", "frame_to_pcm16", "chunk_audio"]
