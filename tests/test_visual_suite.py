import numpy as np
import pytest
from beatstudio.visual_suite import (VisualSuite,VisualSuiteConfig,OverlayCue,neon_outline,composite_asset)
from beatstudio.motion_planner import compile_storyboard
from beatstudio.blender_bridge import BlenderSceneRequest
from beatstudio.intelligence import BeatState

def test_disabled_suite_does_not_change_frame():
    f=np.zeros((80,120,3),np.uint8)
    suite=VisualSuite(VisualSuiteConfig())
    assert np.array_equal(suite.apply(f,BeatState(t=0),0),f)

def test_outline_uses_mask_and_responds_to_beat():
    f=np.zeros((80,120,3),np.uint8)
    m=np.zeros((80,120),np.uint8);m[10:60,30:90]=255
    assert neon_outline(f,m,1,1).sum()>neon_outline(f,m,1,0).sum()
    assert np.array_equal(neon_outline(f,m,0,1),f)

def test_rgba_composite_respects_alpha():
    f=np.zeros((120,200,3),np.uint8)
    asset=np.zeros((20,20,4),np.uint8)
    assert np.array_equal(composite_asset(f,asset),f)
    asset[:,:,3]=255;asset[:,:,1]=255
    assert composite_asset(f,asset).sum()>0

def test_cue_text_and_validation():
    cues=compile_storyboard({"cues":[{"start":1,"end":3,"text":"DROP!","mode":"meme","trigger":"beat"}]})
    suite=VisualSuite(VisualSuiteConfig(cues=cues))
    f=np.zeros((120,200,3),np.uint8)
    assert np.array_equal(suite.apply(f,BeatState(t=0,beat=1),0),f)
    assert suite.apply(f,BeatState(t=2,beat=1),1).sum()>0
    with pytest.raises(ValueError):
        compile_storyboard({"cues":[{"start":2,"end":1}]})

def test_blender_job_is_data_only():
    job=BlenderSceneRequest("Neon city logo").to_mcp_job()
    assert job["sandbox_required"] is True
    assert "python" not in job
