from beatstudio.lyrics_transcription import words_to_cues
import pytest

def test_word_group_limits():
    with pytest.raises(ValueError):
        words_to_cues([],max_words=0)
    with pytest.raises(ValueError):
        words_to_cues([],max_duration=0.1)

def test_group_words_and_boundaries():
    segments=[{"words":[{"word":"One","start":1.0,"end":1.2},
                         {"word":"two","start":1.3,"end":1.6},
                         {"word":"three","start":2.5,"end":2.9}]}]
    cues=words_to_cues(segments)
    assert len(cues)==2
    assert cues[0].words[0][0]=="One"
    assert cues[1].text=="three"
