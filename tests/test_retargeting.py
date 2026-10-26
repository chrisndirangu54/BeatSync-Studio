import unittest
from beatstudio.retargeting import infer_mapping,RetargetSpec,dance_timing
class RetargetTests(unittest.TestCase):
    def test_mixamo_correspondence(self):
        m=infer_mapping(["mixamorig:Hips","mixamorig:Spine","mixamorig:Neck","mixamorig:Head"],
                        ["Hips","Spine","Neck","Head"])
        self.assertEqual(m["mixamorig:Hips"],"Hips")
    def test_dance_grid(self):
        times=dance_timing([],bpm=120,speed=1.2,duration=2)
        self.assertEqual(times[1]["t"],.5)
        self.assertTrue(times[0]["accent"])
    def test_mapping_unique(self):
        with self.assertRaises(ValueError):
            RetargetSpec(mapping=(("a","x"),("b","x"))).validate()
if __name__=="__main__":unittest.main()
