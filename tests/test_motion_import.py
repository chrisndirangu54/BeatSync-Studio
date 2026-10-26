import io
import struct
import tempfile
import unittest
from types import SimpleNamespace
from beatstudio.motion_import import validate_motion_upload,save_motion_uploads
class MotionImportTests(unittest.TestCase):
    def test_bvh_validation(self):
        data=b"HIERARCHY\nROOT Hips\n"+b" "*110
        self.assertTrue(validate_motion_upload(data,".bvh"))
    def test_binary_fbx(self):
        data=b"Kaydara FBX Binary  "+b" "*120
        self.assertTrue(validate_motion_upload(data,".fbx"))
    def test_bad_type(self):
        with self.assertRaises(ValueError):validate_motion_upload(b" "*140,".blend")
    def test_project_scoped(self):
        upload=SimpleNamespace(filename="dance.bvh",file=io.BytesIO(b"HIERARCHY\nROOT Hips\n"+b" "*110))
        with tempfile.TemporaryDirectory() as td:
            paths=save_motion_uploads([upload],td)
            self.assertIn("motion_0",paths)
            self.assertTrue(paths["motion_0"].endswith("motion_0.bvh"))
if __name__=="__main__":unittest.main()
