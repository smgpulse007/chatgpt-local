"""Placeholder vision module for future multimodal extensions."""

from typing import Optional


async def process_frame(_frame_bytes: bytes) -> Optional[str]:
    """Stub hook for future VLM integration."""
    return None


__all__ = ["process_frame"]
