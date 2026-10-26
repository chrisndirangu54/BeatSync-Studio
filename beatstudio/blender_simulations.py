"""Independent beat-driven Blender simulation presets and bounded render manifests."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Mapping
import json

PRESETS = {
    "neon_particles": ("particles", "treble"),
    "particle_vortex": ("particles", "bass"),
    "neon_fireworks": ("particles", "onset"),
    "spectrum_bars": ("visualizer", "bass"),
    "radial_spectrum": ("visualizer", "beat"),
    "wave_tunnel": ("visualizer", "mids"),
    "oscilloscope": ("visualizer", "mids"),
    "audio_terrain": ("visualizer", "energy"),
    "liquid_ribbons": ("procedural_fluid", "bass"),
    "ink_mixing": ("liquid_sim", "energy"),
    "dual_smoke_mix": ("gas_sim", "bass"),
    "smoke_vortex": ("gas_sim", "drop"),
    "mushroom_cloud": ("gas_sim", "drop"),
    "fire_burst": ("gas_sim", "onset"),
    "reactive_metal": ("material", "mids"),
    "neon_displacement": ("material", "treble"),
    "shockwave": ("geometry", "drop"),
}
SIGNALS = {"beat", "onset", "bass", "mids", "treble", "energy", "drop"}
PALETTE = {"cyan": [0.0,1.0,1.0,1.0], "magenta":[1.0,0.06,0.75,1.0],
           "blue":[0.04,0.2,1.0,1.0], "lime":[0.35,1.0,0.12,1.0]}

@dataclass(frozen=True)
class SimulationLayer:
    preset: str
    enabled: bool = True
    signal: str = ""
    intensity: float = 0.8
    color_a: str = "cyan"
    color_b: str = "magenta"
    seed: int = 42
    quality: str = "preview"

    def validate(self):
        if self.preset not in PRESETS: raise ValueError("Unsupported simulation preset")
        if (self.signal or PRESETS[self.preset][1]) not in SIGNALS: raise ValueError("Invalid audio signal")
        if self.color_a not in PALETTE or self.color_b not in PALETTE: raise ValueError("Unknown color")
        if not 0 <= self.intensity <= 1: raise ValueError("Invalid intensity")
        if self.quality not in {"preview","final"}: raise ValueError("Invalid quality")
        if not 0 <= self.seed <= 2**31-1: raise ValueError("Invalid seed")
        return self

    def manifest(self):
        self.validate()
        return {**asdict(self), "family": PRESETS[self.preset][0],
                "signal": self.signal or PRESETS[self.preset][1],
                "palette": [PALETTE[self.color_a], PALETTE[self.color_b]]}

def samples_from_sync(sync, fps: int, duration: float):
    """Samples BeatSync's existing analysis rather than running another beat detector."""
    if not 12 <= fps <= 60 or not .25 <= duration <= 600: raise ValueError("Invalid timeline")
    keys = ("beat","onset","bass","mids","treble","energy","drop")
    return [{k:round(max(0.0,min(1.0,float(getattr(s,k,0)))),5) for k in keys}
            for i in range(int(fps*duration)) for s in (sync.state(i/fps),)]

def build_simulation_manifest(layers, audio_samples, fps=30, width=1920, height=1080):
    if not 1 <= len(layers) <= 12: raise ValueError("Require 1–12 layers")
    if not 12 <= fps <= 60 or width not in {640,1280,1920,3840} or height not in {360,720,1080,2160}:
        raise ValueError("Invalid render parameters")
    if len(audio_samples) > 36000: raise ValueError("Timeline too long")
    for row in audio_samples:
        if set(row) - SIGNALS or any(not isinstance(v,(int,float)) or not 0 <= v <= 1 for v in row.values()):
            raise ValueError("Invalid signal samples")
    return {"schema_version": 1, "engine": "blender",
            "fps":fps,"width":width,"height":height,
            "layers":[x.manifest() for x in layers if x.enabled],
            "audio_samples":audio_samples,
            "output":{"format":"png_sequence","alpha":True}}

def save_manifest(path, manifest):
    from pathlib import Path
    Path(path).write_text(json.dumps(manifest,indent=2),encoding="utf8")
