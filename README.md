# Subtitle Engine

FastAPI microservice for subtitle inspection, extraction, translation, Whisper GPU ASR, and Guardian orphan cleanup across the media stack.

## Development

Requires Python 3.12.

```bash
python3 -m venv .venv
./.venv/bin/pip install -r requirements-dev.txt
./.venv/bin/pytest
```

Run service locally:

```bash
./.venv/bin/python -m app.main
```

## Endpoints

- `GET /health` - Healthcheck status and GPU Whisper readiness.
- `POST /api/v1/probe` - Inspect video audio and subtitle track streams.
- `POST /api/v1/generate` - On-demand subtitle pipeline execution for a media file.
- `POST /api/v1/event` - Tolerant webhook endpoint for Bazarr, Radarr, and Sonarr events.
- `POST /api/v1/batch-missing` - Process media files missing target subtitles from Bazarr DB.
- `POST /api/v1/guardian/audit` - Execute Guardian sync validation and orphan subtitle cleanup.

## Features & Background Scheduler

- **Pipeline**: `probe` -> `extract` -> `translate` -> `transcribe` (Whisper `large-v3-turbo` with CUDA/VAD).
- **Guardian**: Audits Bazarr DB sync history and purges orphan `.srt` files (without matching video).
- **Background Scheduler**: Configurable via environment variables (`SCHEDULER_ENABLED`, `SCHEDULE_BATCH_MISSING_INTERVAL_MINUTES`, `SCHEDULE_GUARDIAN_INTERVAL_HOURS`).


