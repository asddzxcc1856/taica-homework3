# HW3 Student Guide

**UR5 Kinematics, FSM Manipulation, and Semantic Knowledge Graphs**
NYCU Physical AI / TAICA — Homework 3 · Total: 100 points

This guide is self-contained: it covers the assignment goals, every installation step, every task in detail, testing, submission, and troubleshooting. A short-form task specification is in [SPEC.md](SPEC.md), and a visual walkthrough is in [docs/hw3-student-guide.html](docs/hw3-student-guide.html).

---

## 1. Assignment Overview

### Background and motivation

Forward kinematics (FK) and inverse kinematics (IK) are the mathematical core of robot manipulation — but they are usually taught as isolated functions. In this assignment you implement both from scratch for a simulated UR5 arm, then watch them operate inside a complete pick-and-place pipeline, and finally turn your solvers' *execution data* into a machine-readable knowledge graph that can be validated automatically.

### Objectives

1. Implement FK for a 6-DoF arm using classic Denavit–Hartenberg (D-H) parameters, producing an end-effector pose and a 6×6 geometric Jacobian.
2. Implement iterative Jacobian-based IK.
3. Run your solvers inside a deterministic finite-state-machine (FSM) manipulation pipeline.
4. Ground your FK/IK execution process as structured RDF that reuses standard robotics ontologies.
5. Write SHACL shapes that detect problem states (arm out of range, no convergence) directly from the grounded numbers.

### Problem statement

Given the UR5 model in this repository and its D-H table, implement `your_fk` and `your_ik` so that: the accuracy tests pass; the FSM completes 10/10 pick-and-place episodes; your execution process is grounded into `semantic/output/data.ttl`; and your SHACL shapes, applied to a TA-provided 24-record execution dataset, reproduce the published answer key exactly.

### Scope and learning outcomes

In scope: analytic FK, geometric Jacobians, iterative IK, RDF/Turtle authoring with provided serializers, SHACL node shapes. Out of scope: motion planning, learned policies, OWL reasoning, SPARQL. After finishing, you will be able to build and debug the kinematic stack of a real manipulation system and represent its behavior semantically.

### Task overview

| Task | Content | Files you edit | Verification | Points |
|---|---|---|---|---:|
| 1 | Forward Kinematics | `fk.py` — `your_fk()` | `python fk.py` | 20 |
| 2 | Inverse Kinematics | `ik.py` — `your_ik()` | `python ik.py` | 40 |
| 3 | FSM Manipulation Pipeline | none (integration check) | `python fsm_task.py` | 10 |
| 4 | Semantic Grounding + SHACL | `semantic/ground_execution.py`, `semantic/shapes.ttl` | `bash semantic/run_task4.sh` | 30 |

---

## 2. Prerequisites

- **Programming:** comfortable Python (NumPy arrays, matrix operations).
- **Mathematics:** homogeneous transforms, rotation representations (quaternions), basic linear algebra (pseudo-inverse), vector cross products.
- **Concepts you will learn here if new:** classic D-H convention, geometric Jacobian, damped least squares, RDF/Turtle, SHACL.
- **Tools:** a Linux machine with conda; any code editor.

---

## 3. System Requirements

| Component | Requirement | Status |
|---|---|---|
| Operating system | Linux (Ubuntu 20.04+ recommended) | Required |
| CPU | Any modern x86_64 CPU | Required |
| GPU / CUDA / cuDNN | **Not used** — this assignment is CPU-only | Not needed |
| Storage | Less than 1 GB | Required |
| Python | 3.7 in a conda environment | Required |
| Python packages | `pybullet`, `numpy`, `scipy` | Required |
| Java | JDK 11 or later (Task 4 only) | Required |
| Network | Once, for pip installs and one ~30 MB download; offline afterwards | Required (one-time) |
| X display | Only for the optional `-g` GUI modes | Optional |

---

## 4. Installation Guide

Follow every step in order. Each step ends with a verification command.

**Step 1 — Miniconda** (skip if you already have conda):

```bash
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh
source ~/.bashrc
conda --version          # verify: prints a version number
```

**Step 2 — Python 3.7 environment:**

```bash
conda create --name taica-hw3 python=3.7 -y
conda activate taica-hw3
python --version         # verify: Python 3.7.x
```

Activate `taica-hw3` every time you work on this assignment.

**Step 3 — Python packages:**

```bash
pip install pybullet numpy scipy
python -c "import pybullet, numpy, scipy; print('OK')"    # verify: OK
```

**Step 4 — JDK 11+ (needed for Task 4):**

```bash
sudo apt-get -y install openjdk-11-jdk
java -version            # verify: version 11 or later
```

**Step 5 — Get the assignment and check the layout.** Obtain the `hw3` directory from the course distribution channel, then:

```bash
cd hw3
ls
# expect: fk.py  ik.py  fsm_task.py  test_case/  semantic/  hw3_utils/
#         pybullet_robot_envs/  pybullet_planning/  docs/  ...
```

You will edit exactly four files: `fk.py`, `ik.py`, `semantic/ground_execution.py`, `semantic/shapes.ttl`. **Do not modify any other file** — grading re-assembles your four files into a clean copy of the release, so changes elsewhere are discarded (and altering test or scoring files is an integrity violation).

**Step 6 — Toolchain smoke test (optional but recommended):**

```bash
bash semantic/run_task4.sh
```

The first run downloads Apache Jena 4.10.0 (~30 MB) into `semantic/.cache/` and reuses it afterwards. Before you implement Task 1, the script will stop in STEP 3 with `NotImplementedError` — that is expected; if STEP 1 and STEP 2 pass, your environment is ready. If the download fails, extract Jena 4.10.0 manually and run with `export JENA_HOME=<path-to-apache-jena-4.10.0>`.

---

## 5. Assignment Tasks

### Task 1 — Forward Kinematics (20 points)

**Objective:** compute the UR5 end-effector pose and geometric Jacobian analytically.

**Implement** in `fk.py`:

```python
your_fk(DH_params, q, base_pos)  ->  (pose_7d, jacobian)
```

- **Input:** the six-row classic D-H table from `get_ur5_DH_params()`, six joint angles `q`, and the base position.
- **Output:** `pose_7d = [x, y, z, qx, qy, qz, qw]` and a 6×6 geometric Jacobian (linear rows on top, angular rows below, expressed in the base frame).

**Constraints:**

- Use the **classic** D-H convention and only the provided table (it matches this repository's URDF and differs slightly from published UR5 datasheets).
- Do **not** call any PyBullet API inside `your_fk` (no `getLinkState`, no `calculateJacobian`).
- Do **not** modify the `adjustment` block at the end of the function — it aligns your final frame with the simulator's end-effector frame, and everything downstream depends on it.

**Approach:** chain the per-joint transform `Rz(θᵢ)·Tz(dᵢ)·Tx(aᵢ)·Rx(αᵢ)` from the base; for each revolute joint `i`, the Jacobian's linear part is `z(i-1) × (p_end − p(i-1))` and the angular part is `z(i-1)`.

**Test:**

```bash
python fk.py             # easy / medium / hard test cases
python fk.py -g          # optional: GUI, the arm poses per test case
python fk.py -g -vp      # optional: also draw your pose (red) vs ground truth (green)
```

Pass criterion: **Error Count 0** for both FK and Jacobian on all three files. Tolerances: pose error < 0.005 (L2 over the 7-vector), Jacobian error < 0.05 (matrix L2). Grading uses additional hidden test cases of the same format.

### Task 2 — Inverse Kinematics (40 points)

**Objective:** solve joint angles for a target end-effector pose using your own FK and Jacobian.

**Implement** in `ik.py`:

```python
your_ik(robot_id, new_pose, base_pos, max_iters=1000, stop_thresh=0.001)  ->  joint_angles (6)
```

**Constraints and requirements:**

- Iterative Jacobian-based method (damped least squares recommended: `Δq = Jᵀ(JJᵀ + λ²I)⁻¹ Δx`, scaled by a step rate).
- Solve for **both** position and orientation error (convert the quaternion difference to an axis-angle vector for the 6-D error).
- Clip every update to the joint limits.
- **Grading calls your function with default arguments only** — tune damping, step rate, `max_iters`, and `stop_thresh`, then bake the best values in as the defaults.
- You may read `pybullet_ik()` in the same file to compare behavior, but your implementation must not call PyBullet IK APIs.

**Test:**

```bash
python ik.py
```

Pass criterion: Error Count 0 on all three files (threshold: the executed end-effector pose must land within 0.02 m of the target) and mean error around 10⁻³ m. The three difficulty levels differ in the step size between consecutive targets — if easy passes and hard fails, revisit your step rate, damping, and iteration budget.

### Task 3 — FSM Manipulation Pipeline (10 points)

**Objective:** demonstrate that your FK/IK survive integration into a full manipulation loop. **No code changes** — `fsm_task.py` is provided.

The FSM runs ten seeded (fully reproducible) pick-and-place episodes:

```
MOVE_TO_PREPICK → DESCEND_TO_PICK → GRASP → LIFT
  → MOVE_TO_PREPLACE → DESCEND_TO_PLACE → RELEASE → RETREAT → VERIFY
```

Every motion state performs two checks:

| Check | Requirement | Failure message |
|---|---|---|
| IK | achieved end-effector position within **3 cm** of the command | `IK_MISS in <STATE>` |
| FK | `your_fk` on the *measured* joint angles within **1 cm** of the simulator | `FK_MISMATCH in <STATE>` |

`DESCEND_TO_PICK` steps downward until the suction gripper reports contact (`NO_CONTACT` otherwise); `VERIFY` requires the block within **6 cm** of the goal (`PLACE_MISS` otherwise).

**Test:**

```bash
python fsm_task.py        # scoring mode (headless)
python fsm_task.py -g     # watch it in the PyBullet GUI
```

Pass criterion: `10/10 SUCCESS`, score `10.000 / 10.000`. Failure messages tell you **which state and which check** broke — use them to debug Task 1/2 (e.g., `IK_MISS` only on long moves points at solver convergence; `NO_CONTACT` usually means a systematic height error in FK).

### Task 4 — Semantic Grounding (REUSE) + SHACL Validation (30 points)

**Objective:** turn your FK/IK execution numbers into a semantic graph, then let declarative constraints find the problems.

```
                        (1) grounding
your_fk / your_ik  ──>  ground_execution.py  ──>  semantic/output/data.ttl
                                                  (2) SHACL
                        shapes.ttl vs data.ttl                 → validation.ttl
                        shapes.ttl vs ta-faulty-execution.ttl  → probe-validation.ttl
```

**Step A — read the vocabulary** (`semantic/ontology/hw3-ontology.ttl`). The design rule is REUSE — use standard vocabularies wherever one exists:

| Concept | Representation |
|---|---|
| Robot | `cora:Robot` (IEEE 1872 CORA) |
| Joint / joint state | `soma:RevoluteJoint`, `soma:JointState` + `soma:hasJointPosition` |
| Pose | `soma:6DPose` = `pos:Position` component + quaternion component |
| Units | QUDT IRIs: `unit:M`, `unit:RAD` |
| Numbers | typed `"…"^^xsd:double` literals on structured nodes — **never JSON strings** |

Use the serializers in `semantic/common.py` (`pose_to_ttl`, `joint_config_to_ttl`).

**Step B — grounding** (`semantic/ground_execution.py`). One function is a worked example; you implement two:

| Function | Grounds | Status |
|---|---|---|
| `fk_computation_to_triples()` | one FK execution: input configuration, EE pose, errors | worked example — read it first |
| `robot_spec_to_triples()` | the robot: six joints with D-H parameters and limits | **TODO 1** |
| `ik_computation_to_triples()` | one IK execution: status, residual, target distance, joint configuration | **TODO 2** |

The provided `main()` runs your FK (3 cases vs ground truth) and your IK (3 fixed targets: near / mid / far) and writes `semantic/output/data.ttl`.

**Step C — SHACL** (`semantic/shapes.ttl`). The FK-accuracy shape (pose error ≤ 0.005 else `FK_INACCURATE`) is the worked example. Add two shapes targeting `hw3:IKComputation`:

1. `hw3:hasTargetDistance` at most **0.90** → message must begin with `ARM_OUT_OF_RANGE:`
2. `hw3:hasResidual` at most **0.02** → message must begin with `NO_CONVERGENCE:`

Two hard rules: the message **prefix** is what the grader matches, and the thresholds must use **`sh:maxInclusive`** — the TA dataset contains records exactly at 0.90 / 0.02 / 0.005, and those are *conforming*.

**Step D — the TA dataset and answer key.** `semantic/ta-faulty-execution.ttl` holds **24 execution records** (good and bad, including boundary values); `semantic/ta-answer-key.json` is the published expected result. Your shapes are run against the dataset, and each record's set of flags must match the answer key **exactly** — no false positives, no false negatives. Score: `8 × (correct faulty records / 11) + 2 × (correct clean records / 13)`.

**Run everything:**

```bash
conda activate taica-hw3
bash semantic/run_task4.sh --group <your-group-id>
```

Expected full-score output:

```
  [S1] grounding structure (0 violations) OK  (+12)
  [S2] target_mid flagged ARM_OUT_OF_RANGE .... OK  (+2)
  [S2] target_far flagged ARM_OUT_OF_RANGE .... OK  (+2)
  [S2] target_near clean (no problem flags) ... OK  (+2)
  [S2] no JOINT_LIMIT_VIOLATION ............... OK  (+2)
  [S3] TA dataset vs answer key: faulty 11/11, clean 13/13 OK  (+10)
  Your Task 4 Score : 30.0 / 30.0
```

With correct kinematics, your own data genuinely contains two out-of-range targets (mid, far) and one solvable one (near) — S2 checks that your grounding + the TA shapes rediscover exactly that.

---

## 6. Recommended Workflow

1. Read this guide and `SPEC.md` end to end.
2. Install and verify the environment (§4).
3. Run `python fk.py` once to see the harness and output format (it will fail on the stub — that's fine).
4. Implement `your_fk`; iterate until all visible FK tests report zero errors.
5. Implement `your_ik`; tune defaults until all visible IK tests pass.
6. Run `python fsm_task.py`; debug any state-localized failures (they point back at Tasks 1–2).
7. Read the Task 4 worked examples (`fk_computation_to_triples`, the FK shape), then implement the two grounding functions and the two shapes.
8. Run `bash semantic/run_task4.sh --group <id>`; fix issues using the validation reports in `semantic/output/`.
9. Re-run all four commands from a clean state; capture the outputs for your report.
10. Assemble and submit (§8).

---

## 7. Testing and Validation

- **Public tests** are exactly the four commands above — the graders run the same programs (plus additional hidden FK/IK test cases in the same JSON format).
- **Tolerances** (all built into the released code): FK pose 0.005, Jacobian 0.05, IK 0.02 m, FSM 3 cm / 1 cm / 6 cm, SHACL thresholds 0.90 / 0.02 / 0.005.
- **Determinism:** Task 3 episodes are seeded; a correct solution scores identically on every run.
- **Task 4 self-diagnosis:** `semantic/output/ta-validation.ttl` explains every `STRUCTURE:` violation (typically a missing property or an untyped number — write `"0.0892"^^xsd:double`, never a bare `0.0892`); the S3 section of the score output prints `expected [...] , got [...]` for every mismatched record.
- **Common error signatures:** wrong D-H convention (all FK cases fail), missing orientation error (easy IK passes, hard fails), parameters not set as defaults (your runs pass, grading fails), `maxExclusive` shapes (S3 loses exactly the boundary records).

---

## 8. Submission Requirements

Submit:

1. `fk.py` (with `your_fk` completed)
2. `ik.py` (with `your_ik` completed)
3. `semantic/ground_execution.py` (both TODO functions completed)
4. `semantic/shapes.ttl` (both problem shapes completed)
5. A short report (PDF): the four score outputs (screenshots or copied text) plus a brief explanation of what your SHACL validation discovered in `output/validation.ttl` and in the TA dataset (`output/probe-validation.ttl`)

Keep the released directory structure and file names unchanged. Do **not** submit generated directories (`semantic/output/`, `semantic/.cache/`, `__pycache__/`).

Submission platform, deadline, late policy, and re-submission policy: **announced separately by the course staff** — check the course page before the due date.

---

## 9. Troubleshooting

| Problem | Fix |
|---|---|
| `pip install pybullet` fails | Confirm you are inside the conda env with Python 3.7 on Linux (`python --version`). Recreate the env if needed. |
| `ImportError: No module named pybullet` | You forgot `conda activate taica-hw3`. |
| `java: command not found` (Task 4) | Install JDK 11+ (§4 Step 4). |
| Jena download fails | `export JENA_HOME=<manually-extracted apache-jena-4.10.0>` and re-run. |
| `NotImplementedError` in `run_task4.sh` STEP 3 | Expected before Tasks 1–2 are implemented — not an environment problem. |
| GUI window doesn't open / `cannot connect to X server` | You are in a headless session; drop `-g` (scoring never needs the GUI) or set a valid `DISPLAY`. |
| Arm doesn't move in the Task 1 GUI | Don't edit the visualization block in `score_fk` — the release already handles GUI stepping. |
| FSM fails with `NO_CONTACT` | Usually a systematic FK height error — check that you didn't modify the `adjustment` block. |
| `STRUCTURE:` violations in S1 | Open `output/ta-validation.ttl`; each message names the missing property or typing. |
| S3 mismatches | Read the printed `expected/got` lines; verify message prefixes, `sh:maxInclusive`, and the threshold values. |
| Wrong scores after moving files around | Run all commands from the assignment root directory with the released layout. |

If none of this resolves your issue, report it as described in §13.

---

## 10. FAQ

- **Can I use another library?** Only `numpy`, `scipy`, and the Python standard library. The grading environment has nothing else installed.
- **Can I use another framework (PyTorch, ROS, …)?** No.
- **Which files can I modify?** Exactly four: `fk.py`, `ik.py`, `semantic/ground_execution.py`, `semantic/shapes.ttl`. Grading copies only these into a clean release, so edits elsewhere are discarded — and tampering with tests or scoring files is an integrity violation.
- **Can I call PyBullet inside `your_fk` / `your_ik`?** No kinematics APIs (`getLinkState`, `calculateJacobian`, `calculateInverseKinematics`). The rest of the harness already uses PyBullet where appropriate.
- **Can I use external resources?** You may read references (§11); the code you submit must be your own work. See the course's academic-integrity policy.
- **Can I use AI coding assistants?** Follow the course-wide policy announced by the instructor; if unsure, ask before using one.
- **I don't have a GPU.** You don't need one — the assignment is CPU-only.
- **The official environment doesn't work on my machine.** Follow §9; if still stuck, report the issue with the full details in §13. Grading runs on the standard environment described in §3.
- **Can I resubmit?** Governed by the course submission policy — see the course page.
- **How do I report a bug in the assignment itself?** Same procedure as §13; clearly mark it as a suspected assignment bug.

---

## 11. Reading Materials

### Required

| Resource | Author / Org | Link | Relevant to |
|---|---|---|---|
| The Ultimate Guide to Jacobian Matrices for Robotics | Automatic Addison | https://automaticaddison.com/the-ultimate-guide-to-jacobian-matrices-for-robotics/ | Tasks 1–2: the exact Jacobian construction used here |
| SHACL — Shapes Constraint Language (W3C Recommendation, 2017) | W3C | https://www.w3.org/TR/shacl/ | Task 4: node shapes, `sh:maxInclusive`, validation reports |
| The in-repo worked examples | Course staff | `semantic/ground_execution.py`, `semantic/shapes.ttl`, `semantic/ontology/hw3-ontology.ttl` | Task 4: the patterns you are asked to imitate |

### Recommended

| Resource | Author / Org | Link | Relevant to |
|---|---|---|---|
| PyBullet Quickstart Guide | Bullet Physics | https://pybullet.org | Understanding the simulation harness |
| RDF 1.1 Turtle | W3C | https://www.w3.org/TR/turtle/ | Task 4: the syntax you write |
| Apache Jena documentation | Apache Software Foundation | https://jena.apache.org | Task 4: the validator used by `run_task4.sh` |

### Optional

| Resource | Author / Org | Link | Relevant to |
|---|---|---|---|
| Introduction to Robotics: Mechanics and Control | J. J. Craig | (textbook) | D-H conventions and Jacobians in depth |
| IEEE 1872-2015 (CORA) | IEEE | via IEEE Xplore | Origin of the reused robot vocabulary |
| QUDT units vocabulary | QUDT.org | https://qudt.org | The unit IRIs used in grounding |

---

## 12. Academic Integrity

- You may discuss concepts with classmates; you may **not** share or copy code, D-H derivations written as code, shape files, or reports.
- All submitted code must be written by you. Copying from other students, previous years, or online solutions is plagiarism.
- Do not modify protected files (tests, scorers, datasets, the FSM) — grading uses pristine copies, and deliberate tampering is treated as misconduct.
- Hard-coding outputs (e.g., returning memorized ground-truth poses) is misconduct; hidden test cases are designed to detect it.
- Use of external references is allowed for understanding; cite anything non-obvious that influenced your solution in your report.
- AI tool usage is governed by the course-wide policy announced by the instructor.
- Violations are handled according to the course and university policy; consequences are determined by the instructor.

---

## 13. Getting Help

Ask questions through the course's announced channel (course page / forum / TA office hours). When reporting a technical problem, always include:

- Operating system and version
- `python --version` and the active conda environment
- `pip list | grep -Ei 'pybullet|numpy|scipy'`
- `java -version` (for Task 4 issues)
- The exact command you ran and the directory you ran it from
- The **complete** error message or traceback (copied as text)
- For Task 4: the relevant files from `semantic/output/`
- Steps to reproduce, and whether the visible test cases pass on your machine

Reports with this information can usually be answered in one round trip; reports without it will be bounced back for details.
