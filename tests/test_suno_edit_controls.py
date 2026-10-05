from beatstudio.music_provider import compose_suno_edit_instruction

def test_structured_edit_instruction_contains_controls():
    text=compose_suno_edit_instruction(
        add_instruments=["saxophone"],
        remove_instruments=["guitar"],
        genre="afro house",
        tempo_bpm=112,
        pitch_semitones=2,
        vocal_gender="female",
    )
    assert "saxophone" in text
    assert "guitar" in text
    assert "112.0 BPM" in text
    assert "female" in text
