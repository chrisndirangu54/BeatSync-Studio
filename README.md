# BeatSync Studio

**BeatSync Studio** is a UI-driven music-video VFX engine built around **Intelligent Beat Sync** rather than a single hard-coded effect chain. It analyzes musical structure and exposes smooth control signals—beat, onset, bass, mids, treble, energy, spectral brightness, drop likelihood, and song section—to individually enabled effects.

## Why it is different

Most beat-sync scripts simply test whether a frame is near a beat. BeatSync Studio creates a richer musical state for every video frame. Effects can respond to different features: camera shake to transients, zoom to beat pulses, particles to bass, hue changes to sections, glitches to treble, and high-impact effects to likely drops.

## UI

The Streamlit interface lets users upload a video and track, select a subscription tier, turn effects on/off individually, adjust each intensity, render, preview and download the result.

## Effect catalog

The first release exposes 40+ independently selectable effects grouped into Subject, Motion, Glitch, Light, Particles, Texture, Color, Lens, Geometry and HUD categories. Examples include Neon Edges, Body Aura, Ghost Trail, Camera Shake, Zoom Pulse, Micro Punch, Chromatic Split, Glitch Slices, VHS Noise, Bloom, Light Leak, Smart Strobe, Digital Rain, Posterize, Halftone, Solarize, Duotone, Thermal Vision, Fisheye Pulse, Kaleidoscope, Beat Bars and HUD Ring.

## Subscription architecture

| Tier | Price | Export | Simultaneous effects | Intelligence |
|---|---:|---:|---:|---:|
| Free | $0/mo | 720p | 5 | Level 1 |
| Pro | $12/mo | 1080p | 18 | Level 2 |
| Creator | $29/mo | 4K | Unlimited | Level 3 + section analysis |
| Studio | $79/mo | 4K | Unlimited | Level 3 + batch/priority architecture |

The current app provides local/demo entitlement selection. `stripe` is included as a dependency so production can replace this selector with verified Stripe Checkout/customer entitlements.

## Run locally

```bash
sudo apt-get install ffmpeg
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Architecture

```text
Video + Audio
     │
     ├──── Audio → IntelligentBeatSync
     │             ├ beat grid
     │             ├ onsets
     │             ├ bass/mids/treble
     │             ├ RMS energy
     │             ├ spectral brightness
     │             ├ drop likelihood
     │             └ song sections
     │
     └──── Video frames → Effect Rack → Renderer → H.264/AAC
                            ↑
                      per-frame BeatState
```

## Production roadmap

- Verified Stripe Checkout + webhook entitlements
- user authentication and project persistence
- GPU worker queue
- neural person/face/pose masks as reusable effect inputs
- cloud object storage
- timeline editor and keyframes
- effect presets and marketplace
- batch exports
- collaborative projects
- API/SDK for automated music-video generation

## License

Choose a license before public commercial launch. No license is included by default.
