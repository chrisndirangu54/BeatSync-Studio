# BeatSync Independent Creative Modules

## Implemented in this feature branch

- 17 independently configurable Blender simulation presets (procedural particles, visualizers, geometry/material animation, Mantaflow gas/liquid scene recipes).
- BeatSync frequency, onset, energy and drop signals exported once as bounded per-frame curves.
- Two headless Blender scene scripts: procedural animation and gas/liquid fluid-domain baking.
- A background-process orchestration wrapper for preapproved Blender scripts (no LLM Python execution).
- Compositing of transparent Blender output frames with the existing music-video VFX pipeline.
- Optional YOLO neural silhouette contours using the existing neon palette.
- Transparent PNG/GIF/MP4 overlay compositor accessible to worker code.
- Time-coded text-based explainer, title, statistic, lower-third and reaction cues.
- React controls for Blender layers, outline palette and time-coded cues, plus FastAPI form fields.
- Unit tests for manifests, overlays and motion cues.

## Important limitations

- Blender and GPU runtime validation is **not complete**. The repository's Python and Next.js CI verify syntax/tests/build only, not Blender simulations.
- A remote interactive Blender MCP session **has not been connected**. The checked-in workers accept constrained JSON scene manifests and run known scripts; they avoid unsafe arbitrary generated code.
- Ink mixing currently generates two liquid inflows, **not** two independently advected pigment fields. Dual-color gas uses distinct emitter colors and a color attribute for rendering.
- Mushroom-cloud and fireworks presets are artistic effects and not a verified high-fidelity physical explosion model.
- Curated media can be composited via Python worker, but the current HTTP endpoint does not accept meme/video asset files. Project-scoped upload/media storage and license checks remain necessary.
- AI-authored explainer script/storyboard generation and semantic meme matching have not been connected to an LLM/vision provider; current explainer and reaction cues are user-authored.
- Render jobs are currently launched inside development-only local threads. Production requires an authenticated durable queue, isolated workers, storage and limits. Never expose a Blender binary on public request-processing hosts.
- Long tracks and high-resolution Blender simulations are expensive: preview low-poly procedural layers first and bake gas/liquid scenes separately.
- The renderer currently fixes Blender layer render resolution to 1280x720 and resizes composited frames to the target video.

## Typical usage

1. Upload video(s) and soundtrack in BeatSync Studio.
2. Add optional Blender layers (Creator or Studio entitlements), independently choosing preset, trigger, intensity and neon palette.
3. Optionally add a YOLO outline; separately add timed explainer/reaction cues.
4. Render through FastAPI on an installation with Blender, FFmpeg and optional neural dependencies.
5. Evaluate frames and audio synchronization before production deployment.

## Worker requirements

- Blender 4.3+ or a pinned compatible build, FFmpeg, Python audio/vision stack.
- The Blender scripts run with `blender -b --python` in a sandboxed environment.
- Physically accurate gas/liquid layers require Mantaflow baking, cache storage and integration testing. Use approved scene manifest inputs only.
