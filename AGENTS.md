# Midterm — working notes

_Last updated: 2026-10-13_

SVA "Programming for Animators" midterm. Deliverable = a Blender 5.2 add-on.

## ⚠️ RESOLVE FIRST: two conflicting proposals

- **A. "2D-to-3D Parallax Tool"** — pointed to by ikao1 as *the* proposal.
  Lives in GitHub **`ikao1/Midterm-Proposal`** (README.md; pushed 2026-10-13 03:58).
  Flat drawing → artist cuts layers on the canvas → each cut becomes a real
  textured mesh plane at an adjustable Z-depth → camera motion parallaxes them.
- **B. "Lookdev Studio"** — older local draft at
  `~/Desktop/pfa_midterm/README.md` (2026-10-12 20:41). Upgrades the week-5
  Texture GUI into a layer stack + Look Library.

A is newer and is the one ikao1 calls "the proposal", so treat **A (Parallax)**
as authoritative — but **confirm before writing code**.

## Still missing

- **Instructor feedback: never received.** Asked once; ikao1 ended the session.
  Get this at the very start of next session — it may change the direction.

## Decisions made this session

- The engineering spine is a **layer data model** (cut masks + per-layer params)
  that the UI, live preview, rebuild, and export all read/write. Design it first.
- Two unresolved design questions for proposal A:
  1. Mask storage model — "full background plate + N cutouts on top" vs
     "N disjoint tiles that reconstruct the image". These behave differently and
     the rest of the tool depends on the choice.
  2. Inpainting (the stated risk) → plan a **no-ML fallback** (edge-aware fill or
     a duplicated background plate). Do not scope a diffusion model.
- Target Blender **5.2 LTS**. Reuse the node-builder code from
  `pfa_week_5/texture_gui.py` (v1.5.0) and the Week-5 self-check render pattern.

## Next step

1. Get instructor feedback + confirm the authoritative proposal (A vs B).
2. Decide the mask storage model.
3. Draft the layer data model + file layout. **No code yet.**

## Rule — how to work with ikao1

- Do **not** ask ikao1 to paste their own work. Look it up first:
  `gh repo list ikao1` and `~/Desktop`.
- Use `tools/pfa-repos.sh` to see every class repo and local folder at a glance.

## Tooling

- `tools/pfa-repos.sh` — lists the PFA GitHub repos and the local repo folders
  under `~/Desktop` with each one's remote and uncommitted-file count.
  Run: `bash tools/pfa-repos.sh`
