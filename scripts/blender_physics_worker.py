"""Headless Blender Mantaflow fluid/gas presets. Usage:
blender -b -t 4 --python scripts/blender_physics_worker.py -- manifest.json output_dir

Cycles CPU/GPU configuration is deployment-specific. Bake first, then render;
this worker is designed for bounded isolated jobs (one physical layer per job).
"""
import bpy, json, sys, math
from pathlib import Path
from mathutils import Vector

args=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
if len(args)!=2: raise SystemExit("Provide manifest and output folder")
m=json.loads(Path(args[0]).read_text()); out=Path(args[1]).resolve(); out.mkdir(parents=True,exist_ok=True)
layers=[x for x in m["layers"] if x["family"] in {"gas_sim","liquid_sim"}]
if len(layers)!=1: raise SystemExit("Physical worker requires exactly one gas/liquid layer")
layer=layers[0]; preset=layer["preset"]
if preset not in {"ink_mixing","dual_smoke_mix","smoke_vortex","mushroom_cloud","fire_burst"}:
    raise SystemExit("Unsupported physics preset")
fps=int(m["fps"]); signals=m.get("audio_samples",[])
if not signals: raise SystemExit("Missing soundtrack control samples")
bpy.ops.object.select_all(action="SELECT"); bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene; scene.render.engine="BLENDER_EEVEE_NEXT"
scene.render.resolution_x=int(m["width"]);scene.render.resolution_y=int(m["height"])
scene.render.resolution_percentage=100
scene.render.film_transparent=True;scene.render.fps=fps
scene.frame_end=len(signals)
scene.render.image_settings.file_format="PNG"
scene.render.image_settings.color_mode="RGBA"
bpy.ops.object.camera_add(location=(0,-13,5))
camera=bpy.context.object;camera.rotation_euler=(Vector((0,0,1.5))-camera.location).to_track_quat('-Z','Y').to_euler()
scene.camera=camera
bpy.ops.object.light_add(type="AREA",location=(0,-3,7));bpy.context.object.data.energy=2000
def material(name,col):
    mat=bpy.data.materials.new(name);mat.diffuse_color=tuple(col);return mat
colors=layer["palette"]
# Two independently controlled inflows produce contrasting plume colors.
flows=[]
for index in range(2):
    x=(-.95 if index==0 else .95)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=.45,location=(x,0,.4))
    emitter=bpy.context.object;emitter.name="BeatEmitter_%d"%index
    mod=emitter.modifiers.new("FluidFlow","FLUID");mod.fluid_type="FLOW"
    mod.flow_settings.flow_type="LIQUID" if preset=="ink_mixing" else ("FIRE" if preset=="fire_burst" else "SMOKE")
    mod.flow_settings.flow_behavior="INFLOW"
    mod.flow_settings.use_initial_velocity=True
    mod.flow_settings.velocity_coord=(.6 if index==0 else -.6,0,1.0)
    mod.flow_settings.flow_source="MESH"
    if preset!="ink_mixing":
        mod.flow_settings.smoke_color=tuple(colors[index][:3])
    emitter.hide_render=True
    flows.append(mod.flow_settings)
bpy.ops.mesh.primitive_cube_add(size=2,location=(0,0,2.5))
domain=bpy.context.object;domain.name="BeatSyncFluidDomain";domain.scale=(3.6,2.6,3.2)
bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
mod=domain.modifiers.new("MantaflowDomain","FLUID");mod.fluid_type="DOMAIN"
settings=mod.domain_settings
settings.domain_type="LIQUID" if preset=="ink_mixing" else "GAS"
settings.cache_frame_start=1;settings.cache_frame_end=len(signals)
settings.cache_directory=str(out/"cache")
settings.cache_type="MODULAR"
settings.cache_data_format="UNI" if preset!="ink_mixing" else "UNI"
settings.resolution_max=32 if layer["quality"]=="preview" else 96
if preset=="ink_mixing":
    settings.use_mesh=True
    settings.cache_mesh_format="BOBJECT"
else:
    settings.use_noise=True
    settings.vorticity=.35 if preset=="dual_smoke_mix" else 1.5
# Render a colored volume for gas. Multiple inflows mix physically in a single
# domain; smoke color is transported by the gas solver. Liquid dye advection remains a separate requirement.
if preset!="ink_mixing":
    mat=bpy.data.materials.new("VolumetricNeonMix");mat.use_nodes=True
    n=mat.node_tree.nodes;n.clear()
    output=n.new("ShaderNodeOutputMaterial");vol=n.new("ShaderNodeVolumePrincipled")
    volume_color=n.new("ShaderNodeAttribute")
    volume_color.attribute_name="color"
    mat.node_tree.links.new(volume_color.outputs["Color"],vol.inputs["Color"])
    vol.inputs["Density"].default_value=1.6
    mat.node_tree.links.new(vol.outputs["Volume"],output.inputs["Volume"])
    domain.data.materials.append(mat)
for idx,s in enumerate(signals,1):
    amp=float(s.get(layer["signal"],0))*float(layer["intensity"])
    for i,flow in enumerate(flows):
        flow.density=max(.05,.25+amp*1.7)
        flow.keyframe_insert(data_path="density",frame=idx)
    if preset=="mushroom_cloud":
        # Rising, broadening plumes through inflow-rate and vertical velocity.
        for flow in flows: flow.velocity_coord=(0,0,2.2)
    if preset=="smoke_vortex": settings.vorticity=1.8
scene.frame_set(1)
bpy.context.view_layer.objects.active=domain
bpy.ops.object.select_all(action="DESELECT");domain.select_set(True)
try:
    bpy.ops.fluid.bake_data()
    if preset=="ink_mixing": bpy.ops.fluid.bake_mesh()
    elif settings.use_noise: bpy.ops.fluid.bake_noise()
except Exception as exc:
    raise RuntimeError("Mantaflow bake failed: %s"%exc)
for index in range(1,len(signals)+1):
    scene.frame_set(index)
    scene.render.filepath=str(out/("frame_%06d.png"%index))
    bpy.ops.render.render(write_still=True)
