"use client";

import { useEffect, useMemo, useState } from "react";
import { API_BASE, getJSON, postForm } from "@/lib/api";
import UserMenu from "@/components/UserMenu";

type Effect = { key:string; name:string; category:string; description:string; tier:string; default_intensity:number; signal:string; };
type Plan = { key:string; name:string; monthly_usd:number; export_height:number; watermark:boolean; max_effects:number; intelligent_sync_level:number; features:string[]; };
type NarrativeSection = { index:number; start:number; end:number; label:string; intent:string; preferred_tags:string[]; shot_scale:string; motion_style:string; emotional_tone:string; pacing:string; effect_direction:string[]; seedance_prompt:string; };
type BlenderPreset = {key:string;family:string;default_signal:string};
type AssetLayer = {name:string;source:string;asset_id:string;animation:string;signal:string;intensity:number;color:string;position_x:number;position_y:number;position_z:number;size:number;speed:number;enabled:boolean};
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
  const [assetLayers,setAssetLayers]=useState<AssetLayer[]>([]);
  const [assetFiles,setAssetFiles]=useState<File[]>([]);
  const [motionFiles,setMotionFiles]=useState<File[]>([]);
  const [lyricsFile,setLyricsFile]=useState<File|null>(null);
  const [transcribing,setTranscribing]=useState(false);
  const [transcriptionError,setTranscriptionError]=useState("");
  const [lyrics,setLyrics]=useState<Array<{text:string;start:number;end:number;style:string;font:string;color:string;highlight:string;outline:string;position:string;signal:string;glow:boolean;bounce:boolean}>>([]);
  const [characters,setCharacters]=useState<Array<{name:string;species:string;asset_id:string;animation_id:string;motion:string;signal:string;speed:number;intensity:number;scale:number}>>([]);
  const [workflowPrompt,setWorkflowPrompt]=useState("");
  const [workflowPlan,setWorkflowPlan]=useState<any>(null);
  const [workflowBusy,setWorkflowBusy]=useState(false);
  const [workflowError,setWorkflowError]=useState("");
  const [rodinPrompt,setRodinPrompt]=useState("");
  const [rodinJob,setRodinJob]=useState<any>(null);
  const [rodinBusy,setRodinBusy]=useState(false);
  const [camera,setCamera]=useState({mode:"orbit",signal:"beat",speed:1,intensity:.5,distance:12,elevation:4,target_height:1.5});
  const [motionCues,setMotionCues]=useState<{text:string;start:number;duration:number;style:string;trigger:string;position:string}[]>([]);

  useEffect(()=>{ getJSON<BlenderPreset[]>("/v1/blender/presets").then(setBlenderPresets).catch(console.error); Promise.all([getJSON<Effect[]>("/v1/effects"),getJSON<Plan[]>("/v1/plans")]).then(([fx,ps])=>{setEffects(fx);setPlans(ps);}); },[]);

  const grouped=useMemo(()=>{
    const out:Record<string,Effect[]>={};
    for(const effect of effects) (out[effect.category] ||= []).push(effect);
    return out;
  },[effects]);

  async function planWorkflow(){
    if(!workflowPrompt.trim()||workflowBusy)return;
    setWorkflowBusy(true);setWorkflowError("");
    try{const form=new FormData();form.append("prompt",workflowPrompt);
      setWorkflowPlan(await postForm<any>("/v1/agents/plan",form));
    }catch(e){setWorkflowError(e instanceof Error?e.message:String(e));}
    finally{setWorkflowBusy(false);}
  }

  function applyWorkflow(){
    if(!workflowPlan?.config)return;
    const cfg=workflowPlan.config;
    setBlenderLayers(cfg.blender_layers||[]);
    setMotionCues(cfg.motion_cues||[]);
    if(cfg.lyric_theme)setLyrics(ls=>ls.map(line=>({...line,...cfg.lyric_theme})));
  }

  async function transcribeTrack(){
    if(!audio)return;
    setTranscribing(true);setTranscriptionError("");
    try{
      const f=new FormData();f.append("audio",audio);
      const result=await postForm<{cues:Array<{text:string;start:number;end:number;words:Array<[string,number,number]>}>}>("/v1/lyrics/transcribe",f);
      setLyrics(result.cues.map(c=>({...c,style:"karaoke",font:"sans",color:"#FFFFFF",highlight:"#FF40FF",outline:"#101020",position:"bottom",signal:"beat",glow:true,bounce:true})));
    }catch(e){setTranscriptionError(e instanceof Error?e.message:String(e));}
    finally{setTranscribing(false);}
  }

  async function requestRodin(){
    if(!rodinPrompt.trim()||rodinBusy)return;
    setRodinBusy(true);
    try{const f=new FormData();f.append("prompt",rodinPrompt);f.append("t_pose","true");
      setRodinJob(await postForm<any>("/v1/rodin/generate",f));
    }catch(err){setRodinJob({error:err instanceof Error?err.message:String(err)});}
    finally{setRodinBusy(false);}
  }

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
      form.append("motion_cues_json",JSON.stringify(motionCues));
      form.append("asset_layers_json",JSON.stringify(assetLayers));
      form.append("characters_json",JSON.stringify(characters));
      form.append("camera_json",JSON.stringify(camera));
      form.append("lyrics_json",JSON.stringify(lyrics));
      if(lyricsFile)form.append("lyrics_file",lyricsFile);
      assetFiles.forEach(file=>form.append("assets",file));
      motionFiles.forEach(file=>form.append("motion_files",file));
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


      <section className="panel">
        <div className="panelTitle"><span>AI</span><h2>Prompt Director · Agent Workflows</h2></div>
        <p className="muted">Describe the music video, palette, rhythm and typography. Director, Rhythm, Visual FX, Typography and Quality agents propose a reviewable edit plan. Nothing is rendered or sent to external AI automatically.</p>
        <label className="field"><span>Creative brief</span><textarea rows={3} maxLength={2000} value={workflowPrompt} onChange={e=>setWorkflowPrompt(e.target.value)} placeholder="Cinematic neon cyan music video, bass-reactive spectrum bars, cursive lyrics, display 'Into the night'..."/></label>
        <button className="secondary" onClick={planWorkflow} disabled={workflowBusy||workflowPrompt.trim().length<3}>{workflowBusy?"Planning…":"Generate agent workflow"}</button>
        {workflowError&&<p role="alert">{workflowError}</p>}
        {workflowPlan&&<div>
          <p className="muted">Review specialist agent decisions before applying them to your editor.</p>
          {workflowPlan.steps?.map((step:any,i:number)=><div key={i} className="effectCard"><strong>{step.agent} · {step.action}</strong><p className="muted">{step.rationale}</p><pre style={{whiteSpace:"pre-wrap",overflowWrap:"anywhere"}}>{JSON.stringify(step.output,null,2)}</pre></div>)}
          <button className="secondary" onClick={applyWorkflow}>Apply reviewed workflow to editor</button>
        </div>}
      </section>
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

      <section className="panel">
        <div className="panelTitle"><span>06</span><h2>Explainer Graphics, Reaction Memes &amp; Titles</h2></div>
        <p className="muted">Independent, time-coded graphic and reaction text cues. Media uploads and automated AI script generation require an additional service.</p>
        <button className="secondary" onClick={()=>setMotionCues(xs=>xs.length>=50?xs:[...xs,{text:"",start:0,duration:2,style:"explainer",trigger:"beat",position:"bottom"}])}>Add motion cue</button>
        <div className="effectGrid">{motionCues.map((cue,i)=><div className="effectCard active" key={i}>
          <button className="toggle" onClick={()=>setMotionCues(cs=>cs.filter((_,j)=>i!==j))}>Remove cue</button>
          <label className="field"><span>Text</span><input maxLength={140} value={cue.text} onChange={e=>setMotionCues(cs=>cs.map((x,j)=>j===i?{...x,text:e.target.value}:x))}/></label>
          <label className="field"><span>Start (seconds)</span><input type="number" min="0" max="600" step=".1" value={cue.start} onChange={e=>setMotionCues(cs=>cs.map((x,j)=>j===i?{...x,start:Number(e.target.value)}:x))}/></label>
          <label className="field"><span>Duration (seconds)</span><input type="number" min=".2" max="30" step=".1" value={cue.duration} onChange={e=>setMotionCues(cs=>cs.map((x,j)=>j===i?{...x,duration:Number(e.target.value)}:x))}/></label>
          <label className="field"><span>Style</span><select value={cue.style} onChange={e=>setMotionCues(cs=>cs.map((x,j)=>j===i?{...x,style:e.target.value}:x))}>{["explainer","reaction","lower_third","stat","title"].map(x=><option key={x}>{x}</option>)}</select></label>
          <label className="field"><span>Trigger</span><select value={cue.trigger} onChange={e=>setMotionCues(cs=>cs.map((x,j)=>j===i?{...x,trigger:e.target.value}:x))}>{["beat","bass","mids","treble","onset","drop","energy"].map(x=><option key={x}>{x}</option>)}</select></label>
          <label className="field"><span>Placement</span><select value={cue.position} onChange={e=>setMotionCues(cs=>cs.map((x,j)=>j===i?{...x,position:e.target.value}:x))}>{["top","middle","bottom"].map(x=><option key={x}>{x}</option>)}</select></label>
        </div>)}</div>
      </section>
      <section className="panel">
        <div className="panelTitle"><span>07</span><h2>Beat-Sync 3D Asset Animation Engine</h2></div>
        <p className="muted">Animate Blender primitives or GLB models with independent music-driven transforms. For custom models upload GLB, then select the matching numbered asset ID.</p>
        <label className="dropzone"><input type="file" accept=".glb,model/gltf-binary" multiple onChange={e=>setAssetFiles(Array.from(e.target.files||[]).slice(0,8))}/><b>{assetFiles.length?assetFiles.length+" 3D GLB file(s)":"Upload 3D models (.glb)"}</b></label>
        <p className="muted">{assetFiles.map((f,i)=>"asset_"+i+" — "+f.name).join(" · ")}</p>
        <label className="dropzone"><input type="file" accept=".fbx,.bvh,.glb" multiple onChange={e=>setMotionFiles(Array.from(e.target.files||[]).slice(0,8))}/><b>{motionFiles.length?motionFiles.length+" motion file(s)":"Upload Mixamo FBX / BVH / GLB motions"}</b></label>
        <button className="secondary" disabled={assetLayers.length>=8} onClick={()=>setAssetLayers(xs=>[...xs,{name:"Neon 3D Asset",source:"torus",asset_id:"",animation:"pulse",signal:"bass",intensity:.75,color:"cyan",position_x:0,position_y:0,position_z:0,size:1,speed:1,enabled:true}])}>Add 3D asset</button>
        <div className="effectGrid">{assetLayers.map((asset,i)=><div className="effectCard active" key={i}>
          <div className="effectTop"><strong>Asset {i+1}</strong><button className="toggle" onClick={()=>setAssetLayers(xs=>xs.filter((_,j)=>j!==i))}>Remove</button></div>
          <label className="field"><span>Asset name</span><input maxLength={80} value={asset.name} onChange={e=>setAssetLayers(xs=>xs.map((a,j)=>i===j?{...a,name:e.target.value}:a))}/></label>
          <label className="field"><span>Source</span><select value={asset.source} onChange={e=>setAssetLayers(xs=>xs.map((a,j)=>i===j?{...a,source:e.target.value}:a))}>{["cube","sphere","torus","cone","icosphere","text","glb"].map(k=><option key={k} value={k}>{k}</option>)}</select></label>
          {asset.source==="glb"&&<label className="field"><span>Uploaded model</span><select value={asset.asset_id} onChange={e=>setAssetLayers(xs=>xs.map((a,j)=>i===j?{...a,asset_id:e.target.value}:a))}><option value="">Choose uploaded GLB</option>{assetFiles.map((file,j)=><option key={j} value={"asset_"+j}>{file.name}</option>)}</select></label>}
          <label className="field"><span>Animation</span><select value={asset.animation} onChange={e=>setAssetLayers(xs=>xs.map((a,j)=>i===j?{...a,animation:e.target.value}:a))}>{["pulse","spin","bounce","orbit","wobble","scale","material_glow"].map(x=><option key={x}>{x}</option>)}</select></label>
          <label className="field"><span>Signal</span><select value={asset.signal} onChange={e=>setAssetLayers(xs=>xs.map((a,j)=>i===j?{...a,signal:e.target.value}:a))}>{["beat","bass","mids","treble","onset","drop","energy"].map(x=><option key={x}>{x}</option>)}</select></label>
          <label className="field"><span>Neon</span><select value={asset.color} onChange={e=>setAssetLayers(xs=>xs.map((a,j)=>i===j?{...a,color:e.target.value}:a))}>{["cyan","magenta","blue","lime"].map(x=><option key={x}>{x}</option>)}</select></label>
          {(["intensity","size","speed","position_x","position_y","position_z"] as const).map(field=><label className="field" key={field}><span>{field}: {asset[field]}</span><input type="range" min={field==="intensity"?0:(field==="size"||field==="speed")?0.1:-10} max={field==="intensity"?1:field==="size"||field==="speed"?5:10} step=".1" value={asset[field]} onChange={e=>setAssetLayers(xs=>xs.map((a,j)=>i===j?{...a,[field]:Number(e.target.value)}:a))}/></label>)}
        </div>)}</div>
      </section>
      <section className="panel">
        <div className="panelTitle"><span>08</span><h2>Characters, Animals &amp; Camera Choreography</h2></div>
        <p className="muted">Upload rigged GLB characters or motion clips in the 3D asset upload panel. Mixamo downloads can be converted to GLB in Blender. Human and animal tracks are independent. Cross-species skeletal retargeting requires a compatible external model worker.</p>
        <button className="secondary" disabled={characters.length>=8} onClick={()=>setCharacters(xs=>[...xs,{name:"Dancer",species:"human",asset_id:"",animation_id:"",motion:"dance",signal:"beat",speed:1,intensity:.75,scale:1}])}>Add dancer or animal</button>
        <div className="effectGrid">{characters.map((c,i)=><div className="effectCard active" key={i}>
          <button className="toggle" onClick={()=>setCharacters(xs=>xs.filter((_,j)=>j!==i))}>Remove</button>
          <label className="field"><span>Performer</span><input maxLength={80} value={c.name} onChange={e=>setCharacters(xs=>xs.map((v,j)=>j===i?{...v,name:e.target.value}:v))}/></label>
          {(["species","motion","signal"] as const).map(field=><label className="field" key={field}><span>{field}</span><select value={c[field]} onChange={e=>setCharacters(xs=>xs.map((v,j)=>j===i?{...v,[field]:e.target.value}:v))}>{(field==="species"?["human","quadruped","bird","other"]:field==="motion"?["dance","idle","walk","run","jump","spin","imported"]:["beat","onset","bass","mids","treble","energy","drop"]).map(value=><option key={value}>{value}</option>)}</select></label>)}
          <label className="field"><span>Character GLB</span><select value={c.asset_id} onChange={e=>setCharacters(xs=>xs.map((v,j)=>j===i?{...v,asset_id:e.target.value}:v))}><option value="">Choose model</option>{assetFiles.map((file,j)=><option value={"asset_"+j} key={j}>{file.name}</option>)}</select></label>
          {c.motion==="imported"&&<label className="field"><span>Rigged animation GLB (matching skeleton)</span><select value={c.animation_id} onChange={e=>setCharacters(xs=>xs.map((v,j)=>j===i?{...v,animation_id:e.target.value}:v))}><option value="">Choose animation</option>{motionFiles.map((file,j)=><option value={"motion_"+j} key={j}>{file.name}</option>)}</select></label>}
          {(["speed","intensity","scale"] as const).map(field=><label className="field" key={field}><span>{field}: {c[field]}</span><input type="range" min={field==="intensity"?0:0.1} max={field==="intensity"?1:field==="speed"?4:10} step=".05" value={c[field]} onChange={e=>setCharacters(xs=>xs.map((v,j)=>j===i?{...v,[field]:Number(e.target.value)}:v))}/></label>)}
        </div>)}</div>
        <h3>Music-controlled camera</h3>
        <div className="effectGrid">
          <label className="field"><span>Camera move</span><select value={camera.mode} onChange={e=>setCamera(v=>({...v,mode:e.target.value}))}>{["static","orbit","dolly","truck","crane","handheld","zoom_pulse"].map(m=><option key={m}>{m}</option>)}</select></label>
          <label className="field"><span>Camera music signal</span><select value={camera.signal} onChange={e=>setCamera(v=>({...v,signal:e.target.value}))}>{["beat","onset","bass","mids","treble","energy","drop"].map(m=><option key={m}>{m}</option>)}</select></label>
          {(["speed","intensity","distance","elevation","target_height"] as const).map(field=><label className="field" key={field}><span>{field}: {camera[field]}</span><input type="range" min={field==="speed"?0.1:field==="intensity"?0:field==="distance"?2:-10} max={field==="speed"?5:field==="intensity"?1:field==="distance"?40:20} step=".1" value={camera[field]} onChange={e=>setCamera(v=>({...v,[field]:Number(e.target.value)}))}/></label>)}
        </div>
      </section>
      <section className="panel">
        <div className="panelTitle"><span>09</span><h2>Rodin AI Character / 3D Asset Generation</h2></div>
        <p className="muted">Generate a rig-ready T-pose model using your configured Rodin API key. This is a paid external generation request, submitted only when you click Generate.</p>
        <label className="field"><span>Character or 3D asset prompt</span><input value={rodinPrompt} maxLength={1024} onChange={e=>setRodinPrompt(e.target.value)} placeholder="Stylized cyberpunk dancer in a neutral T-pose, clean topology"/></label>
        <button className="secondary" disabled={rodinBusy||!rodinPrompt.trim()} onClick={requestRodin}>{rodinBusy?"Generating…":"Generate with Rodin (provider credits may apply)"}</button>
        {rodinJob&&<pre>{JSON.stringify(rodinJob,null,2)}</pre>}
        <p className="muted">Once generation completes, obtain the GLB through the provider and upload it using the 3D asset panel above. Automatically importing generated files requires project-scoped storage integration.</p>
      </section>
      <section className="panel">
        <div className="panelTitle"><span>10</span><h2>Beat-Synced Lyrics &amp; Calligraphy</h2></div>
        <p className="muted">Timed LRC/SRT subtitles or manual lyrics, per-line font style, neon colours, glow and beat-reactive karaoke.</p>
        <label className="dropzone"><input type="file" accept=".lrc,.srt" onChange={e=>setLyricsFile(e.target.files?.[0]||null)}/><b>{lyricsFile?.name||"Upload LRC or SRT lyrics"}</b></label>
        <button className="secondary" disabled={!audio||transcribing} onClick={transcribeTrack}>{transcribing?"Transcribing…":"Auto-transcribe words (Creator/Studio)"}</button>
        {transcriptionError&&<p role="alert">{transcriptionError}</p>}
        <button className="secondary" disabled={lyrics.length>=500} onClick={()=>setLyrics(ls=>[...ls,{text:"New lyric line",start:0,end:3,style:"karaoke",font:"sans",color:"#FFFFFF",highlight:"#FF40FF",outline:"#101020",position:"bottom",signal:"beat",glow:true,bounce:true}])}>Add timed lyric</button>
        <div className="effectGrid">{lyrics.map((cue,i)=><div className="effectCard active" key={i}>
          <button className="toggle" onClick={()=>setLyrics(ls=>ls.filter((_,j)=>j!==i))}>Remove</button>
          <label className="field"><span>Lyrics</span><input maxLength={240} value={cue.text} onChange={e=>setLyrics(ls=>ls.map((c,j)=>j===i?{...c,text:e.target.value}:c))}/></label>
          {(["start","end"] as const).map(k=><label className="field" key={k}><span>{k} (seconds)</span><input type="number" min="0" max="36000" step=".1" value={cue[k]} onChange={e=>setLyrics(ls=>ls.map((c,j)=>j===i?{...c,[k]:Number(e.target.value)}:c))}/></label>)}
          {(["style","font","position","signal"] as const).map(k=><label className="field" key={k}><span>{k}</span><select value={cue[k]} onChange={e=>setLyrics(ls=>ls.map((c,j)=>j===i?{...c,[k]:e.target.value}:c))}>{(k==="style"?["karaoke","calligraphy","brush","neon_script","serif","bold_pop","gothic","minimal"]:k==="font"?["sans","serif","script","handwriting","display","mono"]:k==="position"?["top","middle","bottom"]:["beat","onset","bass","mids","treble","energy","drop"]).map(v=><option key={v}>{v}</option>)}</select></label>)}
          {(["color","highlight","outline"] as const).map(k=><label className="field" key={k}><span>{k}</span><input type="color" value={cue[k]} onChange={e=>setLyrics(ls=>ls.map((c,j)=>j===i?{...c,[k]:e.target.value}:c))}/></label>)}
          {(["glow","bounce"] as const).map(k=><label className="field" key={k}><span><input type="checkbox" checked={cue[k]} onChange={e=>setLyrics(ls=>ls.map((c,j)=>j===i?{...c,[k]:e.target.checked}:c))}/> {k}</span></label>)}
        </div>)}</div>
      </section>
      <section className="renderBar">
        <div><span className="eyebrow">FINAL OUTPUT</span><h2>Let Intelligent Beat Sync direct the cut.</h2></div>
        <button className="primary" disabled={!audio||videos.length===0||busy} onClick={submitRender}>{busy?"Submitting…":"Create render job"}</button>
      </section>

      {job&&<section className="panel job"><h3>Render job created</h3><pre>{JSON.stringify(job,null,2)}</pre></section>}
    </main>
  );
}
