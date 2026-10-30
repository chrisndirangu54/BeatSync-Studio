# TeknTandao Media Cloud ↔ BeatSync Studio

BeatSync Studio is the editing/rendering engine. Media Cloud is the multi-tenant marketing orchestration system.

## Integration contract (proposed; not deployed)

1. Media Cloud campaign owner selects an existing BeatSync project and export preset.
2. A trusted backend exchanges tenant/project authorization with BeatSync; never pass Media Cloud API keys to an untrusted browser.
3. BeatSync verifies project ownership with its existing Firebase Auth principal and creates a render/export job.
4. BeatSync returns a job ID and later emits a signed, replay-protected completion callback to Media Cloud with an approved asset reference.
5. Media Cloud adds the asset to a **draft** social post; publishing requires a customer approval and platform OAuth.

### JSON handoff envelope

```json
{
  "event_type": "media_cloud.render.requested",
  "campaign_id": "campaign-id",
  "beat_sync_project_id": "project-id",
  "output_preset": "vertical_1080p",
  "idempotency_key": "unique-request-id"
}
```

### Integration status

The separate Media Cloud v0.1 API implements `POST /v1/beatsync/handoffs` to record requests as `pending_connector`. **It does not call this repository or render videos yet.** This file is a non-invasive interface proposal for review, rather than an unsafe unauthenticated endpoint.

### CapCut / Adobe Premiere comparison

Current BeatSync features include audio-reactive effects, lyrics, renderer and animation components. Professional parity must be measured independently using multi-track timeline, media codec support, keyframe/curves, multicam, proxy media, color management, masks/tracking, mixing, collaboration, GPU acceleration, export fidelity and reliability tests. Do not claim SOTA or feature parity without benchmark evidence.

## Implementation gates

- Tenant-to-project identity mapping and backend authorization
- Signed webhook transport and idempotency/replay protection
- Asynchronous render dispatch and object-storage asset transfer
- User consent and licensed media checks
- Automated adapter contract tests and end-to-end rendering tests
