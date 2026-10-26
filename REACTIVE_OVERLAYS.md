# Reactive Motion Overlay integration

This branch adds the first optional creative overlay layer. Existing projects remain unchanged unless overlay options are provided.

## API usage

Send multipart `POST /v1/renders` with the existing audio/videos and a JSON form field:

```json
{
  "neural_outline": true,
  "outline_color": "magenta",
  "outline_intensity": 0.8,
  "trigger": "bass",
  "caption": "THE FUTURE IS HERE"
}
```

Set `neural_outline=false` to disable YOLO inference. Available neon colors: cyan, magenta, blue, lime. Audio signals: beat, onset, bass, mids, treble, drop, energy. The Pro-or-higher restriction is enforced at the render API for neural outlines.

Install the optional YOLO/vision dependencies before enabling the outline. A segmentation checkpoint such as `yolo11n-seg.pt` is loaded by Ultralytics on demand. Secure production systems should pre-provision and pin vetted model weights to avoid runtime downloads.

## GIF/video/meme overlays

The reusable `MediaLayer` and `ReactiveOverlayEngine` support local PNG, JPG, WebP, GIF, MP4, MOV and WebM, including transparent PNG/GIF overlays. They are ready for worker-side project-media paths. Do not accept user-supplied absolute filesystem paths through an untrusted API. Next step: upload assets to authorized project storage, scan/validate them, and attach their stored paths to render jobs. The current API intentionally does not accept `media_paths`.

## Blender MCP

`BlenderScene` emits a bounded JSON manifest for the future Blender worker integration. No Blender MCP server is connected or remotely executed by this branch. Recommended production integration: trusted service adapter -> allowlisted MCP tools -> sandboxed Blender GPU worker -> frame sequence with alpha -> compositor. Do not execute raw, unreviewed generated Python inside Blender.

## AI explainers and contextual reaction memes

This branch supports typed captions and externally prepared visual overlay assets, but does **not** yet include an LLM script/storyboard service, semantic meme selection, GIF discovery API, licensing filter, or Blender-rendered explainer generation. Those require independent providers and editorial controls.

## Testing

```bash
python -m unittest tests.test_reactive_overlays
```

For full integration, test model loading, GPU/CPU worker availability, representative multi-person videos, and FFmpeg exports. Unit tests do not constitute end-to-end validation.
