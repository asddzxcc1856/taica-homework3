# HW3 — Robot Manipulation × Semantic Robot Knowledge

NYCU Physical AI / TAICA — UR5 Kinematics + Transporter Network + Semantic Knowledge Graph

> 圖文版學生引導手冊（任務流程、語意定義、每個欄位的下游用途、練習引導）:
> 在瀏覽器開啟 [docs/hw3-student-guide.html](docs/hw3-student-guide.html)

## Learning Objectives

- **Forward Kinematics (FK)**: Understand and implement forward kinematics for a 6-DoF robot arm using D-H parameters, including end-effector pose and Jacobian computation.
- **Inverse Kinematics (IK)**: Understand and implement iterative inverse kinematics using Jacobian-based methods to compute joint configurations for a target end-effector pose.
- **Application of IK in Robot Manipulation**: Understand how inverse kinematics is integrated into a complete manipulation pipeline by applying the implemented IK solver to the Transporter Network block insertion task (prepick → grasp → preplace → insertion). IK is a component of a larger robotic system, not an isolated mathematical function.
- **Grounding with Standard Robotics Ontologies**: Represent robot specifications and kinematic results as STRUCTURED RDF that reuses existing standard vocabularies — IEEE 1872 CORA robots, SOMA joints/joint-states/poses/episodes, IEEE 1872 POS positions, QUDT units — instead of ad-hoc strings. Symbol grounding turns the numbers of Tasks 1–3 into machine-readable knowledge.
- **Reasoning & SHACL Validation of Execution Semantics**: Define OWL equivalence axioms so evaluation classes are DERIVED (never asserted), and write SHACL shapes that validate the grounded execution data — discovering problem states of the IK/FK process (arm out of range, no convergence) directly from the numbers, including a TA-provided faulty execution trace.

## Overview

| Task | Content | Files you edit | Verification command | Points |
|---|---|---|---|---|
| 1 | Forward Kinematics | `fk.py` → `your_fk()` | `python fk.py` | 20 |
| 2 | Inverse Kinematics | `ik.py` → `your_ik()` | `python ik.py` | 40 |
| 3 | Transporter Network | (integration, no code change) | `python ravens/test.py ...` | 10 |
| 4 | Semantic Grounding (REUSE) + Reasoning + SHACL | 2 functions in `semantic/ground_execution.py` + `semantic/reasoning.ttl` + `semantic/shapes.ttl` | `bash semantic/run_task4.sh` | 30 |

---

## Step 0. Environment Setup

**Step 0-1.** Create the conda environment and install Python dependencies:

```bash
cd hw3
cd ravens
conda create --name taica-hw3 python=3.7 -y
conda activate taica-hw3
sudo apt-get update
sudo apt-get -y install gcc libgl1-mesa-dev
pip install -r requirements.txt
pip install opencv-python==4.5.5.64 transforms3d
cd ..
```

**Step 0-2.** (Optional, for GPU acceleration in Task 3) Install CUDA 10.1 / cuDNN 7.6.5:

```bash
conda install cudatoolkit==10.1.243 -y
conda install cudnn==7.6.5 -y
```

**Step 0-3.** (Required for Task 4) Install JDK 11+ and verify:

```bash
sudo apt-get -y install openjdk-11-jdk
java -version && javac -version
```

The first run of Task 4 automatically downloads Apache Jena 4.10.0 (~30 MB; its `shacl` CLI performs the validation and its rule engine the OWL reasoning). It is cached under `semantic/.cache/` and works offline afterwards.

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

## Task 3. Transporter Network Manipulation Pipeline (10 points)

Where IK sits in the pipeline (see `movep()` → `solve_ik()` → **`your_ik()`** in [ravens/ravens/environments/environment.py](ravens/ravens/environments/environment.py)):

```
Transporter Network → Predict Pick / Place Poses → IK → Joint Configuration
→ Robot Motion → Prepick → Grasp → Preplace → Insertion
```

**Step 3-1.** Download the test data and model checkpoint:
- dataset: https://drive.google.com/file/d/1Jh8hAvraT1Zt1YfSNRT_lMJXbsK4Wcse/view → put the whole `block-insertion-easy-test/` folder under `ravens/`
- checkpoint: https://drive.google.com/file/d/1cmFbqTzuu6IUJPlx1eOq2djRSubfM94H/view → put the whole `checkpoints/` folder under `ravens/`

**Step 3-2.** Run (10 test episodes using your IK):

```bash
cd ravens
CUDA_VISIBLE_DEVICES=-1 python ravens/test.py --assets_root=./ravens/environments/assets/ --disp=True --task=block-insertion-easy --agent=transporter --n_demos=1000 --n_steps=20000
```

Expected output: `Total Reward: 1.0 Done: True` for all 10 episodes.

---

## Task 4. Semantic Grounding (REUSE) + Reasoning + SHACL Validation (30 points)

Turn the *numbers* of your FK/IK **execution process** into *semantics*, then let the semantic layer find what went wrong. You implement three things — **grounding**, **reasoning**, and **SHACL**:

```
                         (1) grounding                    (2) reasoning
your_fk / your_ik  ──>  ground_execution.py  ──>  data.ttl ──> OWL reasoner + reasoning.ttl
  execution process       (2 TODO functions)                     -> inferred.ttl
                                                  (3) SHACL
                          shapes.ttl (2 TODO shapes)  vs  data.ttl            -> validation.ttl
                          shapes.ttl                  vs  ta-faulty-execution.ttl
                                                          (TA's faulty trace)  -> probe-validation.ttl
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

**Step 4-3. REASONING — define the evaluation classes.** Open [semantic/reasoning.ttl](semantic/reasoning.ttl): `SolvedIKComputation ≡ IKComputation ⊓ (hasIKStatus value "SOLVED")` is the worked example; you add `OutOfReachIKComputation` the same way. The OWL reasoner derives the memberships into `output/inferred.ttl` — expected: `SolvedIKComputation = {ik_target_near}`, `OutOfReachIKComputation = {ik_target_mid, ik_target_far}`. Memberships are **never asserted by your code** — if you delete your axiom, the derived set becomes empty.

**Step 4-4. SHACL — write the validation shapes.** Open [semantic/shapes.ttl](semantic/shapes.ttl): the FK-accuracy shape (`hasPoseError <= 0.005` else `FK_INACCURATE`) is the worked example; you add two shapes — `hasTargetDistance <= 0.90` else **`ARM_OUT_OF_RANGE`** (arm beyond the UR5 workspace) and `hasResidual <= 0.02` else **`NO_CONVERGENCE`**. Message prefixes are graded, keep them exact. Two validations run:
- your shapes vs **your** `data.ttl` → `output/validation.ttl` — on correct IK it flags exactly `target_mid` / `target_far` (they really are out of range) and leaves `target_near` clean
- your shapes vs **[semantic/ta-faulty-execution.ttl](semantic/ta-faulty-execution.ttl)** — a TA-provided *faulty* IK/FK execution trace; your shapes must catch its planted problems (one out-of-range IK, one non-converging IK, one inaccurate FK) and leave the good case clean

Note the division of labour: **OWL reasons over symbols** (status strings → concept membership), **SHACL validates numbers** (thresholds on distances/residuals/errors) — OWL cannot compare numeric values, which is exactly why both layers exist.

**Step 4-5. Run and score with one command.**

```bash
conda activate taica-hw3
bash semantic/run_task4.sh --group <your-group-id>   # uses your your_fk / your_ik
```

The script runs 6 steps: toolchain → Jena → grounding (`data.ttl`) → reasoning (`inferred.ttl`) → SHACL (three validation reports) → scoring. Expected output:

```
  [S1] grounding structure (0 violations) OK  (+10)
  [S2] inferred SolvedIKComputation = {near} .. OK  (+3)
  [S2] inferred OutOfReach = {mid, far} ...... OK  (+3)
  [S3] target_mid flagged ARM_OUT_OF_RANGE .... OK  (+2)
  [S3] target_far flagged ARM_OUT_OF_RANGE .... OK  (+2)
  [S3] target_near clean (no problem flags) ... OK  (+1)
  [S3] no JOINT_LIMIT_VIOLATION ............... OK  (+1)
  [S4] faulty trace: good case clean .......... OK  (+2)
  [S4] faulty trace: out-of-range flagged ..... OK  (+2)
  [S4] faulty trace: no-convergence flagged ... OK  (+2)
  [S4] faulty trace: bad FK flagged ........... OK  (+2)
  Your Task 4 Score : 30.0 / 30.0
```

Grading uses **[semantic/ta-shapes-full.ttl](semantic/ta-shapes-full.ttl)** — the TA's complete SHACL suite: `STRUCTURE:*` shapes check your grounding (types, required properties, `xsd:double` typing, exactly 6 `soma:JointState` per configuration), problem shapes re-discover ARM_OUT_OF_RANGE / NO_CONVERGENCE from your numbers, and a SHACL-SPARQL shape cross-checks every joint angle against its joint's limits (`JOINT_LIMIT_VIOLATION`).

**Task 4 FAQ**
- `python` is not the taica-hw3 environment → `PYTHON=~/miniconda3/envs/taica-hw3/bin/python bash semantic/run_task4.sh`
- Jena download fails → manually extract apache-jena-4.10.0 and `export JENA_HOME=<path>` before running
- S1 reports STRUCTURE violations → open `output/ta-validation.ttl`; each `sh:resultMessage` tells you which property/typing is missing (a bare `0.0892` instead of `"0.0892"^^xsd:double` is the classic one)
- S2 FAILs → reasoning did not derive; check your axiom uses `owl:hasValue "OUT_OF_REACH"` exactly (case-sensitive) and that you did not assert memberships by hand
- S4 FAILs → your `sh:message` must START with `ARM_OUT_OF_RANGE:` / `NO_CONVERGENCE:` — the grader matches the prefix

## Grading

| Item | Points |
|---|---|
| Task 1: FK correctness (FK 10 + Jacobian 10, TA test cases) | 20 |
| Task 2: IK correctness (TA test cases, default arguments only) | 40 |
| Task 3: Transporter reward over 10 test episodes | 10 |
| Task 4: S1 grounding structure 10 + S2 reasoning 6 + S3 problem detection 6 + S4 SHACL vs faulty trace 8 | 30 |
| **Total** | **100** |

## Submission

1. `fk.py` (with `your_fk` completed)
2. `ik.py` (with `your_ik` completed)
3. `semantic/ground_execution.py` (with both TODO functions completed)
4. `semantic/reasoning.ttl` (with the `OutOfReachIKComputation` axiom completed)
5. `semantic/shapes.ttl` (with the two problem shapes completed)
6. A short report: screenshots of all four tasks, plus an explanation of what your SHACL validation discovered in `output/validation.ttl` and in the TA faulty trace — and why the OWL-derived classes (symbols) agree with the SHACL findings (numbers)

> Note: `semantic/output/`, `semantic/store/`, and `semantic/.cache/` are auto-generated — do not submit them.

## Reference

- https://github.com/google-research/ravens
- https://automaticaddison.com/the-ultimate-guide-to-jacobian-matrices-for-robotics/
- Apache Jena / TDB2: https://jena.apache.org/documentation/tdb2/
