"""Declarative music-reactive 3D asset layer.

Supports built-in shapes or an uploaded GLB file copied to render workspace.
No arbitrary Python, Blender files, external URLs or unsafe archive imports.
"""
from dataclasses import dataclass, asdict
from pathlib import Path

SIGNALS={"beat","onset","bass","mids","treble","energy","drop"}
ANIMATIONS={"pulse","spin","bounce","orbit","wobble","scale","material_glow"}
SHAPES={"cube","sphere","torus","cone","icosphere","text"}
COLORS={"cyan","magenta","blue","lime"}

@dataclass(frozen=True)
class AssetLayer:
    name: str = "3D Asset"
    source: str = "sphere"
    asset_id: str = ""
    animation: str = "pulse"
    signal: str = "bass"
    intensity: float = .75
    color: str = "cyan"
    position_x: float = 0.
    position_y: float = 0.
    position_z: float = 0.
    size: float = 1.
    speed: float = 1.
    enabled: bool = True

    def validate(self):
        if not isinstance(self.name,str) or not 1<=len(self.name)<=80: raise ValueError("Invalid asset name")
        if self.source not in SHAPES|{"glb"}: raise ValueError("Unsupported asset source")
        if self.animation not in ANIMATIONS or self.signal not in SIGNALS: raise ValueError("Invalid animation/signal")
        if self.color not in COLORS: raise ValueError("Unknown neon color")
        if not 0<=self.intensity<=1 or not .1<=self.size<=5 or not .1<=self.speed<=5: raise ValueError("Invalid asset settings")
        if any(not -10<=v<=10 for v in (self.position_x,self.position_y,self.position_z)): raise ValueError("Invalid position")
        if self.source=="glb" and (not self.asset_id or "/" in self.asset_id or "\\" in self.asset_id):
            raise ValueError("GLB asset must reference an uploaded asset ID")
        return self

    def manifest(self):
        self.validate()
        return asdict(self)

def prepare_assets(layers, uploads, workspace):
    """Resolve trusted upload IDs to local GLB files; perform basic size/header checks."""
    folder=Path(workspace)/"assets"
    folder.mkdir(exist_ok=True)
    resolved={}
    for i,upload in enumerate(uploads):
        data=upload.file.read(50*1024*1024+1)
        if len(data)>50*1024*1024 or len(data)<20 or data[:4]!=b"glTF":
            raise ValueError("3D assets must be valid-sized binary glTF (.glb) files")
        import struct
        version, length=struct.unpack("<II",data[4:12])
        if version!=2 or length!=len(data): raise ValueError("Invalid GLB header")
        identifier=f"asset_{i}"
        target=folder/f"{identifier}.glb"
        target.write_bytes(data)
        resolved[identifier]=str(target)
    for layer in layers:
        if layer.source=="glb" and layer.asset_id not in resolved:
            raise ValueError(f"No uploaded GLB for {layer.asset_id}")
    return resolved
