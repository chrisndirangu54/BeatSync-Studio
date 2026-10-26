import json
import pytest
from beatstudio.ai_director import plan_with_model

class DummyResponse:
    def raise_for_status(self):pass
    def json(self):
        return {"status":"completed","output":[{"type":"message","content":[{"type":"output_text","text":json.dumps({
            "preset":"wave_tunnel","signal":"bass","color_a":"cyan","color_b":"magenta",
            "lyric_style":"neon_script","caption":"Into the night","reason":"Energetic bass-led visuals"
        })}]}]}

def test_structured_model_output_is_validated():
    def mock_post(url,**kwargs):
        assert url=="https://api.openai.com/v1/responses"
        assert kwargs["json"]["store"] is False
        assert kwargs["json"]["text"]["format"]["strict"]
        return DummyResponse()
    out=plan_with_model("A bass reactive cinematic experience",api_key="test-token",post=mock_post)
    assert out["provider"]=="openai_responses"
    assert out["config"]["blender_layers"][0]["preset"]=="wave_tunnel"
    assert out["config"]["motion_cues"][0]["text"]=="Into the night"

def test_requires_server_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY",raising=False)
    with pytest.raises(RuntimeError):
        plan_with_model("Make a cinematic video")

def test_invalid_model_disallowed():
    with pytest.raises(ValueError):
        plan_with_model("Make a cinematic video",api_key="a",model="model/../../evil")
