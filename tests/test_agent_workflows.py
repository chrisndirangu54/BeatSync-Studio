import pytest
from beatstudio.agent_workflows import plan_prompt, AGENTS

def test_agent_roles_and_review():
    plan=plan_prompt("Cinematic neon cyan spectrum bars with cursive lyrics")
    assert plan["status"]=="ready_for_review"
    assert set(AGENTS)=={"director","rhythm","visual_fx","typography","quality"}
    assert plan["config"]["blender_layers"][0]["preset"]=="spectrum_bars"
    assert plan["config"]["lyric_theme"]["style"]=="calligraphy"
    assert plan["steps"][-1]["output"]["requires_user_review"] is True

def test_caption_is_reviewable():
    plan=plan_prompt("Display Into the night.")
    assert plan["config"]["motion_cues"]
    assert plan["config"]["motion_cues"][0]["position"]=="middle"

@pytest.mark.parametrize("prompt",["","ok","a"*2001])
def test_reject_invalid_prompt(prompt):
    with pytest.raises(ValueError):
        plan_prompt(prompt)

@pytest.mark.parametrize("intensity",[-1,2])
def test_reject_intensity(intensity):
    with pytest.raises(ValueError):
        plan_prompt("hello world",intensity=intensity)
