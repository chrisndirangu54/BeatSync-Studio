# Optional AI Visual Suite

This branch introduces optional YOLO-based human segmentation, neon body outlines, timeline-driven text/meme/sticker overlays, and structured Blender render job requests.

## Current integration

The existing Streamlit editor exposes:
- **YOLO neural neon body outline:** disabled by default, lazy-loads `yolo11n-seg.pt`; person-class instance masks and neon colours react to bass, beats and song sections. Installation requires `ultralytics` and locally available or downloadable model weights.
- **AI explainer / meme motion cues:** supply a JSON storyboard in the editor. BeatSync composites cue text or supported local image assets using the existing per-frame music state.
- **Blender MCP:** validates a render job describing a 3D scene, tempo, dimensions and neon palette. It is a *contract*, not a live MCP connection. A separate authenticated, isolated Blender/MCP worker must generate approved PNG frames and hand the resulting assets back to BeatSync. Never pass LLM-authored Python code directly to Blender.
- **Compatibility:** All new modes are optional; existing 45 effects and Auto Director remain unchanged.

Example storyboard:

```json
{
  "cues": [
    {"start": 0.5, "end": 3.0, "mode": "explainer", "text": "How bass drives the visuals", "trigger": "energy", "threshold": 0.1},
    {"start": 4.0, "end": 5.0, "mode": "meme", "text": "THE DROP!", "trigger": "drop", "threshold": 0.5}
  ]
}
```

Programmatic use:

```python
from beatstudio.visual_suite import VisualSuiteConfig
from beatstudio.motion_planner import compile_storyboard
from beatstudio.renderer import VideoRenderer

cues = compile_storyboard({"cues":[{"start":1,"end":3,"mode":"meme","text":"DROP!"}]})
renderer = VideoRenderer("clip.mp4","sound.wav","result.mp4",plan_key="pro",
                         visual_suite=VisualSuiteConfig(body_outline=True,cues=cues))
renderer.render()
```

## Production constraints

This version uses the existing offline CPU/OpenCV compositor. It does **not** yet implement WebM/GIF animated asset decoding, 3D Blender render execution, LLM storyboard generation, typography shape animation, background media uploads, real-time GPU inference, distributed asset storage or worker authentication. Only locally trusted image paths should be allowed; never accept arbitrary server filesystem paths from internet clients. The Streamlit JSON interface is suitable for trusted local development, not multi-tenant public deployment.

Future production work: auth-scoped asset IDs, fully sandboxed Blender worker, GIF/MP4/WebM overlay decoder, typography keyframes, prompt-to-storyboard service with schema validation and content moderation, shot-to-beat preview, and GPU performance benchmarks.

## Verification

```bash
pip install -r requirements-dev.txt
pytest -q tests/test_visual_suite.py
```

No claim of successful GPU/Blender runtime testing is made by this branch. Test YOLO mask generation on representative footage, export timing, no-person footage, and font rendering before deploying to customers.
