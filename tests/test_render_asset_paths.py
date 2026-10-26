import io
import struct
from pathlib import Path
from types import SimpleNamespace
from beatstudio.asset_animation import prepare_assets
from beatstudio.motion_import import save_motion_uploads

def test_asset_upload_paths(tmp_path):
    blob=b"glTF"+struct.pack("<II",2,24)+b"0"*12
    upload=SimpleNamespace(filename="character.glb",file=io.BytesIO(blob))
    paths=prepare_assets([], [upload], tmp_path)
    assert Path(paths["asset_0"]).is_file()
    assert Path(paths["asset_0"]).parent.name=="assets"

def test_motion_upload_paths(tmp_path):
    upload=SimpleNamespace(filename="walk.bvh",file=io.BytesIO(b"HIERARCHY\nROOT Hips\n"+b" "*120))
    paths=save_motion_uploads([upload],tmp_path)
    assert Path(paths["motion_0"]).is_file()
    assert Path(paths["motion_0"]).parent.name=="motions"

def test_render_api_resolves_asset_paths():
    from pathlib import Path
    src=(Path(__file__).resolve().parents[1]/"apps"/"api"/"main.py").read_text()
    assert "asset_paths = prepare_assets(asset_layers, assets, workspace)" in src
    assert "asset_paths.update(save_motion_uploads(motion_files, workspace))" in src
