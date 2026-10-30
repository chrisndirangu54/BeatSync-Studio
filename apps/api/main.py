from __future__ import annotations

import json
import os
import shutil
import tempfile
import threading
import uuid
from pathlib import Path
from typing import List

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from beatstudio.director import DirectorConfig, MultiClipDirector
from beatstudio.effects import SPECS
from beatstudio.narrative import NarrativePlanner
from beatstudio.plans import PLANS
from beatstudio.renderer import VideoRenderer
from beatstudio.reactive_overlays import OverlayConfig
from beatstudio.blender_simulations import SimulationLayer, PRESETS
from beatstudio.motion_cues import MotionCue
from beatstudio.asset_animation import AssetLayer, prepare_assets, ANIMATIONS, SHAPES, SIGNALS, COLORS
from beatstudio.character_animation import CharacterTrack, CameraTrack
from beatstudio.character_providers import RodinClient
from beatstudio.motion_import import save_motion_uploads
from beatstudio.lyrics import LyricCue, parse_lyrics, STYLES, FONTS
from beatstudio.agent_workflows import plan_prompt, AGENTS
from beatstudio.ai_director import plan_with_model
from .auth import Principal, require_admin, require_user
from .admin import router as admin_router
from .media_cloud_bridge import router as media_cloud_router

app = FastAPI(
    title="BeatSync Studio API",
    version="0.2.0",
    description="API for Intelligent Beat Sync, narrative planning and render orchestration.",
)

origins = [x.strip() for x in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if x.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

JOBS: dict[str, dict] = {}
OUTPUT_DIR = Path(os.getenv("BEATSYNC_OUTPUT_DIR", "/tmp/beatsync-outputs"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
app.include_router(admin_router)
app.include_router(media_cloud_router)

def save_upload(upload: UploadFile, directory: Path, prefix: str) -> Path:
    suffix = Path(upload.filename or "").suffix
    destination = directory / f"{prefix}{suffix}"
    with destination.open("wb") as handle:
        shutil.copyfileobj(upload.file, handle)
    return destination

@app.get("/health")
def health():
    return {"status": "ok", "service": "beatsync-api"}

@app.get("/v1/plans")
def plans():
    return [{
        "key": p.key,
        "name": p.name,
        "monthly_usd": p.monthly_usd,
        "export_height": p.export_height,
        "watermark": p.watermark,
        "max_effects": p.max_effects,
        "intelligent_sync_level": p.intelligent_sync_level,
        "features": sorted(p.features),
    } for p in PLANS.values()]

@app.get("/v1/effects")
def effects():
    return [{
        "key": s.key,
        "name": s.name,
        "category": s.category,
        "description": s.description,
        "tier": s.tier,
        "default_intensity": s.default_intensity,
        "signal": s.signal,
    } for s in SPECS]

@app.post("/v1/narrative/plan")
def narrative_plan(audio: UploadFile = File(...), intelligence_level: int = Form(3), user: Principal = Depends(require_user)):
    workspace = Path(tempfile.mkdtemp(prefix="beatsync_narrative_"))
    try:
        audio_path = save_upload(audio, workspace, "audio")
        return NarrativePlanner(
            str(audio_path),
            intelligence_level=max(3, intelligence_level),
        ).plan().to_dict()
    finally:
        shutil.rmtree(workspace, ignore_errors=True)

def _render_job(
    job_id: str,
    workspace: Path,
    audio_path: Path,
    video_paths: list[Path],
    plan_key: str,
    effects: dict[str, float],
    scene_aware: bool,
    narrative_planning: bool,
    automatic_fx: bool,
    automatic_sound_fx: bool,
    overlay_config: OverlayConfig,
    blender_layers: list[SimulationLayer],
    motion_cues: list[MotionCue],
    asset_layers: list[AssetLayer],
    asset_paths: dict[str,str],
    characters: list[CharacterTrack],
    camera: CameraTrack,
    lyric_cues: list[LyricCue],
):
    JOBS[job_id].update(status="running", progress=0.02)
    try:
        source = video_paths[0]
        if len(video_paths) > 1:
            directed = workspace / "directed.mp4"
            config = DirectorConfig(
                semantic_matching=scene_aware,
                narrative_planning=narrative_planning,
            )
            director = MultiClipDirector(
                [str(p) for p in video_paths],
                str(audio_path),
                str(directed),
                intelligence_level=PLANS[plan_key].intelligent_sync_level,
                config=config,
            )
            director.build(
                lambda value: JOBS[job_id].update(progress=round(0.05 + value * 0.35, 4))
            )
            source = directed

        output = OUTPUT_DIR / f"{job_id}.mp4"
        renderer = VideoRenderer(
            str(source),
            str(audio_path),
            str(output),
            plan_key,
            effects,
            automatic_fx=automatic_fx,
            automatic_sound_fx=automatic_sound_fx,
            overlay_config=overlay_config,
            blender_layers=blender_layers,
            motion_cues=motion_cues,
            asset_layers=asset_layers,
            asset_paths=asset_paths,
            characters=characters,
            camera=camera,
            lyric_cues=lyric_cues,
        )
        renderer.render(
            lambda value: JOBS[job_id].update(progress=round(0.40 + value * 0.60, 4))
        )
        JOBS[job_id].update(status="completed", progress=1.0, output_path=str(output))
    except Exception as exc:
        JOBS[job_id].update(status="failed", error=str(exc))
    finally:
        shutil.rmtree(workspace, ignore_errors=True)

@app.post("/v1/renders", status_code=202)
def create_render(
    audio: UploadFile = File(...),
    videos: List[UploadFile] = File(...),
    plan_key: str = Form("free"),
    effects_json: str = Form("{}"),
    scene_aware: bool = Form(True),
    narrative_planning: bool = Form(True),
    automatic_fx: bool = Form(True),
    automatic_sound_fx: bool = Form(False),
    overlays_json: str = Form("{}"),
    blender_layers_json: str = Form("[]"),
    motion_cues_json: str = Form("[]"),
    asset_layers_json: str = Form("[]"),
    characters_json: str = Form("[]"),
    camera_json: str = Form("{}"),
    lyrics_json: str = Form("[]"),
    lyrics_file: UploadFile | None = File(default=None),
    assets: List[UploadFile] = File(default=[]),
    motion_files: List[UploadFile] = File(default=[]),
    user: Principal = Depends(require_user),
):
    if plan_key not in PLANS:
        raise HTTPException(400, "Unknown plan")
    if not videos:
        raise HTTPException(400, "At least one video is required")
    effective_plan = plan_key if user.admin else user.plan
    if effective_plan not in PLANS:
        effective_plan = "free"

    try:
        effects = {str(k): float(v) for k, v in json.loads(effects_json).items()}
    except Exception as exc:
        raise HTTPException(400, f"Invalid effects_json: {exc}")

    try:
        overlay_input = json.loads(overlays_json)
        if not isinstance(overlay_input, dict):
            raise ValueError('Expected an object')
        allowed = {'neural_outline','outline_color','outline_intensity','caption','trigger'}
        if set(overlay_input) - allowed:
            raise ValueError('Unsupported overlay field')
        overlay_config = OverlayConfig(**overlay_input)
        if overlay_config.outline_color not in {'cyan','magenta','blue','lime'} or overlay_config.trigger not in {'beat','onset','bass','mids','treble','drop','energy'} or len(overlay_config.caption) > 100:
            raise ValueError('Invalid overlay configuration')
        if overlay_config.neural_outline and PLANS[effective_plan].intelligent_sync_level < 2:
            raise ValueError('Neural outline requires Pro or higher')
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        raise HTTPException(400, f'Invalid overlays_json: {exc}')

    try:
        raw_layers=json.loads(blender_layers_json)
        if not isinstance(raw_layers,list) or len(raw_layers)>4:
            raise ValueError('Maximum four independent Blender layers per render')
        allowed_layer_fields={'preset','enabled','signal','intensity','color_a','color_b','seed','quality'}
        blender_layers=[]
        for layer in raw_layers:
            if not isinstance(layer,dict) or set(layer)-allowed_layer_fields:
                raise ValueError('Invalid Blender layer')
            item=SimulationLayer(**layer).validate()
            if item.enabled: blender_layers.append(item)
        if blender_layers and PLANS[effective_plan].intelligent_sync_level < 3:
            raise ValueError('Blender simulations require Creator or Studio')
    except (ValueError,TypeError,KeyError,json.JSONDecodeError) as exc:
        raise HTTPException(400,f'Invalid blender_layers_json: {exc}')

    try:
        raw_cues=json.loads(motion_cues_json)
        if not isinstance(raw_cues,list) or len(raw_cues)>50: raise ValueError('Maximum 50 cues')
        allowed_cues={'text','start','duration','style','trigger','position'}
        motion_cues=[]
        for c in raw_cues:
            if not isinstance(c,dict) or set(c)-allowed_cues: raise ValueError('Invalid cue object')
            motion_cues.append(MotionCue(**c).validate())
    except (ValueError,TypeError,json.JSONDecodeError) as exc:
        raise HTTPException(400,f'Invalid motion_cues_json: {exc}')

    try:
        raw_assets=json.loads(asset_layers_json)
        if not isinstance(raw_assets,list) or len(raw_assets)>8: raise ValueError('Maximum 8 animated 3D assets')
        asset_fields=set(AssetLayer.__dataclass_fields__)
        asset_layers=[]
        for obj in raw_assets:
            if not isinstance(obj,dict) or set(obj)-asset_fields: raise ValueError('Unknown asset field')
            asset_layers.append(AssetLayer(**obj).validate())
        if asset_layers and PLANS[effective_plan].intelligent_sync_level < 3:
            raise ValueError('3D asset animation requires Creator or Studio')
        if len(assets)>8: raise ValueError('Maximum 8 uploaded GLB assets')
    except (ValueError,TypeError,json.JSONDecodeError) as exc:
        raise HTTPException(400,f'Invalid asset_layers_json: {exc}')

    try:
        raw_characters=json.loads(characters_json)
        if not isinstance(raw_characters,list) or len(raw_characters)>8: raise ValueError('Maximum eight characters')
        characters=[]
        for item in raw_characters:
            if not isinstance(item,dict) or set(item)-set(CharacterTrack.__dataclass_fields__): raise ValueError('Invalid character data')
            characters.append(CharacterTrack(**item).validate())
        raw_camera=json.loads(camera_json)
        if not isinstance(raw_camera,dict) or set(raw_camera)-set(CameraTrack.__dataclass_fields__): raise ValueError('Invalid camera')
        camera=CameraTrack(**raw_camera).validate()
        if characters and PLANS[effective_plan].intelligent_sync_level<3: raise ValueError('Character animation requires Creator or Studio')
    except (ValueError,TypeError,json.JSONDecodeError) as exc:
        raise HTTPException(400,f'Invalid character animation: {exc}')
    try:
        raw_lyrics=json.loads(lyrics_json)
        if not isinstance(raw_lyrics,list) or len(raw_lyrics)>500: raise ValueError('Maximum 500 lyric cues')
        lyric_cues=[]
        for item in raw_lyrics:
            if not isinstance(item,dict) or set(item)-set(LyricCue.__dataclass_fields__): raise ValueError('Invalid lyric fields')
            lyric_cues.append(LyricCue(**item).validate())
        if lyrics_file and lyrics_file.filename:
            extension=Path(lyrics_file.filename).suffix.lower()
            data=lyrics_file.file.read(256*1024+1)
            if len(data)>256*1024: raise ValueError('Lyric file too large')
            lyric_cues.extend(parse_lyrics(data.decode('utf8-sig'),extension))
        if len(lyric_cues)>500: raise ValueError('Maximum 500 lyric cues')
    except (ValueError,TypeError,UnicodeError,json.JSONDecodeError) as exc:
        raise HTTPException(400,f'Invalid lyric input: {exc}')

    job_id = uuid.uuid4().hex
    workspace = Path(tempfile.mkdtemp(prefix=f"beatsync_{job_id}_"))
    audio_path = save_upload(audio, workspace, "audio")
    video_paths = [save_upload(video, workspace, f"video_{i}") for i, video in enumerate(videos)]

    # Resolve uploaded GLB models and imported FBX/BVH/GLB motion assets before dispatch.
    # Never pass undefined paths into the render worker.
    try:
        if len(motion_files) > 8:
            raise ValueError("Maximum eight imported motion files")
        asset_paths = prepare_assets(asset_layers, assets, workspace)
        asset_paths.update(save_motion_uploads(motion_files, workspace))
        required = {name for character in characters
                    for name in (character.asset_id, character.animation_id) if name}
        missing = required - asset_paths.keys()
        if missing:
            raise ValueError("Missing uploaded character assets: " + ", ".join(sorted(missing)))
    except (ValueError, KeyError, TypeError) as exc:
        shutil.rmtree(workspace, ignore_errors=True)
        raise HTTPException(400, f"Invalid uploaded 3D or motion assets: {exc}") from exc

    JOBS[job_id] = {
        "id": job_id,
        "status": "queued",
        "progress": 0.0,
        "execution_mode": os.getenv("RENDER_EXECUTION_MODE", "local-thread"),
        "owner_uid": user.uid,
        "owner_email": user.email,
        "plan_key": effective_plan,
    }

    thread = threading.Thread(
        target=_render_job,
        kwargs=dict(
            job_id=job_id,
            workspace=workspace,
            audio_path=audio_path,
            video_paths=video_paths,
            plan_key=effective_plan,
            effects=effects,
            scene_aware=scene_aware,
            narrative_planning=narrative_planning,
            automatic_fx=automatic_fx,
            automatic_sound_fx=automatic_sound_fx,
            overlay_config=overlay_config,
            blender_layers=blender_layers,
            motion_cues=motion_cues,
            asset_layers=asset_layers,
            asset_paths=asset_paths,
            characters=characters,
            camera=camera,
            lyric_cues=lyric_cues,
        ),
        daemon=True,
    )
    thread.start()
    return JOBS[job_id]

@app.get("/v1/auth/me")
def auth_me(user: Principal = Depends(require_user)):
    return {
        "uid": user.uid,
        "email": user.email,
        "email_verified": user.email_verified,
        "role": user.role,
        "admin": user.admin,
        "plan": user.plan,
        "permissions": user.permissions,
    }

@app.get("/v1/renders/{job_id}")
def render_status(job_id: str, user: Principal = Depends(require_user)):
    if job_id not in JOBS:
        raise HTTPException(404, "Render job not found")
    job = JOBS[job_id]
    if not user.admin and job.get("owner_uid") != user.uid:
        raise HTTPException(403, "You do not have access to this render")
    return job

@app.get("/v1/admin/renders")
def admin_renders(_: Principal = Depends(require_admin)):
    return list(JOBS.values())

@app.delete("/v1/admin/renders/{job_id}")
def admin_delete_render(job_id: str, _: Principal = Depends(require_admin)):
    if job_id not in JOBS:
        raise HTTPException(404, "Render job not found")
    if JOBS[job_id].get("status") == "running":
        raise HTTPException(409, "Running local-thread jobs cannot be safely cancelled")
    job = JOBS.pop(job_id)
    output = job.get("output_path")
    if output:
        try:
            Path(output).unlink(missing_ok=True)
        except OSError:
            pass
    return {"id": job_id, "deleted": True}

@app.get("/v1/blender/presets")
def blender_presets():
    return [{"key":k,"family":v[0],"default_signal":v[1]} for k,v in PRESETS.items()]

@app.get("/v1/assets/animation-options")
def asset_animation_options():
    return {
        "sources": sorted(SHAPES | {"glb"}),
        "animations": sorted(ANIMATIONS),
        "signals": sorted(SIGNALS),
        "colors": sorted(COLORS),
        "upload_limit_bytes": 52428800,
    }

@app.get("/v1/characters/capabilities")
def character_capabilities():
    from beatstudio.character_providers import MixamoAdapter, HuggingFaceMotionAdapter
    return {"species":["human","quadruped","bird","other"],
            "motions":["idle","dance","walk","run","jump","spin","imported"],
            "camera_modes":["static","orbit","dolly","truck","crane","handheld","zoom_pulse"],
            "mixamo":MixamoAdapter().capability(),
            "huggingface_models":list(HuggingFaceMotionAdapter.MODELS)}

RODIN_TASK_OWNERS: dict[str,str] = {}

@app.post("/v1/rodin/generate")
def rodin_generate(prompt: str = Form(...), t_pose: bool = Form(False),
                   tier: str = Form("Regular"), user: Principal = Depends(require_user)):
    """Explicit action: Rodin submissions consume paid provider credits."""
    if not user.admin and user.plan not in {"creator","studio"}:
        raise HTTPException(403,"Rodin generation requires Creator or Studio")
    try:
        result=RodinClient().generate(prompt,t_pose=t_pose,tier=tier)
        subscription=(result.get("jobs") or {}).get("subscription_key")
        task_id=result.get("uuid")
        if subscription: RODIN_TASK_OWNERS[subscription]=user.uid
        if task_id: RODIN_TASK_OWNERS[task_id]=user.uid
        return result
    except ValueError as exc:
        raise HTTPException(400,str(exc))
    except Exception as exc:
        # Do not surface provider secret-bearing payloads to customers.
        raise HTTPException(502,"Rodin generation request failed") from exc

@app.get("/v1/rodin/status/{subscription_key}")
def rodin_status(subscription_key: str,user: Principal=Depends(require_user)):
    if not user.admin and user.plan not in {"creator","studio"}:
        raise HTTPException(403,"Rodin access restricted")
    if len(subscription_key)>256 or not subscription_key.replace("-","").replace("_","").isalnum():
        raise HTTPException(400,"Invalid task key")
    if not user.admin and RODIN_TASK_OWNERS.get(subscription_key)!=user.uid:
        raise HTTPException(403,"This Rodin task belongs to another session")
    try: return RodinClient().status(subscription_key)
    except Exception as exc: raise HTTPException(502,"Rodin status request failed") from exc

@app.get("/v1/rodin/downloads/{task_uuid}")
def rodin_download_links(task_uuid: str,user: Principal=Depends(require_user)):
    if not user.admin and user.plan not in {"creator","studio"}:
        raise HTTPException(403,"Rodin access restricted")
    try:
        import uuid as uuid_module
        uuid_module.UUID(task_uuid)
        if not user.admin and RODIN_TASK_OWNERS.get(task_uuid)!=user.uid:
            raise HTTPException(403,"This Rodin task belongs to another session")
        return RodinClient().download_links(task_uuid)
    except HTTPException: raise
    except ValueError: raise HTTPException(400,"Invalid Rodin task identifier")
    except Exception as exc: raise HTTPException(502,"Rodin download lookup failed") from exc

@app.get("/v1/lyrics/styles")
def lyric_styles():
    return {"styles":sorted(STYLES),"fonts":sorted(FONTS),"signals":["beat","onset","bass","mids","treble","energy","drop"]}

@app.post("/v1/lyrics/transcribe")
def transcribe_lyrics(audio: UploadFile = File(...),
                      language: str | None = Form(None),
                      user: Principal = Depends(require_user)):
    """Explicit opt-in transcription. For production use a durable isolated worker."""
    if not user.admin and user.plan not in {"creator","studio"}:
        raise HTTPException(403,"Automatic transcription requires Creator or Studio")
    if language and (len(language)>12 or not language.replace("-","").isalpha()):
        raise HTTPException(400,"Invalid language code")
    workspace=Path(tempfile.mkdtemp(prefix="beatsync_asr_"))
    try:
        suffix=Path(audio.filename or "").suffix.lower()
        if suffix not in {".mp3",".wav",".m4a",".ogg",".flac"}:
            raise HTTPException(400,"Unsupported audio file")
        destination=workspace/("audio"+suffix)
        with destination.open("wb") as fh:
            copied=0
            while True:
                chunk=audio.file.read(1024*1024)
                if not chunk:break
                copied+=len(chunk)
                if copied>30*1024*1024:raise HTTPException(413,"Audio exceeds 30 MB")
                fh.write(chunk)
        from beatstudio.lyrics_transcription import transcribe_local
        try:
            return transcribe_local(destination,language=language)
        except RuntimeError as exc:
            raise HTTPException(503,str(exc)) from exc
    finally:
        shutil.rmtree(workspace,ignore_errors=True)

@app.get("/v1/agents")
def list_agents(user: Principal = Depends(require_user)):
    return {"agents":list(AGENTS),"mode":"bounded-deterministic","execution":"review-before-render"}

@app.post("/v1/agents/plan")
def plan_agent_workflow(prompt: str = Form(...), duration: float = Form(30),
                        intensity: float = Form(0.7), mode: str = Form("rules"),
                        user: Principal = Depends(require_user)):
    try:
        if mode not in {"rules","ai"}:raise ValueError("Unknown planning mode")
        if mode=="ai":
            if not user.admin and user.plan not in {"creator","studio"}:
                raise HTTPException(403,"AI Director requires Creator or Studio")
            return plan_with_model(prompt,duration=duration,intensity=intensity)
        return plan_prompt(prompt,duration=duration,intensity=intensity)
    except (ValueError,TypeError) as exc:
        raise HTTPException(400,str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(503,str(exc)) from exc
