"""Blender MCP-compatible render job specification; no arbitrary code execution."""
from __future__ import annotations
from dataclasses import dataclass
import json

@dataclass(frozen=True)
class BlenderSceneRequest:
    prompt: str
    duration_s: float = 8.0
    fps: int = 30
    width: int = 1920
    height: int = 1080
    palette: tuple[str,...] = ("#14f1ff", "#f028ff", "#3cffde")
    def __post_init__(self):
        if not self.prompt.strip() or len(self.prompt)>4000:
            raise ValueError("Prompt required (max 4000 chars)")
        if not .1 <= self.duration_s <= 120 or not 1 <= self.fps <= 120:
            raise ValueError("Invalid render timing")
        if not 64 <= self.width <= 7680 or not 64 <= self.height <= 4320:
            raise ValueError("Invalid dimensions")
    def to_mcp_job(self) -> dict:
        return {"kind":"blender_scene","prompt":self.prompt,"duration_s":self.duration_s,
                "fps":self.fps,"resolution":[self.width,self.height],"palette":list(self.palette),
                "output":"transparent_png_sequence","sandbox_required":True}
    def to_json(self)->str:
        return json.dumps(self.to_mcp_job(),indent=2)
