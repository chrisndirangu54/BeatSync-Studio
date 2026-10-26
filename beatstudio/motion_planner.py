"""Deterministic timeline compiler for AI-authored explainer and reactive media cues."""
from __future__ import annotations
import json
from .visual_suite import OverlayCue

def compile_storyboard(data: dict) -> list[OverlayCue]:
    """Accept a validated storyboard from an AI director; never execute model-generated code."""
    if not isinstance(data, dict) or not isinstance(data.get("cues", []), list):
        raise ValueError("Storyboard must contain a cues list")
    cues=[]
    for item in data.get("cues", []):
        if not isinstance(item, dict):
            raise ValueError("Each cue must be an object")
        cues.append(OverlayCue(
            start=float(item["start"]), end=float(item["end"]),
            text=str(item.get("text",""))[:144], asset=str(item.get("asset","")),
            mode=str(item.get("mode","caption")), trigger=str(item.get("trigger","energy")),
            threshold=float(item.get("threshold",0.0)),
        ))
    return sorted(cues,key=lambda x:x.start)

def load_storyboard(path: str) -> list[OverlayCue]:
    with open(path, encoding="utf-8") as f:
        return compile_storyboard(json.load(f))
