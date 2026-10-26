"""Offline rigged motion import (FBX/BVH/GLB) and isolated conversion adapter.

FBX/BVH conversion is performed only by pre-approved Blender worker script.
Never upload a script, .blend file, or arbitrary archive as an animation asset.
"""
from pathlib import Path
import re
import struct
SUPPORTED={".glb",".fbx",".bvh"}
def validate_motion_upload(data: bytes, suffix: str):
    suffix=suffix.lower()
    if suffix not in SUPPORTED or not 100 <= len(data) <= 50*1024*1024:
        raise ValueError("Unsupported or oversized motion file")
    if suffix==".glb":
        if data[:4]!=b"glTF" or struct.unpack("<II",data[4:12])!=(2,len(data)):
            raise ValueError("Invalid GLB")
    elif suffix==".fbx":
        if not data.startswith(b"Kaydara FBX Binary  "):
            raise ValueError("Only binary FBX is supported")
    elif suffix==".bvh":
        head=data[:4096].decode("utf8","replace")
        if not re.search(r"(?m)^HIERARCHY\s*$",head) or "ROOT " not in head:
            raise ValueError("Invalid BVH hierarchy")
    return True

def save_motion_uploads(uploads,workspace):
    folder=Path(workspace)/"motions"
    folder.mkdir(exist_ok=True)
    paths={}
    for i,upload in enumerate(uploads):
        extension=Path(upload.filename or "").suffix.lower()
        data=upload.file.read(50*1024*1024+1)
        validate_motion_upload(data,extension)
        token=f"motion_{i}"
        path=folder/(token+extension)
        path.write_bytes(data)
        paths[token]=str(path)
    return paths
