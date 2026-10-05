from beatstudio.usage import estimated_render_minutes, quota_for


def test_4k_render_costs_more_than_720p():
    duration = 120
    assert estimated_render_minutes(duration, 2160) > estimated_render_minutes(duration, 720)


def test_paid_plan_has_music_generation_quota():
    assert quota_for("pro").music_generations > 0
    assert quota_for("free").music_generations == 0
