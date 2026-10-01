# RobotUse project page

Public project page: https://robotuse-team.github.io/

Code: https://github.com/robotuse-team/RobotUse

Authors and contribution markers follow the code repository README. The arXiv button is disabled until a paper URL is available.

## Development

Static HTML, CSS, JavaScript, JSON, images, and MP4 video. No build step.
Run `python -m http.server 8323 --bind 127.0.0.1` and open http://localhost:8323/.

GitHub Pages publishes the root of the `main` branch.

## Galleries

- Baseline comparison: 16 matched seed-0 tasks where RobotUse succeeds and at least one baseline fails.
- Grasp ablation: three matched seed-1 tasks where RobotUse succeeds with and without grasp tools and CaP-X changes from success to failure. Only the corrected tools-only CaP-X condition is eligible.
- Continual Harnessing: five tasks across rounds 0 through 3.
- Galleries are selected qualitative examples. Aggregate figures report all 40 tasks.

## ORS simulation replay media

Four selected ORS seed-0 failures use logged-action simulation replays: PickGlassesTask, FruitsOnPlate3Task, Stack3RubiksCubeTask, and PickOrangeObjectTask. They replay saved robot commands without new LLM calls. All four replay verifiers reported failure, but trajectories differ from the original observations; these are not original recordings. The manifest preserves replay provenance and original outcomes; replay labels are omitted from the page at the author's request.
