from __future__ import annotations

from dataclasses import dataclass
from typing import Generator, List, Tuple

import numpy as np
from TTS.api import TTS as CoquiTTS

from config import settings


@dataclass
class AlignmentEvent:
    t: float
    phoneme: str
    weight: float = 1.0


def _lazy_model() -> CoquiTTS:
    if not hasattr(_lazy_model, "_instance"):
        _lazy_model._instance = CoquiTTS(model_name=settings.TTS_VOICE)
    return _lazy_model._instance  # type: ignore[attr-defined]


def _split_text(text: str, chunk_secs: float) -> List[str]:
    sentences: List[str] = []
    current = []
    approx_chars = max(int(chunk_secs * 30), 1)
    for token in text.split():
        current.append(token)
        if sum(len(w) for w in current) > approx_chars and token.endswith(('.', '!', '?')):
            sentences.append(" ".join(current))
            current = []
    if current:
        sentences.append(" ".join(current))
    return sentences or [text]


def _phonemize(words: List[str]) -> List[Tuple[str, List[str]]]:
    # Minimal fallback phoneme mapping
    simple_map = {
        "a": ["AA"],
        "e": ["EE"],
        "i": ["EE"],
        "o": ["OH"],
        "u": ["W-OO"],
        "m": ["MBP"],
        "b": ["MBP"],
        "p": ["MBP"],
        "f": ["FV"],
        "v": ["FV"],
        "l": ["L"],
        "w": ["W-OO"],
        "sh": ["SH"],
        "ch": ["CH-JH"],
        "j": ["CH-JH"],
    }
    result: List[Tuple[str, List[str]]] = []
    for word in words:
        lower = word.lower()
        phonemes: List[str] = []
        i = 0
        while i < len(lower):
            if lower.startswith("sh", i):
                phonemes.extend(simple_map.get("sh", ["REST"]))
                i += 2
                continue
            if lower.startswith("ch", i):
                phonemes.extend(simple_map.get("ch", ["REST"]))
                i += 2
                continue
            phonemes.extend(simple_map.get(lower[i], ["REST"]))
            i += 1
        if not phonemes:
            phonemes = ["REST"]
        result.append((word, phonemes))
    return result


def synthesize_stream(text: str) -> Generator[Tuple[np.ndarray, List[AlignmentEvent]], None, None]:
    tts = _lazy_model()
    sentences = _split_text(text, settings.TTS_CHUNK_SECS)
    elapsed = 0.0
    for sentence in sentences:
        waveform = tts.tts(sentence, speaker=0, sample_rate=settings.TTS_SAMPLE_RATE)
        audio = np.asarray(waveform, dtype=np.float32)
        duration = audio.shape[0] / settings.TTS_SAMPLE_RATE
        words = sentence.split()
        phonemes = _phonemize(words)
        events: List[AlignmentEvent] = []
        if words:
            word_duration = duration / len(words)
            t_cursor = 0.0
            for word, phs in phonemes:
                if not phs:
                    phs = ["REST"]
                per_ph = word_duration / len(phs)
                for ph in phs:
                    events.append(AlignmentEvent(t=elapsed + t_cursor, phoneme=ph))
                    t_cursor += per_ph
        yield audio, events
        elapsed += duration


__all__ = ["synthesize_stream", "AlignmentEvent"]
