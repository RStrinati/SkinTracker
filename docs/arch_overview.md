# Architecture Overview

## High-Level Flow
```mermaid
flowchart LR
    TG[Telegram Bot] -->|webhook| FA[FastAPI `server.py`]
    FA -->|save_photo| ST[Supabase Storage (skin-photos)]
    FA -->|process_skin_image| ML[Processing]
    ST --> ML
    ML --> DB[(Supabase DB)]
    DB --> RP[Reporting / Telegram replies]
```

## Current Endpoints
| Method | Path | Payload | Response |
|--------|------|---------|----------|
| GET | `/` | – | `{"message": "Skin Health Tracker Bot is running"}` |
| GET | `/health` | – | `{status, service, version}` |
| POST | `/auth/telegram` | `TelegramAuthRequest` | `{token}` |
| POST | `/webhook` | Telegram Update JSON | `{status: "ok"}` |
| POST | `/ingredients/analyze` | `IngredientRequest` | `{analysis}` |
| POST | `/set-webhook` | – | `{message}` |
| DELETE | `/webhook` | – | `{message}` |

## Processing & Data Flow
1. `handle_photo` in `bot.py` receives images from Telegram and stores them via `Database.save_photo` in the private Supabase bucket `skin-photos`.
2. The same handler invokes `process_skin_image` to align faces, detect blemishes, and store KPI records plus overlay artifacts.
3. `log_photo` writes a row to `photo_logs`; `process_skin_image` writes to `skin_kpis`.

## Gaps & Tech Debt
- `server.py` serves all routes directly; no modular routers or versioned API.
- Image processing runs synchronously inside the Telegram handler; no background tasks.
- Data model lacks dedicated `images`, `face_landmarks`, or `lesions` tables; `skin_kpis` table not defined in migrations.
- Supabase access uses raw client calls; no ORM or Alembic migrations.
- Minimal test coverage around image processing and storage helpers.

## Refactor Plan
**Keep**
- Telegram bot workflow and command handlers.
- Supabase storage bucket `skin-photos`.

**Replace / Introduce**
- Introduce versioned routers (`/api/v1`) for uploads, processing, and summaries.
- Replace monolithic `process_skin_image` with modular pipeline (`ml/pipeline.py`).
- Add SQLAlchemy models and Alembic migrations for `images`, `face_landmarks`, `lesions`, and related views.
- Move storage helpers into `services/storage.py` with signed URL generation.

**Isolate**
- Define interfaces for face landmarking, lesion detection, and analytics to allow swapping models.
- Encapsulate DB access behind repository layer for easier testing.

## Integration Points (file:function)
- `server.py:app` – include new routers (`api/routers/images.py`, `api/routers/users.py`).
- `bot.py:SkinHealthBot.handle_photo` – replace direct processing with calls to API pipeline.
- `database.py:save_photo` & `log_photo` – refactor into storage service and new `images` table.
- `skin_analysis.py:process_skin_image` – superseded by `ml/pipeline.py` orchestrating face mesh, contour maps, and lesion detection.
