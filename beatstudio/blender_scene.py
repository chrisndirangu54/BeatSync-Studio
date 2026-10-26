"""Secure Blender render job contract.

MCP servers vary in supported tools. This module produces a bounded scene manifest
for a trusted Blender worker/MCP adapter to consume, rather than executing arbitrary
LLM-generated Python or connecting to an unspecified MCP server.
"""
from dataclasses import dataclass, asdict
import json

@dataclass(frozen=True)
class BlenderScene:
    title: str
    duration_seconds: float = 5.0
    fps: int = 30
    style: str = "neon"
    background: str = "transparent"
    trigger: str = "drop"

    def manifest(self):
        if not self.title.strip() or len(self.title) > 160:
            raise ValueError("Title must be 1–160 characters")
        if not 0.25 <= self.duration_seconds <= 30 or not 12 <= self.fps <= 60:
            raise ValueError("Scene duration or frame rate out of bounds")
        if self.style not in {"neon","minimal","hologram","cinematic"}:
            raise ValueError("Unsupported scene style")
        if self.background not in {"transparent","black"}:
            raise ValueError("Unsupported background")
        if self.trigger not in {"beat","drop","onset","section"}:
            raise ValueError("Unsupported trigger")
        return {"schema_version":1,"engine":"blender","scene":asdict(self),
                "output":{"format":"png_sequence","alpha":self.background=="transparent"}}

    def to_json(self):
        return json.dumps(self.manifest(), indent=2)
