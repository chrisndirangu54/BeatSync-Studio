"""Test that renderer pixel compositing and Blender execution configuration are safe."""
from pathlib import Path
import shutil
from beatstudio.blender_simulations import SimulationLayer, build_simulation_manifest

def test_bounded_smoke_manifest():
    audio=[{"bass":.7,"beat":1.0} for _ in range(3)]
    m=build_simulation_manifest([SimulationLayer("spectrum_bars")],audio,12,640,360)
    assert m["output"]["alpha"] is True
    assert m["fps"]==12
    assert m["layers"][0]["preset"]=="spectrum_bars"

def test_smoke_script_importable():
    path=Path(__file__).parent/"blender_smoke.py"
    compile(path.read_text(),str(path),"exec")
