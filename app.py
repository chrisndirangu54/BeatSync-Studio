import os
import tempfile
import requests
import streamlit as st

from beatstudio.ai_dj import AIDJ, AudioCompatibility, JamendoCatalog
from beatstudio.director import MultiClipDirector
from beatstudio.effects import SPECS, TIER_RANK
from beatstudio.music_provider import SunoClient, compose_suno_edit_instruction, download_audio
from beatstudio.plans import PLANS
from beatstudio.renderer import VideoRenderer
from beatstudio.stock_media import PexelsVideoCatalog
from beatstudio.usage import quota_for
from beatstudio.video_provider import SeedanceClient, download_video

st.set_page_config(page_title="BeatSync Studio", page_icon="🎛️", layout="wide")

def save_upload(upload, folder, prefix):
    path=os.path.join(folder,prefix+"_"+os.path.basename(upload.name))
    with open(path,"wb") as fh:
        fh.write(upload.getbuffer())
    return path

def download_url(url, destination):
    with requests.get(url,stream=True,timeout=180) as r:
        r.raise_for_status()
        with open(destination,"wb") as fh:
            for chunk in r.iter_content(1024*1024):
                if chunk:
                    fh.write(chunk)
    return destination

st.title("BeatSync Studio")
st.markdown("### AI music-video direction, beat intelligence, generation and DJ transitions")
st.caption("Build from uploads, generated video, stock footage and uploaded/generated/catalog music. Intelligent Beat Sync drives edit timing, clip choice, visual FX and sound design.")

with st.sidebar:
    st.header("Project")
    plan_key=st.selectbox(
        "Subscription",list(PLANS),
        format_func=lambda k: (f"{PLANS[k].name} — $" + str(PLANS[k].monthly_usd) + "/mo") if PLANS[k].monthly_usd else "Free",
    )
    plan=PLANS[plan_key]; quota=quota_for(plan_key)
    st.metric("Export","4K" if plan.export_height>=2160 else f"{plan.export_height}p")
    st.metric("Beat Intelligence",f"Level {plan.intelligent_sync_level}")
    st.metric("Render allowance",f"{quota.render_minutes} min/mo")
    st.metric("AI music allowance",f"{quota.music_generations}/mo")
    st.divider()
    st.write("✓ Beat + onset grid")
    st.write("✓ Bass / mids / treble")
    st.write("✓ Energy / brightness")
    st.write("✓ Drop likelihood")
    st.write("✓ Scene-aware directing")
    st.write("✓ Song sections" if plan.intelligent_sync_level>=3 else "🔒 Song sections — Creator")

st.subheader("1. Video sources")
uploads=st.file_uploader("Upload one or more clips",type=["mp4","mov","mkv","avi"],accept_multiple_files=True)
video_tabs=st.tabs(["Seedance generation","Pexels stock video"])

with video_tabs[0]:
    seedance=SeedanceClient()
    if not seedance.configured:
        st.info("Set BYTEPLUS_ARK_API_KEY to enable Seedance 2.5 generation.")
    seed_prompt=st.text_area("Video prompt",placeholder="Cinematic night performance in Nairobi, energetic handheld camera, neon rain, dramatic close-ups...",key="seed_prompt")
    c1,c2,c3=st.columns(3)
    seed_duration=c1.slider("Duration",4,30,8)
    seed_resolution=c2.selectbox("Resolution",["720p","1080p"],index=1)
    seed_audio=c3.checkbox("Generate synchronized audio",value=False)
    seed_ref_url=st.text_input("Optional public image/video/audio reference URL")
    seed_ref_kind=st.selectbox("Reference type",["image","video","audio"])
    if st.button("Generate clip with Seedance",disabled=not seedance.configured or not seed_prompt.strip(),use_container_width=True):
        try:
            refs=[]
            if seed_ref_url.strip():
                refs=[{"url":seed_ref_url.strip(),"kind":seed_ref_kind,"role":f"reference_{seed_ref_kind}"}]
            with st.spinner("Seedance is generating the clip…"):
                result=seedance.create(seed_prompt.strip(),duration=seed_duration,resolution=seed_resolution,references=refs,generate_audio=seed_audio)
                result=seedance.wait(result)
                td=tempfile.mkdtemp(prefix="beatsync_seedance_")
                out=os.path.join(td,"seedance_clip.mp4")
                download_video(result.video_url,out)
                st.session_state.setdefault("generated_video_paths",[]).append(out)
                st.success("Generated clip added to this project.")
                st.video(out)
        except Exception as exc:
            st.exception(exc)

with video_tabs[1]:
    pexels=PexelsVideoCatalog()
    if not pexels.configured:
        st.info("Set PEXELS_API_KEY to enable stock-video search.")
    q=st.text_input("Search stock video",placeholder="dancing crowd, city night, sports car, mountains")
    orientation=st.selectbox("Orientation",["","landscape","portrait","square"])
    if st.button("Search Pexels",disabled=not pexels.configured or not q.strip()):
        try:
            st.session_state["pexels_results"]=pexels.search(q.strip(),orientation=orientation or None,per_page=12)
        except Exception as exc:
            st.exception(exc)
    results=st.session_state.get("pexels_results",[])
    if results:
        labels=[f"{i+1}. {r.creator or 'Creator'} · {int(r.duration)}s · {r.width}×{r.height}" for i,r in enumerate(results)]
        selected=st.selectbox("Choose a stock clip",range(len(results)),format_func=lambda i:labels[i])
        item=results[selected]
        st.image(item.preview_image)
        st.caption(f"Video by {item.creator or 'Pexels creator'} on Pexels. Attribution is required by the Pexels API guidelines.")
        if st.button("Add selected stock clip to project",use_container_width=True):
            try:
                td=tempfile.mkdtemp(prefix="beatsync_pexels_")
                out=os.path.join(td,f"pexels_{item.id}.mp4")
                download_url(item.video_url,out)
                st.session_state.setdefault("stock_video_paths",[]).append(out)
                st.session_state.setdefault("stock_credits",[]).append((item.creator,item.page_url))
                st.success("Stock clip added.")
            except Exception as exc:
                st.exception(exc)

asset_count=len(uploads or [])+len(st.session_state.get("generated_video_paths",[]))+len(st.session_state.get("stock_video_paths",[]))
st.caption(f"Project currently has **{asset_count}** video source(s).")

st.subheader("2. Music source")
music_mode=st.radio("Soundtrack workflow",["Upload music","Generate with Suno","Edit with Suno","AI DJ / licensed catalog"],horizontal=True)
uploaded_audio=None
suno=SunoClient()

if music_mode=="Upload music":
    uploaded_audio=st.file_uploader("Music/audio",type=["mp3","wav","m4a","aac","flac"],key="music_upload")

elif music_mode=="Generate with Suno":
    allowed="suno_generation" in plan.features
    if not allowed: st.warning("Suno generation unlocks on Pro.")
    if allowed and not suno.configured: st.info("Configure SUNO_API_KEY and SUNO_GENERATE_URL.")
    left,right=st.columns([2,1])
    with left:
        prompt=st.text_area("Music prompt",placeholder="Afro-house, 112 BPM, female vocal, dramatic pre-chorus, huge percussion drop…")
        lyrics=st.text_area("Lyrics (optional)",height=100)
    with right:
        model=st.selectbox("Model",["v6","v6-wild","v6-mini"])
        title=st.text_input("Title")
        instrumental=st.checkbox("Instrumental")
    if st.button("Generate with Suno",disabled=not allowed or not suno.configured or not prompt.strip(),use_container_width=True):
        try:
            with st.spinner("Generating soundtrack…"):
                r=suno.generate(prompt.strip(),model=model,instrumental=instrumental,title=title.strip() or None,lyrics=lyrics.strip() or None)
                r=suno.wait_for_audio(r)
                if not r.audio_url:
                    st.error("No audio URL yet. Configure the official Suno status endpoint for async jobs.")
                else:
                    td=tempfile.mkdtemp(prefix="beatsync_suno_")
                    path=download_audio(r.audio_url,os.path.join(td,"generated.mp3"))
                    st.session_state["suno_generated_audio_path"]=path
        except Exception as exc: st.exception(exc)
    if st.session_state.get("suno_generated_audio_path"): st.audio(st.session_state["suno_generated_audio_path"])

elif music_mode=="Edit with Suno":
    allowed="suno_editing" in plan.features
    if not allowed: st.warning("Structured Suno editing unlocks on Creator.")
    base_instruction=st.text_area("Creative edit instruction",placeholder="Make the chorus bigger but keep the verse intimate.")
    col1,col2,col3=st.columns(3)
    add_inst=col1.multiselect("Add/emphasize instruments",["drums","bass","guitar","piano","strings","brass","synths","percussion","choir","flute","saxophone"])
    remove_inst=col2.multiselect("Remove/reduce instruments",["drums","bass","guitar","piano","strings","brass","synths","percussion","choir"])
    genre=col3.text_input("Target genre/style",placeholder="Afro-house / amapiano / cinematic")
    col4,col5,col6=st.columns(3)
    tempo=col4.number_input("Target tempo BPM",min_value=40.0,max_value=220.0,value=110.0,step=1.0)
    pitch=col5.slider("Transpose semitones",-12.0,12.0,0.0,.5)
    vocal_gender=col6.selectbox("Lead vocal character",["keep current","female","male"])
    preserve_melody=st.checkbox("Preserve core melody",value=True)
    preserve_lyrics=st.checkbox("Preserve lyrics",value=True)
    track_id=st.text_input("Suno source track ID (optional)")
    audio_url=st.text_input("Public source audio URL (optional)")
    instruction=compose_suno_edit_instruction(
        base_instruction=base_instruction,add_instruments=add_inst,remove_instruments=remove_inst,
        genre=genre,tempo_bpm=tempo,pitch_semitones=pitch,
        vocal_gender="" if vocal_gender=="keep current" else vocal_gender,
        preserve_melody=preserve_melody,preserve_lyrics=preserve_lyrics,
    )
    st.caption("Compiled Suno edit request: "+instruction)
    if st.button("Edit soundtrack with Suno",disabled=not allowed or not suno.edit_url or not instruction or not (track_id.strip() or audio_url.strip()),use_container_width=True):
        try:
            with st.spinner("Editing soundtrack…"):
                r=suno.edit(instruction,source_track_id=track_id.strip() or None,source_audio_url=audio_url.strip() or None,model="v6")
                r=suno.wait_for_audio(r)
                if not r.audio_url: st.error("Edit is still asynchronous; configure SUNO_STATUS_URL_TEMPLATE.")
                else:
                    td=tempfile.mkdtemp(prefix="beatsync_suno_edit_")
                    path=download_audio(r.audio_url,os.path.join(td,"edited.mp3"))
                    st.session_state["suno_edited_audio_path"]=path
        except Exception as exc: st.exception(exc)
    if st.session_state.get("suno_edited_audio_path"): st.audio(st.session_state["suno_edited_audio_path"])

else:
    catalog=JamendoCatalog()
    st.caption("AI DJ finds musically compatible tracks using BPM, harmonic key, energy and spectral brightness.")
    reference=st.file_uploader("Reference/current song",type=["mp3","wav","m4a","aac","flac"],key="dj_reference")
    query=st.text_input("Catalog search",placeholder="afro house energetic female vocal")
    d1,d2,d3=st.columns(3)
    speed=d1.selectbox("Speed",["","verylow","low","medium","high","veryhigh"])
    gender=d2.selectbox("Vocal gender",["","female","male"])
    instrumental=d3.selectbox("Vocal type",["any","instrumental","vocal"])
    if not catalog.configured: st.info("Set JAMENDO_CLIENT_ID to search Jamendo.")
    if st.button("Search licensed catalog",disabled=not catalog.configured or not query.strip()):
        try:
            st.session_state["jamendo_results"]=catalog.search(query.strip(),speed=speed or None,gender=gender or None,instrumental=None if instrumental=="any" else instrumental=="instrumental",pro_licensing=True,limit=20)
        except Exception as exc: st.exception(exc)
    tracks=st.session_state.get("jamendo_results",[])
    if tracks:
        labels=[f"{t.name} — {t.artist}" for t in tracks]
        idx=st.selectbox("Candidate track",range(len(tracks)),format_func=lambda i:labels[i])
        track=tracks[idx]
        st.caption("Commercial licensing still has to be obtained for the selected track; pro-licensing search is discovery, not proof of clearance.")
        if reference and st.button("Analyze and build beat-matched switch",use_container_width=True):
            try:
                td=tempfile.mkdtemp(prefix="beatsync_dj_")
                ref_path=save_upload(reference,td,"reference")
                candidate=download_audio(track.stream_url,os.path.join(td,"candidate.mp3"))
                f1=AudioCompatibility.analyze(ref_path); f2=AudioCompatibility.analyze(candidate)
                score=AudioCompatibility.score(f1,f2)
                st.write(f"Compatibility: **{score:.0%}** · {f1.bpm:.1f}→{f2.bpm:.1f} BPM · key {AudioCompatibility.KEY_NAMES[f1.key_index]}→{AudioCompatibility.KEY_NAMES[f2.key_index]}")
                mix=os.path.join(td,"ai_dj_mix.wav")
                AIDJ.beatmatch_crossfade(ref_path,candidate,mix,crossfade_seconds=8,tempo_match=True,key_lock=True)
                st.session_state["ai_dj_audio_path"]=mix
            except Exception as exc: st.exception(exc)
    if st.session_state.get("ai_dj_audio_path"): st.audio(st.session_state["ai_dj_audio_path"])

st.subheader("3. Intelligent directing & automatic effects")
director_mode=st.toggle("Scene-aware Auto Director",value=asset_count>1,help="Chooses clips by semantic fit: performers, dancing, cars, landscapes, close-ups, wide shots, motion and emotional tone.")
auto_vfx=st.toggle("Automatic beat/tempo-aware video effects",value=True)
auto_sfx=st.toggle("Automatic sound design (impacts, whooshes, risers)",value=False)

st.subheader("4. Manual Effect Rack")
enabled={}; rank=TIER_RANK[plan_key]
for category in sorted(set(s.category for s in SPECS)):
    with st.expander(category,expanded=category in ("Motion","Subject","Glitch")):
        cols=st.columns(3)
        for i,spec in enumerate([s for s in SPECS if s.category==category]):
            locked=TIER_RANK[spec.tier]>rank
            with cols[i%3]:
                on=st.checkbox(f"{spec.name}{' 🔒' if locked else ''}",key="on_"+spec.key,disabled=locked)
                st.caption(f"{spec.description} · sync: {spec.signal}")
                if on and not locked:
                    enabled[spec.key]=st.slider("Intensity",0.0,1.0,float(spec.default_intensity),.05,key="int_"+spec.key,label_visibility="collapsed")

st.subheader("5. Render")
if st.button("Render intelligent music video",type="primary",use_container_width=True):
    workspace=tempfile.mkdtemp(prefix="beatsync_project_")
    clip_paths=[save_upload(clip,workspace,f"upload_{i}") for i,clip in enumerate(uploads or [])]
    clip_paths+=list(st.session_state.get("generated_video_paths",[]))
    clip_paths+=list(st.session_state.get("stock_video_paths",[]))
    if not clip_paths:
        st.error("Add at least one video source."); st.stop()
    if music_mode=="Upload music":
        if uploaded_audio is None: st.error("Upload music first."); st.stop()
        audio_path=save_upload(uploaded_audio,workspace,"soundtrack")
    elif music_mode=="Generate with Suno": audio_path=st.session_state.get("suno_generated_audio_path")
    elif music_mode=="Edit with Suno": audio_path=st.session_state.get("suno_edited_audio_path")
    else: audio_path=st.session_state.get("ai_dj_audio_path")
    if not audio_path or not os.path.exists(audio_path):
        st.error("Prepare the selected soundtrack first."); st.stop()

    bar=st.progress(0.0,"Preparing…")
    try:
        video_input=clip_paths[0]
        if director_mode and len(clip_paths)>1:
            directed=os.path.join(workspace,"auto_directed.mp4")
            MultiClipDirector(clip_paths,audio_path,directed,intelligence_level=plan.intelligent_sync_level).build(
                lambda x:bar.progress(min(.35,x*.35),"Scene-aware director is choosing shots…")
            )
            video_input=directed
        output=os.path.join(workspace,"beatsync_output.mp4")
        renderer=VideoRenderer(video_input,audio_path,output,plan_key,enabled,automatic_fx=auto_vfx,automatic_sound_fx=auto_sfx)
        renderer.render(lambda x:bar.progress(.35+x*.65 if director_mode and len(clip_paths)>1 else x,"Rendering beat-aware effects…"))
        bar.progress(1.0,"Complete")
        st.video(output)
        with open(output,"rb") as fh:
            st.download_button("Download video",fh.read(),file_name="beatsync_output.mp4",mime="video/mp4",use_container_width=True)
        for creator,url in st.session_state.get("stock_credits",[]):
            st.caption(f"Stock footage credit: {creator or 'Pexels creator'} — {url}")
    except Exception as exc:
        st.exception(exc)
