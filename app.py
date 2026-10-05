import os
import tempfile

import streamlit as st

from beatstudio.director import MultiClipDirector
from beatstudio.effects import SPECS, TIER_RANK
from beatstudio.music_provider import MusicProviderError, SunoClient, download_audio
from beatstudio.plans import PLANS
from beatstudio.renderer import VideoRenderer
from beatstudio.usage import quota_for

st.set_page_config(page_title="BeatSync Studio", page_icon="🎛️", layout="wide")
st.markdown(
    """
    <style>
    .block-container{padding-top:1.35rem}
    .hero{font-size:3rem;font-weight:800;letter-spacing:-.04em}
    .plan{border:1px solid rgba(128,128,128,.25);border-radius:18px;padding:16px}
    .small{font-size:.85rem;opacity:.72}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="hero">BeatSync Studio</div>', unsafe_allow_html=True)
st.markdown("### Intelligent music direction for programmable video effects")
st.caption(
    "Upload or generate music → understand rhythm, frequency bands, energy, drops and sections "
    "→ auto-direct clips → drive independently selectable VFX."
)

with st.sidebar:
    st.header("Project")
    plan_key = st.selectbox(
        "Subscription",
        list(PLANS),
        format_func=lambda k: (
            f"{PLANS[k].name} — ${PLANS[k].monthly_usd}/mo"
            if PLANS[k].monthly_usd
            else "Free"
        ),
    )
    plan = PLANS[plan_key]
    quota = quota_for(plan_key)

    st.metric("Export", f"{plan.export_height}p" if plan.export_height < 2160 else "4K")
    st.metric("Active effects", "Unlimited" if plan.max_effects > 100 else plan.max_effects)
    st.metric("Beat Intelligence", f"Level {plan.intelligent_sync_level}")
    st.metric("Render allowance", f"{quota.render_minutes} min/mo")
    st.metric("AI music allowance", f"{quota.music_generations}/mo")

    st.divider()
    st.subheader("Music intelligence")
    st.write("✓ Beat grid")
    st.write("✓ Onset/transient detection")
    st.write("✓ Bass / mids / treble energy")
    st.write("✓ Energy & spectral brightness")
    st.write("✓ Drop likelihood")
    st.write(
        "✓ Song section analysis"
        if plan.intelligent_sync_level >= 3
        else "🔒 Song sections — Creator"
    )

st.subheader("1. Video source")
clips = st.file_uploader(
    "Upload one or more video clips",
    type=["mp4", "mov", "mkv", "avi"],
    accept_multiple_files=True,
)

director_mode = False
if clips and len(clips) > 1:
    director_mode = st.toggle(
        "AI Auto Director",
        value=True,
        help=(
            "Builds a first-pass edit from all uploaded clips. Cut frequency responds to "
            "beats, energy, drops and song sections before VFX are rendered."
        ),
    )
    if director_mode:
        st.caption(
            "Auto Director changes shots faster during high-energy passages, uses structural "
            "section boundaries as edit points, and avoids repeating the same clip consecutively."
        )

st.subheader("2. Music source")
music_mode = st.radio(
    "Choose how the soundtrack enters the project",
    ["Upload music", "Generate with Suno", "Edit with Suno"],
    horizontal=True,
)

uploaded_audio = None
suno = SunoClient()

if music_mode == "Upload music":
    uploaded_audio = st.file_uploader(
        "Music / audio",
        type=["mp3", "wav", "m4a", "aac", "flac"],
        key="uploaded_music",
    )

elif music_mode == "Generate with Suno":
    allowed = "suno_generation" in plan.features
    if not allowed:
        st.warning("Suno generation is available from the Pro plan.")
    elif not suno.configured:
        st.warning(
            "Suno API is not configured. Set SUNO_API_KEY and SUNO_GENERATE_URL using "
            "the endpoint shown in your official Suno developer dashboard."
        )

    col1, col2 = st.columns([2, 1])
    with col1:
        suno_prompt = st.text_area(
            "Music direction",
            placeholder=(
                "Dark Afro-electronic track, 108 BPM, spacious intro, strong percussion, "
                "large cinematic drop after the first chorus..."
            ),
            height=120,
            disabled=not allowed,
        )
        suno_lyrics = st.text_area(
            "Lyrics (optional)",
            placeholder="Leave blank for Suno to infer lyrics, or use instrumental mode.",
            height=90,
            disabled=not allowed,
        )
    with col2:
        suno_title = st.text_input("Working title", disabled=not allowed)
        suno_model = st.selectbox(
            "Suno model",
            ["v6", "v6-wild", "v6-mini"],
            disabled=not allowed,
        )
        suno_instrumental = st.checkbox("Instrumental", disabled=not allowed)

    if st.button(
        "Generate soundtrack with Suno",
        disabled=(not allowed or not suno.configured or not suno_prompt.strip()),
        use_container_width=True,
    ):
        with st.spinner("Requesting music from Suno…"):
            try:
                result = suno.generate(
                    suno_prompt.strip(),
                    model=suno_model,
                    instrumental=suno_instrumental,
                    title=suno_title.strip() or None,
                    lyrics=suno_lyrics.strip() or None,
                )
                result = suno.wait_for_audio(result)
                if not result.audio_url:
                    st.error(
                        "Suno accepted the request but no audio URL is available yet. "
                        "Configure SUNO_STATUS_URL_TEMPLATE from your developer dashboard "
                        "if the API returns asynchronous jobs."
                    )
                else:
                    td = tempfile.mkdtemp(prefix="beatsync_suno_")
                    generated_path = os.path.join(td, "suno_generated_audio.mp3")
                    download_audio(result.audio_url, generated_path)
                    st.session_state["suno_generated_audio_path"] = generated_path
                    st.session_state["suno_generated_audio_url"] = result.audio_url
                    st.success("Suno soundtrack is ready for Intelligent Beat Sync.")
            except Exception as exc:
                st.exception(exc)

    if st.session_state.get("suno_generated_audio_path"):
        st.audio(st.session_state["suno_generated_audio_path"])

else:
    allowed = "suno_editing" in plan.features
    if not allowed:
        st.warning("Suno editing is available from the Creator plan.")
    elif not suno.edit_url:
        st.warning(
            "Set SUNO_EDIT_URL using the official editing endpoint shown in your "
            "Suno developer dashboard."
        )

    source_track_id = st.text_input(
        "Suno source track ID (optional)",
        disabled=not allowed,
    )
    source_audio_url = st.text_input(
        "Public source audio URL (optional)",
        disabled=not allowed,
        help="Use either a Suno track ID or a URL supported by your configured Suno edit endpoint.",
    )
    edit_instruction = st.text_area(
        "Editing instruction",
        placeholder=(
            "Make the chorus larger, replace the drums with Afro-house percussion, "
            "keep the vocal melody, and create a cleaner 16-bar instrumental intro."
        ),
        height=120,
        disabled=not allowed,
    )
    edit_model = st.selectbox(
        "Editing model",
        ["v6", "v6-wild", "v6-mini"],
        key="edit_model",
        disabled=not allowed,
    )

    if st.button(
        "Edit soundtrack with Suno",
        disabled=(
            not allowed
            or not suno.edit_url
            or not edit_instruction.strip()
            or not (source_track_id.strip() or source_audio_url.strip())
        ),
        use_container_width=True,
    ):
        with st.spinner("Sending the music edit to Suno…"):
            try:
                result = suno.edit(
                    edit_instruction.strip(),
                    source_track_id=source_track_id.strip() or None,
                    source_audio_url=source_audio_url.strip() or None,
                    model=edit_model,
                )
                result = suno.wait_for_audio(result)
                if not result.audio_url:
                    st.error(
                        "The edit request was accepted but is still asynchronous. "
                        "Configure SUNO_STATUS_URL_TEMPLATE to poll the official job endpoint."
                    )
                else:
                    td = tempfile.mkdtemp(prefix="beatsync_suno_edit_")
                    edited_path = os.path.join(td, "suno_edited_audio.mp3")
                    download_audio(result.audio_url, edited_path)
                    st.session_state["suno_edited_audio_path"] = edited_path
                    st.session_state["suno_edited_audio_url"] = result.audio_url
                    st.success("Edited soundtrack is ready.")
            except Exception as exc:
                st.exception(exc)

    if st.session_state.get("suno_edited_audio_path"):
        st.audio(st.session_state["suno_edited_audio_path"])

st.subheader("3. Effect Rack")
st.caption(
    "Each visual feature is independent. Its sync label shows which musical signal controls "
    "the effect's dynamic intensity."
)

enabled = {}
rank = TIER_RANK[plan_key]
for category in sorted(set(spec.category for spec in SPECS)):
    with st.expander(category, expanded=category in ("Motion", "Subject", "Glitch")):
        columns = st.columns(3)
        specs = [spec for spec in SPECS if spec.category == category]
        for i, spec in enumerate(specs):
            locked = TIER_RANK[spec.tier] > rank
            with columns[i % 3]:
                on = st.checkbox(
                    f"{spec.name}{' 🔒' if locked else ''}",
                    key="on_" + spec.key,
                    disabled=locked,
                )
                st.caption(
                    f"{spec.description} · sync: **{spec.signal}** · {spec.tier}"
                )
                if on and not locked:
                    enabled[spec.key] = st.slider(
                        "Intensity",
                        0.0,
                        1.0,
                        float(spec.default_intensity),
                        0.05,
                        key="int_" + spec.key,
                        label_visibility="collapsed",
                    )

st.subheader("4. Subscription model")
columns = st.columns(4)
for column, (key, current) in zip(columns, PLANS.items()):
    q = quota_for(key)
    with column:
        st.markdown(
            f"""
            <div class="plan">
            <b>{current.name}</b><br>
            <span style="font-size:1.8rem">${current.monthly_usd}</span>
            <span class="small"> / month</span><hr>
            <span class="small">
            {current.export_height}p export<br>
            {"Watermark" if current.watermark else "No watermark"}<br>
            {"Unlimited" if current.max_effects > 100 else current.max_effects} simultaneous effects<br>
            Beat Intelligence L{current.intelligent_sync_level}<br>
            {q.render_minutes} render min/mo<br>
            {q.music_generations} AI music generations/mo
            </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.info(
    "Stripe remains the intended production entitlement source. The selector above is a "
    "local/demo plan switch; production should validate plans from Stripe webhooks and persist "
    "usage in your database."
)

render = st.button(
    "Render with Intelligent Beat Sync",
    type="primary",
    use_container_width=True,
)

if render:
    if not clips:
        st.error("Upload at least one video clip.")
        st.stop()

    if not enabled:
        st.error("Enable at least one effect.")
        st.stop()

    workspace = tempfile.mkdtemp(prefix="beatsync_project_")

    clip_paths = []
    for index, clip in enumerate(clips):
        safe_name = f"clip_{index}_{os.path.basename(clip.name)}"
        path = os.path.join(workspace, safe_name)
        with open(path, "wb") as handle:
            handle.write(clip.getbuffer())
        clip_paths.append(path)

    if music_mode == "Upload music":
        if uploaded_audio is None:
            st.error("Upload a soundtrack.")
            st.stop()
        audio_path = os.path.join(
            workspace,
            "soundtrack_" + os.path.basename(uploaded_audio.name),
        )
        with open(audio_path, "wb") as handle:
            handle.write(uploaded_audio.getbuffer())
    else:
        session_key = (
            "suno_generated_audio_path"
            if music_mode == "Generate with Suno"
            else "suno_edited_audio_path"
        )
        audio_path = st.session_state.get(session_key)
        if not audio_path or not os.path.exists(audio_path):
            st.error("Generate or edit the selected Suno soundtrack first.")
            st.stop()

    bar = st.progress(0.0, "Preparing project…")

    try:
        video_input = clip_paths[0]
        if director_mode and len(clip_paths) > 1:
            directed_path = os.path.join(workspace, "auto_directed.mp4")
            director = MultiClipDirector(
                clip_paths,
                audio_path,
                directed_path,
                intelligence_level=plan.intelligent_sync_level,
            )
            director.build(
                lambda value: bar.progress(
                    min(0.35, value * 0.35),
                    "AI Auto Director is building the first-pass edit…",
                )
            )
            video_input = directed_path

        output_path = os.path.join(workspace, "beatsync_output.mp4")
        renderer = VideoRenderer(
            video_input,
            audio_path,
            output_path,
            plan_key,
            enabled,
        )

        st.write(
            f"Estimated tempo: **{renderer.sync.tempo:.1f} BPM** · "
            f"detected structural regions: **{len(renderer.sync.section_boundaries)-1}**"
        )

        renderer.render(
            lambda value: bar.progress(
                0.35 + value * 0.65 if director_mode and len(clip_paths) > 1 else value,
                "Rendering music-aware visual effects…",
            )
        )
        bar.progress(1.0, "Complete")
        st.video(output_path)
        with open(output_path, "rb") as handle:
            st.download_button(
                "Download rendered video",
                handle.read(),
                file_name="beatsync_output.mp4",
                mime="video/mp4",
                use_container_width=True,
            )
    except Exception as exc:
        st.exception(exc)
