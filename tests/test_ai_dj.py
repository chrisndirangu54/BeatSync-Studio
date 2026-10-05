from beatstudio.ai_dj import AudioCompatibility, TrackFeatures

def test_identical_tracks_score_high():
    a=TrackFeatures(120,0,.5,.5,180)
    assert AudioCompatibility.score(a,a)>.99

def test_half_time_bpm_is_compatible():
    a=TrackFeatures(120,0,.5,.5,180)
    b=TrackFeatures(60,0,.5,.5,180)
    assert AudioCompatibility.score(a,b)>.90
