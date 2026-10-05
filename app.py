import os, tempfile, json
import streamlit as st
from beatstudio.effects import SPECS, TIER_RANK
from beatstudio.plans import PLANS
from beatstudio.renderer import VideoRenderer

st.set_page_config(page_title='BeatSync Studio', page_icon='🎛️', layout='wide')
st.markdown('''<style>
.block-container{padding-top:1.4rem}.hero{font-size:3rem;font-weight:800;letter-spacing:-.04em}.muted{opacity:.7}
.plan{border:1px solid rgba(128,128,128,.25);border-radius:18px;padding:16px}.small{font-size:.85rem;opacity:.72}
</style>''', unsafe_allow_html=True)

st.markdown('<div class="hero">BeatSync Studio</div>',unsafe_allow_html=True)
st.markdown('### Intelligent beat sync for programmable music-video effects')
st.caption('Upload video + music → analyze rhythm, bass, transients, energy, drops and sections → independently enable the visual reactions you want.')

with st.sidebar:
    st.header('Project')
    plan_key=st.selectbox('Subscription',list(PLANS),format_func=lambda k:f"{PLANS[k].name} — ${PLANS[k].monthly_usd}/mo" if PLANS[k].monthly_usd else 'Free')
    plan=PLANS[plan_key]
    st.metric('Export',f'{plan.export_height}p' if plan.export_height<2160 else '4K')
    st.metric('Active effects', 'Unlimited' if plan.max_effects>100 else plan.max_effects)
    st.metric('Beat Intelligence',f'Level {plan.intelligent_sync_level}')
    st.divider()
    st.subheader('Intelligence')
    st.write('✓ Beat grid')
    st.write('✓ Onset/transient detection')
    st.write('✓ Bass / mids / treble energy')
    st.write('✓ Energy & brightness envelopes')
    st.write('✓ Drop likelihood')
    st.write('✓ Song sections' if plan.intelligent_sync_level>=3 else '🔒 Song sections — Creator')

video=st.file_uploader('Video',type=['mp4','mov','mkv','avi'])
audio=st.file_uploader('Music / audio',type=['mp3','wav','m4a','aac','flac'])

st.subheader('Effect Rack')
st.caption('Every feature is independent. The signal shown on each control is what Intelligent Beat Sync uses to drive its intensity.')

enabled={}
rank=TIER_RANK[plan_key]
for category in sorted(set(s.category for s in SPECS)):
    with st.expander(category, expanded=category in ('Motion','Subject','Glitch')):
        cols=st.columns(3)
        specs=[s for s in SPECS if s.category==category]
        for i,s in enumerate(specs):
            locked=TIER_RANK[s.tier]>rank
            with cols[i%3]:
                on=st.checkbox(f"{s.name}{' 🔒' if locked else ''}",key='on_'+s.key,disabled=locked)
                st.caption(f'{s.description} · sync: **{s.signal}** · {s.tier}')
                if on and not locked:
                    enabled[s.key]=st.slider('Intensity',0.0,1.0,float(s.default_intensity),.05,key='int_'+s.key,label_visibility='collapsed')

st.subheader('Subscription model')
cols=st.columns(4)
for c,(k,p) in zip(cols,PLANS.items()):
    with c:
        st.markdown(f'<div class="plan"><b>{p.name}</b><br><span style="font-size:1.8rem">${p.monthly_usd}</span><span class="small"> / month</span><hr><span class="small">{p.export_height}p export<br>{"Watermark" if p.watermark else "No watermark"}<br>{"Unlimited" if p.max_effects>100 else p.max_effects} simultaneous effects<br>Beat Intelligence L{p.intelligent_sync_level}</span></div>',unsafe_allow_html=True)

st.info('Billing architecture is Stripe-ready; connect your Stripe Price IDs in environment variables before production. The UI plan selector acts as local/demo entitlement mode.')

if st.button('Render with Intelligent Beat Sync',type='primary',use_container_width=True):
    if not video or not audio:
        st.error('Upload both a video and an audio file.')
    elif not enabled:
        st.error('Enable at least one effect.')
    else:
        td=tempfile.mkdtemp(prefix='beatsync_')
        vp=os.path.join(td,video.name); ap=os.path.join(td,audio.name); op=os.path.join(td,'beatsync_output.mp4')
        open(vp,'wb').write(video.getbuffer()); open(ap,'wb').write(audio.getbuffer())
        bar=st.progress(0.0,'Analysing music and rendering…')
        try:
            r=VideoRenderer(vp,ap,op,plan_key,enabled)
            st.write(f'Estimated tempo: **{r.sync.tempo:.1f} BPM** · sections: **{len(r.sync.section_boundaries)-1}**')
            r.render(lambda x:bar.progress(x,'Rendering intelligent beat-synced effects…'))
            bar.progress(1.0,'Complete')
            st.video(op)
            st.download_button('Download rendered video',open(op,'rb'),file_name='beatsync_output.mp4',mime='video/mp4',use_container_width=True)
        except Exception as e:
            st.exception(e)
