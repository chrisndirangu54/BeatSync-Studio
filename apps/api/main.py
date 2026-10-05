from __future__ import annotations

import json
import os
import shutil
import tempfile
import threading
import uuid
from pathlib import Path
from typing import List

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from beatstudio.director import DirectorConfig, MultiClipDirector
from beatstudio.effects import SPECS
from beatstudio.narrative import NarrativePlanner
from beatstudio.plans import PLANS
from beatstudio.renderer import VideoRenderer

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
def narrative_plan(audio: UploadFile = File(...), intelligence_level: int = Form(3)):
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
):
    if plan_key not in PLANS:
        raise HTTPException(400, "Unknown plan")
    if not videos:
        raise HTTPException(400, "At least one video is required")

    try:
        effects = {str(k): float(v) for k, v in json.loads(effects_json).items()}
    except Exception as exc:
        raise HTTPException(400, f"Invalid effects_json: {exc}")

    job_id = uuid.uuid4().hex
    workspace = Path(tempfile.mkdtemp(prefix=f"beatsync_{job_id}_"))
    audio_path = save_upload(audio, workspace, "audio")
    video_paths = [save_upload(video, workspace, f"video_{i}") for i, video in enumerate(videos)]

    JOBS[job_id] = {
        "id": job_id,
        "status": "queued",
        "progress": 0.0,
        "execution_mode": os.getenv("RENDER_EXECUTION_MODE", "local-thread"),
    }

    thread = threading.Thread(
        target=_render_job,
        kwargs=dict(
            job_id=job_id,
            workspace=workspace,
            audio_path=audio_path,
            video_paths=video_paths,
            plan_key=plan_key,
            effects=effects,
            scene_aware=scene_aware,
            narrative_planning=narrative_planning,
            automatic_fx=automatic_fx,
            automatic_sound_fx=automatic_sound_fx,
        ),
        daemon=True,
    )
    thread.start()
    return JOBS[job_id]

@app.get("/v1/renders/{job_id}")
def render_status(job_id: str):
    if job_id not in JOBS:
        raise HTTPException(404, "Render job not found")
    return JOBS[job_id]
