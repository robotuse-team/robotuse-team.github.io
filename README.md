# RobotUse project page

Public page: https://robotuse-team.github.io/
Code: https://github.com/robotuse-team/RobotUse

One HTML file, one stylesheet and one JavaScript file. No framework, build step,
package installation or analytics. GitHub Pages publishes the root on `main`.

```bash
python3 -m http.server 8323 --bind 127.0.0.1
```

## Native visual handoffs

The opening replay follows **language → point → gripper → inspection → execution**.
Main agent, Subagent and Backend remain visible beside the recorded execution.
Each replay starts with a sent instruction. The role boxes keep that instruction
visible through the local visual choice, the subagent's report and backend output.
Short captions condense recorded requests and reports; a collapsed disclosure
shows their original wording, with backend-generated prompts attributed separately.
`data/handoff.json` supplies the browser and downloadable videos with the same
selected decisions, native tool images, source references and presentation timing.

Three executions are included:

- RoboLab bowl stacking, September 23: original simulation video, native selection
  cross/mask, three Contact-GraspNet mesh previews, selected 44 mm opening, fresh
  pregrasp inspection and two recorded placement translations. The native task
  verifier reports success. The release request ends with the episode.
- Physical Panda pick/place, September 26: geometric mean proposals, selected
  `g_009`, pregrasp check and prepared tray placement.
- Physical Panda cube stacking, September 26: geometric median proposals,
  selected `g_005`, pregrasp check and prepared placement on the green cube.

Real replays use timestamped camera observations, with reading intervals. They
are sampled stills. Completion is agent-reported; final images show the requested
object relations. An independent physical task-success verifier is unavailable.
One physical pick/place segment misses its arrival tolerance before a later
segment reaches the target; command completion is distinct from task success.

Native cross/mask overlays and cyan gripper meshes are preserved. Enlarged crops
link the full original tool images. Pose-editor crops show the actual SIDE / TOP /
CLOSING PLANE panels; lower purple rotation examples do not represent applied
edits. Both real pregrasp checks continue without a nudge. Captions summarize
recorded tool arguments and assessments. Earlier retries are omitted from the
compact replays. Model and planning waits are compressed.

Learning from execution is one collapsed comparison of two separate complete
bowl-stacking attempts. Aggregate results and conditions are in `data/results.json`.
File hashes, native source identifiers and exact crop boxes are in `data/media.json`.
Private provider logs, credentials, depth/calibration and server paths are excluded.

## Media authoring

Optional authoring requires Python 3.10+, Pillow, ffmpeg and ffprobe. Rebuild from
curated public inputs:

```bash
python3 scripts/render_handoff.py
# Or one execution:
python3 scripts/render_handoff.py --case panda-stack-cubes
```

The script produces a browser execution track and a standalone video combining
native previews, execution and the three agent/backend roles. Simulator motion
stays in its original order with reading pauses; physical camera samples remain
in capture order. Media provenance is updated for generated files. MP4s use
H.264 with front-loaded metadata. Lower-section videos load when played.

## Design reference

VISTA's public page and source informed the masthead, large title, video-first
opening, numbered sections and section rail:
https://github.com/vista-research/vista-research.github.io

This implementation is written for RobotUse. No VISTA code, fonts, images,
recordings or research text are bundled.
