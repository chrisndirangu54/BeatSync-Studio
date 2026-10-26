import unittest
from types import SimpleNamespace
import numpy as np
from beatstudio.reactive_overlays import OverlayConfig, ReactiveOverlayEngine, composite
from beatstudio.blender_scene import BlenderScene

class OverlayTests(unittest.TestCase):
    def test_disabled_pipeline_is_identity(self):
        eng=ReactiveOverlayEngine(OverlayConfig())
        frame=np.zeros((80,120,3),np.uint8)
        state=SimpleNamespace(beat=1.0)
        self.assertTrue(np.array_equal(eng.apply(frame,state,0),frame))
        eng.close()

    def test_rgba_composite_preserves_outside(self):
        frame=np.zeros((100,120,3),np.uint8)
        layer=np.zeros((20,20,4),np.uint8)
        layer[:,:,:3]=255
        layer[:,:,3]=255
        out=composite(frame,layer,1)
        self.assertGreater(out.sum(),0)
        self.assertEqual(int(out[0,0].sum()),0)

    def test_invalid_trigger(self):
        with self.assertRaises(ValueError):
            ReactiveOverlayEngine(OverlayConfig(trigger="script"))

    def test_blender_manifest(self):
        obj=BlenderScene("EXPLAINER")
        self.assertEqual(obj.manifest()["engine"],"blender")
        with self.assertRaises(ValueError):
            BlenderScene("x",duration_seconds=100).manifest()

if __name__=="__main__":
    unittest.main()
