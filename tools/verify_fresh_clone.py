"""Fresh-clone verification for Motion Texture Studio (Blender 5.2+).

Run from the repository root with Blender in the background:

    BLENDER_USER_CONFIG=/tmp/mts-config \
    BLENDER_USER_SCRIPTS=/tmp/mts-scripts \
    /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup \
      --python tools/verify_fresh_clone.py

The script installs the add-on from this clone, enables it, builds a cube,
applies a still, keys the Scroll X preset, fits UVs, loads a two-frame image
sequence, and saves/loads a preset. It prints PASS/FAIL for each check.
Baking is verified separately in the GUI because Blender's OpenGL render is
unavailable in background mode.
"""

import os
import shutil
import sys
import tempfile
import traceback

import bpy

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADDON = os.path.join(ROOT, "motion_texture_studio.py")
ASSET = os.path.join(ROOT, "assets", "test_texture.png")

results = []


def check(name, condition, detail=""):
    results.append(bool(condition))
    print(("PASS" if condition else "FAIL") + " :: " + name + ((" :: " + detail) if detail else ""))


try:
    print("repo:", ROOT)
    check("add-on exists in clone", os.path.isfile(ADDON), ADDON)
    check("test texture exists in clone", os.path.isfile(ASSET), ASSET)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    result = bpy.ops.preferences.addon_install(filepath=ADDON)
    check("Install from Disk succeeds", result == {"FINISHED"}, repr(result))
    result = bpy.ops.preferences.addon_enable(module="motion_texture_studio")
    check("add-on enables", result == {"FINISHED"}, repr(result))
    check("sidebar settings are registered", hasattr(bpy.types.Object, "motion_texture"))

    bpy.ops.mesh.primitive_cube_add(size=2.0)
    obj = bpy.context.view_layer.objects.active
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    settings = obj.motion_texture
    settings.image = bpy.data.images.load(ASSET)
    settings.source_path = ASSET
    settings.source_mode = "STILL"

    result = bpy.ops.motiontexture.apply()
    check("Apply to Selected", result == {"FINISHED"}, repr(result))
    mat = bpy.data.materials.get("MotionTexture_Cube")
    check("material is MotionTexture_<object>", mat is not None, str(mat))
    check("shader graph is built", mat is not None and mat.node_tree.nodes.get("MT_BSDF") is not None)
    check("faces use the material",
          mat is not None and all(p.material_index == obj.data.materials.find(mat.name) for p in obj.data.polygons))
    check("UV layer exists", obj.data.uv_layers.active is not None)

    result = bpy.ops.motiontexture.motion_preset(preset="SCROLL_X")
    check("Scroll X preset", result == {"FINISHED"}, repr(result))
    import motion_texture_studio as mts
    action = mat.node_tree.animation_data.action if mat.node_tree.animation_data else None
    curves = list(mts._iter_fcurves(action)) if action else []
    check("shader keys are created", len(curves) > 0, "%d curves" % len(curves))
    check("CYCLES repeats the cycle", any(any(m.type == "CYCLES" for m in fc.modifiers) for fc in curves))
    check("animation flag is on", settings.enable_animation)

    mapping = mat.node_tree.nodes["MT_Map"]
    bpy.context.scene.frame_set(1)
    first = tuple(mapping.inputs["Location"].default_value)
    bpy.context.scene.frame_set(13)
    later = tuple(mapping.inputs["Location"].default_value)
    check("offset changes over time", first != later, "%s -> %s" % (first, later))

    result = bpy.ops.motiontexture.fit_surface(face="ALL")
    check("Fit Image to Surface", result == {"FINISHED"}, repr(result))

    seq_dir = tempfile.mkdtemp(prefix="mts-seq-")
    for index in (1, 2):
        shutil.copyfile(ASSET, os.path.join(seq_dir, "frame_%04d.png" % index))
    result = bpy.ops.motiontexture.open_sequence(filepath=os.path.join(seq_dir, "frame_0001.png"))
    check("Open Image Sequence", result == {"FINISHED"}, repr(result))
    check("sequence range auto-detected", (settings.frame_start, settings.frame_end) == (1, 2),
          "%s-%s" % (settings.frame_start, settings.frame_end))
    check("sequence source mode", settings.source_mode == "SEQUENCE", settings.source_mode)

    result = bpy.ops.motiontexture.save_preset(preset_name="verify_preset")
    check("save preset", result == {"FINISHED"}, repr(result))
    preset_path = os.path.join(bpy.utils.user_resource("SCRIPTS", path="presets"),
                               "motion_texture_studio", "verify_preset.json")
    check("preset JSON written", os.path.isfile(preset_path), preset_path)
    if os.path.isfile(preset_path):
        result = bpy.ops.motiontexture.load_preset(preset=preset_path)
        check("load preset", result == {"FINISHED"}, repr(result))

    shutil.rmtree(seq_dir, ignore_errors=True)
except Exception:
    traceback.print_exc()
    print("SUMMARY: harness crashed")
    sys.exit(1)

passed = sum(1 for ok in results if ok)
failed = len(results) - passed
print("\nSUMMARY: %d passed, %d failed" % (passed, failed))
if failed:
    sys.exit(2)
