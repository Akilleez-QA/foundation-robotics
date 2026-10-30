# Foundation Robotics / Mechanical Engineering v0.1

The physics that motion must obey, for characters and machines alike. It owns what "this walk is right for his size",
"he would not fall", "the arm can reach that", "those rotors mesh" and "the squash keeps his volume" mean, as checks
that can fail. Animation tools stop guessing: they measure their motion and ask this Foundation. POODO governs how it
is used; it is a sibling of the other Foundations, never a subclass.

Every tool is a read-only observation and a pure function of the numbers the caller supplies: no file paths, no
rigs, no renders, no network. **Producers measure, Foundations judge.** A producer samples an animation (three.js
`TonPose`, a Blender action, a baked GLB) into numbers; this Foundation turns them into verdicts with Evidence. A
verdict is **not acceptance of an animation**: that stays a person's call on moving playblasts, so every receipt
says `acceptance_decision: false` (I11, I12).

## The first principles

Each tool rests on a relation real bodies and machines cannot break. Specifics (proportions, thresholds, the
calibration cases) live in data: `foundation_robotics/data/defaults.json` and `data/calibration.json`.

| Area | First principle | Source | Tool |
|---|---|---|---|
| Scale | Under gravity, similar bodies move alike at equal **Froude number** v²/(gL). Times scale with √(L/g), speeds with √(gL), accelerations not at all. A 6 m giant swings his legs √3.4 = 1.85× slower than a 1.75 m man and walks 1.85× faster. | Alexander and Jayes 1983 | `scale_timing` |
| Scale | Strength grows with area, weight with volume, so strength-to-weight falls as 1/L: a big body cannot snap a limb as sharply relative to g, which is why it reads as heavy. Mass does not change the kinematics. | Haldane 1926 (square-cube law) | `scale_timing` |
| Timing | A limb or appendage swings like a pendulum, T = 2π√(I/(mgd)); for a uniform rod, 2π√(2L/3g). Follow-through and overlap lag by about that period; a fall from h takes √(2h/g). | any mechanics text | `scale_timing` |
| Gait | Stride follows speed: one full cycle λ ≈ 2.3 L Fr^0.3. Long strides at a slow cadence are the slow-motion look. | Alexander 1976 | `gait_check` |
| Gait | Walking gives way to running near Fr 0.5. A walk cannot exceed Fr 1, because the body would leave the ground. | Alexander 1989; Kram et al. 1997 | `gait_check` |
| Gait | Walking has double support, so each foot is down at least half the cycle (duty factor ≥ 0.5). A run has less than half. Stance is about 60 % at a free walk. | Alexander 1989; Perry and Burnfield 2010 | `gait_check` |
| Gait | A planted foot does not move (no footskate). Root speed = stride / cycle, or the foot must slide. | Kovar et al. 2002; kinematics | `gait_check` |
| Balance | Static: the centre of mass projects inside the support polygon. | statics | `balance_check` |
| Balance | Dynamic: the zero-moment point x − z ẍ/(z̈+g) stays inside the support polygon, or the body tips about its edge. | Vukobratović and Borovac 2004; Kajita et al. 2003 | `balance_check` |
| Balance | A body stops without another step only if its capture point x + ẋ/√(g/z) is inside the polygon. Weight shift before a step is the body moving the ZMP. | Pratt et al. 2006; Hof et al. 2005 | `balance_check` |
| Dynamics | With no support, the centre of mass falls at g whatever the limbs do (the floaty jump). | Newton | `balance_check` |
| Kinematics | Forward kinematics is a product of exponentials of joint screws. The positional Jacobian maps joint speeds to tip speed. | Lynch and Park 2017, ch. 4–5 | `ik_check` |
| Kinematics | At a singularity (a straight knee or elbow, aligned axes) the Jacobian loses rank. IK then needs unbounded joint speed and pops, so keep σ_min/σ_max away from 0. Reach is bounded by the extended chain, and joints have limits. | Yoshikawa 1985; Lynch and Park 2017 | `ik_check` |
| Mechanisms | Meshing gears have equal pitch-line speed: ω₂ = ω₁N₁/N₂, reversed by an external mesh. Screw rotors are gears whose teeth are lobes (a 4-lobe male drives a 6-lobe female at 4/6 speed, the other way). Mesh phase is locked modulo one tooth pitch. | Norton 2012, ch. 9; Stošić et al. 2005 | `mechanism_check` |
| Mechanisms | A slider-crank puts its slider at r cos θ + √(l² − (r sin θ − e)²), which is not a sine. A four-bar's Grashof condition s + l ≤ p + q decides which link can turn fully, and loop closure fixes the output angle. | Norton 2012, ch. 2 and 4 | `mechanism_check` |
| Sampling | A rotor sampled at the frame rate reads true only below half a blade pitch per frame. Faster, it aliases (wagon wheel) unless motion blur smears each blade over a pitch. | Shannon 1949 | `mechanism_check` |
| Animation | Squash and stretch keeps the volume: sx·sy·sz = 1, so squash s along one axis and 1/√s along the other two. | Thomas and Johnston 1981; Lasseter 1987 | `squash_check` |

The other animation principles have a physical reading, and for now they are tracked as gaps (listed at the end).
Anticipation is a counter-movement that loads the muscles and moves the ZMP before the move. Follow-through and
overlap are damped secondary dynamics that lag their driver by their own period. Arcs come from joints that rotate,
which sweep circles. Timing and spacing come from mass and size through the scale laws above.

## Numeric profile

Bounded integers only, in **milli-SI** units, `round(value * 1000)` of the SI unit, except lengths in millimetres:

| Quantity | On the wire | Example |
|---|---|---|
| length, position | mm | hip height 0.93 m → `930` |
| time | ms | 1.2 s cycle → `1200` |
| speed / acceleration | mm/s, mm/s² | 1.35 m/s → `1350`; g → `9807` |
| angle / angular speed | mrad, mrad/s | 30° → `524`; 3550 rpm → `371755` |
| frame rate | milli-fps | 24 fps → `24000`; 23.976 → `23976` |
| ratio, dimensionless | per-mille | Froude 0.25 → `250`; scale 1.18 → `1180` |

Positions are world space, after root motion. `up_axis` is `"y"` (three.js, glTF; the default) or `"z"` (Blender).
The host reuses the shared integer decoder (`adapters/wire.py`), so no float crosses the bridge.

## Tools

| Tool | Takes | Returns |
|---|---|---|
| `scale_timing` | height or leg length, optional gravity, Froude numbers, appendage lengths, drop heights | time, speed and strength factors against a 1.75 m adult; speed, stride, step, cycle and cadence at each Froude number; walk-run and walking-limit speeds; leg and appendage swing periods; fall times |
| `gait_check` | leg length or height, root speed, optional stride and cycle, feet with stance time, mean slide or a per-frame track (position + contact flag), frame rate, gait (`walk`, `run`, `stand`) | Froude number; stride against Alexander's prediction; kinematic mismatch; per-foot strikes, cycle, stance, duty, stride and slide (mean, p95, max); step-time asymmetry; the walk this body would make at this speed and at its preferred speed |
| `balance_check` | per frame: COM and the contact points; mode `static`, `dynamic` or `stop` | per frame: COM, ZMP and capture-point margins (signed; positive inside), free-fall error in flight; worst values and first failing frame. Derivatives use a Savitzky–Golay quadratic over 200 ms, because positions arrive as whole millimetres |
| `ik_check` | a joint chain (revolute or prismatic: axis, offset, limits), a tip offset, and poses (joint values, optional target) | per pose: forward-kinematics tip, limit margin, joints outside limits, Jacobian singular values and their ratio, reach margin and tip error |
| `mechanism_check` | `kind` and its geometry: `gear_train` (stages, shafts, measured speeds), `gear_mesh` (per-frame angles), `slider_crank`, `four_bar`, `rotor_strobe` (blades, speed, fps, shutter) | expected speeds and senses, phase drift in tooth pitches, expected slider or output angles and their errors, Grashof class, what a rotor reads as on screen (`true_motion`, `slowed`, `stationary`, `backwards`, `smeared_disc`) |
| `squash_check` | per-frame scale triples, squash axis | volume per frame and the side scale that would keep it |

Every check reads `{"check", "value", "min", "max", "status"}` with status `pass`, `fail` or `not_measured`. A verdict
is `thresholds_met`, `thresholds_not_met` or `not_scored`, and it is never met while any check is unmeasured. Each
threshold can be overridden by the caller (`thresholds`), and the receipt reports where each one came from.

Evidence on every receipt cites the source of each principle (`cited`), what was computed here (`derived`), and
values the caller supplied (`caller`). **`CHECK`** marks a threshold still awaiting calibration and a qualified
person's approval (I3). `RECORDED` marks a physical law, a cited measured ratio, or a computed value.

## Calibration (I3)

`data/calibration.json` holds real motion from this repository with the verdict a person reached, and the suite
replays every case:

| Case | Label | Result |
|---|---|---|
| alex `walk_corridor` loop final (1.35 m/s, 1.617 m stride, 1.2 s cycle, slide 0.29 cm/s) | known good (approved for S07) | passes; stride 1.23× Alexander, Fr 0.20 |
| Wan `walk_corridor_rt2_s4` (0.37 m/s, 0.83 s steps) | known bad (rejected: slow) | fails Froude (0.015) |
| Wan `walk_corridor_s1` (≈0.25 m/s, ≈2 s steps) | known bad (rejected: slow motion) | fails Froude (0.007) and stride (2.09×). Its raw foot slide *passed*, so slide alone missed it |
| Kimodo `walk_v150` raw, SAM raw walk | known bad (foot slide 5–16 cm/s) | fail slide |
| Mr. Ton L1 strut | finding, not yet judged by a person | fails stride (2.19×) |
| Mr. Ton compressor squeeze | finding, not yet judged by a person | fails volume (+8.6 %) |

Balance, IK and mechanism thresholds are tried only on constructed exact and perturbed cases so far. They stay
`CHECK` until captured known-good and known-bad motion is added for them.

## First findings

- **Mr. Ton over-strides 2.2×: the slow-motion signature.** `mr-ton.ts` advances the stride phase by
  `distance / (1.1 · S) · π`, so one leg cycle is 7.14 m, and `l1-mr-ton.ts` walks him at 1.3–1.45 m/s, a man's
  speed. For a 6 m body (hip 3.18 m), that speed is a stroll (Fr 0.067), whose stride should be about 3.26 m with a
  2.25 s cycle. He takes 7.14 m strides on a 4.9 s cycle, the same signature as the rejected Wan walk. Either walk
  him at his own preferred speed (`scale_timing`: about 2.8 m/s, 4.8 m stride, 1.73 s cycle) or keep the stroll and
  shorten the stride phase to `distance / 1.63 · π`. Then sample his feet and run `gait_check` with tracks, because
  the hip and knee swing amplitudes also have to match the stride or the planted foot slides.
- **His squeeze gains 8.6 % volume.** The scale is `(1 + 0.18 sq, 1 − 0.22 sq, 1 + 0.18 sq)`. Keeping the volume
  needs 1/√(1 − 0.22 sq) sideways, which is 1.132 rather than 1.18 at full squeeze.
- **A real-speed rotor strobes without motion blur.** A 4-blade fan at 1750 rpm moves 4.9 blade pitches per frame at
  24 fps. With no shutter blur it reads as a crawl, a stop or a reverse. A 180° shutter smears it into a disc. Screw
  rotors at a real 3550 rpm are worse. Either state the shutter or slow the rotor below half a pitch per frame.
- **Integer millimetres and finite differences do not mix.** A plain second difference of mm-rounded positions at
  30 fps has about 630 mm/s² of noise (one standard deviation), which is about 60 mm of ZMP error at hip height. The
  first smoke run showed it as an 80 mm false failure. The balance tool fits a quadratic over 200 ms instead (about
  5 mm), and any producer that differentiates positions should do the same (I21).

## How animation tools call it

Every caller follows the same three steps. **Sample** the motion per frame into world-space numbers. **Scale** them
to the wire units. **Call** the tool and keep the receipt next to the clip's QA.

- **three.js timeline (`series/rai-reta`).** Poses are pure functions of lesson time (`TonPose`, `figures.ts`
  `walk()`), so a producer can evaluate them offline with no render. For each frame, run `pose(t)`, update the rig's
  world matrices, and read the foot (ankle/toe) world positions, the root, and the body's mass-weighted centre. Then
  call `gait_check` with `feet[].track` and `balance_check` with the COM and the planted foot corners. Mr. Ton's
  per-frame eval hook (`mr-ton-evals.ts` → `evals.jsonl`, gated by `check-mrton.mjs`) is the natural home for that
  sampling. Its rules can then cite a receipt instead of an invented number. Machines (`rotors.ts`, fans, pistons)
  call `mechanism_check` with their angle functions sampled per frame and the render's fps and shutter.
- **Blender bridge.** Per frame, `scene.frame_set(f)`, evaluate the depsgraph, and read pose-bone heads and tails in
  world space (`obj.matrix_world @ pbone.head`), × 1000 to mm, with `up_axis: "z"`. Joint chains for `ik_check` come
  from the armature's rest pose: each bone's head offset from its parent's head, and its local rotation axis.
- **Closed-loop motion (`media/nh3-kit/trial/motion`).** `src/post.py` already measures speed, stride, cycle, stance
  and slide per clip (`qa/*.json`). `gait_check` takes them directly (`speed_mps × 1000`, `stride_m × 1000`,
  `cycle_s × 1000`, `stance_s × 1000`, `slide.mean_cm_s × 10`), with the clip's leg length. That adds Froude and
  stride relations to the existing slide, pop and symmetry gates, and those relations caught the slow-motion takes
  that slide passed.
- **From POODO.** `bootstrap.build_robotics(goal_id)` composes the read-only domain. Every call is a pinned,
  bounded, receipted observation (`tests/test_robotics_conformance.py` shows the round trip).

Direct, for a quick look (from `foundations/robotics`):

```sh
printf '%s\n' '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"foundation-robotics-jsonrpc/1"}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"scale_timing","arguments":{"height_mm":6000}}}' \
  | python -B -m foundation_robotics_bridge
```

## Check it

```sh
cd foundations/robotics
python -B -m unittest discover -s tests       # calibration replay, invariances, refusals, the bridge, the manifest
python -B tools/build_manifest.py             # rewrites SOURCE-MANIFEST.json; prints the three pins
python -B tools/build_manifest.py --inventory > ../../schemas/robotics-v01-tools.json
```

With `jsonschema` importable (the root `requirements.txt`), the tool tests also validate every input and output
against its schema. After any change, re-pin `adapters/robotics_stdio.py` and `contracts/SOURCE-PINS.json`. From the
repository root, `python -B -m unittest tests.test_robotics_conformance` runs the host side.

## Not in v0.1 (gaps, in order of what animation needs next)

- **Producers.** Foot, COM and joint sampling for the three.js stage and for Blender, emitting this Foundation's
  arguments. Until they exist, callers hand-scale numbers.
- **Pops and smoothness.** Angular-acceleration spikes and jerk per joint (the motion loop's `pops` gate), with
  joint speed against the Jacobian near singularities.
- **Anticipation, follow-through and arcs.** Lead time of a counter-movement against the move's scale time, the lag
  and decay of secondary parts against their pendulum period, and end-effector path curvature.
- **Contact detail.** Sole penetration and hover, heel-to-toe roll, and hand contacts on fixed targets (the motion
  loop's 1 cm valve-rim gate).
- **Angular momentum in the ZMP.** Whole-body inertia per segment (Winter's segment masses), so arm swing and torso
  twist enter the balance check.
- **Machines.** Rotor spin-up from torque and inertia (τ = Iα), pump and valve stroke timing, belt and chain drives
  with slip.
- **Calibration.** Captured known-good and known-bad cases for balance, IK and mechanisms, a person's verdict on the
  two Mr. Ton findings, and quadrupeds and runs for the gait bands.
