import math
import pytest
from beatstudio.blender_simulations import SimulationLayer, build_simulation_manifest

@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -0.1, 1.01])
def test_reject_bad_intensity(bad):
    with pytest.raises(ValueError):
        SimulationLayer("spectrum_bars",intensity=bad).validate()

def test_reject_empty_timeline():
    with pytest.raises(ValueError):
        build_simulation_manifest([SimulationLayer("spectrum_bars")],[],12,640,360)

@pytest.mark.parametrize("bad", [float("nan"),float("inf"),-1,1.5])
def test_reject_invalid_signal(bad):
    with pytest.raises(ValueError):
        build_simulation_manifest([SimulationLayer("spectrum_bars")],[{"bass":bad}],12,640,360)
