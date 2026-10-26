import unittest
from beatstudio.lyrics import LyricCue
from beatstudio.lyrics_transcription import words_to_cues
class WordLyricsTests(unittest.TestCase):
    def test_word_timing(self):
        cues=words_to_cues([{"words":[{"word":"Hello","start":1.0,"end":1.3},{"word":"world","start":1.4,"end":1.8}]}])
        self.assertEqual(cues[0].text,"Hello world")
        self.assertEqual(len(cues[0].words),2)
        self.assertEqual(cues[0].start,1.)
    def test_invalid_word_bounds(self):
        with self.assertRaises(ValueError):
            LyricCue("bad",1,2,words=(("bad",0,3),)).validate()
    def test_group_split(self):
        cues=words_to_cues([{"words":[{"word":str(i),"start":i,"end":i+.5} for i in range(8)]}])
        self.assertGreater(len(cues),1)
if __name__=="__main__":unittest.main()
