"""Restricted Blender batch execution with no user-generated scripts.

Deploy in isolated CPU/GPU workers with resource quotas and no outbound network.
The local runner is opt-in and deliberately not exposed in the HTTP API.
"""
from __future__ import annotations
import json, os, shutil, subprocess, tempfile
from pathlib import Path
from .blender_simulations import build_simulation_manifest, SimulationLayer

def render_blender_layers(layers: list[SimulationLayer], audio_samples: list[dict],
                          output_dir: str, *, fps=30, width=1280, height=720,
                          blender_binary="blender", timeout_seconds=900):
    if not 30 <= timeout_seconds <= 7200:
        raise ValueError("Invalid worker timeout")
    output=Path(output_dir).resolve();output.mkdir(parents=True,exist_ok=True)
    if not shutil.which(blender_binary):
        raise RuntimeError("Blender executable is not installed on worker")
    scripts=Path(__file__).resolve().parents[1]/"scripts"
    manifest=build_simulation_manifest(layers,audio_samples,fps,width,height)
    generated=[]
    for index,layer in enumerate(manifest["layers"]):
        layer_dir=output/("layer_%02d"%index);layer_dir.mkdir(exist_ok=True)
        selected={**manifest,"layers":[layer]}
        file=layer_dir/"manifest.json";file.write_text(json.dumps(selected),encoding="utf8")
        script="blender_physics_worker.py" if layer["family"] in {"gas_sim","liquid_sim"} else "blender_simulation_worker.py"
        cmd=[blender_binary,"-b","-t","4","--python",str(scripts/script),"--",str(file),str(layer_dir)]
        try:
            process=subprocess.run(cmd,check=True,capture_output=True,text=True,timeout=timeout_seconds,
                                   env={k:v for k,v in os.environ.items() if not k.startswith(("AWS_","GOOGLE_","SUNO_","BYTEPLUS_"))})
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("Blender rendering timed out") from exc
        except subprocess.CalledProcessError as exc:
            raise RuntimeError("Blender rendering failed: "+(exc.stderr or exc.stdout)[-2000:]) from exc
        if not list(layer_dir.glob("frame_*.png")):
            raise RuntimeError("Blender worker exited without frames")
        generated.append(layer_dir)
    return generated

def render_asset_layers(layers, asset_paths, audio_samples, output_dir, *,
                        fps=30, width=1280, height=720, blender_binary="blender",
                        timeout_seconds=900):
    """Render reviewed asset specifications in isolated Blender process."""
    from .asset_animation import AssetLayer
    if not 1 <= len(layers) <= 8:
        raise ValueError("Expected 1–8 3D asset layers")
    for layer in layers: layer.validate()
    if not shutil.which(blender_binary):
        raise RuntimeError("Blender executable is not installed on worker")
    if not 30 <= timeout_seconds <= 7200:
        raise ValueError("Invalid worker timeout")
    output=Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    manifest=build_simulation_manifest([SimulationLayer("neon_particles")],
                                       audio_samples,fps,width,height)
    assets=[layer.manifest() for layer in layers if layer.enabled]
    if not assets: return []
    root=Path(next(iter(asset_paths.values()))).resolve().parent if asset_paths else output.resolve()
    safe_paths={}
    for layer in assets:
        if layer["source"]=="glb":
            asset=Path(asset_paths[layer["asset_id"]]).resolve()
            if root not in asset.parents or not asset.is_file():
                raise ValueError("Asset is outside project upload directory")
            safe_paths[layer["asset_id"]]=str(asset)
    manifest["assets"]=assets
    manifest["asset_paths"]=safe_paths
    manifest["asset_root"]=str(root)
    path=output/"asset_manifest.json"
    path.write_text(json.dumps(manifest),encoding="utf8")
    script=Path(__file__).resolve().parents[1]/"scripts"/"blender_asset_worker.py"
    command=[blender_binary,"-b","-t","4","--python",str(script),"--",str(path),str(output)]
    try:
        subprocess.run(command,check=True,capture_output=True,text=True,timeout=timeout_seconds,
                       env={k:v for k,v in os.environ.items() if not k.startswith(("AWS_","GOOGLE_","SUNO_","BYTEPLUS_"))})
    except subprocess.CalledProcessError as exc:
        raise RuntimeError("Asset render failed: "+(exc.stderr or exc.stdout)[-2000:]) from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("Asset render timed out") from exc
    if not list(output.glob("frame_*.png")):
        raise RuntimeError("Blender did not generate asset frames")
    return [output]
