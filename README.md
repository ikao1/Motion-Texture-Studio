# Motion Texture Studio — midterm proposal (resubmit)

An upgrade to my Week 5 **Texture GUI** Blender add-on (`texture_gui.py`, v1.8.0).

## The tool in one sentence

Motion Texture Studio is a Blender add-on that turns the existing Texture GUI into an animation tool: it maps stills, image sequences, and movies onto the selected object, animates every texture and relief control over time, and previews the moving surface live in the viewport.

**App:** Blender 5.2 LTS. It lives in the 3D Viewport sidebar (`N`) under the tab **Motion Texture**.

## The chore it ends

Today, putting moving imagery on a surface means building the shader by hand: wiring an Image Texture node, switching it to Image Sequence or Movie, setting frame range and cyclic playback, keyframing mapping offset/rotation, adding a bump or displacement node, keyframing the relief, checking playback, and redoing all of it when the art changes. That is roughly **45–90 minutes per asset**, repeated every revision. My current Texture GUI only handles still images and one surface at a time. This tool collapses the job to **open source → choose motion → preview → apply**, in minutes.

## The UI

Sidebar tab **Motion Texture** (`N`), collapsible sections:

- **Source**
  - `Still`, `Sequence`, `Movie` buttons, `Recent` menu, `Folder` (reveal source)
  - source path field, `Refresh Source`, `Clear Source`
  - Frame Start, Frame End, FPS fields (frame range auto-detected from the filenames)
  - Frame Offset field, Loop Mode menu (Once, Loop, Ping-Pong), Color Space menu (sRGB, Non-Color, Linear)
  - frame count / resolution readout, `Auto-Fit UVs` toggle (on by default)
  - EXIF orientation is applied automatically for still photos; MP4/MOV display-matrix rotation is applied automatically for videos
  - With `Auto-Fit UVs` on, opening a source on a cube auto-rewrites its UVs so the image fills every face upright
- **Playback**
  - `Play/Pause`, `Previous Frame`, `Next Frame`, Current Frame field, timeline scrubber
  - Scene Start / End fields, `Preview on Selected` toggle, `Preview Render`
  - `Bake Frame` and `Bake Sequence` — save the animated surface as PNGs next to the source
- **Animate Texture**
  - `Enable Animation` toggle
  - **Speed** menu (0.25x–4x) — presets key one cycle whose length Speed chooses (24 frames at 1x), and a CYCLES modifier repeats it for a shot of any length
  - **On Twos** toggle + Hold Frames — stepped, stop-motion playback of every animated value
  - Motion preset buttons (Scroll X, Scroll Y, Drift, Pulse, Breathe, Ripple, Flicker), with the active motion shown underneath
  - `Key at Frame`, `Delete Key`, `Clear Animation`, Interpolation menu, `Copy Still Values to Frame 1`
  - **Batch Offset** (frames) + `Apply to All` — every selected object gets the same animation, staggered so a row ripples
- **Raised Surface**
  - Relief Mode menu (Bump, Displacement)
  - Relief Source menu (Image Luminance, Image Sequence, Noise, Wave)
  - `Animate Relief` toggle, Relief Amount, Depth, Midlevel, Detail, Detail Scale, Invert Relief
  - Motion Direction menu (X, Y, Radial), Speed, Amplitude, Phase Offset
  - `True Displacement` toggle, Subdivision Level slider
  - Normal Map field + `Load Normal Map…`, Normal Strength
  - Raised presets: Drift, Pulse, Ripple, Crawl, Breathe
- **Transform**
  - Scale, **Scale Z**, Tiling X/Y
  - **Rotation X/Y/Z** (X/Y tilt, Z with -90°/+90° buttons)
  - **Offset X/Y/Z**, Flip X/Y
  - **Reset Transform** — restore scale, tiling, rotation (X/Y/Z), offset (X/Y/Z), scale Z, and flips to defaults
  - **Clean Up Materials** — assign the Motion Texture material to all faces and remove unused material slots (fixes stray default materials)
  - `Fit to Object` — rewrite the object's UVs so the image fills every face upright (`Every Face`) or a single front face (`Front`). Use this on cubes and multi-face objects, where a single image otherwise shows sideways or split across the default UV islands
- **Surface** (kept from v1.8)
  - Roughness, Metallic, Specular, IOR, Coat, Coat Roughness, Sheen, Sheen Roughness, Anisotropic, Subsurface, Transmission, Alpha
  - Glow, Glow Tint, `Glow From Image` toggle
  - Surface Preset menu (Matte, Glossy, Plastic, Ceramic, Metal, Brushed, Velvet, Glass, Glowing)
- **Apply / Settings**
  - `Apply to Selected`, `Apply to All Selected`, `Revert to Still`, `Rebuild`
  - `Save Motion Preset…`, `Load…`, `Rename…`, `Delete…`, `Import…`, `Export…`
  - Reset menu (Color, Transform, Surface, Animation, Everything)
  - Main panel guides the first steps: open a source → pick a motion preset

## Why it's advanced

- Real **animation system**, not a single script: keyframes and drivers on node inputs, synced to the scene timeline, with loop modes, frame offsets, and interpolation.
- Handles **moving images** as a source: image sequences and movies with frame ranges, offsets, cyclic playback, and per-object timing.
- **Moving raised textures**: animated bump and optional true displacement, driven by image luminance, sequences, or procedural motion. Bump is the fast fallback; displacement is the heavy option.
- **Non-destructive preview**: edits run live in Material Preview; nothing is baked until you press Bake. `Preview Render` checks the current frame or range.
- Works on **whatever is selected**, with batch apply and per-object settings; remembers the last source, preset, and motion setup.
- **Presets saved to disk** as portable JSON (motion + surface), with optional thumbnail; can be imported/exported and shared.
- **Blender's native undo/redo** covers every operator, so no custom Undo buttons are needed; automatic stale-node-graph rebuild is carried over from v1.8.
- **Handles mistakes without crashing**: missing/corrupt frames, unsupported codec, start frame after end frame, missing normal map, and unsupported true displacement all produce a clear warning and a safe fallback.
- **Bakes to a portable image sequence** so the animated texture can leave Blender and be handed off.

## The three weeks

| Milestone | Deliverable |
| --- | --- |
| **By Oct 13** | Existing Texture GUI v1.8 is the baseline: still-image path, surface presets, drag-and-drop, node rebuild. New: source manager for image sequences/movies; scene-synced playback; basic animated offset/rotation; live preview. |
| **By Oct 20** | Keyframes and interpolation for all texture/surface controls; moving raised surface (bump + optional displacement) with motion presets; per-object settings; save/load motion presets. |
| **By Oct 26** | Bake current frame and motion-to-sequence; batch apply; undo/redo; loop/offset edge cases; missing-file recovery; performance/cache pass; 2–3 demo assets; README + 60-second recording. |

## The smallest version that still counts

Load one image sequence or movie onto the selected object, animate Offset X/Y (scroll) and Relief/Depth (pulse) on the timeline, and preview the playback. No presets, no batch, no bake — still a real upgrade over the still-only v1.8 and enough to demo.

## The riskiest part

Frame-accurate, non-blocking playback and caching of movie/image-sequence textures while the material graph rebuilds, plus **true displacement** support/performance in EEVEE. Bake is the second risk.

- **Fallback:** prefer image sequences over compressed movies, ship animated **bump** as the primary “raised” look, bake only the current frame, and use proxy/reduced-resolution playback. If displacement is unreliable, keep it as an optional Cycles path and label it clearly.

---

# Install and run

## What you need

- **Blender 5.2 LTS** (tested on 5.2.1 LTS). Blender 4.2+ should also work but has not been tested.
- The file `motion_texture_studio.py` from this repo (no other install, no dependencies).

## Steps

1. Clone this repo: `git clone https://github.com/ikao1/Motion-Texture-Studio.git` or download the ZIP.
2. Open Blender. Go to **Edit → Preferences → Add-ons**.
3. Click the **⌄** (dropdown) at the top right → **Install from Disk…**.
4. Select **`motion_texture_studio.py`** from the cloned repo.
5. Tick the checkbox next to **Motion Texture Studio** to enable it.
6. In the 3D Viewport press **N** to open the sidebar and click the **Motion Texture** tab.
7. Select a mesh object (the default cube is fine). Click **Open Still…** and choose **`assets/test_texture.png`** or **`assets/demo_texture.png`**.
8. Click **Apply to Selected**. The object now has a material called `MotionTexture_<objectname>`.
9. Open the **Animate Texture** section and click a motion preset such as **Scroll X**. Set the scene end frame to ~48 and press **Play/Pause** — the texture scrolls in the viewport.
10. For a sequence: **Open Image Sequence…** and pick the **first** file of a numbered sequence (`frame_0001.png`). The frame range is detected from the filenames.
11. For a movie: **Open Movie…** and pick a video file.

If a movie or sequence codec will not load, use an **image sequence** instead — it is the more reliable path.

## Demo Video

**[Add your 1–3 minute screen recording here](YOUR_RECORDING_LINK_HERE)** — Upload an unlisted YouTube video or shareable link showing: load a source → apply motion preset → play → Fit to Object (if needed) → bake a frame/sequence.

# What works right now

- Installs and registers as a Blender add-on; sidebar tab **Motion Texture** opens.
- Per-object material named `MotionTexture_<object>` with a full non-destructive node graph.
- **Sources:** still image, numbered image sequence (auto frame range), movie, drag-and-drop, recent-sources menu; EXIF orientation corrected for photos and MP4/MOV display-matrix rotation corrected for videos (portrait phone clips show upright).
- **Fit to Object:** one-click UV rewrite so a single image/video fills a cube's faces upright instead of showing sideways or split across the default UV islands.
- **Playback:** play/pause, frame step, scrub, preview render, scene-synced timeline.
- **Loop modes:** Once, Loop (cyclic), Ping-Pong (mirrored playback for sequences and movies).
- **Speed:** one menu sets the cycle length of every preset — 96/48/24/16/12/6 frames; the CYCLES modifier repeats the cycle for a shot of any length, so the scene range never matters. Re-keying a preset after a Speed change keeps the modifiers.
- **On Twos:** stepped playback (hold 1–6 frames) on every animated value, for stop-motion feel.
- **Motion presets:** Scroll X/Y, Drift, Pulse, Breathe, Ripple, Flicker (noise-driven, never repeats). Relief presets: Drift, Pulse, Ripple, Crawl.
- **Animation:** keyframe offset/rotation/scale/hue/brightness/contrast/relief/depth/glow, delete key, clear animation, linear/bezier/constant interpolation, copy still to frame 1, key at current frame.
- **Raised surface:** animated bump; relief source from image / noise / wave; amplitude and phase.
- **True displacement:** optional, via a displacement output + subdivision modifier, with clear warning that it is heavy and best on Cycles.
- **Color / transform / surface / emission** controls with per-material Hue Color Ramp and Remap blend.
- **Bake:** current frame and the whole source range to PNG files next to the source image.
- **Batch apply:** copies settings *and* animation curves to every selected object, staggered by Batch Offset frames.
- **Save / load / rename / import / export** motion presets as JSON in Blender’s user presets folder.
- **Apply to Selected**, **Rebuild**, **Revert to Still**, guided main panel.

# What does not work yet

- **Per-preset thumbnails** are not implemented (presets show names only).
- **Movie auto-duration** depends on the codec loading correctly; image sequences are more reliable.
- **True displacement** is unreliable in EEVEE and should be used on Cycles. Bump is the safe path.
- The add-on was tested headless; interactive UI polish (button layout, long menus) is still rough. 

# What I'd build next

- **Per-preset thumbnails** for saved motion presets
- **More animation curves/easing** options (custom easing graphs)
- **Improved UV projection tools** (Project from View, Pack Islands) for modeling workflows
- **Better movie codec handling/proxies** for more reliable playback
- **More demo assets** and a polished 1-3 minute walkthrough video

# Peer run

**Classmate:** Brent Shultz (A6: Wire Body Profile - InBody Data Build)

1. **What they did:** I cloned Brent's repo, opened `InBody Data Build.mb` in Maya 2027, launched the Wire Body Profile UI manually (`import body_profile_ui; body_profile_ui.show()`), and entered dated measurements to build a profile.
2. **What happened:** Everything worked as described — saving entries, loading history, deleting entries, rebuilding the wire body, and using the slider to reshape the figure all functioned correctly. The window had to be launched manually and required Maya 2027 specifically.
3. **What confused or broke:** The UI didn't auto-launch on scene open, requiring manual import/run. **Fix applied:** I ran the module directly from the Maya Script Editor to launch it, and verified all functions after launch. The tool was otherwise solid once opened.

# Running a classmate's tool

> To be completed after testing a classmate’s add-on with their README. Three sentences about their tool.

1. _(what I installed and tried)_
2. _(what worked)_
3. _(what I got stuck on)_
