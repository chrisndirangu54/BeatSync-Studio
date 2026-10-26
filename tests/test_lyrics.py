import unittest
from types import SimpleNamespace
import numpy as np
from beatstudio.lyrics import LyricCue,parse_lrc,parse_srt
from beatstudio.lyric_renderer import LyricRenderer
class LyricTests(unittest.TestCase):
    def test_lrc(self):
        cues=parse_lrc("[00:01.50]Hello\n[00:03.00]World")
        self.assertEqual(len(cues),2)
        self.assertEqual(cues[0].end,3)
    def test_srt(self):
        cues=parse_srt("1\n00:00:01,000 --> 00:00:02,500\nHello world\n")
        self.assertEqual((cues[0].start,cues[0].end),(1,2.5))
    def test_invalid_color(self):
        with self.assertRaises(ValueError):LyricCue("A",0,1,color="javascript:1").validate()
    def test_render(self):
        frame=np.zeros((240,426,3),dtype=np.uint8)
        renderer=LyricRenderer([LyricCue("BeatSync Neon",0,2)])
        idle=renderer.apply(frame,SimpleNamespace(t=4,beat=.5))
        self.assertTrue(np.array_equal(frame,idle))
        active=renderer.apply(frame,SimpleNamespace(t=1,beat=.8))
        self.assertGreater(active.sum(),0)
if __name__=="__main__":unittest.main()
