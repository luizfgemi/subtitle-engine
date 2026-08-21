# Subtitle Engine Guidance

## Purpose

`subtitle-engine` is a lightweight Python/FastAPI microservice for subtitle generation, extraction, translation, and ASR (Whisper) fallback.

## Project Layout

- `app/config.py`: Environment configuration and paths.
- `app/probe.py`: `ffprobe` wrapper to inspect video audio and subtitle tracks.
- `app/extract.py`: `ffmpeg` wrapper to extract embedded subtitle streams to `.srt`.
- `app/translate.py`: Translation module (e.g., EN -> pt-BR) via Google Translate API.
- `app/transcribe.py`: Speech-to-text ASR via `faster-whisper` with GPU/VAD support.
- `app/formatter.py`: SRT cue formatting and timestamp utilities.
- `app/pipeline.py`: Main decision tree (probe -> extract -> transcribe -> translate).
- `app/api.py`: FastAPI routes (`/health`, `/api/v1/probe`, `/api/v1/generate`, `/api/v1/event`, `/api/v1/batch-missing`).
- `app/main.py`: Uvicorn runner.

## Testing & Environment

- Environment setup: `python3 -m venv .venv && ./.venv/bin/pip install -r requirements-dev.txt`
- Run tests: `./.venv/bin/pytest`
