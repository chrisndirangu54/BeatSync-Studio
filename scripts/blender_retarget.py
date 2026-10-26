"""Blender animation retarget helpers, to be executed by the trusted character worker.

Uses constraints for per-bone rotation transfers and optional root translation.
Supports matched armatures with different bone labels via explicit mapping;
rest-pose calibration and advanced IK must be performed before use.
"""
def retarget_action(source, target, mapping, *, preserve_root=True):
    import bpy
    if source.type!="ARMATURE" or target.type!="ARMATURE":
        raise ValueError("Retargeting requires armatures")
    if not source.animation_data or not source.animation_data.action:
        raise ValueError("Source armature has no animation")
    if not mapping:
        raise ValueError("No valid bone mapping")
    constraints=[]
    for source_name,target_name in mapping.items():
        if source_name not in source.pose.bones or target_name not in target.pose.bones:
            continue
        target_bone=target.pose.bones[target_name]
        constraint=target_bone.constraints.new("COPY_ROTATION")
        constraint.target=source
        constraint.subtarget=source_name
        constraint.target_space="LOCAL"
        constraint.owner_space="LOCAL"
        constraints.append((target_bone,constraint))
    if not constraints:
        raise ValueError("No matching target bones")
    if preserve_root:
        first_source,first_target=next(iter(mapping.items()))
        if first_source in source.pose.bones and first_target in target.pose.bones:
            c=target.pose.bones[first_target].constraints.new("COPY_LOCATION")
            c.target=source;c.subtarget=first_source
            c.target_space="POSE";c.owner_space="POSE"
            constraints.append((target.pose.bones[first_target],c))
    return constraints

def bake_retarget(scene, armature, frame_start, frame_end):
    import bpy
    bpy.ops.object.select_all(action="DESELECT")
    armature.select_set(True)
    bpy.context.view_layer.objects.active=armature
    bpy.ops.nla.bake(frame_start=frame_start,frame_end=frame_end,
                     only_selected=False,visual_keying=True,
                     clear_constraints=True,use_current_action=False,
                     bake_types={"POSE"})
