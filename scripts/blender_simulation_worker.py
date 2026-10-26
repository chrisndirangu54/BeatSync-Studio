"""Blender headless worker for procedural simulation previews.

Run: blender -b -t 4 --python scripts/blender_simulation_worker.py -- manifest.json output_dir
Uses trusted JSON only. Heavy Mantaflow liquid/gas preset names are not silently
rendered as physical simulations; they require the dedicated simulation worker.
"""
import bpy, json, math, random, sys
from pathlib import Path
from mathutils import Vector

args=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
if len(args)!=2: raise SystemExit("Usage: -- manifest.json output_dir")
manifest=json.loads(Path(args[0]).read_text())
out=Path(args[1]).resolve()
out.mkdir(parents=True,exist_ok=True)
layers=manifest.get("layers",[])
allowed={"neon_particles","particle_vortex","neon_fireworks","spectrum_bars",
         "radial_spectrum","wave_tunnel","oscilloscope","audio_terrain",
         "liquid_ribbons","reactive_metal","neon_displacement","shockwave"}
unsupported=[x["preset"] for x in layers if x["preset"] not in allowed]
if unsupported: raise SystemExit("Physical simulation worker required for: "+", ".join(unsupported))
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene
scene.render.engine="BLENDER_EEVEE_NEXT"
scene.render.resolution_x=int(manifest["width"])
scene.render.resolution_y=int(manifest["height"])
scene.render.resolution_percentage=100
scene.render.film_transparent=True
scene.render.image_settings.file_format="PNG"
scene.render.image_settings.color_mode="RGBA"
scene.render.fps=int(manifest["fps"])
scene.world.color=(0,0,0)
bpy.ops.object.camera_add(location=(0,-17,6))
camera=bpy.context.object
direction=Vector((0,0,0))-camera.location
camera.rotation_euler=direction.to_track_quat('-Z','Y').to_euler()
camera.data.type='ORTHO'
camera.data.ortho_scale=15
scene.camera=camera

def material(name,color):
    m=bpy.data.materials.new(name)
    m.diffuse_color=color
    m.use_nodes=True
    nodes=m.node_tree.nodes
    nodes.clear()
    o=nodes.new("ShaderNodeOutputMaterial")
    e=nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value=color
    e.inputs["Strength"].default_value=3
    m.node_tree.links.new(e.outputs[0],o.inputs["Surface"])
    return m

objects=[]
for li,layer in enumerate(layers):
    random.seed(layer.get("seed",42))
    preset=layer["preset"]
    colors=layer["palette"]
    count=80 if preset in {"neon_particles","particle_vortex","neon_fireworks"} else 36
    count=12 if preset in {"reactive_metal","neon_displacement","shockwave"} else count
    mats=[material("neon_%d_%d"%(li,j),tuple(c)) for j,c in enumerate(colors)]
    group=[]
    for j in range(count):
        a=2*math.pi*j/count
        radius=2.1+(j%9)*0.19
        if preset in {"spectrum_bars","wave_tunnel","audio_terrain","oscilloscope"}:
            bpy.ops.mesh.primitive_cube_add(size=1,location=((j-count/2)*.22,0,0))
            obj=bpy.context.object
            obj.scale=(.075,.12,.4)
        else:
            bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1,radius=.09,location=(radius*math.cos(a),radius*math.sin(a),0))
            obj=bpy.context.object
        obj.name="%s_%d_%d"%(preset,li,j)
        obj.data.materials.append(mats[j%2])
        group.append((obj,a,radius))
    objects.append((layer,group))
samples=manifest.get("audio_samples",[])
for frame,s in enumerate(samples,1):
    scene.frame_set(frame)
    for layer,group in objects:
        v=max(0.0,min(1.0,float(s.get(layer["signal"],0.0))))*float(layer["intensity"])
        preset=layer["preset"]
        for j,(obj,a,r) in enumerate(group):
            if preset in {"spectrum_bars","audio_terrain"}:
                obj.scale.z=.1+2.5*v*(.5+.5*math.sin(j*.4+frame*.09)**2)
                obj.location.z=obj.scale.z*.5
            elif preset=="oscilloscope":
                obj.location.z=2*v*math.sin(j*.45+frame*.13)
            elif preset=="wave_tunnel":
                obj.location.z=1.6*v*math.sin(j*.5+frame*.12)
            elif preset=="neon_fireworks":
                blast=v*4
                obj.location=(blast*math.cos(a),blast*math.sin(a),.5+blast*math.sin(a*.5))
            elif preset=="shockwave":
                obj.location=(math.cos(a)*(2+v*5),math.sin(a)*(2+v*5),0)
            else:
                phase=frame*.035*(1+v)
                obj.location=(r*math.cos(a+phase),r*math.sin(a+phase),v*2*math.sin(a*4+phase))
            obj.keyframe_insert(data_path="location",frame=frame)
            obj.keyframe_insert(data_path="scale",frame=frame)
    scene.render.filepath=str(out/("frame_%06d.png"%frame))
    bpy.ops.render.render(write_still=True)
