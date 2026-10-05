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


## Visual scene understanding

The Auto Director can now score each clip semantically before editing. `beatstudio/scene_understanding.py` combines YOLO object detection, Haar face detection, optical-flow motion analysis, shot-scale heuristics and optional CLIP zero-shot scene semantics.

The resulting `SceneProfile` includes signals for:

- people and faces,
- performers,
- dancing,
- cars/vehicles,
- landscapes,
- close-up vs wide shot,
- motion intensity,
- approximate joyful / sad / intense / calm tone.

During a cut, `music_scene_score()` compares those visual signals with the current `BeatState`. High-energy drops prefer dancing, motion, performers and cars; quieter sections prefer close-ups, landscapes and calmer emotional imagery.

Install the optional semantic model stack with:

```bash
pip install -r requirements-vision.txt
```

Without the optional CLIP stack, the director still falls back to object, face, shot-scale and motion signals.

## Structured Suno editing

The Suno editor now exposes structured controls for:

- adding/emphasizing instruments,
- removing/reducing instruments,
- changing genre/style,
- target tempo/BPM,
- pitch transposition in semitones,
- female/male lead-vocal character,
- preserving melody,
- preserving lyrics.

These controls are translated into a precise natural-language v6 edit instruction, keeping the provider integration flexible rather than assuming undocumented parameter names.

## AI DJ

`beatstudio/ai_dj.py` analyzes tracks with Librosa and compares:

- BPM, including sensible half-time/double-time compatibility,
- estimated chroma/key,
- RMS energy,
- spectral brightness.

The AI DJ can time-stretch the incoming track toward the outgoing tempo, optionally transpose toward the reference key, and create an equal-power beatmatched crossfade.

Jamendo support is included for catalog discovery. The search adapter can request tracks enrolled in Jamendo's pro-licensing program and filter by search text, tags, speed, instrumental/vocal mode and vocalist gender.

**Important:** catalog discovery is not license clearance. A track still needs the appropriate commercial/synchronization license before release.

## Seedance 2.5

`beatstudio/video_provider.py` integrates the official BytePlus ModelArk video-generation API using Dreamina Seedance 2.5.

Supported product flows include:

- text-to-video,
- image/video/audio references,
- reference-to-video,
- video editing,
- video extension,
- optional synchronized audio generation,
- 4–30 second generations,
- asynchronous job polling.

Configure:

```bash
BYTEPLUS_ARK_API_KEY=
SEEDANCE_API_BASE=https://ark.ap-southeast.bytepluses.com/api/v3/contents/generations/tasks
```

## Stock video

`beatstudio/stock_media.py` adds Pexels video search. Users can search by prompt and orientation, preview a result, add it to the project and keep its attribution metadata for export.

Configure:

```bash
PEXELS_API_KEY=
```

## Automatic sound and visual effects

`beatstudio/auto_fx.py` maps the live music state to automatic video effects. Ordinary beats stay subtle, strong onsets add transient effects, and drops trigger the strongest reactions.

`beatstudio/sound_fx.py` can synthesize and mix original transition sounds without relying on a copyrighted SFX pack:

- low-frequency impacts,
- whooshes,
- risers.

These are placed at strong drop peaks and structural song boundaries detected from the same Librosa analysis driving the visual effects.

## Updated entitlements

| Tier | Key additions |
|---|---|
| Free | Uploads, stock search, basic beat sync, rhythm-based Auto Director |
| Pro | Semantic scene matching, Suno generation, AI DJ, licensed-catalog discovery, automatic sound design |
| Creator | 4K, Suno structured editing, Seedance generation, full song-structure intelligence |
| Studio | All features plus higher quotas, batch/team/priority architecture |

Generated media and catalog/API usage should be metered separately from render minutes because the upstream providers have their own variable costs.
