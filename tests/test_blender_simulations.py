import unittest
from types import SimpleNamespace
from beatstudio.blender_simulations import PRESETS, SimulationLayer, build_simulation_manifest, samples_from_sync

class SimulationTests(unittest.TestCase):
    def test_catalog(self):
        self.assertGreaterEqual(len(PRESETS),15)
        self.assertEqual(SimulationLayer("dual_smoke_mix").manifest()["family"],"gas_sim")
    def test_independent_layers(self):
        data=build_simulation_manifest([SimulationLayer("neon_particles"),
               SimulationLayer("spectrum_bars",signal="treble",enabled=False)], [{"bass":.5}])
        self.assertEqual(len(data["layers"]),1)
        self.assertEqual(data["layers"][0]["signal"],"treble")
    def test_clamped_audio_curve(self):
        sync=SimpleNamespace(state=lambda t:SimpleNamespace(bass=0.6,beat=1.2))
        rows=samples_from_sync(sync,12,.5)
        self.assertEqual(len(rows),6)
        self.assertEqual(rows[0]["beat"],1)
    def test_reject_invalid(self):
        with self.assertRaises(ValueError): SimulationLayer("unknown").manifest()
        with self.assertRaises(ValueError): build_simulation_manifest([SimulationLayer("neon_particles")],[{"bass":-1}])
if __name__=="__main__": unittest.main()
