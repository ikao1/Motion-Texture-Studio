# Motion Texture Studio — working notes

_Last updated: 2026-11-03_

SVA "Programming for Animators" midterm. Deliverable = the Blender 5.2 add-on in this repo.

- **Repo:** https://github.com/ikao1/Motion-Texture-Studio
- **Add-on:** `motion_texture_studio.py` (v2.1.0)
- **Verified:** Blender 5.2.1 LTS, fresh clone; 22 headless checks pass
  (`tools/verify_fresh_clone.py`), and the GUI bake path was checked by hand.
- **Demo:** `assets/motion_texture_studio_demo.mp4` (77 s), poster
  `assets/demo_poster.png`.
- **Known limits:** multi-material faces are not reassigned by Apply; Bake is a
  camera-view OpenGL render; true displacement is Cycles-only; the sidebar
  layout is long and not tuned for small windows.
- **Build history:** Week 5 prototype in `ikao1/pfa_week_5`; midterm
  checkpoint/peer run in `ikao1/Midterm-checkpoint-peer-run`.

## Rule — how to work with ikao1

- Do **not** ask ikao1 to paste their own work. Look it up first:
  `gh repo list ikao1` and `~/Desktop`.
- Use `tools/pfa-repos.sh` to see every class repo and local folder at a glance.

## Tooling

- `tools/pfa-repos.sh` — lists the PFA GitHub repos and the local repo folders
  under `~/Desktop` with each one's remote and uncommitted-file count.
  Run: `bash tools/pfa-repos.sh`
