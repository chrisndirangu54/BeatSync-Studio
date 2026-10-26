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
