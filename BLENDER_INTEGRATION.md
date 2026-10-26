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

## Beat-reactive 3D Asset Animation

An additional modular animation engine supports Blender primitives and uploaded binary glTF 2.0 (.glb) assets. Each asset layer has independently selectable signal (beat/onset/bass/mids/treble/energy/drop), motion (pulse, spin, bounce, orbit, wobble, scale or material-glow preset), intensity, speed, 3D position, neon color and scale.

The React editor supports at most eight asset layers and eight uploaded GLB files; uploads have a 50 MiB limit each and are copied into a dedicated render-job workspace. The GLB header is checked before Blender imports the file. Note: header validation is not a full asset security scan. Blender import and GPU processing **must** run in containers without external network access, with strict CPU/RAM/time limits.

The `/v1/assets/animation-options` endpoint advertises supported controls. `POST /v1/renders` accepts `asset_layers_json` and the multipart `assets` fields, with predictable IDs `asset_0`, `asset_1`, etc. Example JSON:

```json
[
  {"name":"Brand logo","source":"glb","asset_id":"asset_0","animation":"pulse","signal":"bass","intensity":0.8,"color":"cyan"},
  {"name":"3D Wave","source":"torus","animation":"spin","signal":"treble","color":"magenta"}
]
```

Only Creator/Studio plans can request asset rendering via this endpoint. All models are rendered with a shared neon-emission aesthetic; sophisticated preservation of user-authored glTF material graphs, animations, skeleton rigging and physics interactions remain future work. Animated transforms have not yet been tested inside an actual Blender runtime.
