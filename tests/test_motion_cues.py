import unittest
from types import SimpleNamespace
import numpy as np
from beatstudio.motion_cues import MotionCue,CueRenderer

class MotionCueTests(unittest.TestCase):
    def test_neutral_when_not_active(self):
        image=np.zeros((200,360,3),dtype=np.uint8)
        cue=CueRenderer([MotionCue("TEST",start=10)])
        result=cue.apply(image,SimpleNamespace(t=0,beat=1))
        self.assertTrue(np.array_equal(result,image))
    def test_explainer_draws(self):
        image=np.zeros((240,400,3),dtype=np.uint8)
        cue=CueRenderer([MotionCue("BEAT SYNC",start=0,duration=2)])
        result=cue.apply(image,SimpleNamespace(t=1,beat=.9))
        self.assertGreater(result.sum(),0)
    def test_reject_invalid(self):
        with self.assertRaises(ValueError): MotionCue("",0).validate()
        with self.assertRaises(ValueError): MotionCue("hey",0,style="exec").validate()
if __name__=="__main__": unittest.main()
