from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse

from rtc import create_pc_and_tracks

app = FastAPI()


@app.get("/healthz")
async def healthz() -> dict:
    return {"ok": True}


@app.get("/config")
async def get_config() -> dict:
    from config import settings

    return settings.__dict__


@app.post("/webrtc/offer", response_class=PlainTextResponse)
async def webrtc_offer(req: Request) -> str:
    sdp = await req.body()
    answer_sdp = await create_pc_and_tracks(sdp.decode("utf-8"))
    return answer_sdp
