# Motion import and retargeting

BeatSync now accepts project-scoped binary FBX, BVH, or GLB motion uploads. A separate character GLB supplies the visible humanoid/animal model. In the editor choose `imported` motion and select a `motion_N` file. The Blender worker loads the motion via `bpy.ops.import_scene.fbx`, `bpy.ops.import_anim.bvh`, or `bpy.ops.import_scene.gltf`.

The character renderer attempts a direct action transfer only with identical bone name sets; otherwise it constructs explicit rotation-copy constraints for normalized matching bone labels and bakes an action. This is a simple retargeting method, **not** generic human-to-animal retargeting. Different rest poses, root proportions, feet sliding, ground contact, and quadruped skeleton semantics need external IK and motion-model inference.

Security boundaries: binaries have size/signature checks, fixed file extensions, and sandboxed job-scoped paths. Content remains untrusted: Blender parsing must run in non-networked containers with memory, disk and CPU limits, and ideally a malware scan. There is no public or unofficial Mixamo API integration; Mixamo assets must be obtained legitimately and licensed appropriately.

Provider scope: Rodin submission/status/download adapter exists but requires `RODIN_API_KEY`, durable task ownership and tested provider payloads. Hugging Face candidate models are catalog references, not a hosted model service; no model inference is wired. The motion timing and procedural dance fallback can be used without external model providers.

Verification requirement: CI compilation, unit tests and Next.js builds do not validate Blender's FBX/BVH importer, action constraints, IK, baking, quality, or synchronization under a real GPU worker. Keep draft PR unmerged until that is validated.
