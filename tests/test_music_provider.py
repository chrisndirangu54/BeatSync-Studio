from beatstudio.music_provider import SunoClient


def test_suno_result_normalization():
    result = SunoClient._normalize({
        "data": {
            "jobId": "job-123",
            "track": {"audioUrl": "https://example.test/song.mp3", "trackId": "track-9"},
        }
    })
    assert result.provider == "suno"
    assert result.job_id == "job-123"
    assert result.audio_url == "https://example.test/song.mp3"
    assert result.track_id == "track-9"


def test_suno_configuration_requires_key_and_generate_url(monkeypatch):
    monkeypatch.delenv("SUNO_API_KEY", raising=False)
    monkeypatch.delenv("SUNO_GENERATE_URL", raising=False)
    assert not SunoClient().configured
