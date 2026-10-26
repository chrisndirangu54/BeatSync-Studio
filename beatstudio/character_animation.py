"""Character dance, retargeting and cinematic camera control contracts."""
from dataclasses import dataclass, asdict
from pathlib import Path

SPECIES={"human","quadruped","bird","other"}
MOTIONS={"idle","dance","walk","run","jump","spin","imported"}
CAMERAS={"static","orbit","dolly","truck","crane","handheld","zoom_pulse"}
SIGNALS={"beat","onset","bass","mids","treble","energy","drop"}

@dataclass(frozen=True)
class CharacterTrack:
    name: str = "Performer"
    species: str = "human"
    asset_id: str = ""
    animation_id: str = ""
    motion: str = "dance"
    signal: str = "beat"
    speed: float = 1.0
    intensity: float = .75
    loop: bool = True
    retarget: bool = False
    root_motion: bool = False
    position_x: float = 0.
    position_y: float = 0.
    position_z: float = 0.
    scale: float = 1.

    def validate(self):
        if not 1 <= len(self.name) <= 80: raise ValueError("Invalid name")
        if self.species not in SPECIES or self.motion not in MOTIONS: raise ValueError("Unsupported character or motion")
        if self.signal not in SIGNALS: raise ValueError("Invalid music signal")
        if not .1 <= self.speed <= 4 or not 0 <= self.intensity <= 1 or not .05 <= self.scale <= 10:
            raise ValueError("Invalid timing/intensity/scale")
        if any(not -25<=p<=25 for p in (self.position_x,self.position_y,self.position_z)):
            raise ValueError("Invalid location")
        for ref in (self.asset_id,self.animation_id):
            if ref and (not ref.replace("_","").isalnum() or len(ref)>64):
                raise ValueError("Invalid upload identifier")
        if not self.asset_id: raise ValueError("Character must reference an uploaded model")
        if self.motion=="imported" and not self.animation_id: raise ValueError("Imported motion requires an animation")
        return self

    def manifest(self):
        return asdict(self.validate())

@dataclass(frozen=True)
class CameraTrack:
    mode: str = "orbit"
    signal: str = "beat"
    speed: float = 1.
    intensity: float = .5
    distance: float = 12.
    elevation: float = 4.
    target_height: float = 1.5

    def validate(self):
        if self.mode not in CAMERAS or self.signal not in SIGNALS: raise ValueError("Unsupported camera")
        if not .1<=self.speed<=5 or not 0<=self.intensity<=1: raise ValueError("Invalid camera motion")
        if not 2<=self.distance<=40 or not -10<=self.elevation<=20 or not -10<=self.target_height<=20:
            raise ValueError("Invalid camera position")
        return self

    def manifest(self):
        return asdict(self.validate())

def character_manifest(characters, camera, samples, fps=30, width=1280, height=720):
    if not 1<=len(characters)<=8: raise ValueError("Expected 1–8 characters")
    if not 12<=fps<=60 or width not in (640,1280,1920,3840) or height not in (360,720,1080,2160):
        raise ValueError("Invalid export")
    if not 1<=len(samples)<=36000: raise ValueError("Invalid timeline")
    return {"schema_version":1,"characters":[x.manifest() for x in characters],
            "camera":camera.manifest(),"audio_samples":samples,
            "fps":fps,"width":width,"height":height}
