# BeatSync Studio

**BeatSync Studio** is an intelligent music-video creation platform. Its core is **Intelligent Beat Sync**: music is converted into continuous creative control signals—beat, onset, bass, mids, treble, RMS energy, spectral brightness, drop likelihood and song sections—and those signals drive an independently selectable visual-effect rack.

The product now accepts music in three ways:

1. **Upload an existing track**
2. **Generate a new soundtrack with Suno**
3. **Edit an existing Suno/public track through Suno**

It can also take multiple video clips and automatically create a first-pass edit before applying the selected VFX.

## Product pipeline

```text
                    ┌───────────────────────────────┐
                    │          MUSIC SOURCE         │
                    │ upload | Suno create | edit   │
                    └───────────────┬───────────────┘
                                    │
                                    ▼
                       Intelligent Beat Sync
                                    │
             ┌──────────────────────┼───────────────────────┐
             │                      │                       │
         beat/onset             frequency               structure
        + tempo grid        bass / mids / treble     drops / sections
             │                      │                       │
             └──────────────────────┴───────────────────────┘
                                    │
                   ┌────────────────┴────────────────┐
                   │                                 │
            AI Auto Director                    Effect Rack
          multi-clip shot cuts             45 independent VFX
                   │                                 │
                   └────────────────┬────────────────┘
                                    ▼
                            H.264/AAC export
```

## Intelligent Beat Sync

Most beat-sync scripts reduce music to a Boolean: "is this frame near a beat?" BeatSync Studio instead computes a `BeatState` for every frame. Effects can therefore respond to different musical phenomena:

- camera shake → transient/onset
- zoom → beat pulse
- particles → bass
- glitches → treble
- hue/scene changes → song section
- hard visual events → drop likelihood
- ambient effects → RMS energy or spectral brightness

Level 3 analysis additionally performs structural segmentation so longer musical regions can influence editing and visual direction.

## Automatic multi-clip director

Upload multiple raw clips and enable **AI Auto Director**. The first-pass editor:

- changes shots on musical phrase/section boundaries,
- shortens shots as energy increases,
- can trigger cuts at probable drops,
- groups beats into slower or faster edit cadences,
- rotates through clips to avoid immediate repetition.

The directed silent edit is then passed into the normal VFX renderer and muxed with the chosen soundtrack.

## Suno integration

Suno now provides an official developer platform for music generation. BeatSync Studio uses a provider adapter instead of reverse-engineered endpoints.

Set these values from the authenticated Suno developer documentation/dashboard:

```bash
SUNO_API_KEY=
SUNO_GENERATE_URL=
SUNO_EDIT_URL=
SUNO_STATUS_URL_TEMPLATE=
```

The endpoint URLs deliberately remain environment-configured because API paths and asynchronous job formats may evolve. BeatSync Studio sends standard Bearer-authenticated JSON requests and normalizes common result fields into a provider-independent `MusicResult`.

The UI supports:

- prompt-to-song generation,
- v6, v6-wild and v6-mini model selection,
- instrumental generation,
- optional lyrics and working title,
- natural-language editing of a source track,
- asynchronous status polling when a status endpoint is configured,
- direct handoff of generated/edited audio into Intelligent Beat Sync.

Do **not** store Suno API keys in the repository. Copy `.env.example` to your deployment secret manager or environment configuration.

## Effect catalog

The first release exposes **45 independently selectable effects** across:

- Subject
- Motion
- Glitch
- Light
- Particles
- Texture
- Color
- Lens
- Geometry
- HUD

Examples include Neon Edges, Body Aura, Ghost Trail, Camera Shake, Zoom Pulse, Micro Punch, Chromatic Split, Glitch Slices, VHS Noise, Bloom, Light Leak, Smart Strobe, Digital Rain, Posterize, Halftone, Solarize, Duotone, Thermal Vision, Fisheye Pulse, Kaleidoscope, Beat Bars and HUD Ring.

## Subscription and unit economics

Video rendering and generative music both have variable compute/API costs, so plans meter expensive operations rather than only restricting effect count.

| Tier | Price | Export | Effects | Intelligence | Render allowance | AI music |
|---|---:|---:|---:|---:|---:|---:|
| Free | $0/mo | 720p | 5 | L1 | 10 min/mo | 0 |
| Pro | $19/mo | 1080p | 18 | L2 | 180 min/mo | 10 |
| Creator | $39/mo | 4K | Unlimited | L3 | 600 min/mo | 40 |
| Studio | $99/mo | 4K | Unlimited | L3 | 2400 min/mo | 200 |

These are product defaults for testing, not final market pricing.

`beatstudio/usage.py` contains quota definitions and a transparent resolution-weighted render-minute estimator. In production, replace local/demo plan selection with verified Stripe entitlements and GPU-worker usage records.

## Current repository layout

```text
BeatSync-Studio/
├── app.py
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
├── legacy_neural_outline.py
├── beatstudio/
│   ├── __init__.py
│   ├── intelligence.py
│   ├── effects.py
│   ├── renderer.py
│   ├── director.py
│   ├── music_provider.py
│   ├── usage.py
│   └── plans.py
└── tests/
    └── test_registry.py
```

## Install and run

FFmpeg is required.

```bash
sudo apt-get install ffmpeg
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

On Windows, install FFmpeg separately and ensure `ffmpeg` is on `PATH`.

## Production SaaS architecture

The codebase is still an MVP/prototype. A production deployment should separate the web/API layer from media workers:

```text
Browser
  │
  ▼
Web/API ───────── Authentication
  │              Stripe webhooks
  │              Project database
  │
  ├── Object storage
  │
  └── Render queue
          │
          ▼
       GPU/CPU workers
          │
          ├── Intelligent Beat Sync
          ├── Auto Director
          ├── Neural masks
          └── VFX render
          │
          ▼
        CDN/output
```

Recommended next infrastructure:

- verified Stripe Checkout + webhook entitlements,
- authentication,
- project and preset persistence,
- S3/R2/GCS media storage,
- Redis/SQS/PubSub render queue,
- autoscaled CPU/GPU workers,
- render failure recovery,
- usage ledger,
- project history,
- collaborative Studio accounts,
- privacy controls for unreleased music,
- C2PA/provenance awareness for generated audio,
- API/SDK for automated music-video creation.

## Security

Never expose `SUNO_API_KEY`, Stripe secrets or storage credentials to browser code. Music generation and edit calls should run server-side. Treat unreleased audio/video as private customer data and use expiring object-store URLs in production.

## License

Choose a license before public commercial launch. No license is included by default.
