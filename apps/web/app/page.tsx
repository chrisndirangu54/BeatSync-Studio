"use client";

import { useEffect, useMemo, useState } from "react";
import { API_BASE, getJSON, postForm } from "@/lib/api";
import UserMenu from "@/components/UserMenu";

type Effect = { key:string; name:string; category:string; description:string; tier:string; default_intensity:number; signal:string; };
type Plan = { key:string; name:string; monthly_usd:number; export_height:number; watermark:boolean; max_effects:number; intelligent_sync_level:number; features:string[]; };
type NarrativeSection = { index:number; start:number; end:number; label:string; intent:string; preferred_tags:string[]; shot_scale:string; motion_style:string; emotional_tone:string; pacing:string; effect_direction:string[]; seedance_prompt:string; };
type BlenderPreset = {key:string;family:string;default_signal:string};
type BlenderLayer = {preset:string;enabled:boolean;signal:string;intensity:number;color_a:string;color_b:string;seed:number;quality:string};
type NarrativePlan = { duration:number; tempo:number; arc:string; sections:NarrativeSection[]; };

export default function Home() {
  const [effects,setEffects]=useState<Effect[]>([]);
  const [plans,setPlans]=useState<Plan[]>([]);
  const [planKey,setPlanKey]=useState("pro");
  const [audio,setAudio]=useState<File|null>(null);
  const [videos,setVideos]=useState<File[]>([]);
  const [selected,setSelected]=useState<Record<string,number>>({});
  const [narrative,setNarrative]=useState<NarrativePlan|null>(null);
  const [job,setJob]=useState<any>(null);
  const [busy,setBusy]=useState(false);
  const [blenderPresets,setBlenderPresets]=useState<BlenderPreset[]>([]);
  const [blenderLayers,setBlenderLayers]=useState<BlenderLayer[]>([]);
  const [outline,setOutline]=useState(false);
  const [outlineColor,setOutlineColor]=useState("magenta");
  const [caption,setCaption]=useState("");

  useEffect(()=>{ getJSON<BlenderPreset[]>("/v1/blender/presets").then(setBlenderPresets).catch(console.error); Promise.all([getJSON<Effect[]>("/v1/effects"),getJSON<Plan[]>("/v1/plans")]).then(([fx,ps])=>{setEffects(fx);setPlans(ps);}); },[]);

  const grouped=useMemo(()=>{
    const out:Record<string,Effect[]>={};
    for(const effect of effects) (out[effect.category] ||= []).push(effect);
    return out;
  },[effects]);

  async function analyzeNarrative(){
    if(!audio)return; setBusy(true);
    try{
      const form=new FormData(); form.append("audio",audio); form.append("intelligence_level","3");
      setNarrative(await postForm<NarrativePlan>("/v1/narrative/plan",form));
    }finally{setBusy(false);}
  }

  async function submitRender(){
    if(!audio||videos.length===0)return; setBusy(true);
    try{
      const form=new FormData(); form.append("audio",audio);
      videos.forEach(v=>form.append("videos",v));
      form.append("plan_key",planKey);
      form.append("effects_json",JSON.stringify(selected));
      form.append("overlays_json",JSON.stringify({neural_outline:outline,outline_color:outlineColor,caption}));
      form.append("blender_layers_json",JSON.stringify(blenderLayers));
      form.append("scene_aware","true");
      form.append("narrative_planning","true");
      form.append("automatic_fx","true");
      setJob(await postForm<any>("/v1/renders",form));
    }finally{setBusy(false);}
  }

  return (
    <main className="shell">
      <header className="hero">
        <div>
          <span className="eyebrow">BEATSYNC STUDIO</span>
          <h1>Direct music videos with music intelligence.</h1>
          <p>Upload clips and a soundtrack. BeatSync analyzes rhythm, energy, drops, structure and scene semantics before building the edit.</p>
        </div>
        <div className="statusCard"><span>API</span><strong>{API_BASE.replace(/^https?:\/\//,"")}</strong></div>
      </header>

      <section className="grid two">
        <div className="panel">
          <div className="panelTitle"><span>01</span><h2>Project</h2></div>
          <label className="field">
            <span>Subscription</span>
            <select value={planKey} onChange={e=>setPlanKey(e.target.value)}>
              {plans.map(p=><option key={p.key} value={p.key}>{p.name} · {"$"}{p.monthly_usd}/mo · {p.export_height>=2160?"4K":p.export_height+"p"}</option>)}
            </select>
          </label>
          <label className="dropzone">
            <input type="file" accept="video/*" multiple onChange={e=>setVideos(Array.from(e.target.files||[]))}/>
            <b>{videos.length?videos.length+" video source(s)":"Add video clips"}</b>
            <span>Uploads, generated clips and stock sources can all feed Auto Director.</span>
          </label>
          <label className="dropzone">
            <input type="file" accept="audio/*" onChange={e=>setAudio(e.target.files?.[0]||null)}/>
            <b>{audio?audio.name:"Add soundtrack"}</b>
            <span>Upload now; Suno and AI-DJ providers are exposed through the backend API.</span>
          </label>
          <button className="secondary" disabled={!audio||busy} onClick={analyzeNarrative}>{busy?"Analyzing…":"Generate narrative plan"}</button>
        </div>

        <div className="panel">
          <div className="panelTitle"><span>02</span><h2>Narrative Director</h2></div>
          {!narrative?(
            <div className="empty"><b>No narrative plan yet.</b><p>Analyze the soundtrack to see the proposed visual arc before rendering.</p></div>
          ):(
            <>
              <div className="metricRow">
                <div><small>TEMPO</small><strong>{narrative.tempo.toFixed(1)} BPM</strong></div>
                <div><small>SECTIONS</small><strong>{narrative.sections.length}</strong></div>
              </div>
              <p className="arc">{narrative.arc}</p>
              <div className="timeline">
                {narrative.sections.map(s=>(
                  <article key={s.index} className="timelineItem">
                    <div className="time">{s.start.toFixed(1)}–{s.end.toFixed(1)}s</div>
                    <div><h3>{s.label}</h3><p>{s.intent}</p><div className="chips">{s.preferred_tags.slice(0,4).map(t=><span key={t}>{t}</span>)}</div></div>
                  </article>
                ))}
              </div>
            </>
          )}
        </div>
      </section>

      <section className="panel">
        <div className="panelTitle"><span>03</span><h2>Effect Rack</h2></div>
        <p className="muted">Every effect is independent. The sync label shows which musical signal drives it.</p>
        <div className="effectGroups">
          {Object.entries(grouped).map(([category,items])=>(
            <div className="effectGroup" key={category}>
              <h3>{category}</h3>
              <div className="effectGrid">
                {items.map(effect=>{
                  const active=selected[effect.key]!==undefined;
                  return <div className={"effectCard "+(active?"active":"")} key={effect.key}>
                    <div className="effectTop">
                      <button className="toggle" onClick={()=>setSelected(current=>{const next={...current};if(next[effect.key]!==undefined)delete next[effect.key];else next[effect.key]=effect.default_intensity;return next;})}>{active?"ON":"OFF"}</button>
                      <span>{effect.signal}</span>
                    </div>
                    <h4>{effect.name}</h4><p>{effect.description}</p>
                    {active&&<input type="range" min="0" max="1" step="0.05" value={selected[effect.key]} onChange={e=>setSelected({...selected,[effect.key]:Number(e.target.value)})}/>}
                  </div>
                })}
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="panel">
        <div className="panelTitle"><span>04</span><h2>Blender Simulation Layers</h2></div>
        <p className="muted">Independent neon visuals. Blender workers are required for export; physical fluid/smoke scenes require a Mantaflow bake. Creator/Studio plans only.</p>
        <button className="secondary" disabled={blenderLayers.length>=4} onClick={()=>setBlenderLayers(old=>[...old,{preset:"neon_particles",enabled:true,signal:"treble",intensity:.8,color_a:"cyan",color_b:"magenta",seed:42,quality:"preview"}])}>Add Blender layer</button>
        <div className="effectGrid">
        {blenderLayers.map((layer,i)=><div className="effectCard active" key={i}>
          <div className="effectTop"><b>Layer {i+1}</b><button className="toggle" onClick={()=>setBlenderLayers(ls=>ls.filter((_,j)=>j!==i))}>Remove</button></div>
          <label className="field"><span>Simulation</span><select value={layer.preset} onChange={e=>setBlenderLayers(ls=>ls.map((x,j)=>j===i?{...x,preset:e.target.value,signal:blenderPresets.find(p=>p.key===e.target.value)?.default_signal||"beat"}:x))}>{blenderPresets.map(p=><option key={p.key} value={p.key}>{p.key.replaceAll("_"," ")} · {p.family}</option>)}</select></label>
          <label className="field"><span>Driven by</span><select value={layer.signal} onChange={e=>setBlenderLayers(ls=>ls.map((x,j)=>j===i?{...x,signal:e.target.value}:x))}>{["beat","onset","bass","mids","treble","energy","drop"].map(t=><option key={t}>{t}</option>)}</select></label>
          <label className="field"><span>Intensity {layer.intensity.toFixed(2)}</span><input type="range" min="0" max="1" step=".05" value={layer.intensity} onChange={e=>setBlenderLayers(ls=>ls.map((x,j)=>j===i?{...x,intensity:Number(e.target.value)}:x))}/></label>
          {(["color_a","color_b"] as const).map(k=><label className="field" key={k}><span>{k==="color_a"?"Primary neon":"Secondary neon"}</span><select value={layer[k]} onChange={e=>setBlenderLayers(ls=>ls.map((x,j)=>j===i?{...x,[k]:e.target.value}:x))}>{["cyan","magenta","blue","lime"].map(c=><option key={c}>{c}</option>)}</select></label>)}
          <label className="field"><span>Quality</span><select value={layer.quality} onChange={e=>setBlenderLayers(ls=>ls.map((x,j)=>j===i?{...x,quality:e.target.value}:x))}><option value="preview">Preview</option><option value="final">Final</option></select></label>
        </div>)}
        </div>
      </section>
      <section className="panel">
        <div className="panelTitle"><span>05</span><h2>Optional Neural Outline &amp; Typography</h2></div>
        <label className="field"><span><input type="checkbox" checked={outline} onChange={e=>setOutline(e.target.checked)}/> Enable YOLO body outline</span></label>
        <label className="field"><span>Neon color</span><select value={outlineColor} onChange={e=>setOutlineColor(e.target.value)}>{["magenta","cyan","blue","lime"].map(c=><option key={c}>{c}</option>)}</select></label>
        <label className="field"><span>Animated caption</span><input maxLength={100} value={caption} onChange={e=>setCaption(e.target.value)} placeholder="Short video overlay text"/></label>
      </section>

      <section className="renderBar">
        <div><span className="eyebrow">FINAL OUTPUT</span><h2>Let Intelligent Beat Sync direct the cut.</h2></div>
        <button className="primary" disabled={!audio||videos.length===0||busy} onClick={submitRender}>{busy?"Submitting…":"Create render job"}</button>
      </section>

      {job&&<section className="panel job"><h3>Render job created</h3><pre>{JSON.stringify(job,null,2)}</pre></section>}
    </main>
  );
}
