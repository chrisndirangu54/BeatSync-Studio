"""Media Cloud authenticated handoff inbox. No rendering or cross-tenant access implied."""
from __future__ import annotations
import hashlib
import hmac
import json
import os
import sqlite3
import time
from pathlib import Path

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/v1/integrations/media-cloud", tags=["Media Cloud"])
MAX_SKEW = 300

class Handoff(BaseModel):
    handoff_id: str = Field(min_length=12, max_length=128)
    tenant_id: str = Field(min_length=1, max_length=128)
    campaign_id: str = Field(min_length=1, max_length=128)
    project_id: str = Field(min_length=1, max_length=128)
    output_preset: str

def _canonical(payload: dict) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()

def _db():
    filename = os.environ.get("BEATSYNC_BRIDGE_DB", "/tmp/beatsync-media-bridge.sqlite")
    Path(filename).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(filename)
    conn.execute("""CREATE TABLE IF NOT EXISTS bridge_requests(
        id TEXT PRIMARY KEY, tenant TEXT NOT NULL, project TEXT NOT NULL,
        status TEXT NOT NULL, created INTEGER NOT NULL)""")
    return conn

@router.post("/handoffs", status_code=202)
async def receive_handoff(
    request: Request,
    x_bridge_timestamp: str = Header(default=""),
    x_bridge_signature: str = Header(default=""),
):
    secret = os.getenv("BEATSYNC_BRIDGE_SECRET", "")
    if not secret:
        raise HTTPException(503, "Media Cloud bridge disabled")
    try:
        timestamp = int(x_bridge_timestamp)
    except ValueError:
        raise HTTPException(401, "Invalid signature")
    if abs(int(time.time()) - timestamp) > MAX_SKEW:
        raise HTTPException(401, "Expired signature")
    body = await request.body()
    if len(body) > 16384:
        raise HTTPException(413, "Payload too large")
    try:
        payload = json.loads(body)
        handoff = Handoff.model_validate(payload)
    except Exception:
        raise HTTPException(422, "Invalid handoff payload")
    expected = hmac.new(secret.encode(), str(timestamp).encode() + b"." + _canonical(payload), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, x_bridge_signature):
        raise HTTPException(401, "Invalid signature")
    if handoff.output_preset not in {"vertical_1080p", "square_1080p", "landscape_1080p"}:
        raise HTTPException(422, "Invalid output preset")
    allowed = {s.strip() for s in os.getenv("BEATSYNC_MEDIA_ALLOWED_TENANTS", "").split(",") if s.strip()}
    if handoff.tenant_id not in allowed:
        raise HTTPException(403, "Tenant not authorized for bridge")
    with _db() as db:
        existing = db.execute("SELECT tenant,project FROM bridge_requests WHERE id=?", (handoff.handoff_id,)).fetchone()
        if existing and existing != (handoff.tenant_id, handoff.project_id):
            raise HTTPException(409, "Handoff ID conflict")
        db.execute("INSERT OR IGNORE INTO bridge_requests(id,tenant,project,status,created) VALUES (?,?,?,?,?)",
                   (handoff.handoff_id, handoff.tenant_id, handoff.project_id, "awaiting_media", int(time.time())))
    return {"status": "accepted", "job_id": handoff.handoff_id,
            "next_step": "Authorized BeatSync account must attach licensed media and start rendering."}
