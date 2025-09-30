from __future__ import annotations

import functools
from typing import Tuple

import numpy as np
from faster_whisper import WhisperModel

from config import settings


class ASRTranscriber:
    def __init__(self) -> None:
        compute_type = "float16" if settings.ASR_FP16 else "float32"
        self.model = WhisperModel(
            settings.ASR_MODEL,
            device="cuda",
            compute_type=compute_type,
            beam_size=settings.ASR_BEAM,
        )

    @functools.lru_cache(maxsize=1)
    def language(self) -> str:
        return settings.ASR_LANG

    def transcribe(self, pcm16: np.ndarray, sr: int = 24000) -> Tuple[str, list, float]:
        if pcm16.dtype != np.int16:
            raise ValueError("ASR expects PCM16 input")
        segments, info = self.model.transcribe(
            audio=pcm16.astype(np.float32) / 32768.0,
            language=self.language(),
            beam_size=settings.ASR_BEAM,
        )
        text = " ".join(seg.text.strip() for seg in segments).strip()
        tokens = [token for seg in segments for token in seg.tokens]
        avg_conf = float(info["avg_logprob"]) if "avg_logprob" in info else 0.0
        return text, tokens, avg_conf


__all__ = ["ASRTranscriber"]
