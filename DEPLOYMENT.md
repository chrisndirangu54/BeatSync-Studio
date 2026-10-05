# BeatSync Studio Web Deployment

BeatSync is now split into three production concerns:

1. **React/Next.js web UI** — `apps/web`
2. **FastAPI control/API service** — `apps/api`
3. **Render workers** — existing `beatstudio` engine, intended for durable background jobs

## Local development

```bash
docker compose up --build
```

Open:

- Web: http://localhost:3000
- API: http://localhost:8000
- FastAPI docs: http://localhost:8000/docs

## Frontend: Vercel

Create a Vercel project from this repository and set the **Root Directory** to:

```text
apps/web
```

Set:

```bash
NEXT_PUBLIC_API_BASE_URL=https://YOUR_API_HOST
```

Vercel will run the normal Next.js build.

## API: Google Cloud Run

Build from the repository root because the API image also needs the shared `beatstudio` package and root requirements.

Example:

```bash
gcloud builds submit \
  --tag REGION-docker.pkg.dev/PROJECT/beatsync/api \
  -f apps/api/Dockerfile .

gcloud run deploy beatsync-api \
  --image REGION-docker.pkg.dev/PROJECT/beatsync/api \
  --region REGION \
  --allow-unauthenticated \
  --set-env-vars CORS_ORIGINS=https://YOUR_WEB_DOMAIN
```

Then set the resulting Cloud Run URL as `NEXT_PUBLIC_API_BASE_URL` in Vercel.

## Render workers

The current API uses an in-process background thread only for **local development**.

Do not use that execution mode for production video rendering. Production should:

```text
Browser
  ↓
FastAPI
  ↓
Object storage
  ↓
Durable render job / queue
  ↓
Cloud Run Job or GPU worker
  ↓
Object storage / CDN
  ↓
Browser polls job status
```

Recommended production flow:

1. Upload source media directly to object storage with signed URLs.
2. Store project/render metadata in a database.
3. API creates a durable render job.
4. Worker receives storage object keys and render configuration.
5. Worker runs Narrative Planner → Scene Understanding → Auto Director → VFX renderer.
6. Worker uploads final MP4.
7. API exposes status/progress/output URL.

Cloud Run Jobs are appropriate because each task executes and exits rather than serving requests. GPU-backed Cloud Run jobs can be used for heavier semantic vision or generation workloads.

## Suggested managed services

A practical first deployment:

- **Vercel** — Next.js frontend
- **Google Cloud Run** — FastAPI API
- **Cloud Run Jobs** — render workers
- **Google Cloud Storage** — source and rendered media
- **Firestore or Postgres** — users/projects/job metadata
- **Stripe** — subscription entitlements
- **Suno / BytePlus Seedance / Jamendo / Pexels** — provider integrations already represented in the codebase

## Environment variables

Backend:

```bash
CORS_ORIGINS=
BEATSYNC_OUTPUT_DIR=
RENDER_EXECUTION_MODE=

SUNO_API_KEY=
SUNO_GENERATE_URL=
SUNO_EDIT_URL=
SUNO_STATUS_URL_TEMPLATE=

BYTEPLUS_ARK_API_KEY=
SEEDANCE_API_BASE=

PEXELS_API_KEY=
JAMENDO_CLIENT_ID=

STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
STRIPE_PRICE_PRO=
STRIPE_PRICE_CREATOR=
STRIPE_PRICE_STUDIO=
```

Frontend:

```bash
NEXT_PUBLIC_API_BASE_URL=
```

## Before public launch

The current web split is suitable for development and staging, but production still needs:

- authentication,
- durable database-backed render jobs,
- signed object-storage uploads,
- real Stripe webhook entitlements,
- persistent usage metering,
- worker retry/recovery,
- secure provider secret storage,
- downloadable output URLs instead of local filesystem paths.
