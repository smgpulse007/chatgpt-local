from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List

from config import settings
from tts import AlignmentEvent


@dataclass
class VisemeEvent:
    t: float
    viseme: str
    weight: float
    blendshapes: Dict[str, float]


def _load_map() -> Dict[str, Dict[str, float]]:
    path = Path(settings.PHONEME_TO_VISEME_MAP_PATH)
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def phoneme_events_to_visemes(events: Iterable[AlignmentEvent]) -> List[VisemeEvent]:
    mapping = _load_map()
    visemes: List[VisemeEvent] = []
    alpha = 0.6
    prev_weights: Dict[str, float] = {}
    for event in events:
        viseme_key = event.phoneme if event.phoneme in mapping else "REST"
        target = mapping.get(viseme_key, mapping.get("REST", {}))
        smoothed: Dict[str, float] = {}
        for blendshape, weight in target.items():
            prev = prev_weights.get(blendshape, 0.0)
            smoothed_weight = alpha * weight + (1 - alpha) * prev
            smoothed[blendshape] = round(smoothed_weight, 4)
        prev_weights.update(smoothed)
        visemes.append(
            VisemeEvent(
                t=event.t + settings.AUDIO_VISEME_OFFSET_MS / 1000.0,
                viseme=viseme_key,
                weight=event.weight,
                blendshapes=smoothed,
            )
        )
    return visemes


__all__ = ["VisemeEvent", "phoneme_events_to_visemes"]
