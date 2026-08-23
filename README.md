# HW3 — Robot Manipulation × Semantic Robot Knowledge

NYCU Physical AI / TAICA — UR5 Kinematics + FSM Manipulation + Semantic Knowledge Graph

> **Student Guide** — Covers the task workflow, semantic definitions, downstream usage of each field, and guided exercises:
> Open [docs/hw3-student-guide.html](docs/hw3-student-guide.html) in your browser.
>
> **Official Specification** — Covers the assignment objectives, step-by-step installation instructions, detailed task procedures, and grading criteria: [SPEC.md](SPEC.md)

## Learning Objectives

- **Forward Kinematics (FK)**: Understand and implement forward kinematics for a 6-DoF robot arm using D-H parameters, including end-effector pose and Jacobian computation.
- **Inverse Kinematics (IK)**: Understand and implement iterative inverse kinematics using Jacobian-based methods to compute joint configurations for a target end-effector pose.
- **Application of IK/FK in Robot Manipulation**: Understand how kinematics is integrated into a complete manipulation pipeline — a deterministic **Finite State Machine** drives the UR5 through pick-and-place episodes, solving every motion with YOUR IK and cross-checking YOUR FK against the simulator at every state transition. IK/FK are components of a larger robotic system, not isolated mathematical functions.
- **Grounding with Standard Robotics Ontologies**: Represent robot specifications and kinematic results as STRUCTURED RDF that reuses existing standard vocabularies — IEEE 1872 CORA robots, SOMA joints/joint-states/poses/episodes, IEEE 1872 POS positions, QUDT units — instead of ad-hoc strings. Symbol grounding turns the numbers of Tasks 1–3 into machine-readable knowledge.
- **SHACL Validation of Execution Semantics**: Write SHACL shapes that validate the grounded execution data — discovering problem states of the IK/FK process (arm out of range, no convergence) directly from the numbers, and your validation result on a TA-provided 24-record execution dataset must match the TA answer key exactly.

## Overview

| Task | Content | Files you edit | Verification command | Points |
|---|---|---|---|---|
| 1 | Forward Kinematics | `fk.py` → `your_fk()` | `python fk.py` | 20 |
| 2 | Inverse Kinematics | `ik.py` → `your_ik()` | `python ik.py` | 40 |
| 3 | FSM Manipulation Pipeline | (integration, no code change) | `python fsm_task.py` | 10 |
| 4 | Semantic Grounding (REUSE) + SHACL Validation | 2 functions in `semantic/ground_execution.py` + `semantic/shapes.ttl` | `bash semantic/run_task4.sh` | 30 |

---

## Step 0. Environment Setup

**Step 0-1.** Create the conda environment and install Python dependencies
(no deep-learning framework, no dataset, no checkpoint — everything runs
locally with PyBullet):

```bash
cd hw3
conda create --name taica-hw3 python=3.7 -y
conda activate taica-hw3
pip install pybullet numpy scipy
```

**Step 0-2.** (Required for Task 4) Install JDK 11+ and verify:

```bash
sudo apt-get -y install openjdk-11-jdk
java -version && javac -version
```

The first run of Task 4 automatically downloads Apache Jena 4.10.0 (~30 MB; its `shacl` CLI performs the validation). It is cached under `semantic/.cache/` and works offline afterwards.

---

## Task 1. Forward Kinematics (20 points)

**Step 1-1.** Open [fk.py](fk.py) and read the D-H parameter table in `get_ur5_DH_params()`. It follows this project's `ur5.urdf` and differs slightly from the official UR5 spec — always use this table.

**Step 1-2.** Implement `your_fk(DH_params, q, base_pos)`:
- Input: 6 sets of D-H parameters, 6 joint angles `q`, base position `base_pos`
- Output: `(pose_7d, jacobian)` — the 7d end-effector pose `[x, y, z, qx, qy, qz, qw]` and the 6×6 geometric Jacobian
- **Do NOT use any pybullet API**; do not touch the `adjustment` block at the end of the function

**Step 1-3.** Verify (easy / medium / hard test cases; grading uses hidden ta1/ta2 cases):

```bash
python fk.py          # add -g for GUI, -vp to visualize end-effector poses
```

Expected output (Error Count must be 0 for every test file):

```
============================ Task 1 : Forward Kinematic ============================
- Testcase file : fk_test_case_easy.json
- Your Score Of Forward Kinematic : ... Error Count :    0 /  ...
- Your Score Of Jacobian Matrix   : ... Error Count :    0 /  ...
```

## Task 2. Inverse Kinematics (40 points)

**Step 2-1.** Open [ik.py](ik.py) and implement `your_ik(robot_id, new_pose, base_pos, ...)`:
- Use your `your_fk` and its Jacobian in an iterative method (e.g., damped least squares / pseudo-inverse)
- Be careful when computing delta x; tune hyper-parameters such as the step rate. Grading calls your function with **default arguments only**, so make your defaults the best ones
- `pybullet_ik()` in the same file is a reference you may compare behavior against, but your implementation must not call pybullet IK APIs

**Step 2-2.** Verify:

```bash
python ik.py
```

Expected output: Error Count 0 on all three test files, Mean Error in the 1e-3 range.

## Task 3. FSM Manipulation Pipeline (10 points)

Your IK/FK now drive a complete manipulation pipeline — no learned model, no
downloads: a deterministic **Finite State Machine** ([fsm_task.py](fsm_task.py),
TA-provided, no code change) runs 10 seeded pick-and-place episodes:

```
MOVE_TO_PREPICK -> DESCEND_TO_PICK -> GRASP -> LIFT
    -> MOVE_TO_PREPLACE -> DESCEND_TO_PLACE -> RELEASE -> RETREAT
    -> VERIFY -> SUCCESS / FAILURE
```

Every motion state performs **two validations**:
- **IK validation** — the target pose is solved by `your_ik`, executed with
  position control, and the achieved end-effector position must land within
  3 cm of the command (`IK_MISS` otherwise)
- **FK validation** — `your_fk` is evaluated on the MEASURED joint angles and
  must agree with the simulator's end-effector position within 1 cm
  (`FK_MISMATCH` otherwise) — your kinematic model is checked against physics
  at every state transition

`DESCEND_TO_PICK` steps downward until the suction gripper reports contact,
`GRASP`/`RELEASE` toggle the suction constraint, and `VERIFY` requires the
block to rest within 6 cm of the goal marker.

**Run** (10 seeded episodes; add `-g` to watch in the GUI):

```bash
python fsm_task.py
python fsm_task.py -g     # PyBullet window: watch the FSM drive the arm
```

Expected output:

```
============================ Task 3 : FSM Manipulation Pipeline ============================
FSM: MOVE_TO_PREPICK -> DESCEND_TO_PICK -> GRASP -> ... -> VERIFY
Episode  1/10 | SUCCESS  (place error 0.000 m)
...
Episode 10/10 | SUCCESS  (place error 0.000 m)
- Your Total Score : 10.000 / 10.000
```

A failure names the state and the reason (`IK_MISS in MOVE_TO_PREPICK ...`,
`FK_MISMATCH in LIFT ...`, `NO_CONTACT`, `PLACE_MISS`) — the FSM localizes
WHERE in the pipeline your kinematics broke.

---

## Task 4. Semantic Grounding (REUSE) + SHACL Validation (30 points)

Turn the *numbers* of your FK/IK **execution process** into *semantics*, then let the semantic layer find what went wrong. You implement two things — **grounding** and **SHACL**:

```
                         (1) grounding
your_fk / your_ik  ──>  ground_execution.py  ──>  data.ttl
  execution process       (2 TODO functions)
                                                  (2) SHACL
                          shapes.ttl (2 TODO shapes)  vs  data.ttl            -> validation.ttl
                          shapes.ttl                  vs  ta-faulty-execution.ttl
                                                          (TA dataset, 24 cases) -> probe-validation.ttl
```

**Step 4-1. Understand the REUSEd vocabulary.** Open [semantic/ontology/hw3-ontology.ttl](semantic/ontology/hw3-ontology.ttl):
- Design rule: **reuse existing standard vocabularies wherever possible** — robots are `cora:Robot` (IEEE 1872 CORA), joints are `soma:RevoluteJoint`, joint states are `soma:JointState`, poses are `soma:6DPose` composed of an IEEE 1872 `pos:Position` + quaternion component, units are QUDT IRIs (`unit:M` / `unit:RAD`); `hw3:` only mints what no standard covers (kinematic computations, D-H parameters, statuses, distances)
- **Structured representation, no JSON strings**: numeric values are typed `xsd:double` literals on structured nodes. `semantic/common.py` provides the serializers (`pose_to_ttl` / `joint_config_to_ttl`) — use them

**Step 4-2. GROUNDING — implement the ontology-API functions.** Open [semantic/ground_execution.py](semantic/ground_execution.py):

| Function | Grounds | Status |
|---|---|---|
| `fk_computation_to_triples()` | one FK execution: input config, EE pose, pose/Jacobian errors | **worked example** — read it first |
| `robot_spec_to_triples()` | robot spec: D-H params + joint limits for all 6 joints | **TODO 1** |
| `ik_computation_to_triples()` | one IK execution: status, residual, `hw3:hasTargetDistance`, structured joint configuration | **TODO 2** |

The script runs your `your_fk` (3 test cases vs ground truth) and `your_ik` (3 fixed targets: near / mid / far) and writes everything into **`output/data.ttl`** — your execution process as a semantic graph.

**Step 4-3. SHACL — write the validation shapes.** Open [semantic/shapes.ttl](semantic/shapes.ttl): the FK-accuracy shape (`hasPoseError <= 0.005` else `FK_INACCURATE`) is the worked example; you add two shapes — `hasTargetDistance <= 0.90` else **`ARM_OUT_OF_RANGE`** (arm beyond the UR5 workspace) and `hasResidual <= 0.02` else **`NO_CONVERGENCE`**. Message prefixes are graded, keep them exact. Two validations run:
- your shapes vs **your** `data.ttl` → `output/validation.ttl` — on correct IK it flags exactly `target_mid` / `target_far` (they really are out of range) and leaves `target_near` clean
- your shapes vs **[semantic/ta-faulty-execution.ttl](semantic/ta-faulty-execution.ttl)** — a TA-provided dataset of **24 IK/FK execution records** (good/bad mixed, *including values exactly at the thresholds*). The grader compares your validation result against the TA answer key **[semantic/ta-answer-key.json](semantic/ta-answer-key.json)** case by case — each record's flags must match the answer **exactly** (no false positives, no false negatives) to count as correct

Design note: SHACL validates the **numbers** (thresholds on distances / residuals / errors) directly from the grounded data — the numeric判斷 stays in the data layer, the constraints live declaratively in shapes.

**Step 4-4. Run and score with one command.**

```bash
conda activate taica-hw3
bash semantic/run_task4.sh --group <your-group-id>   # uses your your_fk / your_ik
```

The script runs 5 steps: toolchain → Jena → grounding (`data.ttl`) → SHACL (three validation reports) → scoring. Expected output:

```
  [S1] grounding structure (0 violations) OK  (+12)
  [S2] target_mid flagged ARM_OUT_OF_RANGE .... OK  (+2)
  [S2] target_far flagged ARM_OUT_OF_RANGE .... OK  (+2)
  [S2] target_near clean (no problem flags) ... OK  (+2)
  [S2] no JOINT_LIMIT_VIOLATION ............... OK  (+2)
  [S3] TA dataset vs answer key: faulty 11/11, clean 13/13 OK  (+10)
  Your Task 4 Score : 30.0 / 30.0
```

Grading uses **[semantic/ta-shapes-full.ttl](semantic/ta-shapes-full.ttl)** — the TA's complete SHACL suite: `STRUCTURE:*` shapes check your grounding (types, required properties, `xsd:double` typing, exactly 6 `soma:JointState` per configuration), problem shapes re-discover ARM_OUT_OF_RANGE / NO_CONVERGENCE from your numbers, and a SHACL-SPARQL shape cross-checks every joint angle against its joint's limits (`JOINT_LIMIT_VIOLATION`).

**Task 4 FAQ**
- `python` is not the taica-hw3 environment → `PYTHON=~/miniconda3/envs/taica-hw3/bin/python bash semantic/run_task4.sh`
- Jena download fails → manually extract apache-jena-4.10.0 and `export JENA_HOME=<path>` before running
- S1 reports STRUCTURE violations → open `output/ta-validation.ttl`; each `sh:resultMessage` tells you which property/typing is missing (a bare `0.0892` instead of `"0.0892"^^xsd:double` is the classic one)
- S3 mismatches → the grader prints `expected [...] , got [...]` per wrong case. Your `sh:message` must START with `ARM_OUT_OF_RANGE:` / `NO_CONVERGENCE:` (prefix-matched), and thresholds must use `sh:maxInclusive` — the dataset contains records exactly at 0.90 / 0.02 / 0.005, which are *conforming*

## Grading

| Item | Points |
|---|---|
| Task 1: FK correctness (FK 10 + Jacobian 10, TA test cases) | 20 |
| Task 2: IK correctness (TA test cases, default arguments only) | 40 |
| Task 3: FSM pick-and-place success over 10 seeded episodes | 10 |
| Task 4: S1 grounding structure 12 + S2 problem detection 8 + S3 SHACL vs TA dataset & answer key 10 | 30 |
| **Total** | **100** |

## Submission

1. `fk.py` (with `your_fk` completed)
2. `ik.py` (with `your_ik` completed)
3. `semantic/ground_execution.py` (with both TODO functions completed)
4. `semantic/shapes.ttl` (with the two problem shapes completed)
5. A short report: screenshots of all four tasks, plus an explanation of what your SHACL validation discovered in `output/validation.ttl` and in the TA dataset (`output/probe-validation.ttl`)

> Note: `semantic/output/`, `semantic/store/`, and `semantic/.cache/` are auto-generated — do not submit them.

## Reference

- https://automaticaddison.com/the-ultimate-guide-to-jacobian-matrices-for-robotics/
- Apache Jena / TDB2: https://jena.apache.org/documentation/tdb2/
