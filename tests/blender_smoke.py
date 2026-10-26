"""Blender end-to-end integration smoke test using generated procedural assets."""
import json, math, subprocess, sys, tempfile
from pathlib import Path
import cv2
from beatstudio.blender_simulations import SimulationLayer, build_simulation_manifest
from beatstudio.blender_worker import render_blender_layers, render_asset_layers, render_character_layers
from beatstudio.asset_animation import AssetLayer
from beatstudio.character_animation import CharacterTrack, CameraTrack

def assert_pngs(folder):
    paths=sorted(Path(folder).glob("frame_*.png"))
    if len(paths)!=3: raise AssertionError(f"Expected 3 frames, got {len(paths)}")
    for path in paths:
        frame=cv2.imread(str(path),cv2.IMREAD_UNCHANGED)
        if frame is None or frame.shape[2]!=4:raise AssertionError("No RGBA output")

def run():
    samples=[{"beat":i/2,"bass":.6,"mids":.3,"treble":.5,"onset":.5,"energy":.5,"drop":.2} for i in range(3)]
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)
        rendered=render_blender_layers([SimulationLayer("spectrum_bars")],samples,
                     str(root/"procedural"),fps=12,width=640,height=360,timeout_seconds=180)
        assert_pngs(rendered[0])
        rendered=render_asset_layers([AssetLayer(source="torus")],{},samples,
                     str(root/"asset_render"),fps=12,width=640,height=360,timeout_seconds=180)
        assert_pngs(rendered[0])
        # Model fixture generated using Blender itself; validates GLB import and camera pipeline.
        directory=root/"assets";directory.mkdir()
        fixture=root/"create_glb.py"
        fixture.write_text("""
import bpy
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.mesh.primitive_uv_sphere_add()
bpy.ops.export_scene.gltf(filepath=r'%s', export_format='GLB')
""" % str(directory/"asset_0.glb"))
        subprocess.run(["blender","-b","--python",str(fixture)],check=True,timeout=120,
                       stdout=subprocess.DEVNULL)
        rendered=render_character_layers([CharacterTrack(asset_id="asset_0")],
                        CameraTrack(),{"asset_0":str(directory/"asset_0.glb")},
                        samples,str(root/"character_render"),fps=12,width=640,height=360)
        assert_pngs(rendered[0])
    print("Blender integration smoke tests passed")

if __name__=="__main__":run()
