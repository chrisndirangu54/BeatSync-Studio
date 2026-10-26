"""Headless Blender procedural 3D asset animation worker.
Blender executable runs only this reviewed script, reading a bounded JSON manifest.
"""
import bpy, json, math, sys
from pathlib import Path
from mathutils import Vector

args=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
if len(args)!=2: raise SystemExit("Need manifest and output directory")
manifest=json.loads(Path(args[0]).read_text())
output=Path(args[1]).resolve();output.mkdir(parents=True,exist_ok=True)
assets=manifest["assets"]
frames=manifest["audio_samples"]
if len(assets)>8 or len(frames)>36000: raise SystemExit("Asset limits exceeded")
bpy.ops.object.select_all(action="SELECT");bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene
scene.render.engine="BLENDER_EEVEE_NEXT" if bpy.app.version >= (4,2,0) else "BLENDER_EEVEE"
scene.render.film_transparent=True
scene.render.resolution_x=int(manifest["width"])
scene.render.resolution_y=int(manifest["height"])
scene.render.resolution_percentage=100
scene.render.image_settings.file_format="PNG"
scene.render.image_settings.color_mode="RGBA"
scene.render.fps=int(manifest["fps"])
bpy.ops.object.camera_add(location=(0,-16,5))
camera=bpy.context.object
camera.rotation_euler=(Vector((0,0,0))-camera.location).to_track_quat("-Z","Y").to_euler()
camera.data.type="ORTHO";camera.data.ortho_scale=17
scene.camera=camera
bpy.ops.object.light_add(type="AREA",location=(0,-6,8));bpy.context.object.data.energy=1500

colors={"cyan":(0.0,1.0,1.0,1.0),"magenta":(1.0,.06,.75,1.0),
        "blue":(.04,.2,1,1),"lime":(.35,1,.12,1)}

def emitter(color):
    mat=bpy.data.materials.new("BeatSync Neon")
    mat.use_nodes=True
    nodes=mat.node_tree.nodes;nodes.clear()
    out=nodes.new("ShaderNodeOutputMaterial")
    e=nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value=colors[color]
    e.inputs["Strength"].default_value=3
    mat.node_tree.links.new(e.outputs[0],out.inputs["Surface"])
    return mat,e

objects=[]
for spec in assets:
    source=spec["source"]
    before=set(bpy.data.objects)
    if source=="cube": bpy.ops.mesh.primitive_cube_add()
    elif source=="sphere": bpy.ops.mesh.primitive_uv_sphere_add(segments=32,ring_count=16)
    elif source=="torus": bpy.ops.mesh.primitive_torus_add()
    elif source=="cone": bpy.ops.mesh.primitive_cone_add()
    elif source=="icosphere": bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2)
    elif source=="text":
        bpy.ops.object.text_add()
        bpy.context.object.data.body=spec["name"]
        bpy.context.object.data.extrude=.05
    elif source=="glb":
        asset=Path(manifest["asset_paths"][spec["asset_id"]]).resolve()
        root=Path(manifest["asset_root"]).resolve()
        if root not in asset.parents or not asset.is_file() or asset.suffix.lower()!=".glb":
            raise SystemExit("Asset path outside the job sandbox")
        bpy.ops.import_scene.gltf(filepath=str(asset))
    else: raise SystemExit("Unsupported asset")
    imported=list(set(bpy.data.objects)-before)
    if not imported: raise SystemExit("No mesh imported")
    bpy.ops.object.empty_add(location=(spec["position_x"],spec["position_y"],spec["position_z"]))
    pivot=bpy.context.object
    pivot.name="MusicDriven_"+spec["name"]
    for obj in imported:
        obj.parent=pivot
        if obj.type in {"MESH","FONT"}:
            mat,node=emitter(spec["color"])
            obj.data.materials.clear()
            obj.data.materials.append(mat)
    objects.append((pivot,spec))
for i,s in enumerate(frames,1):
    scene.frame_set(i)
    t=(i-1)/scene.render.fps
    for pivot,spec in objects:
        v=float(s.get(spec["signal"],0))*spec["intensity"]
        speed=spec["speed"];a=2*math.pi*t*speed
        position=(spec["position_x"],spec["position_y"],spec["position_z"])
        pivot.location=position;pivot.rotation_euler=(0,0,0)
        pivot.scale=(spec["size"],)*3
        animation=spec["animation"]
        if animation in {"pulse","scale","material_glow"}:
            size=spec["size"]*(1+v*.9)
            pivot.scale=(size,)*3
        elif animation=="spin": pivot.rotation_euler=(v*.2,a*(.2+v),a)
        elif animation=="bounce": pivot.location.z=position[2]+abs(math.sin(a))*v*2
        elif animation=="orbit":
            pivot.location.x=position[0]+math.cos(a)*v*2
            pivot.location.y=position[1]+math.sin(a)*v*2
        elif animation=="wobble": pivot.rotation_euler=(math.sin(a)*v,math.cos(a)*v,0)
    scene.render.filepath=str(output/("frame_%06d.png"%i))
    bpy.ops.render.render(write_still=True)
