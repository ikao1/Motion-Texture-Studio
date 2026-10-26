bl_info = {
    "name": "Motion Texture Studio",
    "author": "Irene Kao",
    "version": (2, 1, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > Motion Texture",
    "description": "Animate stills, image sequences, and movies on objects, with moving raised textures.",
    "category": "Material",
}

import json
import math
import os
import re
import struct
from collections import defaultdict
from contextlib import contextmanager

import bpy

GRAPH_VERSION = 13
MATERIAL_PREFIX = "MotionTexture_"
MODIFIER_NAME = "MotionTexture Displacement"
IMAGE_EXTENSIONS = ".png;.jpg;.jpeg;.jpe;.bmp;.tga;.tif;.tiff;.exr;.hdr;.webp;.gif"
MOVIE_EXTENSIONS = ".mp4;.mov;.avi;.mkv;.webm;.m4v"
DROP_EXTENSIONS = IMAGE_EXTENSIONS + ";" + MOVIE_EXTENSIONS
IMAGE_FILTER = "*.png;*.jpg;*.jpeg;*.jpe;*.bmp;*.tga;*.tif;*.tiff;*.exr;*.hdr;*.webp;*.gif"
MOVIE_FILTER = "*.mp4;*.mov;*.avi;*.mkv;*.webm;*.m4v"
IMAGE_EXT_SET = {".png", ".jpg", ".jpeg", ".jpe", ".bmp", ".tga", ".tif", ".tiff", ".exr", ".hdr", ".webp", ".gif"}
MOVIE_EXT_SET = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}
RECENT_SOURCES_FILE = "recent_sources.json"
MAX_RECENT_SOURCES = 8

_SUSPEND_UPDATES = False


@contextmanager
def _suspend_updates():
    global _SUSPEND_UPDATES
    previous = _SUSPEND_UPDATES
    _SUSPEND_UPDATES = True
    try:
        yield
    finally:
        _SUSPEND_UPDATES = previous

DEFAULTS = {
    "invert": False,
    "grayscale": 0.0,
    "hue": 0.0,
    "saturation": 1.0,
    "brightness": 1.0,
    "contrast": 1.0,
    "gamma": 1.0,
    "temperature": 0.0,
    "tint": 0.0,
    "posterize": 0,
    "remap": 0.0,
    "amount": 1.0,
    "scale": 1.0,
    "tiling_x": 1.0,
    "tiling_y": 1.0,
    "rotation": 0.0,
    "rotation_x": 0.0,
    "rotation_y": 0.0,
    "offset_x": 0.0,
    "offset_y": 0.0,
    "offset_z": 0.0,
    "scale_z": 1.0,
    "flip_x": False,
    "flip_y": False,
    "relief": 0.5,
    "depth": 0.5,
    "relief_invert": False,
    "detail": 0.0,
    "detail_scale": 8.0,
    "relief_speed": 0.5,
    "relief_amplitude": 0.5,
    "relief_phase": 0.0,
    "stop_motion": False,
    "step_frames": 2,
    "roughness": 0.5,
    "metallic": 0.0,
    "specular": 0.5,
    "ior": 1.5,
    "coat": 0.0,
    "coat_roughness": 0.03,
    "sheen": 0.0,
    "sheen_roughness": 0.5,
    "anisotropic": 0.0,
    "subsurface": 0.0,
    "transmission": 0.0,
    "alpha": 1.0,
    "normal_strength": 1.0,
    "emission": 0.0,
    "glow_mask": False,
    "glow_color": (1.0, 1.0, 1.0, 1.0),
}

RESET_SECTIONS = {
    "COLOR": (
        "invert", "grayscale", "hue", "saturation", "brightness", "contrast",
        "gamma", "temperature", "tint", "posterize", "remap", "amount",
    ),
    "TRANSFORM": (
        "scale", "tiling_x", "tiling_y", "rotation", "rotation_x", "rotation_y",
        "offset_x", "offset_y", "offset_z", "scale_z", "flip_x", "flip_y",
    ),
    "SURFACE": (
        "relief", "depth", "relief_invert", "detail", "detail_scale",
        "roughness", "metallic", "specular", "ior", "coat", "coat_roughness",
        "sheen", "sheen_roughness", "anisotropic", "subsurface", "transmission",
        "alpha", "normal_strength", "emission", "glow_mask", "glow_color",
    ),
    "ANIMATION": (
        "relief_speed", "relief_amplitude", "relief_phase", "stop_motion", "step_frames",
    ),
    "ALL": tuple(DEFAULTS.keys()),
}

SURFACE_PRESETS = {
    "MATTE": {"label": "Matte", "roughness": 0.9, "metallic": 0.0, "specular": 0.25, "ior": 1.45, "coat": 0.0, "coat_roughness": 0.1, "sheen": 0.0, "sheen_roughness": 0.5, "anisotropic": 0.0, "subsurface": 0.0, "transmission": 0.0, "alpha": 1.0, "emission": 0.0},
    "GLOSSY": {"label": "Glossy", "roughness": 0.15, "metallic": 0.0, "specular": 0.8, "ior": 1.5, "coat": 0.4, "coat_roughness": 0.05, "sheen": 0.0, "sheen_roughness": 0.5, "anisotropic": 0.0, "subsurface": 0.0, "transmission": 0.0, "alpha": 1.0, "emission": 0.0},
    "PLASTIC": {"label": "Plastic", "roughness": 0.3, "metallic": 0.0, "specular": 0.6, "ior": 1.45, "coat": 0.0, "coat_roughness": 0.03, "sheen": 0.0, "sheen_roughness": 0.5, "anisotropic": 0.0, "subsurface": 0.0, "transmission": 0.0, "alpha": 1.0, "emission": 0.0},
    "CERAMIC": {"label": "Ceramic", "roughness": 0.12, "metallic": 0.0, "specular": 0.7, "ior": 1.5, "coat": 0.6, "coat_roughness": 0.03, "sheen": 0.0, "sheen_roughness": 0.5, "anisotropic": 0.0, "subsurface": 0.0, "transmission": 0.0, "alpha": 1.0, "emission": 0.0},
    "METAL": {"label": "Metal", "roughness": 0.25, "metallic": 1.0, "specular": 0.5, "ior": 1.5, "coat": 0.0, "coat_roughness": 0.03, "sheen": 0.0, "sheen_roughness": 0.5, "anisotropic": 0.0, "subsurface": 0.0, "transmission": 0.0, "alpha": 1.0, "emission": 0.0},
    "BRUSHED": {"label": "Brushed", "roughness": 0.35, "metallic": 1.0, "specular": 0.5, "ior": 1.5, "coat": 0.0, "coat_roughness": 0.03, "sheen": 0.0, "sheen_roughness": 0.5, "anisotropic": 0.8, "subsurface": 0.0, "transmission": 0.0, "alpha": 1.0, "emission": 0.0},
    "VELVET": {"label": "Velvet", "roughness": 0.85, "metallic": 0.0, "specular": 0.2, "ior": 1.45, "coat": 0.0, "coat_roughness": 0.03, "sheen": 1.0, "sheen_roughness": 0.3, "anisotropic": 0.0, "subsurface": 0.1, "transmission": 0.0, "alpha": 1.0, "emission": 0.0},
    "GLASS": {"label": "Glass", "roughness": 0.05, "metallic": 0.0, "specular": 0.5, "ior": 1.45, "coat": 0.0, "coat_roughness": 0.03, "sheen": 0.0, "sheen_roughness": 0.5, "anisotropic": 0.0, "subsurface": 0.0, "transmission": 1.0, "alpha": 1.0, "emission": 0.0},
    "GLOWING": {"label": "Glowing", "roughness": 0.6, "metallic": 0.0, "specular": 0.4, "ior": 1.45, "coat": 0.0, "coat_roughness": 0.03, "sheen": 0.0, "sheen_roughness": 0.5, "anisotropic": 0.0, "subsurface": 0.0, "transmission": 0.0, "alpha": 1.0, "emission": 1.5},
}
PRESET_ITEMS = [(key, SURFACE_PRESETS[key]["label"], "") for key in SURFACE_PRESETS]

MOTION_PRESETS = (
    ("SCROLL_X", "Scroll X", "Slide the image and its relief horizontally; loops seamlessly"),
    ("SCROLL_Y", "Scroll Y", "Slide the image and its relief vertically; loops seamlessly"),
    ("DRIFT", "Drift", "Slow diagonal movement; loops seamlessly"),
    ("PULSE", "Pulse", "Breathe the raised relief in and out"),
    ("BREATHE", "Breathe", "Gently scale the texture"),
    ("RIPPLE", "Ripple", "Move the relief with a repeating swell"),
    ("FLICKER", "Flicker", "Flicker like unstable light, driven by noise so it never repeats"),
)
MOTION_PRESET_ITEMS = [(key, label, desc) for key, label, desc in MOTION_PRESETS]

RELIEF_MOTION_ITEMS = (
    ("DRIFT", "Drift", "Move the procedural relief sideways"),
    ("PULSE", "Pulse", "Raise and lower the relief"),
    ("RIPPLE", "Ripple", "Move and pulse the relief"),
    ("CRAWL", "Crawl", "Creep the relief diagonally"),
)

SOURCE_MODE_ITEMS = (
    ("STILL", "Still", "One image"),
    ("SEQUENCE", "Image Sequence", "Numbered image files"),
    ("MOVIE", "Movie", "Video file"),
)
LOOP_ITEMS = (
    ("ONCE", "Once", "Play once and hold the last frame"),
    ("LOOP", "Loop", "Repeat from the start"),
    ("PING_PONG", "Ping-Pong", "Play forward then backward"),
)
COLOR_SPACE_ITEMS = (
    ("sRGB", "sRGB", ""),
    ("Non-Color", "Non-Color", ""),
    ("Linear Rec.709", "Linear", ""),
)
RELIEF_MODE_ITEMS = (
    ("BUMP", "Bump", "Fast raised shading"),
    ("DISPLACEMENT", "Displacement", "True displaced geometry; best in Cycles"),
)
RELIEF_SOURCE_ITEMS = (
    ("IMAGE", "Image Luminance", "Use the source image's brightness as height"),
    ("NOISE", "Noise", "Use animated procedural noise as height"),
    ("WAVE", "Wave", "Use animated bands as height"),
)
INTERPOLATION_ITEMS = (
    ("BEZIER", "Bezier", ""),
    ("LINEAR", "Linear", ""),
    ("CONSTANT", "Constant", ""),
)
SPEED_ITEMS = (
    ("0.25", "Speed 0.25x", "One motion cycle every 96 frames"),
    ("0.5", "Speed 0.5x", "One motion cycle every 48 frames"),
    ("1", "Speed 1x", "One motion cycle every 24 frames (one second at 24 fps)"),
    ("1.5", "Speed 1.5x", "One motion cycle every 16 frames"),
    ("2", "Speed 2x", "One motion cycle every 12 frames"),
    ("4", "Speed 4x", "One motion cycle every 6 frames"),
)
SPEED_CYCLE_FRAMES = {"0.25": 96, "0.5": 48, "1": 24, "1.5": 16, "2": 12, "4": 6}


def _cycle_frames(s):
    if s is None:
        return 24
    return SPEED_CYCLE_FRAMES.get(getattr(s, "speed", "1"), 24)


def _exif_transform(code):
    """Return (rotation_degrees, flip_x, flip_y) to correct an EXIF orientation code."""
    table = {
        1: (0.0, False, False),
        2: (0.0, True, False),
        3: (180.0, False, False),
        4: (0.0, False, True),
        5: (90.0, True, False),
        6: (-90.0, False, False),
        7: (-90.0, True, False),
        8: (90.0, False, False),
    }
    return table.get(int(code or 1), (0.0, False, False))


def _parse_exif_orientation(tiff):
    try:
        if len(tiff) < 8 or tiff[:2] not in (b"II", b"MM"):
            return 1
        endian = "<" if tiff[:2] == b"II" else ">"
        ifd_off = struct.unpack(endian + "I", tiff[4:8])[0]
        if ifd_off + 2 > len(tiff):
            return 1
        count = struct.unpack(endian + "H", tiff[ifd_off:ifd_off + 2])[0]
        for i in range(count):
            entry = ifd_off + 2 + i * 12
            if entry + 12 > len(tiff):
                break
            tag, typ, num, value = struct.unpack(endian + "HHII", tiff[entry:entry + 12])
            if tag == 0x0112 and typ == 3 and num == 1:
                orientation = value & 0xFFFF if endian == "<" else value >> 16
                return max(1, min(8, orientation))
    except Exception:
        pass
    return 1


def _exif_orientation(path):
    """Read the EXIF orientation tag from a JPEG or PNG. Returns 1-8, default 1."""
    try:
        with open(path, "rb") as handle:
            head = handle.read(8)
            if head[:2] == b"\xff\xd8":
                handle.seek(2)
                while True:
                    marker = handle.read(2)
                    if len(marker) < 2 or marker[0] != 0xFF:
                        return 1
                    code = marker[1]
                    if code in (0xD9, 0xDA):
                        return 1
                    segment = handle.read(2)
                    if len(segment) < 2:
                        return 1
                    length = struct.unpack(">H", segment)[0]
                    if length < 2:
                        return 1
                    if code == 0xE1:
                        data = handle.read(length - 2)
                        if data[:6] == b"Exif\x00\x00":
                            return _parse_exif_orientation(data[6:])
                    else:
                        handle.seek(length - 2, 1)
            elif head[:8] == b"\x89PNG\r\n\x1a\n":
                handle.seek(8)
                while True:
                    chunk_header = handle.read(8)
                    if len(chunk_header) < 8:
                        return 1
                    length, chunk_type = struct.unpack(">I4s", chunk_header)
                    if chunk_type == b"eXIf":
                        return _parse_exif_orientation(handle.read(length))
                    if chunk_type in (b"IDAT", b"IEND"):
                        return 1
                    handle.seek(length + 4, 1)
    except Exception:
        pass
    return 1


def _video_rotation(path):
    """Read the display-matrix rotation from a movie's MP4/MOV container.

    Phone and camera videos are usually stored landscape with a rotation
    matrix telling players to turn them upright. Blender ignores that matrix,
    so a portrait clip shows sideways on the texture. We translate the matrix
    into an EXIF-style orientation code so the shader rotates it back.

    Returns an EXIF code (1-8), defaulting to 1 (no correction).
    """
    return _parse_video_matrix(_read_track_matrix(path))


def _read_track_matrix(path):
    """Return the 9 fixed-point values of the tkhd (or mvhd) display matrix."""
    try:
        with open(path, "rb") as handle:
            data = handle.read()
    except Exception:
        return None
    for atom in (b"tkhd", b"mvhd"):
        index = data.find(atom)
        if index < 0:
            continue
        matrix = _matrix_from_atom(data, index + 4, atom == b"tkhd")
        if matrix is not None:
            return matrix
    return None


def _matrix_from_atom(data, body, is_track):
    try:
        version = data[body]
        pos = body + 4
        if is_track:
            if version == 1:
                pos += 8 + 8 + 4 + 4 + 8
            else:
                pos += 4 + 4 + 4 + 4 + 4
            pos += 8 + 2 + 2 + 2 + 2
        else:
            if version == 1:
                pos += 8 + 8 + 4 + 8
            else:
                pos += 4 + 4 + 4 + 4
            pos += 4 + 2 + 2 + 2 + 2 + 4 + 4
            pos += 4 * 9 + 4 * 4 + 4 * 4
        values = struct.unpack(">9i", data[pos:pos + 36])
        return [value / 65536.0 for value in values]
    except Exception:
        return None


def _parse_video_matrix(values):
    if not values:
        return 1
    a, b, u, c, d, v, x, y, w = values
    if abs(a - 1.0) < 0.01 and abs(d - 1.0) < 0.01 and abs(b) < 0.01 and abs(c) < 0.01:
        return 1
    if abs(a + 1.0) < 0.01 and abs(d + 1.0) < 0.01 and abs(b) < 0.01 and abs(c) < 0.01:
        return 3
    if abs(a) < 0.01 and abs(d) < 0.01:
        if b < 0 and c > 0:
            return 6
        if b > 0 and c < 0:
            return 8
    return 1


def _mix(nt, name, blend="MIX"):
    node = nt.nodes.new("ShaderNodeMixRGB")
    node.name = name
    node.blend_type = blend
    return node


def _link_single(nt, to_socket, from_socket):
    for link in list(to_socket.links):
        nt.links.remove(link)
    if from_socket is not None:
        nt.links.new(from_socket, to_socket)


def _vmath(nt, name, op, a, b=None):
    node = nt.nodes.new("ShaderNodeVectorMath")
    node.name = name
    node.operation = op
    if isinstance(a, tuple):
        node.inputs[0].default_value = a
    else:
        nt.links.new(a, node.inputs[0])
    if b is not None:
        if isinstance(b, tuple):
            node.inputs[1].default_value = b
        else:
            nt.links.new(b, node.inputs[1])
    return node


def _posterize(nt, in_socket):
    mul = _vmath(nt, "MT_Post_mul", "MULTIPLY", in_socket, (8.0,) * 3)
    flr = _vmath(nt, "MT_Post_flr", "FLOOR", mul.outputs["Vector"])
    div = _vmath(nt, "MT_Post_div", "MULTIPLY", flr.outputs["Vector"], (1.0 / 8.0,) * 3)
    return mul, div


def _set_input(node, name, value):
    try:
        node.inputs[name].default_value = value
    except Exception:
        pass


def _tint_color(temperature, tint):
    r = 1.0 + 0.28 * temperature + 0.12 * tint
    g = 1.0 - 0.18 * tint
    b = 1.0 - 0.28 * temperature + 0.12 * tint
    clamp = lambda v: max(0.05, min(2.0, v))
    return (clamp(r), clamp(g), clamp(b), 1.0)


def _show_material_preview():
    wm = getattr(bpy.context, "window_manager", None)
    if wm is None:
        return
    for win in wm.windows:
        screen = getattr(win, "screen", None)
        if screen is None:
            continue
        for area in screen.areas:
            if area.type != "VIEW_3D":
                continue
            for space in area.spaces:
                shading = getattr(space, "shading", None)
                if shading is not None and shading.type == "SOLID":
                    shading.type = "MATERIAL"


def _material_name(obj):
    return MATERIAL_PREFIX + re.sub(r"[^A-Za-z0-9_]+", "_", obj.name)[:48]


def _find_material(obj):
    mat = bpy.data.materials.get(_material_name(obj))
    if mat is not None:
        return mat
    for slot in getattr(obj, "material_slots", ()):
        candidate = slot.material
        if candidate is not None and candidate.name.startswith(MATERIAL_PREFIX):
            return candidate
    return None


def _get_material(obj):
    mat = _find_material(obj)
    if mat is None:
        mat = bpy.data.materials.new(_material_name(obj))
    mat.use_nodes = True
    slots = obj.data.materials
    index = next((i for i, slot in enumerate(slots) if slot == mat), None)
    if index is None:
        slots.append(mat)
        index = len(slots) - 1
    obj.active_material_index = index
    # Make the Motion Texture material visible on the mesh, but never stomp a
    # multi-material setup: reassign every face only when the mesh effectively
    # uses a single material (a fresh object keeps every face on slot 0, so
    # without the reassignment the texture never appears).
    mesh = obj.data
    if mesh is not None and not any(poly.material_index == index for poly in mesh.polygons):
        used = {poly.material_index for poly in mesh.polygons}
        if not used or used == {0}:
            for poly in mesh.polygons:
                poly.material_index = index
    return mat


def _settings(context):
    obj = getattr(context, "active_object", None)
    if obj is not None and obj.type == "MESH":
        return getattr(obj, "motion_texture", None)
    return None


def _settings_for(obj):
    if obj is None or obj.type != "MESH":
        return None
    return getattr(obj, "motion_texture", None)


def _sequence_range(path):
    folder = os.path.dirname(path)
    base = os.path.basename(path)
    stem, ext = os.path.splitext(base)
    match = re.match(r"^(.*?)(\d+)$", stem)
    if not match or not os.path.isdir(folder):
        return None
    prefix, _number = match.group(1), int(match.group(2))
    pattern = re.compile(r"^%s(\d+)%s$" % (re.escape(prefix), re.escape(ext)), re.IGNORECASE)
    numbers = []
    try:
        for filename in os.listdir(folder):
            found = pattern.match(filename)
            if found:
                numbers.append(int(found.group(1)))
    except OSError:
        return None
    if not numbers:
        return None
    return min(numbers), max(numbers)


def _apply_source_settings(node, s):
    if node is None or s is None:
        return
    image = node.image
    if image is None:
        return
    try:
        image.colorspace_settings.name = s.color_space
    except Exception:
        pass
    user = node.image_user
    loop_cyclic = s.loop_mode == "LOOP"
    if s.source_mode == "SEQUENCE":
        try:
            image.source = "SEQUENCE"
        except Exception:
            pass
        start = max(1, s.frame_start)
        end = max(start, s.frame_end)
        user.frame_start = start
        user.frame_duration = max(1, end - start + 1)
        user.frame_offset = s.frame_offset
        user.use_cyclic = loop_cyclic
        user.use_auto_refresh = True
    elif s.source_mode == "MOVIE":
        try:
            image.source = "MOVIE"
        except Exception:
            pass
        user.frame_start = 1
        # The ImageUser must span the whole movie, or Blender clamps it to a single
        # frame and the video looks frozen on the texture.
        user.frame_duration = max(1, int(getattr(image, "frame_duration", 0) or 0))
        user.frame_offset = s.frame_offset
        user.use_cyclic = loop_cyclic
        user.use_auto_refresh = True
    else:
        try:
            image.source = "FILE"
        except Exception:
            pass
        user.frame_start = 1
        user.frame_duration = 1
        user.frame_offset = 0
        user.use_cyclic = False


def _build(mat, s):
    nt = mat.node_tree
    nt.nodes.clear()
    nt["mt_version"] = GRAPH_VERSION
    link = nt.links.new

    coord = nt.nodes.new("ShaderNodeTexCoord")
    coord.name = "MT_Coord"
    coord.location = (-1900, 0)

    orient = nt.nodes.new("ShaderNodeVectorRotate")
    orient.name = "MT_Orient"
    orient.location = (-1600, 0)
    orient.rotation_type = "Z_AXIS"
    orient.inputs["Center"].default_value = (0.5, 0.5, 0.0)

    tilt_x = nt.nodes.new("ShaderNodeVectorRotate")
    tilt_x.name = "MT_TiltX"
    tilt_x.location = (-1520, 0)
    tilt_x.rotation_type = "X_AXIS"
    tilt_x.inputs["Center"].default_value = (0.5, 0.5, 0.0)

    tilt_y = nt.nodes.new("ShaderNodeVectorRotate")
    tilt_y.name = "MT_TiltY"
    tilt_y.location = (-1520, -220)
    tilt_y.rotation_type = "Y_AXIS"
    tilt_y.inputs["Center"].default_value = (0.5, 0.5, 0.0)

    mapn = nt.nodes.new("ShaderNodeMapping")
    mapn.name = "MT_Map"
    mapn.location = (-1680, 0)

    image = nt.nodes.new("ShaderNodeTexImage")
    image.name = "MT_Image"
    image.location = (-1460, 0)
    image.extension = "REPEAT"

    invert = nt.nodes.new("ShaderNodeInvert")
    invert.name = "MT_Invert"
    invert.location = (-1240, 220)

    mono_bw = nt.nodes.new("ShaderNodeRGBToBW")
    mono_bw.name = "MT_Mono_BW"
    mono_bw.location = (-1240, -40)

    mono_mix = _mix(nt, "MT_Mono_Mix")
    mono_mix.location = (-1040, 120)

    hsv = nt.nodes.new("ShaderNodeHueSaturation")
    hsv.name = "MT_HueSat"
    hsv.location = (-820, 120)

    gamma = nt.nodes.new("ShaderNodeGamma")
    gamma.name = "MT_Gamma"
    gamma.location = (-600, 120)

    bc = nt.nodes.new("ShaderNodeBrightContrast")
    bc.name = "MT_BC"
    bc.location = (-400, 120)

    tint = _mix(nt, "MT_Tint", blend="MULTIPLY")
    tint.location = (-200, 120)

    hue_ramp = nt.nodes.new("ShaderNodeValToRGB")
    hue_ramp.name = "MT_HueRamp"
    hue_ramp.location = (-200, 400)

    remap = _mix(nt, "MT_Remap")
    remap.location = (0, 220)

    post_mul, post_div = _posterize(nt, remap.outputs["Color"])
    post_mul.location = (0, -140)
    post_div.location = (260, -140)

    post_mix = _mix(nt, "MT_Post_Mix")
    post_mix.location = (460, 80)

    amount = _mix(nt, "MT_Amount")
    amount.location = (660, 80)

    glow = _mix(nt, "MT_Glow", blend="MULTIPLY")
    glow.location = (220, 320)

    glow_lum = nt.nodes.new("ShaderNodeRGBToBW")
    glow_lum.name = "MT_Glow_Lum"
    glow_lum.location = (220, 580)

    glow_mul = nt.nodes.new("ShaderNodeMath")
    glow_mul.name = "MT_Glow_Mul"
    glow_mul.operation = "MULTIPLY"
    glow_mul.location = (420, 580)

    motion_map = nt.nodes.new("ShaderNodeMapping")
    motion_map.name = "MT_MotionMap"
    motion_map.location = (-1460, -620)

    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.name = "MT_Noise"
    noise.location = (-1240, -540)
    noise.inputs["Detail"].default_value = 6.0

    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.name = "MT_Wave"
    wave.location = (-1240, -820)
    wave.wave_type = "BANDS"
    wave.bands_direction = "X"
    wave.wave_profile = "SIN"

    proc_mix = _mix(nt, "MT_ProcMix")
    proc_mix.location = (-1020, -660)

    bump_bw = nt.nodes.new("ShaderNodeRGBToBW")
    bump_bw.name = "MT_Bump_BW"
    bump_bw.location = (-1020, -340)

    detail_mix = _mix(nt, "MT_Detail_Mix")
    detail_mix.location = (-800, -500)

    bump = nt.nodes.new("ShaderNodeBump")
    bump.name = "MT_Bump"
    bump.location = (-580, -500)

    displacement = nt.nodes.new("ShaderNodeDisplacement")
    displacement.name = "MT_Displace"
    displacement.location = (-360, -700)

    normal_img = nt.nodes.new("ShaderNodeTexImage")
    normal_img.name = "MT_Normal_Img"
    normal_img.location = (260, -620)

    normal_flat = nt.nodes.new("ShaderNodeRGB")
    normal_flat.name = "MT_NormalFlat"
    normal_flat.location = (260, -840)
    normal_flat.outputs["Color"].default_value = (0.5, 0.5, 1.0, 1.0)

    normal_map = nt.nodes.new("ShaderNodeNormalMap")
    normal_map.name = "MT_NormalMap"
    normal_map.location = (460, -620)

    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.name = "MT_BSDF"
    bsdf.location = (600, 80)

    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.name = "MT_Out"
    out.location = (920, 80)

    link(coord.outputs["UV"], orient.inputs["Vector"])
    link(orient.outputs["Vector"], tilt_x.inputs["Vector"])
    link(tilt_x.outputs["Vector"], tilt_y.inputs["Vector"])
    link(tilt_y.outputs["Vector"], mapn.inputs["Vector"])
    link(mapn.outputs["Vector"], image.inputs["Vector"])

    link(image.outputs["Color"], invert.inputs["Color"])
    link(invert.outputs["Color"], mono_bw.inputs["Color"])
    link(invert.outputs["Color"], mono_mix.inputs["Color1"])
    link(mono_bw.outputs["Val"], mono_mix.inputs["Color2"])
    link(mono_mix.outputs["Color"], hsv.inputs["Color"])
    link(hsv.outputs["Color"], gamma.inputs["Color"])
    link(gamma.outputs["Color"], bc.inputs["Color"])
    link(bc.outputs["Color"], tint.inputs["Color1"])
    link(tint.outputs["Color"], hue_ramp.inputs["Fac"])
    link(tint.outputs["Color"], remap.inputs["Color1"])
    link(hue_ramp.outputs["Color"], remap.inputs["Color2"])
    link(remap.outputs["Color"], post_mul.inputs[0])
    link(post_div.outputs["Vector"], post_mix.inputs["Color2"])
    link(remap.outputs["Color"], post_mix.inputs["Color1"])
    link(post_mix.outputs["Color"], amount.inputs["Color2"])
    link(image.outputs["Color"], amount.inputs["Color1"])
    link(amount.outputs["Color"], bsdf.inputs["Base Color"])

    link(amount.outputs["Color"], glow.inputs["Color1"])
    try:
        link(glow.outputs["Color"], bsdf.inputs["Emission Color"])
    except Exception:
        pass
    link(amount.outputs["Color"], glow_lum.inputs["Color"])
    link(glow_lum.outputs["Val"], glow_mul.inputs[0])

    link(coord.outputs["Object"], motion_map.inputs["Vector"])
    link(motion_map.outputs["Vector"], noise.inputs["Vector"])
    link(motion_map.outputs["Vector"], wave.inputs["Vector"])
    link(noise.outputs["Factor"], proc_mix.inputs["Color1"])
    link(wave.outputs["Fac"], proc_mix.inputs["Color2"])
    link(image.outputs["Color"], bump_bw.inputs["Color"])
    link(bump_bw.outputs["Val"], detail_mix.inputs["Color1"])
    link(proc_mix.outputs["Color"], detail_mix.inputs["Color2"])
    link(detail_mix.outputs["Color"], bump.inputs["Height"])
    link(detail_mix.outputs["Color"], displacement.inputs["Height"])
    link(mapn.outputs["Vector"], normal_img.inputs["Vector"])
    link(normal_flat.outputs["Color"], normal_map.inputs["Color"])
    link(normal_map.outputs["Normal"], bump.inputs["Normal"])
    link(bump.outputs["Normal"], bsdf.inputs["Normal"])

    link(bsdf.outputs["BSDF"], out.inputs["Surface"])
    _set_values(nt, s)


def _set_values(nt, s):
    mapn = nt.nodes["MT_Map"]
    image_node = nt.nodes["MT_Image"]
    invert = nt.nodes["MT_Invert"]
    mono_mix = nt.nodes["MT_Mono_Mix"]
    hsv = nt.nodes["MT_HueSat"]
    gamma = nt.nodes["MT_Gamma"]
    bc = nt.nodes["MT_BC"]
    tint = nt.nodes["MT_Tint"]
    remap = nt.nodes["MT_Remap"]
    post_mul = nt.nodes["MT_Post_mul"]
    post_div = nt.nodes["MT_Post_div"]
    post_mix = nt.nodes["MT_Post_Mix"]
    amount = nt.nodes["MT_Amount"]
    glow = nt.nodes["MT_Glow"]
    glow_lum = nt.nodes["MT_Glow_Lum"]
    glow_mul = nt.nodes["MT_Glow_Mul"]
    noise = nt.nodes["MT_Noise"]
    wave = nt.nodes["MT_Wave"]
    proc_mix = nt.nodes["MT_ProcMix"]
    detail_mix = nt.nodes["MT_Detail_Mix"]
    bump = nt.nodes["MT_Bump"]
    displacement = nt.nodes["MT_Displace"]
    normal_img = nt.nodes["MT_Normal_Img"]
    normal_flat = nt.nodes["MT_NormalFlat"]
    normal_map = nt.nodes["MT_NormalMap"]
    bsdf = nt.nodes["MT_BSDF"]
    out = nt.nodes["MT_Out"]

    if s.image is not None:
        image_node.image = s.image
        _apply_source_settings(image_node, s)
    else:
        image_node.image = None

    flip_x = -1.0 if s.flip_x else 1.0
    flip_y = -1.0 if s.flip_y else 1.0
    exif_rot, exif_fh, exif_fv = _exif_transform(getattr(s, "exif_code", 1))
    if exif_fh:
        flip_x = -flip_x
    if exif_fv:
        flip_y = -flip_y
    orient = nt.nodes.get("MT_Orient")
    if orient is not None:
        orient.inputs["Center"].default_value = (0.5, 0.5, 0.0)
        orient.inputs["Angle"].default_value = math.radians(exif_rot)
    tilt_x = nt.nodes.get("MT_TiltX")
    if tilt_x is not None:
        tilt_x.inputs["Center"].default_value = (0.5, 0.5, 0.0)
        tilt_x.inputs["Angle"].default_value = math.radians(s.rotation_x)
    tilt_y = nt.nodes.get("MT_TiltY")
    if tilt_y is not None:
        tilt_y.inputs["Center"].default_value = (0.5, 0.5, 0.0)
        tilt_y.inputs["Angle"].default_value = math.radians(s.rotation_y)
    mapn.inputs["Location"].default_value = (s.offset_x, s.offset_y, s.offset_z)
    mapn.inputs["Rotation"].default_value = (0.0, 0.0, math.radians(s.rotation))
    mapn.inputs["Scale"].default_value = (
        max(s.tiling_x, 0.001) * s.scale * flip_x,
        max(s.tiling_y, 0.001) * s.scale * flip_y,
        max(s.scale_z, 0.001),
    )

    invert.inputs["Factor"].default_value = 1.0 if s.invert else 0.0
    mono_mix.inputs["Factor"].default_value = s.grayscale
    hsv.inputs["Hue"].default_value = 0.5 + s.hue * 0.5
    hsv.inputs["Saturation"].default_value = s.saturation
    hsv.inputs["Value"].default_value = s.brightness
    gamma.inputs["Gamma"].default_value = max(s.gamma, 0.01)
    bc.inputs["Brightness"].default_value = 0.0
    bc.inputs["Contrast"].default_value = s.contrast - 1.0
    tint.inputs["Factor"].default_value = 1.0
    tint.inputs["Color2"].default_value = _tint_color(s.temperature, s.tint)
    remap.inputs["Factor"].default_value = s.remap
    amount.inputs["Factor"].default_value = s.amount

    levels = s.posterize
    on = levels >= 2
    lv = float(levels if on else 8)
    post_mul.inputs[1].default_value = (lv, lv, lv)
    post_div.inputs[1].default_value = (1.0 / lv,) * 3
    post_mix.inputs["Factor"].default_value = 1.0 if on else 0.0

    glow.inputs["Factor"].default_value = 1.0
    glow.inputs["Color2"].default_value = s.glow_color
    glow_mul.inputs[1].default_value = s.emission
    strength = bsdf.inputs.get("Emission Strength")
    if strength is not None:
        if s.glow_mask:
            _link_single(nt, strength, glow_mul.outputs["Value"])
        else:
            _link_single(nt, strength, None)
            strength.default_value = s.emission

    bump.invert = s.relief_invert
    bump.inputs["Strength"].default_value = s.relief
    bump.inputs["Distance"].default_value = 0.02 + 0.5 * s.depth
    displacement.inputs["Scale"].default_value = 0.02 + 0.35 * s.depth
    displacement.inputs["Midlevel"].default_value = 0.5

    if s.relief_source == "IMAGE":
        detail_mix.inputs["Factor"].default_value = s.detail
    else:
        detail_mix.inputs["Factor"].default_value = 1.0
    proc_mix.inputs["Factor"].default_value = 1.0 if s.relief_source == "WAVE" else 0.0
    noise.inputs["Scale"].default_value = max(s.detail_scale, 0.1)
    wave.inputs["Scale"].default_value = max(s.detail_scale, 0.1)
    wave.inputs["Distortion"].default_value = 1.5

    if s.normal_image is not None:
        normal_img.image = s.normal_image
        _link_single(nt, normal_map.inputs["Color"], normal_img.outputs["Color"])
    else:
        normal_img.image = None
        _link_single(nt, normal_map.inputs["Color"], normal_flat.outputs["Color"])
    normal_map.inputs["Strength"].default_value = s.normal_strength

    _set_input(bsdf, "Roughness", s.roughness)
    _set_input(bsdf, "Metallic", s.metallic)
    _set_input(bsdf, "Specular IOR Level", s.specular)
    _set_input(bsdf, "IOR", s.ior)
    _set_input(bsdf, "Coat Weight", s.coat)
    _set_input(bsdf, "Coat Roughness", s.coat_roughness)
    _set_input(bsdf, "Sheen Weight", s.sheen)
    _set_input(bsdf, "Sheen Roughness", s.sheen_roughness)
    _set_input(bsdf, "Anisotropic", s.anisotropic)
    _set_input(bsdf, "Subsurface Weight", s.subsurface)
    _set_input(bsdf, "Transmission Weight", s.transmission)
    _set_input(bsdf, "Alpha", s.alpha)

    _link_single(nt, out.inputs["Displacement"], displacement.outputs["Displacement"] if s.relief_mode == "DISPLACEMENT" else None)


def _set_displacement_modifier(obj, s):
    modifier = obj.modifiers.get(MODIFIER_NAME)
    if s.relief_mode == "DISPLACEMENT":
        if modifier is None:
            modifier = obj.modifiers.new(MODIFIER_NAME, "SUBSURF")
            modifier.subdivision_type = "SIMPLE"
        level = max(0, min(6, int(s.subdivision_level)))
        modifier.levels = level
        modifier.render_levels = level
    elif modifier is not None:
        obj.modifiers.remove(modifier)


def _apply(context, rebuild=False, obj=None):
    obj = obj or getattr(context, "active_object", None)
    if obj is None or obj.type != "MESH":
        return False
    s = _settings_for(obj)
    if s is None:
        return False
    mat = _get_material(obj)
    nt = mat.node_tree
    stale = nt.get("mt_version") != GRAPH_VERSION
    if rebuild or stale or nt.nodes.get("MT_BSDF") is None:
        _build(mat, s)
    else:
        _set_values(nt, s)
    _set_displacement_modifier(obj, s)
    if s.preview_on_selected:
        _show_material_preview()
    try:
        blended = s.alpha < 0.999 or s.transmission > 0.0
        mat.surface_render_method = "BLENDED" if blended else "DITHERED"
    except Exception:
        pass
    try:
        mat.displacement_method = "BOTH" if s.relief_mode == "DISPLACEMENT" else "BUMP"
    except Exception:
        pass
    if nt.animation_data is not None and nt.animation_data.action is not None:
        action = nt.animation_data.action
        for fcurve in _iter_fcurves(action):
            fcurve.mute = not s.enable_animation
        context.scene.frame_set(context.scene.frame_current)
    return True


def _on_update(self, context):
    if _SUSPEND_UPDATES:
        return
    obj = getattr(context, "active_object", None)
    if obj is None or obj.type != "MESH":
        return
    if getattr(obj, "motion_texture", None) is None:
        return
    _apply(context, rebuild=False, obj=obj)


def _on_interpolation(self, context):
    if _SUSPEND_UPDATES:
        return
    obj = getattr(context, "active_object", None)
    if obj is None or obj.type != "MESH":
        return
    action = _action_for(obj)
    _set_interpolation(action, self.interpolation)


def _on_fps(self, context):
    try:
        context.scene.render.fps = max(1, int(round(self.fps)))
    except Exception:
        pass


def _on_speed(self, context):
    if _SUSPEND_UPDATES:
        return
    obj = getattr(context, "active_object", None)
    s = _settings_for(obj)
    if s is None:
        return
    if not (s.last_motion_preset or s.last_relief_preset):
        return
    _reset_preset_curves(obj)
    if s.last_motion_preset:
        _apply_motion_preset(obj, context, s.last_motion_preset, reset=False)
    if s.last_relief_preset:
        _apply_relief_motion(obj, context, s.last_relief_preset, reset=False)


def _on_fcurve_modifiers(self, context):
    if _SUSPEND_UPDATES:
        return
    obj = getattr(context, "active_object", None)
    s = _settings_for(obj)
    if s is None:
        return
    _refresh_fcurve_modifiers(_action_for(obj), s)


def _iter_fcurves(action):
    if action is None:
        return
    fcurves = getattr(action, "fcurves", None)
    if fcurves is not None:
        try:
            for fcurve in fcurves:
                yield fcurve
            return
        except Exception:
            pass
    for layer in getattr(action, "layers", ()):
        for strip in getattr(layer, "strips", ()):
            if getattr(strip, "type", "") != "KEYFRAME":
                continue
            for channelbag in getattr(strip, "channelbags", ()):
                for fcurve in getattr(channelbag, "fcurves", ()):
                    yield fcurve


def _action_for(obj):
    mat = _find_material(obj)
    if mat is None or mat.node_tree is None:
        return None
    animation_data = mat.node_tree.animation_data
    if animation_data is None:
        return None
    return animation_data.action


def _key_socket(node, socket_name, frame, value=None):
    if node is None:
        return
    socket = node.inputs.get(socket_name)
    if socket is None:
        return
    if value is not None:
        socket.default_value = value
    socket.keyframe_insert(data_path="default_value", frame=frame)


def _key_all(obj, context, frame=None):
    mat = _find_material(obj)
    if mat is None:
        return False
    nt = mat.node_tree
    s = _settings_for(obj)
    _set_values(nt, s)
    frame = context.scene.frame_current if frame is None else frame
    _key_socket(nt.nodes["MT_Map"], "Location", frame)
    _key_socket(nt.nodes["MT_Map"], "Rotation", frame)
    _key_socket(nt.nodes["MT_Map"], "Scale", frame)
    _key_socket(nt.nodes["MT_HueSat"], "Hue", frame)
    _key_socket(nt.nodes["MT_HueSat"], "Saturation", frame)
    _key_socket(nt.nodes["MT_HueSat"], "Value", frame)
    _key_socket(nt.nodes["MT_Gamma"], "Gamma", frame)
    _key_socket(nt.nodes["MT_BC"], "Contrast", frame)
    _key_socket(nt.nodes["MT_Amount"], "Factor", frame)
    _key_socket(nt.nodes["MT_Bump"], "Strength", frame)
    _key_socket(nt.nodes["MT_Bump"], "Distance", frame)
    _key_socket(nt.nodes["MT_Detail_Mix"], "Factor", frame)
    _key_socket(nt.nodes["MT_Noise"], "Scale", frame)
    _key_socket(nt.nodes["MT_Wave"], "Scale", frame)
    _key_socket(nt.nodes["MT_BSDF"], "Roughness", frame)
    _key_socket(nt.nodes["MT_BSDF"], "Metallic", frame)
    _key_socket(nt.nodes["MT_BSDF"], "Specular IOR Level", frame)
    _key_socket(nt.nodes["MT_Displace"], "Scale", frame)
    _set_interpolation(_action_for(obj), s.interpolation)
    _refresh_fcurve_modifiers(_action_for(obj), s)
    return True


def _clear_animation(obj):
    mat = _find_material(obj)
    if mat is None or mat.node_tree is None:
        return
    if mat.node_tree.animation_data is not None:
        mat.node_tree.animation_data_clear()


def _reset_preset_curves(obj):
    """Drop the material's existing animation so a preset can re-key cleanly.

    Without this, changing Speed (which re-keys at a new cycle length) would
    leave the previous cycle's keyframes behind and the curve would drift.
    """
    mat = _find_material(obj)
    if mat is None or mat.node_tree is None:
        return
    if mat.node_tree.animation_data is not None:
        mat.node_tree.animation_data_clear()


def _set_interpolation(action, mode):
    if action is None:
        return
    for fcurve in _iter_fcurves(action):
        for point in fcurve.keyframe_points:
            point.interpolation = mode
        fcurve.update()


def _refresh_fcurve_modifiers(action, s):
    """Rebuild CYCLES and STEPPED modifiers on every curve from the settings.

    NOISE modifiers are left alone — they belong to the Flicker preset.
    """
    if action is None or s is None:
        return
    for fcurve in _iter_fcurves(action):
        for modifier in list(fcurve.modifiers):
            if modifier.type in {"CYCLES", "STEPPED"}:
                fcurve.modifiers.remove(modifier)
        fcurve.modifiers.new("CYCLES")
        if s.stop_motion:
            stepped = fcurve.modifiers.new("STEPPED")
            try:
                stepped.frame_step = max(1, int(s.step_frames))
            except Exception:
                pass
        fcurve.update()


def _set_noise_modifier(fcurve, strength, scale, phase):
    if fcurve is None:
        return
    for modifier in list(fcurve.modifiers):
        if modifier.type == "NOISE":
            fcurve.modifiers.remove(modifier)
    if strength <= 0.0:
        return
    modifier = fcurve.modifiers.new("NOISE")
    for attribute, value in (("strength", strength), ("scale", scale), ("phase", phase)):
        try:
            setattr(modifier, attribute, value)
        except Exception:
            pass


def _socket_data_path(node, socket_name):
    if node is None:
        return None
    index = node.inputs.find(socket_name)
    if index < 0:
        return None
    return 'nodes["%s"].inputs[%d].default_value' % (node.name, index)


def _resolve_socket(nt, data_path):
    match = re.match(r'^nodes\["([^"]+)"\]\.inputs\[(\d+)\]\.default_value$', data_path or "")
    if not match:
        return None
    node = nt.nodes.get(match.group(1))
    if node is None:
        return None
    index = int(match.group(2))
    if index >= len(node.inputs):
        return None
    return node.inputs[index]


def _copy_action_curves(source_obj, target_obj, frame_offset=0):
    """Copy the source object's material animation onto the target, shifted in time."""
    src_action = _action_for(source_obj)
    if src_action is None:
        return False
    mat = _find_material(target_obj)
    if mat is None or mat.node_tree is None:
        return False
    nt = mat.node_tree
    if nt.animation_data is not None:
        nt.animation_data_clear()
    groups = defaultdict(list)
    for fcurve in _iter_fcurves(src_action):
        groups[fcurve.data_path].append(fcurve)
    for data_path, curves in groups.items():
        sock = _resolve_socket(nt, data_path)
        if sock is None:
            continue
        by_index = {fc.array_index: fc for fc in curves}
        frames = sorted({int(round(p.co.x)) for fc in curves for p in fc.keyframe_points})
        if not frames:
            continue
        sock_type = sock.type
        size = 3 if sock_type == "VECTOR" else (4 if sock_type == "RGBA" else 1)
        for frame in frames:
            values = []
            for i in range(size):
                fc = by_index.get(i)
                if fc is not None:
                    values.append(fc.evaluate(frame))
                elif size > 1:
                    values.append(float(sock.default_value[i]))
                else:
                    values.append(float(sock.default_value))
            try:
                sock.default_value = values if size > 1 else values[0]
            except Exception:
                continue
            sock.keyframe_insert(data_path="default_value", frame=frame + frame_offset)
        src_interp = {int(round(p.co.x)): p.interpolation for fc in curves for p in fc.keyframe_points}
        if nt.animation_data is not None and nt.animation_data.action is not None:
            for tc in _iter_fcurves(nt.animation_data.action):
                if tc.data_path != data_path:
                    continue
                for point in tc.keyframe_points:
                    key = int(round(point.co.x - frame_offset))
                    if key in src_interp:
                        point.interpolation = src_interp[key]
                tc.update()
    s = _settings_for(target_obj)
    target_action = nt.animation_data.action if nt.animation_data is not None else None
    _refresh_fcurve_modifiers(target_action, s)
    src_noises = {}
    for fc in _iter_fcurves(src_action):
        for modifier in fc.modifiers:
            if modifier.type == "NOISE":
                src_noises[(fc.data_path, fc.array_index)] = modifier
    if src_noises and target_action is not None:
        for tc in _iter_fcurves(target_action):
            modifier = src_noises.get((tc.data_path, tc.array_index))
            if modifier is not None:
                _set_noise_modifier(tc, modifier.strength, modifier.scale, modifier.phase)
    return True


def _delete_key_at_frame(obj, frame):
    action = _action_for(obj)
    if action is None:
        return 0
    removed = 0
    for fcurve in list(_iter_fcurves(action)):
        for point in list(fcurve.keyframe_points):
            if abs(point.co.x - frame) < 0.5:
                fcurve.keyframe_points.remove(point)
                removed += 1
        fcurve.update()
    return removed


def _copy_settings(source, target):
    if source is None or target is None:
        return
    with _suspend_updates():
        for prop in source.bl_rna.properties:
            key = prop.identifier
            if key == "rna_type":
                continue
            try:
                setattr(target, key, getattr(source, key))
            except Exception:
                pass


def _preset_directory():
    directory = bpy.utils.user_resource("SCRIPTS", path="presets/motion_texture_studio", create=True)
    os.makedirs(directory, exist_ok=True)
    return directory


def _preset_files():
    directory = _preset_directory()
    files = []
    try:
        for name in os.listdir(directory):
            if name.lower().endswith(".json") and name != RECENT_SOURCES_FILE:
                files.append(os.path.join(directory, name))
    except OSError:
        pass
    return sorted(files, key=lambda value: os.path.basename(value).lower())


def _safe_filename(name):
    cleaned = re.sub(r"[^A-Za-z0-9_\- ]+", "_", name).strip()
    return cleaned or "Preset"


def _recent_source_files():
    path = os.path.join(_preset_directory(), RECENT_SOURCES_FILE)
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, list):
            return [p for p in data if isinstance(p, str) and os.path.exists(p)][:MAX_RECENT_SOURCES]
    except Exception:
        pass
    return []


def _remember_source(path):
    try:
        files = [p for p in _recent_source_files() if p != path]
        files.insert(0, path)
        directory = _preset_directory()
        with open(os.path.join(directory, RECENT_SOURCES_FILE), "w", encoding="utf-8") as handle:
            json.dump(files[:MAX_RECENT_SOURCES], handle, indent=2)
    except Exception:
        pass


def _settings_dict(s):
    data = {"format": "motion-texture-studio", "version": 1}
    for key in DEFAULTS:
        value = getattr(s, key, None)
        if hasattr(value, "__len__") and not isinstance(value, str):
            value = list(value)
        data[key] = value
    for key in (
        "source_mode", "frame_start", "frame_end", "fps", "frame_offset",
        "loop_mode", "color_space", "enable_animation", "interpolation",
        "relief_mode", "relief_source", "animate_relief", "subdivision_level",
        "speed", "last_motion_preset", "last_relief_preset", "stop_motion",
        "step_frames", "spread_frames", "auto_fit",
    ):
        data[key] = getattr(s, key, None)
    data["image_path"] = bpy.path.abspath(s.image.filepath) if s.image is not None else ""
    data["normal_image_path"] = bpy.path.abspath(s.normal_image.filepath) if s.normal_image is not None else ""
    return data


def _write_preset(path, s):
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(_settings_dict(s), handle, indent=2)


def _apply_settings_dict(s, data):
    image_path = ""
    normal_path = ""
    with _suspend_updates():
        for key, value in data.items():
            if key in {"format", "version", "image_path", "normal_image_path"}:
                continue
            prop = s.bl_rna.properties.get(key)
            if prop is None:
                continue
            try:
                if key == "glow_color" and isinstance(value, list):
                    value = tuple(value)
                setattr(s, key, value)
            except Exception:
                pass
        image_path = data.get("image_path", "")
        normal_path = data.get("normal_image_path", "")
        if image_path and os.path.exists(bpy.path.abspath(image_path)):
            image = bpy.data.images.load(bpy.path.abspath(image_path), check_existing=True)
            s.image = image
            s.source_path = bpy.path.abspath(image_path)
            s.exif_code = _exif_orientation(bpy.path.abspath(image_path))
        if normal_path and os.path.exists(bpy.path.abspath(normal_path)):
            s.normal_image = bpy.data.images.load(bpy.path.abspath(normal_path), check_existing=True)


def _apply_settings_file(context, path, warn=True):
    obj = getattr(context, "active_object", None)
    s = _settings_for(obj)
    if s is None:
        return False, "Select a mesh object first"
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except Exception as exc:
        return False, "Could not read preset: %s" % exc
    if data.get("format") != "motion-texture-studio":
        return False, "That file is not a Motion Texture preset"
    _apply_settings_dict(s, data)
    if s.source_mode in {"SEQUENCE", "MOVIE"}:
        context.scene.frame_start = max(1, s.frame_start)
        context.scene.frame_end = max(s.frame_start, s.frame_end)
    _apply(context, rebuild=False, obj=obj)
    return True, ""


def _load_source(context, path, mode):
    obj = getattr(context, "active_object", None)
    s = _settings_for(obj)
    if s is None:
        return False, "Select a mesh object first"
    if not path or not os.path.exists(path):
        return False, "File not found"
    extension = os.path.splitext(path)[1].lower()
    if mode == "STILL" and extension in IMAGE_EXT_SET:
        detected = _sequence_range(path)
        if detected is not None and detected[1] > detected[0]:
            mode = "SEQUENCE"
    try:
        image = bpy.data.images.load(path, check_existing=True)
    except Exception as exc:
        return False, "Could not load source: %s" % exc
    with _suspend_updates():
        s.image = image
        s.source_path = path
        s.source_mode = mode
        s.exif_code = _exif_orientation(path) if extension in IMAGE_EXT_SET else 1
        if mode == "MOVIE":
            s.exif_code = _video_rotation(path)
        if mode == "SEQUENCE":
            detected = _sequence_range(path)
            if detected is not None:
                s.frame_start, s.frame_end = detected
            else:
                s.frame_start = 1
                s.frame_end = max(1, context.scene.frame_end)
            s.enable_animation = True
        elif mode == "MOVIE":
            try:
                image.source = "MOVIE"
                image.reload()
            except Exception:
                pass
            s.frame_start = 1
            duration = int(getattr(image, "frame_duration", 0) or 0)
            s.frame_end = duration if duration > 1 else max(1, context.scene.frame_end)
            s.enable_animation = True
        else:
            s.frame_start = 1
            s.frame_end = 1
        s.frame_offset = 0
    if mode in {"SEQUENCE", "MOVIE"}:
        context.scene.frame_start = s.frame_start
        context.scene.frame_end = s.frame_end
        context.scene.frame_set(s.frame_start)
    _remember_source(path)
    if s.auto_fit and getattr(obj, "type", "") == "MESH" and len(obj.data.polygons) > 1:
        _fit_object_uvs(obj, "ALL")
    _apply(context, rebuild=False, obj=obj)
    return True, ""


def _fit_object_uvs(obj, face="ALL"):
    """Rewrite the object's UVs so the image fills the face(s) upright.

    Returns the number of faces fitted.
    """
    if obj is None or obj.type != "MESH":
        return 0
    mesh = obj.data
    uv_layer = mesh.uv_layers.active
    if uv_layer is None:
        uv_layer = mesh.uv_layers.new(name="UVMap")
    if uv_layer is None:
        return 0
    mesh.calc_loop_triangles()
    aspect = _image_aspect(obj)
    count = 0
    for poly in mesh.polygons:
        loops = list(poly.loop_indices)
        if len(loops) < 3:
            continue
        if face == "FRONT" and not _is_front_facing(obj, poly):
            for index in loops:
                uv_layer.data[index].uv = (0.0, 0.0)
            continue
        _map_poly_to_unit_square(mesh, uv_layer, poly, aspect)
        count += 1
    uv_layer.active_render = True
    mesh.update()
    return count


class MotionTextureSettings(bpy.types.PropertyGroup):
    image: bpy.props.PointerProperty(name="Image", type=bpy.types.Image, update=_on_update)
    normal_image: bpy.props.PointerProperty(name="Normal Map", type=bpy.types.Image, update=_on_update)
    source_path: bpy.props.StringProperty(name="Source", default="", subtype="FILE_PATH")
    source_mode: bpy.props.EnumProperty(name="Source Type", items=SOURCE_MODE_ITEMS, default="STILL", update=_on_update)
    frame_start: bpy.props.IntProperty(name="Source Start", min=1, default=1, update=_on_update)
    frame_end: bpy.props.IntProperty(name="Source End", min=1, default=1, update=_on_update)
    fps: bpy.props.FloatProperty(name="FPS", min=1.0, max=240.0, default=24.0, update=_on_fps)
    frame_offset: bpy.props.IntProperty(name="Frame Offset", default=0, update=_on_update)
    loop_mode: bpy.props.EnumProperty(name="Loop", items=LOOP_ITEMS, default="LOOP", update=_on_update)
    color_space: bpy.props.EnumProperty(name="Color Space", items=COLOR_SPACE_ITEMS, default="sRGB", update=_on_update)
    preview_on_selected: bpy.props.BoolProperty(name="Preview on Selected", default=True, update=_on_update)
    auto_fit: bpy.props.BoolProperty(
        name="Auto-Fit UVs", default=True,
        description="When opening a source on a multi-face object like a cube, rewrite its UVs so the image fills each face upright instead of showing sideways",
    )

    enable_animation: bpy.props.BoolProperty(name="Enable Animation", default=False, update=_on_update)
    interpolation: bpy.props.EnumProperty(name="Interpolation", items=INTERPOLATION_ITEMS, default="BEZIER", update=_on_interpolation)
    animate_relief: bpy.props.BoolProperty(name="Animate Relief with Presets", default=True, update=_on_update)
    speed: bpy.props.EnumProperty(name="Speed", items=SPEED_ITEMS, default="1", update=_on_speed)
    last_motion_preset: bpy.props.StringProperty(name="Last Motion Preset", default="")
    last_relief_preset: bpy.props.StringProperty(name="Last Relief Preset", default="")
    stop_motion: bpy.props.BoolProperty(
        name="On Twos", default=False, update=_on_fcurve_modifiers,
        description="Hold every animated value for a few frames, like stop-motion on twos or threes",
    )
    step_frames: bpy.props.IntProperty(
        name="Hold Frames", min=1, max=6, default=2, update=_on_fcurve_modifiers,
    )
    spread_frames: bpy.props.IntProperty(
        name="Batch Offset", min=0, max=24, default=4,
        description="When applying to all selected, offset each object's animation by this many frames so a row ripples instead of moving in lockstep",
    )
    exif_code: bpy.props.IntProperty(name="EXIF Orientation", min=1, max=8, default=1)

    invert: bpy.props.BoolProperty(name="Invert", default=False, update=_on_update)
    grayscale: bpy.props.FloatProperty(name="Desaturate", min=0.0, max=1.0, default=0.0, subtype="FACTOR", update=_on_update)
    hue: bpy.props.FloatProperty(name="Hue", min=0.0, max=1.0, default=0.0, subtype="FACTOR", update=_on_update)
    saturation: bpy.props.FloatProperty(name="Saturation", min=0.0, max=2.0, default=1.0, subtype="FACTOR", update=_on_update)
    brightness: bpy.props.FloatProperty(name="Brightness", min=0.0, max=2.0, default=1.0, subtype="FACTOR", update=_on_update)
    contrast: bpy.props.FloatProperty(name="Contrast", min=0.0, max=2.0, default=1.0, subtype="FACTOR", update=_on_update)
    gamma: bpy.props.FloatProperty(name="Gamma / Midtones", min=0.2, max=4.0, default=1.0, update=_on_update)
    temperature: bpy.props.FloatProperty(name="Temperature", min=-1.0, max=1.0, default=0.0, subtype="FACTOR", update=_on_update)
    tint: bpy.props.FloatProperty(name="Tint", min=-1.0, max=1.0, default=0.0, subtype="FACTOR", update=_on_update)
    posterize: bpy.props.IntProperty(name="Posterize", min=0, max=16, default=0, update=_on_update)
    remap: bpy.props.FloatProperty(
        name="Color Map", min=0.0, max=1.0, default=0.0, subtype="FACTOR", update=_on_update,
        description="Blend the image toward the per-object color ramp below",
    )
    amount: bpy.props.FloatProperty(name="Amount", min=0.0, max=1.0, default=1.0, subtype="FACTOR", update=_on_update)

    scale: bpy.props.FloatProperty(name="Scale", min=0.05, max=16.0, default=1.0, update=_on_update)
    tiling_x: bpy.props.FloatProperty(name="Tiling X", min=0.05, max=50.0, default=1.0, update=_on_update)
    tiling_y: bpy.props.FloatProperty(name="Tiling Y", min=0.05, max=50.0, default=1.0, update=_on_update)
    rotation: bpy.props.FloatProperty(name="Rotation Z", min=-180.0, max=180.0, default=0.0, update=_on_update)
    rotation_x: bpy.props.FloatProperty(name="Rotation X", min=-180.0, max=180.0, default=0.0, update=_on_update)
    rotation_y: bpy.props.FloatProperty(name="Rotation Y", min=-180.0, max=180.0, default=0.0, update=_on_update)
    offset_x: bpy.props.FloatProperty(name="Offset X", min=-4.0, max=4.0, default=0.0, subtype="FACTOR", update=_on_update)
    offset_y: bpy.props.FloatProperty(name="Offset Y", min=-4.0, max=4.0, default=0.0, subtype="FACTOR", update=_on_update)
    offset_z: bpy.props.FloatProperty(name="Offset Z", min=-4.0, max=4.0, default=0.0, subtype="FACTOR", update=_on_update)
    scale_z: bpy.props.FloatProperty(name="Scale Z", min=0.05, max=16.0, default=1.0, update=_on_update)
    flip_x: bpy.props.BoolProperty(name="Flip X", default=False, update=_on_update)
    flip_y: bpy.props.BoolProperty(name="Flip Y", default=False, update=_on_update)

    relief_mode: bpy.props.EnumProperty(name="Relief Mode", items=RELIEF_MODE_ITEMS, default="BUMP", update=_on_update)
    relief_source: bpy.props.EnumProperty(name="Relief Source", items=RELIEF_SOURCE_ITEMS, default="IMAGE", update=_on_update)
    relief: bpy.props.FloatProperty(name="Relief", min=0.0, max=1.0, default=0.5, subtype="FACTOR", update=_on_update)
    depth: bpy.props.FloatProperty(name="Depth", min=0.0, max=2.0, default=0.5, subtype="FACTOR", update=_on_update)
    relief_invert: bpy.props.BoolProperty(name="Invert Relief", default=False, update=_on_update)
    detail: bpy.props.FloatProperty(name="Detail", min=0.0, max=1.0, default=0.0, subtype="FACTOR", update=_on_update)
    detail_scale: bpy.props.FloatProperty(name="Detail Scale", min=0.5, max=40.0, default=8.0, update=_on_update)
    relief_speed: bpy.props.FloatProperty(name="Relief Speed", min=0.05, max=3.0, default=0.5, update=_on_update)
    relief_amplitude: bpy.props.FloatProperty(name="Relief Amplitude", min=0.0, max=1.0, default=0.5, subtype="FACTOR", update=_on_update)
    relief_phase: bpy.props.FloatProperty(name="Relief Phase", min=0.0, max=6.283, default=0.0, update=_on_update)
    subdivision_level: bpy.props.IntProperty(name="Subdivision Level", min=0, max=6, default=2, update=_on_update)

    roughness: bpy.props.FloatProperty(name="Roughness", min=0.0, max=1.0, default=0.5, subtype="FACTOR", update=_on_update)
    metallic: bpy.props.FloatProperty(name="Metallic", min=0.0, max=1.0, default=0.0, subtype="FACTOR", update=_on_update)
    specular: bpy.props.FloatProperty(name="Specular", min=0.0, max=1.0, default=0.5, subtype="FACTOR", update=_on_update)
    ior: bpy.props.FloatProperty(name="IOR", min=1.0, max=3.0, default=1.5, update=_on_update)
    coat: bpy.props.FloatProperty(name="Coat", min=0.0, max=1.0, default=0.0, subtype="FACTOR", update=_on_update)
    coat_roughness: bpy.props.FloatProperty(name="Coat Roughness", min=0.0, max=1.0, default=0.03, subtype="FACTOR", update=_on_update)
    sheen: bpy.props.FloatProperty(name="Sheen", min=0.0, max=1.0, default=0.0, subtype="FACTOR", update=_on_update)
    sheen_roughness: bpy.props.FloatProperty(name="Sheen Roughness", min=0.0, max=1.0, default=0.5, subtype="FACTOR", update=_on_update)
    anisotropic: bpy.props.FloatProperty(name="Anisotropic", min=-1.0, max=1.0, default=0.0, subtype="FACTOR", update=_on_update)
    subsurface: bpy.props.FloatProperty(name="Subsurface", min=0.0, max=1.0, default=0.0, subtype="FACTOR", update=_on_update)
    transmission: bpy.props.FloatProperty(name="Transmission", min=0.0, max=1.0, default=0.0, subtype="FACTOR", update=_on_update)
    alpha: bpy.props.FloatProperty(name="Alpha", min=0.0, max=1.0, default=1.0, subtype="FACTOR", update=_on_update)
    normal_strength: bpy.props.FloatProperty(name="Normal Strength", min=0.0, max=3.0, default=1.0, update=_on_update)

    emission: bpy.props.FloatProperty(name="Glow", min=0.0, max=5.0, default=0.0, update=_on_update)
    glow_mask: bpy.props.BoolProperty(name="Glow From Image", default=False, update=_on_update)
    glow_color: bpy.props.FloatVectorProperty(
        name="Glow Tint", subtype="COLOR", size=4, min=0.0, max=1.0,
        default=(1.0, 1.0, 1.0, 1.0), update=_on_update,
    )


class MOTIONTEXTURE_OT_apply(bpy.types.Operator):
    bl_idname = "motiontexture.apply"
    bl_label = "Apply to Selected"
    bl_description = "Build or refresh the animated material on the active mesh"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        obj = context.active_object
        if obj is None or obj.type != "MESH":
            self.report({"WARNING"}, "Select a mesh object first")
            return {"CANCELLED"}
        _apply(context, rebuild=False, obj=obj)
        self.report({"INFO"}, "Applied Motion Texture to %s" % obj.name)
        return {"FINISHED"}


class MOTIONTEXTURE_OT_apply_all(bpy.types.Operator):
    bl_idname = "motiontexture.apply_all"
    bl_label = "Apply to All Selected"
    bl_description = "Copy the active object's motion setup and animation to every selected mesh, offset in time so a row ripples"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        source = _settings(context)
        if source is None:
            self.report({"WARNING"}, "Select the source mesh first")
            return {"CANCELLED"}
        targets = [obj for obj in context.selected_objects if obj.type == "MESH"]
        if not targets:
            self.report({"WARNING"}, "No mesh objects are selected")
            return {"CANCELLED"}
        active = context.active_object
        copied = 0
        offset = 0
        for obj in targets:
            if obj != active:
                offset += source.spread_frames
                _copy_settings(source, _settings_for(obj))
                _apply(context, rebuild=False, obj=obj)
                if _copy_action_curves(active, obj, frame_offset=offset):
                    copied += 1
            else:
                _apply(context, rebuild=False, obj=obj)
        self.report({"INFO"}, "Applied to %d meshes; animation copied to %d with %d-frame offsets" % (
            len(targets), copied, source.spread_frames))
        return {"FINISHED"}


class MOTIONTEXTURE_OT_rebuild(bpy.types.Operator):
    bl_idname = "motiontexture.rebuild"
    bl_label = "Rebuild Material"
    bl_description = "Rebuild the node graph from scratch. This clears existing animation"
    bl_options = {"REGISTER", "UNDO"}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        obj = context.active_object
        if obj is None or obj.type != "MESH":
            self.report({"WARNING"}, "Select a mesh object first")
            return {"CANCELLED"}
        _clear_animation(obj)
        _apply(context, rebuild=True, obj=obj)
        self.report({"INFO"}, "Rebuilt material; animation cleared")
        return {"FINISHED"}


class MOTIONTEXTURE_OT_revert_still(bpy.types.Operator):
    bl_idname = "motiontexture.revert_still"
    bl_label = "Revert to Still"
    bl_description = "Remove animation and return to the static texture values"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        obj = context.active_object
        if obj is None or obj.type != "MESH":
            self.report({"WARNING"}, "Select a mesh object first")
            return {"CANCELLED"}
        s = _settings_for(obj)
        _clear_animation(obj)
        with _suspend_updates():
            s.enable_animation = False
        _apply(context, rebuild=False, obj=obj)
        self.report({"INFO"}, "Animation cleared")
        return {"FINISHED"}


class MOTIONTEXTURE_OT_play(bpy.types.Operator):
    bl_idname = "motiontexture.play"
    bl_label = "Play / Pause"
    bl_description = "Play or pause the scene timeline"

    def execute(self, context):
        try:
            bpy.ops.screen.animation_play()
        except Exception as exc:
            self.report({"WARNING"}, "Playback is not available: %s" % exc)
            return {"CANCELLED"}
        return {"FINISHED"}


class MOTIONTEXTURE_OT_frame_step(bpy.types.Operator):
    bl_idname = "motiontexture.frame_step"
    bl_label = "Step Frame"
    bl_description = "Move the scene one frame backward or forward"
    direction: bpy.props.IntProperty(default=1)

    def execute(self, context):
        context.scene.frame_set(context.scene.frame_current + self.direction)
        return {"FINISHED"}


class MOTIONTEXTURE_OT_preview_render(bpy.types.Operator):
    bl_idname = "motiontexture.preview_render"
    bl_label = "Preview Render"
    bl_description = "Render the current frame to a temporary PNG"
    bl_options = {"REGISTER"}

    def execute(self, context):
        scene = context.scene
        path = os.path.join(bpy.app.tempdir, "motion_texture_preview.png")
        previous_path = scene.render.filepath
        previous_format = scene.render.image_settings.file_format
        scene.render.filepath = path
        scene.render.image_settings.file_format = "PNG"
        try:
            bpy.ops.render.render(write_still=True)
        except Exception as exc:
            self.report({"ERROR"}, "Render failed: %s" % exc)
            return {"CANCELLED"}
        finally:
            scene.render.filepath = previous_path
            scene.render.image_settings.file_format = previous_format
        self.report({"INFO"}, "Preview rendered to %s" % path)
        return {"FINISHED"}


class MOTIONTEXTURE_OT_key_all(bpy.types.Operator):
    bl_idname = "motiontexture.key_all"
    bl_label = "Key at Current Frame"
    bl_description = "Key the main texture, surface, and relief controls at the current frame"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        obj = context.active_object
        if obj is None or obj.type != "MESH":
            self.report({"WARNING"}, "Select a mesh object first")
            return {"CANCELLED"}
        _apply(context, rebuild=False, obj=obj)
        if not _key_all(obj, context):
            self.report({"WARNING"}, "No Motion Texture material found")
            return {"CANCELLED"}
        s = _settings_for(obj)
        with _suspend_updates():
            s.enable_animation = True
        self.report({"INFO"}, "Keyed at frame %d" % context.scene.frame_current)
        return {"FINISHED"}


class MOTIONTEXTURE_OT_copy_still(bpy.types.Operator):
    bl_idname = "motiontexture.copy_still"
    bl_label = "Copy Still Values to Frame 1"
    bl_description = "Key the current values at frame 1"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        obj = context.active_object
        if obj is None or obj.type != "MESH":
            self.report({"WARNING"}, "Select a mesh object first")
            return {"CANCELLED"}
        _apply(context, rebuild=False, obj=obj)
        if not _key_all(obj, context, frame=1):
            self.report({"WARNING"}, "No Motion Texture material found")
            return {"CANCELLED"}
        s = _settings_for(obj)
        with _suspend_updates():
            s.enable_animation = True
        self.report({"INFO"}, "Copied still values to frame 1")
        return {"FINISHED"}


class MOTIONTEXTURE_OT_delete_key(bpy.types.Operator):
    bl_idname = "motiontexture.delete_key"
    bl_label = "Delete Key"
    bl_description = "Delete animation keys at the current frame"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        obj = context.active_object
        if obj is None or obj.type != "MESH":
            self.report({"WARNING"}, "Select a mesh object first")
            return {"CANCELLED"}
        removed = _delete_key_at_frame(obj, context.scene.frame_current)
        self.report({"INFO"}, "Removed %d keyframes" % removed)
        return {"FINISHED"}


class MOTIONTEXTURE_OT_clear_animation(bpy.types.Operator):
    bl_idname = "motiontexture.clear_animation"
    bl_label = "Clear Animation"
    bl_description = "Remove all animation from this object's material"
    bl_options = {"REGISTER", "UNDO"}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        obj = context.active_object
        if obj is None or obj.type != "MESH":
            self.report({"WARNING"}, "Select a mesh object first")
            return {"CANCELLED"}
        _clear_animation(obj)
        s = _settings_for(obj)
        with _suspend_updates():
            s.enable_animation = False
            s.last_motion_preset = ""
            s.last_relief_preset = ""
        _apply(context, rebuild=False, obj=obj)
        self.report({"INFO"}, "Animation cleared")
        return {"FINISHED"}


def _apply_motion_preset(obj, context, preset, reset=True):
    """Key one motion cycle (a short repeating segment) on the material.

    A CYCLES modifier on every curve repeats the cycle for a shot of any
    length, so the scene frame range does not matter. The Speed setting
    chooses the cycle length.
    """
    s = _settings_for(obj)
    if s is None:
        return False, "Select a mesh object first"
    _apply(context, rebuild=False, obj=obj)
    mat = _find_material(obj)
    if mat is None or mat.node_tree is None:
        return False, "No Motion Texture material found"
    if reset:
        _reset_preset_curves(obj)
    nt = mat.node_tree
    cycle = _cycle_frames(s)
    start = 1
    end = start + cycle
    middle = start + cycle // 2
    mapping = nt.nodes["MT_Map"]
    motion_map = nt.nodes["MT_MotionMap"]
    bump = nt.nodes["MT_Bump"]
    displacement = nt.nodes["MT_Displace"]
    hsv = nt.nodes["MT_HueSat"]
    glow_mul = nt.nodes["MT_Glow_Mul"]
    relief_travel = max(0.05, s.relief_speed)
    amplitude = max(0.0, s.relief_amplitude)
    mode = s.interpolation

    if preset == "SCROLL_X":
        _key_socket(mapping, "Location", start, (0.0, 0.0, 0.0))
        _key_socket(mapping, "Location", end, (1.0, 0.0, 0.0))
        mode = "LINEAR"
        if s.animate_relief:
            _key_socket(motion_map, "Location", start, (0.0, 0.0, 0.0))
            _key_socket(motion_map, "Location", end, (relief_travel, 0.0, 0.0))
    elif preset == "SCROLL_Y":
        _key_socket(mapping, "Location", start, (0.0, 0.0, 0.0))
        _key_socket(mapping, "Location", end, (0.0, 1.0, 0.0))
        mode = "LINEAR"
        if s.animate_relief:
            _key_socket(motion_map, "Location", start, (0.0, 0.0, 0.0))
            _key_socket(motion_map, "Location", end, (0.0, relief_travel, 0.0))
    elif preset == "DRIFT":
        _key_socket(mapping, "Location", start, (0.0, 0.0, 0.0))
        _key_socket(mapping, "Location", end, (1.0, 0.5, 0.0))
        mode = "LINEAR"
        if s.animate_relief:
            _key_socket(motion_map, "Location", start, (0.0, 0.0, 0.0))
            _key_socket(motion_map, "Location", end, (relief_travel, relief_travel * 0.5, 0.0))
    elif preset == "PULSE":
        _key_socket(bump, "Strength", start, 0.15)
        _key_socket(bump, "Strength", middle, 0.15 + 0.85 * amplitude)
        _key_socket(bump, "Strength", end, 0.15)
        _key_socket(displacement, "Scale", start, 0.01)
        _key_socket(displacement, "Scale", middle, 0.01 + 0.25 * amplitude)
        _key_socket(displacement, "Scale", end, 0.01)
        mode = "BEZIER"
    elif preset == "BREATHE":
        _key_socket(mapping, "Scale", start, (1.0, 1.0, 1.0))
        _key_socket(mapping, "Scale", middle, (1.0 + 0.08 * amplitude, 1.0 + 0.08 * amplitude, 1.0))
        _key_socket(mapping, "Scale", end, (1.0, 1.0, 1.0))
        mode = "BEZIER"
    elif preset == "RIPPLE":
        _key_socket(motion_map, "Location", start, (0.0, 0.0, 0.0))
        _key_socket(motion_map, "Location", end, (relief_travel, 0.0, 0.0))
        _key_socket(bump, "Strength", start, 0.2)
        _key_socket(bump, "Strength", middle, 0.2 + 0.8 * amplitude)
        _key_socket(bump, "Strength", end, 0.2)
        mode = "BEZIER"
    elif preset == "FLICKER":
        _key_socket(hsv, "Value", start, 1.0)
        _key_socket(glow_mul, "Value", start, 0.5)
        mode = "LINEAR"

    action = _action_for(obj)
    _set_interpolation(action, mode)
    if preset == "FLICKER":
        strength = 0.35 + 0.65 * amplitude
        value_path = _socket_data_path(hsv, "Value")
        glow_path = _socket_data_path(glow_mul, "Value")
        for fcurve in _iter_fcurves(action):
            if fcurve.data_path in {value_path, glow_path}:
                _set_noise_modifier(fcurve, strength=strength, scale=4.0, phase=0.0)
    _refresh_fcurve_modifiers(action, s)
    with _suspend_updates():
        s.interpolation = mode
        s.enable_animation = True
        s.last_motion_preset = preset
    return True, ""


def _apply_relief_motion(obj, context, preset, reset=True):
    """Key one relief cycle on the raised-surface nodes; CYCLES repeats it."""
    s = _settings_for(obj)
    if s is None:
        return False, "Select a mesh object first"
    _apply(context, rebuild=False, obj=obj)
    mat = _find_material(obj)
    if mat is None or mat.node_tree is None:
        return False, "No Motion Texture material found"
    if reset:
        _reset_preset_curves(obj)
    nt = mat.node_tree
    cycle = _cycle_frames(s)
    start = 1
    end = start + cycle
    middle = start + cycle // 2
    motion_map = nt.nodes["MT_MotionMap"]
    bump = nt.nodes["MT_Bump"]
    relief_travel = max(0.05, s.relief_speed)
    amplitude = max(0.0, s.relief_amplitude)
    base = max(0.05, s.relief)
    mode = s.interpolation

    if preset == "DRIFT":
        _key_socket(motion_map, "Location", start, (0.0, 0.0, 0.0))
        _key_socket(motion_map, "Location", end, (relief_travel, 0.0, 0.0))
        mode = "LINEAR"
    elif preset == "PULSE":
        _key_socket(bump, "Strength", start, base * 0.35)
        _key_socket(bump, "Strength", middle, base * 0.35 + amplitude * 0.9)
        _key_socket(bump, "Strength", end, base * 0.35)
        mode = "BEZIER"
    elif preset == "RIPPLE":
        _key_socket(motion_map, "Location", start, (0.0, 0.0, 0.0))
        _key_socket(motion_map, "Location", end, (relief_travel, 0.0, 0.0))
        _key_socket(bump, "Strength", start, base * 0.3)
        _key_socket(bump, "Strength", middle, base * 0.3 + amplitude)
        _key_socket(bump, "Strength", end, base * 0.3)
        mode = "BEZIER"
    else:
        _key_socket(motion_map, "Location", start, (0.0, 0.0, 0.0))
        _key_socket(motion_map, "Location", end, (relief_travel, relief_travel * 0.4, 0.0))
        mode = "LINEAR"

    action = _action_for(obj)
    _set_interpolation(action, mode)
    _refresh_fcurve_modifiers(action, s)
    with _suspend_updates():
        s.interpolation = mode
        s.enable_animation = True
        s.last_relief_preset = preset
    return True, ""


class MOTIONTEXTURE_OT_motion_preset(bpy.types.Operator):
    bl_idname = "motiontexture.motion_preset"
    bl_label = "Motion Preset"
    bl_description = "Create a ready-made motion that loops over one cycle and repeats for any shot length"
    bl_options = {"REGISTER", "UNDO"}

    preset: bpy.props.EnumProperty(items=MOTION_PRESET_ITEMS)

    def execute(self, context):
        obj = context.active_object
        if obj is None or obj.type != "MESH":
            self.report({"WARNING"}, "Select a mesh object first")
            return {"CANCELLED"}
        ok, message = _apply_motion_preset(obj, context, self.preset)
        if not ok:
            self.report({"WARNING"}, message)
            return {"CANCELLED"}
        self.report({"INFO"}, "Applied %s motion — one %d-frame cycle, repeats automatically" % (
            self.preset, _cycle_frames(_settings_for(obj))))
        return {"FINISHED"}


class MOTIONTEXTURE_OT_relief_motion(bpy.types.Operator):
    bl_idname = "motiontexture.relief_motion"
    bl_label = "Relief Motion"
    bl_description = "Animate the moving raised surface over one repeating cycle"
    bl_options = {"REGISTER", "UNDO"}

    preset: bpy.props.EnumProperty(items=RELIEF_MOTION_ITEMS)

    def execute(self, context):
        obj = context.active_object
        if obj is None or obj.type != "MESH":
            self.report({"WARNING"}, "Select a mesh object first")
            return {"CANCELLED"}
        ok, message = _apply_relief_motion(obj, context, self.preset)
        if not ok:
            self.report({"WARNING"}, message)
            return {"CANCELLED"}
        self.report({"INFO"}, "Applied %s relief motion — one %d-frame cycle, repeats automatically" % (
            self.preset, _cycle_frames(_settings_for(obj))))
        return {"FINISHED"}


class MOTIONTEXTURE_OT_rotate(bpy.types.Operator):
    bl_idname = "motiontexture.rotate"
    bl_label = "Rotate Image"
    bl_description = "Nudge the image rotation by a fixed step"
    angle: bpy.props.FloatProperty(default=90.0)

    def execute(self, context):
        s = _settings(context)
        if s is None:
            return {"CANCELLED"}
        s.rotation = ((s.rotation + self.angle + 180.0) % 360.0) - 180.0
        return {"FINISHED"}


class MOTIONTEXTURE_OT_reset_transform(bpy.types.Operator):
    bl_idname = "motiontexture.reset_transform"
    bl_label = "Reset Transform"
    bl_description = "Reset scale, tiling, rotation, offset and flips to their defaults"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        s = _settings(context)
        if s is None:
            self.report({"WARNING"}, "Select a mesh object first")
            return {"CANCELLED"}
        for key in ("scale", "tiling_x", "tiling_y", "rotation", "rotation_x",
                    "rotation_y", "offset_x", "offset_y", "offset_z", "scale_z",
                    "flip_x", "flip_y"):
            setattr(s, key, DEFAULTS[key])
        self.report({"INFO"}, "Transform reset to defaults")
        return {"FINISHED"}


class MOTIONTEXTURE_OT_fit_surface(bpy.types.Operator):
    bl_idname = "motiontexture.fit_surface"
    bl_label = "Fit Image to Surface"
    bl_description = (
        "Rewrite the object's UVs so the image fills one face upright. "
        "Use this on cubes and multi-face objects, where a single image "
        "otherwise shows sideways or split across the default UV islands"
    )
    bl_options = {"REGISTER", "UNDO"}

    face: bpy.props.EnumProperty(
        name="Face",
        items=(
            ("ALL", "Every Face", "Map the full image onto each face, upright"),
            ("FRONT", "Front Face Only", "Map the full image onto the front face and collapse the other faces"),
        ),
        default="ALL",
    )

    def execute(self, context):
        obj = context.active_object
        print("[MotionTexture] fit_surface clicked: face=%r obj=%r" % (
            self.face, obj.name if obj else None))
        if obj is None or obj.type != "MESH":
            self.report({"WARNING"}, "Select a mesh object first")
            return {"CANCELLED"}
        if len(obj.data.polygons) == 0:
            self.report({"WARNING"}, "This object has no faces")
            return {"CANCELLED"}
        count = _fit_object_uvs(obj, self.face)
        print("[MotionTexture] fit_surface fitted %d faces (face=%s)" % (count, self.face))
        if self.face == "FRONT" and count == 0:
            self.report({"WARNING"}, "No front-facing polygon found")
            return {"CANCELLED"}
        for window in context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == "VIEW_3D":
                    area.tag_redraw()
        self.report({"INFO"}, "Fitted the image to %d face%s — switch the viewport to Material Preview if you cannot see it" % (
            count, "" if count == 1 else "s"))
        return {"FINISHED"}


def _image_aspect(obj):
    s = _settings_for(obj)
    image = s.image if s is not None else None
    if image is not None:
        try:
            width, height = image.size
            if width > 0 and height > 0:
                return width / height
        except Exception:
            pass
    return 1.0


def _is_front_facing(obj, poly):
    normal = poly.normal
    from mathutils import Vector
    world = (obj.matrix_world.to_3x3() @ normal).normalized()
    view = Vector((0.0, 0.0, 1.0))
    return world.dot(view) > 0.1


def _map_poly_to_unit_square(mesh, uv_layer, poly, aspect):
    """Assign UVs so each face shows the whole image, upright (V grows with world up)."""
    from mathutils import Vector
    loops = list(poly.loop_indices)
    coords = [mesh.vertices[mesh.loops[index].vertex_index].co for index in loops]
    center = Vector((0.0, 0.0, 0.0))
    for co in coords:
        center += co
    center /= len(coords)
    normal = poly.normal.normalized()
    up = Vector((0.0, 0.0, 1.0))
    if abs(normal.dot(up)) > 0.9:
        up = Vector((0.0, 1.0, 0.0))
    right = up.cross(normal).normalized()
    up = normal.cross(right).normalized()
    span_x = _poly_span(coords, right)
    span_y = _poly_span(coords, up)
    for index, co in zip(loops, coords):
        local = co - center
        u = 0.5 + (local.dot(right) / span_x)
        v = 0.5 + (local.dot(up) / span_y)
        uv_layer.data[index].uv = (u, v)


def _poly_span(coords, axis):
    values = [co.dot(axis) for co in coords]
    span = max(values) - min(values)
    return span if span > 1e-6 else 1.0


class MOTIONTEXTURE_OT_surface_preset(bpy.types.Operator):
    bl_idname = "motiontexture.surface_preset"
    bl_label = "Surface Preset"
    bl_description = "Apply a ready-made surface look"
    bl_options = {"REGISTER", "UNDO"}

    preset: bpy.props.EnumProperty(items=PRESET_ITEMS)

    def execute(self, context):
        s = _settings(context)
        if s is None:
            return {"CANCELLED"}
        values = SURFACE_PRESETS.get(self.preset)
        if not values:
            return {"CANCELLED"}
        with _suspend_updates():
            for key, value in values.items():
                if key != "label":
                    setattr(s, key, value)
        _apply(context, rebuild=False, obj=context.active_object)
        return {"FINISHED"}


class MOTIONTEXTURE_OT_reset_section(bpy.types.Operator):
    bl_idname = "motiontexture.reset_section"
    bl_label = "Reset Section"
    bl_description = "Reset a group of controls to their defaults"
    bl_options = {"REGISTER", "UNDO"}

    section: bpy.props.EnumProperty(items=(
        ("COLOR", "Color", ""),
        ("TRANSFORM", "Transform", ""),
        ("SURFACE", "Surface", ""),
        ("ANIMATION", "Animation", ""),
        ("ALL", "Everything", ""),
    ), default="ALL")

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        obj = context.active_object
        s = _settings_for(obj)
        if s is None:
            return {"CANCELLED"}
        with _suspend_updates():
            for key in RESET_SECTIONS.get(self.section, ()):
                setattr(s, key, DEFAULTS[key])
            if self.section in {"ANIMATION", "ALL"}:
                s.enable_animation = False
                s.animate_relief = True
                s.last_motion_preset = ""
                s.last_relief_preset = ""
        if self.section in {"ANIMATION", "ALL"}:
            _clear_animation(obj)
        _apply(context, rebuild=self.section == "ALL", obj=obj)
        return {"FINISHED"}


class MOTIONTEXTURE_MT_reset(bpy.types.Menu):
    bl_idname = "MOTIONTEXTURE_MT_reset"
    bl_label = "Reset"

    def draw(self, context):
        for key, label in (("COLOR", "Color"), ("TRANSFORM", "Transform"),
                           ("SURFACE", "Surface"), ("ANIMATION", "Animation"),
                           ("ALL", "Everything")):
            operator = self.layout.operator("motiontexture.reset_section", text=label)
            operator.section = key


class MOTIONTEXTURE_OT_open_still(bpy.types.Operator):
    bl_idname = "motiontexture.open_still"
    bl_label = "Open Still"
    bl_description = "Load a single image as the texture"
    filepath: bpy.props.StringProperty(subtype="FILE_PATH")
    filter_glob: bpy.props.StringProperty(default=IMAGE_FILTER, options={"HIDDEN"})

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        ok, message = _load_source(context, self.filepath, "STILL")
        if not ok:
            self.report({"ERROR"}, message)
            return {"CANCELLED"}
        s = _settings(context)
        if s is not None and s.source_mode == "SEQUENCE":
            self.report({"INFO"}, "Auto-detected image sequence %s (%d-%d)" % (
                os.path.basename(self.filepath), s.frame_start, s.frame_end))
        else:
            self.report({"INFO"}, "Loaded still %s" % os.path.basename(self.filepath))
        return {"FINISHED"}


class MOTIONTEXTURE_OT_open_sequence(bpy.types.Operator):
    bl_idname = "motiontexture.open_sequence"
    bl_label = "Open Image Sequence"
    bl_description = "Load a numbered image sequence. Pick any frame; the range is detected"
    filepath: bpy.props.StringProperty(subtype="FILE_PATH")
    filter_glob: bpy.props.StringProperty(default=IMAGE_FILTER, options={"HIDDEN"})

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        ok, message = _load_source(context, self.filepath, "SEQUENCE")
        if not ok:
            self.report({"ERROR"}, message)
            return {"CANCELLED"}
        self.report({"INFO"}, "Loaded sequence from %s" % os.path.basename(self.filepath))
        return {"FINISHED"}


class MOTIONTEXTURE_OT_open_movie(bpy.types.Operator):
    bl_idname = "motiontexture.open_movie"
    bl_label = "Open Movie"
    bl_description = "Load a movie file as an animated texture"
    filepath: bpy.props.StringProperty(subtype="FILE_PATH")
    filter_glob: bpy.props.StringProperty(default=MOVIE_FILTER, options={"HIDDEN"})

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        ok, message = _load_source(context, self.filepath, "MOVIE")
        if not ok:
            self.report({"ERROR"}, message)
            return {"CANCELLED"}
        self.report({"INFO"}, "Loaded movie %s" % os.path.basename(self.filepath))
        return {"FINISHED"}


class MOTIONTEXTURE_OT_refresh_source(bpy.types.Operator):
    bl_idname = "motiontexture.refresh_source"
    bl_label = "Refresh Source"
    bl_description = "Reload the source image from disk"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        obj = context.active_object
        s = _settings_for(obj)
        if s is None or s.image is None:
            self.report({"WARNING"}, "No source image to refresh")
            return {"CANCELLED"}
        try:
            s.image.reload()
        except Exception as exc:
            self.report({"ERROR"}, "Could not reload source: %s" % exc)
            return {"CANCELLED"}
        _apply(context, rebuild=False, obj=obj)
        return {"FINISHED"}


class MOTIONTEXTURE_OT_clear_source(bpy.types.Operator):
    bl_idname = "motiontexture.clear_source"
    bl_label = "Clear Source"
    bl_description = "Remove the source image from this object"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        obj = context.active_object
        s = _settings_for(obj)
        if s is None:
            return {"CANCELLED"}
        with _suspend_updates():
            s.image = None
            s.source_path = ""
            s.source_mode = "STILL"
            s.frame_start = 1
            s.frame_end = 1
            s.exif_code = 0
        _apply(context, rebuild=False, obj=obj)
        return {"FINISHED"}


class MOTIONTEXTURE_OT_open_normal(bpy.types.Operator):
    bl_idname = "motiontexture.open_normal"
    bl_label = "Load Normal Map"
    bl_description = "Load a normal map image"
    filepath: bpy.props.StringProperty(subtype="FILE_PATH")
    filter_glob: bpy.props.StringProperty(default=IMAGE_FILTER, options={"HIDDEN"})

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        s = _settings(context)
        if s is None:
            self.report({"WARNING"}, "Select a mesh object first")
            return {"CANCELLED"}
        try:
            image = bpy.data.images.load(self.filepath, check_existing=True)
        except Exception as exc:
            self.report({"ERROR"}, "Could not load normal map: %s" % exc)
            return {"CANCELLED"}
        try:
            image.colorspace_settings.name = "Non-Color"
        except Exception:
            pass
        s.normal_image = image
        _apply(context, rebuild=False, obj=context.active_object)
        return {"FINISHED"}


class MOTIONTEXTURE_OT_drop_source(bpy.types.Operator):
    bl_idname = "motiontexture.drop_source"
    bl_label = "Motion Texture: Drop Source"
    bl_description = "Load a dragged-and-dropped image or movie as the texture"
    bl_options = {"REGISTER", "UNDO"}

    filepath: bpy.props.StringProperty(subtype="FILE_PATH", options={"SKIP_SAVE"})

    def execute(self, context):
        if not self.filepath:
            return {"CANCELLED"}
        extension = os.path.splitext(self.filepath)[1].lower().lstrip(".")
        if extension in MOVIE_EXT_SET:
            mode = "MOVIE"
        elif extension in IMAGE_EXT_SET:
            mode = "STILL"
        else:
            self.report({"WARNING"}, "Unsupported file type: .%s" % extension)
            return {"CANCELLED"}
        ok, message = _load_source(context, self.filepath, mode)
        if not ok:
            self.report({"ERROR"}, message)
            return {"CANCELLED"}
        self.report({"INFO"}, "Loaded %s" % os.path.basename(self.filepath))
        return {"FINISHED"}


class MOTIONTEXTURE_FH_source_drop(bpy.types.FileHandler):
    bl_idname = "MOTIONTEXTURE_FH_source_drop"
    bl_label = "Motion Texture Source"
    bl_import_operator = "motiontexture.drop_source"
    bl_file_extensions = DROP_EXTENSIONS

    @classmethod
    def poll_drop(cls, context):
        area = getattr(context, "area", None)
        return area is not None and area.type in {"VIEW_3D", "IMAGE_EDITOR"}


class MOTIONTEXTURE_OT_save_preset(bpy.types.Operator):
    bl_idname = "motiontexture.save_preset"
    bl_label = "Save Motion Preset"
    bl_description = "Save the current source, motion, relief, and surface setup to disk"
    bl_options = {"REGISTER"}

    preset_name: bpy.props.StringProperty(name="Preset Name", default="My Motion")

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        s = _settings(context)
        if s is None:
            self.report({"WARNING"}, "Select a mesh object first")
            return {"CANCELLED"}
        filename = _safe_filename(self.preset_name) + ".json"
        path = os.path.join(_preset_directory(), filename)
        try:
            _write_preset(path, s)
        except Exception as exc:
            self.report({"ERROR"}, "Could not save preset: %s" % exc)
            return {"CANCELLED"}
        self.report({"INFO"}, "Saved preset %s" % filename)
        return {"FINISHED"}


class MOTIONTEXTURE_OT_load_preset(bpy.types.Operator):
    bl_idname = "motiontexture.load_preset"
    bl_label = "Load Motion Preset"
    bl_description = "Load a saved motion preset"
    bl_options = {"REGISTER", "UNDO"}

    preset: bpy.props.StringProperty()

    def execute(self, context):
        ok, message = _apply_settings_file(context, self.preset)
        if not ok:
            self.report({"ERROR"}, message)
            return {"CANCELLED"}
        self.report({"INFO"}, "Loaded preset %s" % os.path.basename(self.preset))
        return {"FINISHED"}


class MOTIONTEXTURE_OT_delete_preset(bpy.types.Operator):
    bl_idname = "motiontexture.delete_preset"
    bl_label = "Delete Motion Preset"
    bl_description = "Delete a saved motion preset from disk"
    bl_options = {"REGISTER"}

    preset: bpy.props.StringProperty()

    def execute(self, context):
        try:
            os.remove(self.preset)
        except Exception as exc:
            self.report({"ERROR"}, "Could not delete preset: %s" % exc)
            return {"CANCELLED"}
        self.report({"INFO"}, "Deleted %s" % os.path.basename(self.preset))
        return {"FINISHED"}


class MOTIONTEXTURE_OT_export_preset(bpy.types.Operator):
    bl_idname = "motiontexture.export_preset"
    bl_label = "Export Motion Preset"
    bl_description = "Export the current setup as a portable JSON preset"
    filepath: bpy.props.StringProperty(subtype="FILE_PATH")
    filter_glob: bpy.props.StringProperty(default="*.json", options={"HIDDEN"})

    def invoke(self, context, event):
        self.filepath = "motion_texture_preset.json"
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        s = _settings(context)
        if s is None:
            self.report({"WARNING"}, "Select a mesh object first")
            return {"CANCELLED"}
        path = self.filepath if self.filepath.lower().endswith(".json") else self.filepath + ".json"
        try:
            _write_preset(path, s)
        except Exception as exc:
            self.report({"ERROR"}, "Could not export preset: %s" % exc)
            return {"CANCELLED"}
        self.report({"INFO"}, "Exported %s" % path)
        return {"FINISHED"}


class MOTIONTEXTURE_OT_import_preset(bpy.types.Operator):
    bl_idname = "motiontexture.import_preset"
    bl_label = "Import Motion Preset"
    bl_description = "Import a portable JSON motion preset"
    bl_options = {"REGISTER", "UNDO"}
    filepath: bpy.props.StringProperty(subtype="FILE_PATH")
    filter_glob: bpy.props.StringProperty(default="*.json", options={"HIDDEN"})

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        ok, message = _apply_settings_file(context, self.filepath)
        if not ok:
            self.report({"ERROR"}, message)
            return {"CANCELLED"}
        self.report({"INFO"}, "Imported %s" % os.path.basename(self.filepath))
        return {"FINISHED"}


def _bake_render(context, mode):
    s = _settings(context)
    if s is None or s.image is None:
        return "No source image loaded"
    directory = os.path.dirname(bpy.path.abspath(s.source_path)) if s.source_path else ""
    if not directory or not os.path.isdir(directory):
        directory = bpy.path.abspath("//") or os.path.expanduser("~/Desktop")
    if not os.path.isdir(directory):
        return "No folder to save the bake into"
    base = os.path.splitext(os.path.basename(s.source_path))[0] or "motion_texture"

    if mode == "SEQUENCE":
        frame_numbers = list(range(s.frame_start, s.frame_end + 1))
        targets = [(frame, os.path.join(directory, "%s_bake_%04d.png" % (base, frame)))
                   for frame in frame_numbers]
    else:
        targets = [(context.scene.frame_current, os.path.join(directory, "%s_bake.png" % base))]

    scene = context.scene
    rd = scene.render
    previous = (rd.filepath, rd.image_settings.file_format,
                scene.frame_current, rd.use_overwrite)
    try:
        rd.image_settings.file_format = "PNG"
        rd.use_overwrite = True
        for frame, target in targets:
            scene.frame_set(frame)
            rd.filepath = target
            bpy.ops.render.opengl(write_still=True, view_context=False)
    except Exception as exc:
        return "Render failed: %s" % exc
    finally:
        rd.filepath = previous[0]
        rd.image_settings.file_format = previous[1]
        rd.use_overwrite = previous[3]
        scene.frame_current = previous[2]
    return ""


class MOTIONTEXTURE_OT_bake_frame(bpy.types.Operator):
    bl_idname = "motiontexture.bake_frame"
    bl_label = "Bake Current Frame"
    bl_description = "Save the current frame's material as a PNG next to the source image"
    bl_options = {"REGISTER"}

    def execute(self, context):
        message = _bake_render(context, "FRAME")
        if message:
            self.report({"ERROR"}, message)
            return {"CANCELLED"}
        s = _settings(context)
        self.report({"INFO"}, "Baked current frame next to source" if s else "Baked")
        return {"FINISHED"}


class MOTIONTEXTURE_OT_bake_sequence(bpy.types.Operator):
    bl_idname = "motiontexture.bake_sequence"
    bl_label = "Bake Sequence"
    bl_description = "Save every frame of the source range as a PNG sequence next to the source"
    bl_options = {"REGISTER"}

    def execute(self, context):
        message = _bake_render(context, "SEQUENCE")
        if message:
            self.report({"ERROR"}, message)
            return {"CANCELLED"}
        self.report({"INFO"}, "Baked frame sequence next to source")
        return {"FINISHED"}


class MOTIONTEXTURE_OT_rename_preset(bpy.types.Operator):
    bl_idname = "motiontexture.rename_preset"
    bl_label = "Rename Motion Preset"
    bl_options = {"REGISTER"}

    preset: bpy.props.StringProperty()
    new_name: bpy.props.StringProperty(name="New Name")

    def invoke(self, context, event):
        self.new_name = os.path.splitext(os.path.basename(self.preset))[0]
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        directory = _preset_directory()
        old_path = self.preset
        filename = _safe_filename(self.new_name) + ".json"
        new_path = os.path.join(directory, filename)
        if old_path == new_path:
            return {"CANCELLED"}
        if os.path.exists(new_path):
            self.report({"ERROR"}, "A preset named %s already exists" % filename)
            return {"CANCELLED"}
        try:
            os.rename(old_path, new_path)
        except OSError as exc:
            self.report({"ERROR"}, "Could not rename: %s" % exc)
            return {"CANCELLED"}
        self.report({"INFO"}, "Renamed to %s" % filename)
        return {"FINISHED"}


class MOTIONTEXTURE_OT_open_path(bpy.types.Operator):
    bl_idname = "motiontexture.open_path"
    bl_label = "Open Source Location"
    bl_description = "Open the folder that contains the current source image"

    path: bpy.props.StringProperty()

    def execute(self, context):
        path = self.path
        s = _settings(context)
        if not path and s is not None and s.source_path:
            path = s.source_path
        path = bpy.path.abspath(path) if path else ""
        directory = path if os.path.isdir(path) else os.path.dirname(path)
        if not directory or not os.path.isdir(directory):
            self.report({"WARNING"}, "No source folder to open")
            return {"CANCELLED"}
        try:
            bpy.ops.wm.path_open(filepath=directory)
        except Exception as exc:
            self.report({"WARNING"}, "Could not open folder: %s" % exc)
            return {"CANCELLED"}
        return {"FINISHED"}


class MOTIONTEXTURE_MT_recent(bpy.types.Menu):
    bl_idname = "MOTIONTEXTURE_MT_recent"
    bl_label = "Recent Sources"

    def draw(self, context):
        files = _recent_source_files()
        if not files:
            self.layout.label(text="No recent sources")
            return
        for path in files:
            self.layout.operator("motiontexture.load_source_path",
                                 text=os.path.basename(path),
                                 icon="IMAGE_DATA").filepath = path


class MOTIONTEXTURE_OT_load_source_path(bpy.types.Operator):
    bl_idname = "motiontexture.load_source_path"
    bl_label = "Load Recent Source"
    bl_description = "Load a recently used image, sequence, or movie"
    bl_options = {"REGISTER", "UNDO"}

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")

    def execute(self, context):
        extension = os.path.splitext(self.filepath)[1].lower().lstrip(".")
        if extension in MOVIE_EXT_SET:
            mode = "MOVIE"
        elif extension in IMAGE_EXT_SET:
            mode = "STILL"
        else:
            self.report({"WARNING"}, "Unsupported file type: .%s" % extension)
            return {"CANCELLED"}
        ok, message = _load_source(context, self.filepath, mode)
        if not ok:
            self.report({"ERROR"}, message)
            return {"CANCELLED"}
        self.report({"INFO"}, "Loaded %s" % os.path.basename(self.filepath))
        return {"FINISHED"}


class MOTIONTEXTURE_MT_presets(bpy.types.Menu):
    bl_idname = "MOTIONTEXTURE_MT_presets"
    bl_label = "Load Motion Preset"

    def draw(self, context):
        files = _preset_files()
        if not files:
            self.layout.label(text="No saved presets")
            return
        for path in files:
            operator = self.layout.operator("motiontexture.load_preset", text=os.path.splitext(os.path.basename(path))[0])
            operator.preset = path


class MOTIONTEXTURE_MT_delete_preset(bpy.types.Menu):
    bl_idname = "MOTIONTEXTURE_MT_delete_preset"
    bl_label = "Delete Motion Preset"

    def draw(self, context):
        files = _preset_files()
        if not files:
            self.layout.label(text="No saved presets")
            return
        for path in files:
            operator = self.layout.operator("motiontexture.delete_preset", text=os.path.splitext(os.path.basename(path))[0])
            operator.preset = path


class MOTIONTEXTURE_MT_rename_preset(bpy.types.Menu):
    bl_idname = "MOTIONTEXTURE_MT_rename_preset"
    bl_label = "Rename Motion Preset"

    def draw(self, context):
        files = _preset_files()
        if not files:
            self.layout.label(text="No saved presets")
            return
        for path in files:
            operator = self.layout.operator("motiontexture.rename_preset",
                                            text=os.path.splitext(os.path.basename(path))[0])
            operator.preset = path


def _ping_pong_handler(scene, depsgraph=None):
    """Steer the image user's frame offset so a PING_PONG source plays
    forward then backward, independent of Blender's native looping."""
    frame = scene.frame_current
    for obj in bpy.data.objects:
        s = getattr(obj, "motion_texture", None)
        if s is None or s.image is None or s.loop_mode != "PING_PONG":
            continue
        if s.source_mode not in {"SEQUENCE", "MOVIE"}:
            continue
        mat = _find_material(obj)
        if mat is None or mat.node_tree is None:
            continue
        node = mat.node_tree.nodes.get("MT_Image")
        if node is None or node.image is None or node.image != s.image:
            continue
        user = node.image_user
        duration = max(1, int(user.frame_duration or 1))
        if duration <= 1:
            continue
        period = max(2, 2 * duration - 2)
        position = (frame - 1 + s.frame_offset) % period
        if position >= duration:
            position = period - position
        user.use_cyclic = True
        user.frame_offset = (position - (frame - 1)) % duration


def _no_mesh(layout):
    layout.label(text="Select a mesh object", icon="INFO")


def _ui_apply(layout, s):
    row = layout.row(align=True)
    row.operator("motiontexture.apply", icon="PLAY")
    row.operator("motiontexture.rebuild", text="", icon="FILE_REFRESH")
    row = layout.row(align=True)
    row.operator("motiontexture.apply_all", icon="DUPLICATE")
    row.operator("motiontexture.revert_still", icon="LOOP_BACK")


def _ui_source(layout, context, s):
    if s is None:
        _no_mesh(layout)
        return
    col = layout.column()
    row = col.row(align=True)
    row.operator("motiontexture.open_still", text="Still", icon="IMAGE_DATA")
    row.operator("motiontexture.open_sequence", text="Sequence", icon="SEQUENCE")
    row.operator("motiontexture.open_movie", text="Movie", icon="FILE_MOVIE")
    row = col.row(align=True)
    row.menu("MOTIONTEXTURE_MT_recent", text="Recent", icon="DISC")
    row.operator("motiontexture.open_path", text="Folder", icon="FILE_FOLDER")
    if s.source_path:
        col.label(text=os.path.basename(s.source_path), icon="FILE")
    row = col.row(align=True)
    row.operator("motiontexture.refresh_source", icon="FILE_REFRESH")
    row.operator("motiontexture.clear_source", icon="X")
    col.prop(s, "source_mode")
    if s.source_mode in {"SEQUENCE", "MOVIE"}:
        row = col.row(align=True)
        row.prop(s, "frame_start")
        row.prop(s, "frame_end")
        col.prop(s, "frame_offset")
        col.prop(s, "loop_mode")
    col.prop(s, "fps")
    col.prop(s, "color_space")
    col.prop(s, "auto_fit", toggle=True)
    if s.image is not None:
        try:
            width, height = s.image.size
            col.label(text="%d x %d px" % (width, height), icon="INFO")
        except Exception:
            pass
    col.label(text="Drop an image or movie into the viewport", icon="IMPORT")


def _ui_playback(layout, context, s):
    if s is None:
        _no_mesh(layout)
        return
    col = layout.column()
    row = col.row(align=True)
    row.operator("motiontexture.play", text="Play / Pause", icon="PLAY")
    previous = row.operator("motiontexture.frame_step", text="", icon="TRIA_LEFT")
    previous.direction = -1
    following = row.operator("motiontexture.frame_step", text="", icon="TRIA_RIGHT")
    following.direction = 1
    col.prop(context.scene, "frame_current", text="Frame")
    row = col.row(align=True)
    row.prop(context.scene, "frame_start")
    row.prop(context.scene, "frame_end")
    col.prop(s, "preview_on_selected", toggle=True)
    col.operator("motiontexture.preview_render", icon="RENDER_STILL")
    if s.image is not None and s.source_path:
        col.separator()
        col.label(text="Bake to PNG", icon="IMAGE_DATA")
        row = col.row(align=True)
        row.operator("motiontexture.bake_frame", text="Frame", icon="RENDER_STILL")
        row.operator("motiontexture.bake_sequence", text="Sequence", icon="RENDER_ANIMATION")


def _ui_animation(layout, context, s):
    if s is None:
        _no_mesh(layout)
        return
    col = layout.column()
    col.prop(s, "enable_animation", toggle=True)
    col.prop(s, "speed")
    col.prop(s, "stop_motion", toggle=True)
    if s.stop_motion:
        col.prop(s, "step_frames")
    col.prop(s, "interpolation")
    col.prop(s, "animate_relief", toggle=True)
    col.separator()
    col.label(text="Motion Presets (one %d-frame cycle, repeats)" % _cycle_frames(s), icon="PRESET")
    grid = col.grid_flow(columns=2, even_columns=True, align=True)
    for key, label, description in MOTION_PRESETS:
        operator = grid.operator("motiontexture.motion_preset", text=label)
        operator.preset = key
        try:
            operator.description = description
        except Exception:
            pass
    if s.last_motion_preset:
        col.label(text="Active motion: %s" % s.last_motion_preset.title(), icon="CHECKMARK")
    col.separator()
    col.label(text="Keyframe Tools", icon="KEY_HLT")
    row = col.row(align=True)
    row.operator("motiontexture.key_all", text="Key at Frame", icon="KEY_HLT")
    row.operator("motiontexture.delete_key", text="Delete Key", icon="KEY_DEHLT")
    col.operator("motiontexture.copy_still", text="Copy Still Values to Frame 1", icon="DUPLICATE")
    col.operator("motiontexture.clear_animation", text="Clear Animation", icon="X")
    col.separator()
    col.label(text="Batch Apply (staggered keys)", icon="DUPLICATE")
    col.prop(s, "spread_frames")
    row = col.row(align=True)
    row.operator("motiontexture.apply_all", text="Apply to All", icon="DUPLICATE")
    if s.enable_animation:
        col.label(text="Animation is active", icon="ANIM")


def _ui_raised(layout, context, s):
    if s is None:
        _no_mesh(layout)
        return
    col = layout.column()
    col.prop(s, "relief_mode")
    col.prop(s, "relief_source")
    col.prop(s, "relief", slider=True)
    col.prop(s, "depth", slider=True)
    row = col.row(align=True)
    row.prop(s, "relief_invert", toggle=True)
    row.prop(s, "detail", slider=True)
    col.prop(s, "detail_scale")
    if s.relief_mode == "DISPLACEMENT":
        col.prop(s, "subdivision_level")
        col.label(text="Displacement is most reliable in Cycles", icon="INFO")
    col.separator()
    col.label(text="Moving Raised Texture", icon="MODIFIER")
    grid = col.grid_flow(columns=2, even_columns=True, align=True)
    for key, label, description in RELIEF_MOTION_ITEMS:
        operator = grid.operator("motiontexture.relief_motion", text=label)
        operator.preset = key
        try:
            operator.description = description
        except Exception:
            pass
    col.prop(s, "relief_speed")
    col.prop(s, "relief_amplitude", slider=True)
    col.prop(s, "relief_phase")
    col.separator()
    col.prop(s, "normal_image", text="Normal")
    col.operator("motiontexture.open_normal", text="Load Normal Map", icon="FILE_IMAGE")
    col.prop(s, "normal_strength", slider=True)


def _ui_surface(layout, context, s):
    if s is None:
        _no_mesh(layout)
        return
    col = layout.column()
    col.prop(s, "roughness", slider=True)
    col.prop(s, "metallic", slider=True)
    row = col.row(align=True)
    row.prop(s, "specular", slider=True)
    row.prop(s, "ior", slider=True)


def _ui_surface_advanced(layout, context, s):
    if s is None:
        _no_mesh(layout)
        return
    col = layout.column()
    col.prop(s, "coat", slider=True)
    col.prop(s, "coat_roughness", slider=True)
    row = col.row(align=True)
    row.prop(s, "sheen", slider=True)
    row.prop(s, "sheen_roughness", slider=True)
    col.prop(s, "anisotropic", slider=True)
    col.prop(s, "subsurface", slider=True)
    col.prop(s, "transmission", slider=True)
    col.prop(s, "alpha", slider=True)


def _ui_color(layout, context, s):
    if s is None:
        _no_mesh(layout)
        return
    col = layout.column()
    row = col.row(align=True)
    row.prop(s, "invert", toggle=True)
    row.prop(s, "grayscale")
    col.prop(s, "amount")
    col.separator()
    col.label(text="Hue Color Ramp", icon="COLOR")
    obj = getattr(context, "active_object", None)
    mat = _find_material(obj) if obj is not None else None
    ramp_node = mat.node_tree.nodes.get("MT_HueRamp") if (mat is not None and mat.node_tree is not None) else None
    if ramp_node is not None:
        col.template_color_ramp(ramp_node, "color_ramp", expand=True)
    col.prop(s, "remap", slider=True)
    col.prop(s, "hue", slider=True)
    col.prop(s, "saturation")
    col.prop(s, "brightness")
    col.prop(s, "contrast")
    col.prop(s, "gamma")
    row = col.row(align=True)
    row.prop(s, "temperature")
    row.prop(s, "tint")
    col.prop(s, "posterize")


def _ui_transform(layout, context, s):
    if s is None:
        _no_mesh(layout)
        return
    col = layout.column()
    col.prop(s, "scale")
    col.prop(s, "scale_z")
    row = col.row(align=True)
    row.prop(s, "tiling_x")
    row.prop(s, "tiling_y")
    col.separator()
    col.label(text="Rotation", icon="ORIENTATION_GLOBAL")
    col.prop(s, "rotation_x")
    col.prop(s, "rotation_y")
    row = col.row(align=True)
    row.prop(s, "rotation", text="Z")
    back = row.operator("motiontexture.rotate", text="", icon="LOOP_BACK")
    back.angle = -90.0
    forward = row.operator("motiontexture.rotate", text="", icon="LOOP_FORWARDS")
    forward.angle = 90.0
    col.separator()
    col.label(text="Offset", icon="TRIA_UP")
    col.prop(s, "offset_x")
    col.prop(s, "offset_y")
    col.prop(s, "offset_z")
    row = col.row(align=True)
    row.prop(s, "flip_x", toggle=True)
    row.prop(s, "flip_y", toggle=True)
    col.separator()
    col.operator("motiontexture.reset_transform", icon="LOOP_BACK")
    col.separator()
    col.label(text="Fit to Object", icon="UV")
    row = col.row(align=True)
    every = row.operator("motiontexture.fit_surface", text="Every Face", icon="FACESEL")
    every.face = "ALL"
    front = row.operator("motiontexture.fit_surface", text="Front", icon="SNAP_FACE")
    front.face = "FRONT"
    col.label(text="Uses this on cubes to stop the image showing sideways", icon="INFO")


def _ui_emission(layout, context, s):
    if s is None:
        _no_mesh(layout)
        return
    col = layout.column()
    col.prop(s, "emission", slider=True)
    col.prop(s, "glow_mask", toggle=True)
    col.prop(s, "glow_color", text="")


def _ui_presets(layout, context, s):
    if s is None:
        _no_mesh(layout)
        return
    col = layout.column()
    col.label(text="Surface Presets", icon="MATERIAL")
    grid = col.grid_flow(columns=3, even_columns=True, align=True)
    for key in SURFACE_PRESETS:
        operator = grid.operator("motiontexture.surface_preset", text=SURFACE_PRESETS[key]["label"])
        operator.preset = key
    col.separator()
    col.label(text="Saved Motion Presets", icon="PRESET")
    col.operator("motiontexture.save_preset", text="Save Motion Preset", icon="ADD")
    col.menu("MOTIONTEXTURE_MT_presets", text="Load Motion Preset", icon="PRESET")
    col.menu("MOTIONTEXTURE_MT_rename_preset", text="Rename Motion Preset", icon="GREASEPENCIL")
    row = col.row(align=True)
    row.operator("motiontexture.import_preset", text="Import", icon="IMPORT")
    row.operator("motiontexture.export_preset", text="Export", icon="EXPORT")
    col.menu("MOTIONTEXTURE_MT_delete_preset", text="Delete Motion Preset", icon="TRASH")
    col.separator()
    col.menu("MOTIONTEXTURE_MT_reset", text="Reset", icon="LOOP_BACK")


class MOTIONTEXTURE_PT_main(bpy.types.Panel):
    bl_label = "Motion Texture"
    bl_idname = "MOTIONTEXTURE_PT_main"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Motion Texture"

    def draw(self, context):
        layout = self.layout
        obj = context.active_object
        s = _settings(context)
        if s is None:
            layout.label(text="Select a mesh object", icon="INFO")
            return
        if s.image is None:
            box = layout.box()
            box.label(text="1. Open a source image", icon="IMAGE_DATA")
            box.operator("motiontexture.open_still", text="Choose Image", icon="FILEBROWSER")
        elif not s.enable_animation:
            box = layout.box()
            box.label(text="2. Add motion with a preset", icon="ANIM")
            box.label(text="Animate Texture section below", icon="DOWNARROW_HLT")
        else:
            layout.label(text="Animated: %s" % (s.last_motion_preset.title() or "custom"), icon="ANIM")
        layout.label(text="Object: %s" % obj.name, icon="OBJECT_DATAMODE")
        if s.image is not None:
            layout.label(text=s.image.name, icon="IMAGE_DATA")
        if obj.type == "MESH" and len(obj.data.polygons) > 1:
            row = layout.row(align=True)
            every = row.operator("motiontexture.fit_surface", text="Fit to Object", icon="UV")
            every.face = "ALL"
        _ui_apply(layout, s)


def _make_section(name, label, icon, order, draw_fn, default_closed=True):
    def draw(self, context):
        draw_fn(self.layout, context, _settings(context))
    options = {"DEFAULT_CLOSED"} if default_closed else set()
    return type("MOTIONTEXTURE_PT_%s" % name, (bpy.types.Panel,), {
        "bl_label": label,
        "bl_idname": "MOTIONTEXTURE_PT_%s" % name,
        "bl_parent_id": "MOTIONTEXTURE_PT_main",
        "bl_space_type": "VIEW_3D",
        "bl_region_type": "UI",
        "bl_options": options,
        "bl_order": order,
        "draw": draw,
    })


MOTIONTEXTURE_PT_source = _make_section("source", "Source", "IMAGE_DATA", 0, _ui_source)
MOTIONTEXTURE_PT_playback = _make_section("playback", "Playback", "PLAY", 1, _ui_playback)
MOTIONTEXTURE_PT_animation = _make_section("animation", "Animate Texture", "ANIM", 2, _ui_animation)
MOTIONTEXTURE_PT_raised = _make_section("raised", "Raised Surface", "MODIFIER", 3, _ui_raised)
MOTIONTEXTURE_PT_colour = _make_section("colour", "Color", "COLOR", 4, _ui_color)
MOTIONTEXTURE_PT_transform = _make_section("transform", "Transform", "UV", 5, _ui_transform, default_closed=False)
MOTIONTEXTURE_PT_surface = _make_section("surface", "Surface", "MATERIAL", 6, _ui_surface)
MOTIONTEXTURE_PT_surface_advanced = _make_section("surface_advanced", "Surface Advanced", "SHADERFX", 7, _ui_surface_advanced)
MOTIONTEXTURE_PT_emission = _make_section("emission", "Emission", "LIGHT", 8, _ui_emission)
MOTIONTEXTURE_PT_presets = _make_section("presets", "Presets", "PRESET", 9, _ui_presets)


_classes = (
    MotionTextureSettings,
    MOTIONTEXTURE_OT_apply,
    MOTIONTEXTURE_OT_apply_all,
    MOTIONTEXTURE_OT_rebuild,
    MOTIONTEXTURE_OT_revert_still,
    MOTIONTEXTURE_OT_play,
    MOTIONTEXTURE_OT_frame_step,
    MOTIONTEXTURE_OT_preview_render,
    MOTIONTEXTURE_OT_key_all,
    MOTIONTEXTURE_OT_copy_still,
    MOTIONTEXTURE_OT_delete_key,
    MOTIONTEXTURE_OT_clear_animation,
    MOTIONTEXTURE_OT_motion_preset,
    MOTIONTEXTURE_OT_relief_motion,
    MOTIONTEXTURE_OT_rotate,
    MOTIONTEXTURE_OT_reset_transform,
    MOTIONTEXTURE_OT_fit_surface,
    MOTIONTEXTURE_OT_surface_preset,
    MOTIONTEXTURE_OT_reset_section,
    MOTIONTEXTURE_MT_reset,
    MOTIONTEXTURE_OT_open_still,
    MOTIONTEXTURE_OT_open_sequence,
    MOTIONTEXTURE_OT_open_movie,
    MOTIONTEXTURE_OT_refresh_source,
    MOTIONTEXTURE_OT_clear_source,
    MOTIONTEXTURE_OT_open_normal,
    MOTIONTEXTURE_OT_drop_source,
    MOTIONTEXTURE_FH_source_drop,
    MOTIONTEXTURE_OT_save_preset,
    MOTIONTEXTURE_OT_load_preset,
    MOTIONTEXTURE_OT_delete_preset,
    MOTIONTEXTURE_OT_export_preset,
    MOTIONTEXTURE_OT_import_preset,
    MOTIONTEXTURE_MT_presets,
    MOTIONTEXTURE_MT_delete_preset,
    MOTIONTEXTURE_MT_rename_preset,
    MOTIONTEXTURE_OT_rename_preset,
    MOTIONTEXTURE_OT_open_path,
    MOTIONTEXTURE_OT_load_source_path,
    MOTIONTEXTURE_MT_recent,
    MOTIONTEXTURE_OT_bake_frame,
    MOTIONTEXTURE_OT_bake_sequence,
    MOTIONTEXTURE_PT_main,
    MOTIONTEXTURE_PT_source,
    MOTIONTEXTURE_PT_playback,
    MOTIONTEXTURE_PT_animation,
    MOTIONTEXTURE_PT_raised,
    MOTIONTEXTURE_PT_colour,
    MOTIONTEXTURE_PT_transform,
    MOTIONTEXTURE_PT_surface,
    MOTIONTEXTURE_PT_surface_advanced,
    MOTIONTEXTURE_PT_emission,
    MOTIONTEXTURE_PT_presets,
)


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)
    bpy.types.Object.motion_texture = bpy.props.PointerProperty(type=MotionTextureSettings)
    bpy.app.handlers.frame_change_pre.append(_ping_pong_handler)


def unregister():
    handler = getattr(bpy.app.handlers, "frame_change_pre", None)
    if handler is not None and _ping_pong_handler in handler:
        handler.remove(_ping_pong_handler)
    if hasattr(bpy.types.Object, "motion_texture"):
        del bpy.types.Object.motion_texture
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
