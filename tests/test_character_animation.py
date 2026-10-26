import unittest
from beatstudio.character_animation import CharacterTrack,CameraTrack,character_manifest
from beatstudio.character_providers import MixamoAdapter,HuggingFaceMotionAdapter
class CharacterTests(unittest.TestCase):
    def test_independent_tracks(self):
        a=CharacterTrack(asset_id="asset_0",species="human",motion="dance",signal="bass")
        b=CharacterTrack(asset_id="asset_1",species="quadruped",motion="walk",signal="onset")
        m=character_manifest([a,b],CameraTrack(mode="orbit"),[{"bass":.5}],30,1280,720)
        self.assertEqual(len(m["characters"]),2)
    def test_untrusted_ids(self):
        with self.assertRaises(ValueError): CharacterTrack(asset_id="../../etc").validate()
    def test_motion_requires_file(self):
        with self.assertRaises(ValueError): CharacterTrack(asset_id="asset_0",motion="imported").validate()
    def test_mixamo_not_public_api(self):
        self.assertFalse(MixamoAdapter().capability()["public_api_verified"])
        self.assertEqual(HuggingFaceMotionAdapter("nvidia/Kimodo-SOMA-RP-v1.2").capability()["execution"],"external-model-worker-required")
if __name__=="__main__": unittest.main()
