import io
import struct
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from beatstudio.asset_animation import AssetLayer, prepare_assets

class AssetAnimationTests(unittest.TestCase):
    def test_builtin_layer(self):
        m=AssetLayer(source="torus",signal="bass",animation="pulse").manifest()
        self.assertEqual(m["animation"],"pulse")
    def test_reject_invalid(self):
        for layer in (AssetLayer(source="../file"),AssetLayer(animation="exec"),
                      AssetLayer(source="glb",asset_id="../../unsafe"),
                      AssetLayer(position_x=100)):
            with self.assertRaises(ValueError): layer.validate()
    def test_glb_upload_mapping(self):
        # Lightweight valid header, not a geometry-valid GLB; Blender validates contents.
        data=b"glTF"+struct.pack("<II",2,20)+b"12345678"
        fake=SimpleNamespace(file=io.BytesIO(data))
        with tempfile.TemporaryDirectory() as td:
            paths=prepare_assets([AssetLayer(source="glb",asset_id="asset_0")],[fake],td)
            self.assertTrue(Path(paths["asset_0"]).is_file())
    def test_reject_upload(self):
        fake=SimpleNamespace(file=io.BytesIO(b"not-a-model"))
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError): prepare_assets([],[fake],td)

if __name__=="__main__": unittest.main()
