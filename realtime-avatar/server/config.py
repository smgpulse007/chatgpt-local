import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    ASR_MODEL: str = os.getenv("ASR_MODEL", "medium")
    ASR_FP16: bool = os.getenv("ASR_FP16", "true").lower() == "true"
    ASR_BEAM: int = int(os.getenv("ASR_BEAM", "1"))
    ASR_LANG: str = os.getenv("ASR_LANG", "en")
    LLM_URL: str = os.getenv("OLLAMA_URL", "http://host.docker.internal:11434")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "qwen2.5:7b-instruct-q5_K_M")
    TTS_SAMPLE_RATE: int = int(os.getenv("TTS_SAMPLE_RATE", "24000"))
    TTS_CHUNK_SECS: float = float(os.getenv("TTS_CHUNK_SECS", "1.0"))
    TTS_VOICE: str = os.getenv("TTS_VOICE", "xtts_v2_en")
    AUDIO_BITRATE: int = int(os.getenv("AUDIO_BITRATE", "32000"))
    VAD_SILENCE_MS: int = int(os.getenv("VAD_SILENCE_MS", "300"))
    VAD_FRAME_MS: int = int(os.getenv("VAD_FRAME_MS", "20"))
    VAD_ENERGY_THRESHOLD: float = float(os.getenv("VAD_ENERGY_THRESHOLD", "0.5"))
    DEBUG_LATENCY: bool = os.getenv("DEBUG_LATENCY", "true").lower() == "true"
    PHONEME_TO_VISEME_MAP_PATH: Path = Path(
        os.getenv("PHONEME_TO_VISEME_MAP_PATH", "../assets/blendshape_map.json")
    )
    AUDIO_VISEME_OFFSET_MS: float = float(os.getenv("AUDIO_VISEME_OFFSET_MS", "0"))


settings = Settings()
