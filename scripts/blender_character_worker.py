"""Blender headless character animation from validated, local manifest."""
import bpy,json,math,sys
from blender_retarget import retarget_action, bake_retarget
from pathlib import Path
from mathutils import Vector
a=sys.argv[sys.argv.index("--")+1:]
m=json.loads(Path(a[0]).read_text()); destination=Path(a[1]);destination.mkdir(parents=True,exist_ok=True)
root=Path(m["asset_root"]).resolve()
bpy.ops.object.select_all(action="SELECT");bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene;scene.render.engine="BLENDER_EEVEE_NEXT" if bpy.app.version >= (4,2,0) else "BLENDER_EEVEE"
scene.render.resolution_x=m["width"];scene.render.resolution_y=m["height"];scene.render.resolution_percentage=100
scene.render.film_transparent=True;scene.render.fps=m["fps"]
scene.render.image_settings.file_format="PNG";scene.render.image_settings.color_mode="RGBA"
def safe_path(identifier):
    path=m.get("asset_paths",{}).get(identifier)
    if not path: raise RuntimeError("Missing project-scoped asset")
    p=Path(path).resolve()
    if p.suffix.lower() not in {".glb",".fbx",".bvh"} or not p.is_file():
        raise RuntimeError("Invalid motion asset")
    if not any(folder in p.parents for folder in [root,root.parent/"motions"]):
        raise RuntimeError("Asset outside project workspace")
    return p

def import_motion(path):
    ext=path.suffix.lower()
    if ext==".glb": bpy.ops.import_scene.gltf(filepath=str(path))
    elif ext==".fbx": bpy.ops.import_scene.fbx(filepath=str(path))
    elif ext==".bvh": bpy.ops.import_anim.bvh(filepath=str(path))
    else: raise RuntimeError("Unsupported animation type")
tracks=[]
for spec in m["characters"]:
    before=set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(safe_path(spec["asset_id"])))
    imported=list(set(bpy.data.objects)-before)
    bpy.ops.object.empty_add(location=(spec["position_x"],spec["position_y"],spec["position_z"]))
    parent=bpy.context.object
    roots=[obj for obj in imported if obj.parent not in imported]
    for obj in roots:obj.parent=parent
    armatures=[o for o in imported if o.type=="ARMATURE"]
    if spec["motion"]=="imported" and spec["animation_id"]:
        # Source animation must be a rigged GLB with a compatible skeleton.
        before_motion=set(bpy.data.objects)
        import_motion(safe_path(spec["animation_id"]))
        motion_arms=[o for o in set(bpy.data.objects)-before_motion if o.type=="ARMATURE"]
        if armatures and motion_arms:
            source=motion_arms[0];target=armatures[0]
            # Explicit name correspondence permits constrained rotation retargeting.
            if source.animation_data and source.animation_data.action and {b.name for b in source.data.bones}=={b.name for b in target.data.bones}:
                target.animation_data_create()
                target.animation_data.action=source.animation_data.action
            elif source.animation_data and source.animation_data.action:
                from collections import OrderedDict
                def normalized(name):return name.lower().replace("mixamorig:","").replace("_","").replace(" ","")
                target_names={normalized(b.name):b.name for b in target.data.bones}
                mapping=OrderedDict((b.name,target_names[normalized(b.name)]) for b in source.data.bones if normalized(b.name) in target_names)
                if len(mapping)>=4:
                    retarget_action(source,target,mapping,preserve_root=spec.get("root_motion",False))
                    bake_retarget(scene,target,1,len(m["audio_samples"]))
                else:
                    raise RuntimeError("Insufficient skeleton correspondence; external retargeting is required")
        for obj in set(bpy.data.objects)-before_motion: obj.hide_render=True
    tracks.append((parent,spec,armatures))
bpy.ops.object.camera_add(location=(0,-12,5))
camera=bpy.context.object;scene.camera=camera
bpy.ops.object.light_add(type="AREA",location=(1,-5,8));bpy.context.object.data.energy=2000
for frame,samples in enumerate(m["audio_samples"],1):
    scene.frame_set(frame);t=(frame-1)/m["fps"]
    for parent,spec,arms in tracks:
        pulse=float(samples.get(spec["signal"],0))*spec["intensity"]
        speed=spec["speed"]; motion=spec["motion"]
        parent.location=(spec["position_x"],spec["position_y"],spec["position_z"])
        parent.rotation_euler=(0,0,0);parent.scale=(spec["scale"]*(1+.15*pulse),)*3
        phase=2*math.pi*t*speed
        if motion in {"dance","spin"}:
            parent.rotation_euler.z=math.sin(phase)*(.2+pulse*.5) if motion=="dance" else phase
            if motion=="dance":parent.location.z+=abs(math.sin(phase))*pulse*.3
        elif motion in {"walk","run"}:
            parent.location.x+=t*speed*(1+pulse)
            parent.rotation_euler.z=.05*math.sin(phase)
        elif motion=="jump":parent.location.z+=abs(math.sin(phase))*pulse*2
        # Armature action plays with speed scaling using remapped action-strip timing in future.
    camera_mode=m["camera"]["mode"];strength=float(samples.get(m["camera"]["signal"],0))*m["camera"]["intensity"]
    distance=m["camera"]["distance"];elev=m["camera"]["elevation"];a=t*m["camera"]["speed"]*.6
    camera.location=(0,-distance,elev)
    if camera_mode=="orbit":camera.location=(distance*math.sin(a),-distance*math.cos(a),elev)
    elif camera_mode=="dolly":camera.location.y=-distance+strength*4
    elif camera_mode=="truck":camera.location.x=math.sin(a)*strength*5
    elif camera_mode=="crane":camera.location.z=elev+strength*4
    elif camera_mode=="handheld":camera.location.x=.2*strength*math.sin(a*23)
    elif camera_mode=="zoom_pulse":camera.location.y=-max(2,distance-strength*3)
    camera.rotation_euler=(Vector((0,0,m["camera"]["target_height"]))-camera.location).to_track_quat("-Z","Y").to_euler()
    scene.render.filepath=str(destination/("frame_%06d.png"%frame))
    bpy.ops.render.render(write_still=True)
