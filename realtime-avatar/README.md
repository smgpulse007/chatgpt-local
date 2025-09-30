# Realtime Avatar Assistant

This repository provides a fully local, real-time talking avatar assistant that runs entirely on Windows 11 with WSL2 and Docker Desktop. Speech captured in the browser is streamed to the backend over WebRTC where it is processed by GPU-accelerated ASR (faster-whisper), routed to a local Ollama LLM, and synthesized back into speech with Coqui XTTS while simultaneously emitting viseme events for a three.js avatar.

## Prerequisites

- Windows 11 with WSL2 and Docker Desktop installed
- NVIDIA RTX GPU with recent drivers and CUDA support (validated with Docker `--gpus all`)
- Ollama installed on the host machine with the desired model pulled:
  ```bash
  ollama pull qwen2.5:7b-instruct-q5_K_M
  ```

## Running the stack

In a host terminal, start Ollama:

```bash
ollama serve
```

Build and start the containers from the repository root:

```bash
docker compose -f docker/compose.yml up --build
```

Open the client in a modern browser (Chrome or Edge recommended):

```
http://localhost:5173
```

Grant microphone access when prompted. Speak naturally—after roughly 0.7–1.5 seconds the avatar should begin responding with synthesized speech and synchronized lip movements.

## Testing & Troubleshooting

- If latency exceeds ~2 seconds, open a shell inside the server container and confirm GPU utilization with `nvidia-smi`.
- Ensure the host firewall allows connections to `host.docker.internal:11434` so the server can reach Ollama.
- Interruptibility is built-in: start speaking while the avatar talks to trigger a graceful stop and listen cycle.

## Configuration

Environment defaults live in `server/config.py`. You can override values such as VAD timings, ASR model size, or TTS chunk length to balance latency versus accuracy.

Important environment variable:

- `OLLAMA_URL` (defaults to `http://host.docker.internal:11434`)

## Known Issues

- Minor lip-sync offsets (~100–200 ms) can be compensated by adjusting `AUDIO_VISEME_OFFSET_MS` in `server/config.py`.
- On low-power devices or mobile browsers, reduce the update rate to 60 FPS and limit morph target deltas.
- If XTTS alignment metadata is unavailable, the server automatically falls back to word-duration splitting with G2P phoneme allocation.

## Repository Layout

```
realtime-avatar/
  docker/
    Dockerfile.server
    Dockerfile.client
    compose.yml
  server/
    app.py
    rtc.py
    vad.py
    asr.py
    llm.py
    tts.py
    visemes.py
    vision.py
    audio.py
    config.py
    requirements.txt
  client/
    index.html
    vite.config.ts
    package.json
    tsconfig.json
    public/
      avatar.glb
    src/
      main.ts
      webrtc.ts
      avatar.ts
      viseme-mapping.ts
      ui.ts
  assets/
    blendshape_map.json
  scripts/
    dev.ps1
    dev.sh
```

Happy hacking!
