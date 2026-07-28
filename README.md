# HW3 — Robot Manipulation × Semantic Robot Knowledge

NYCU Physical AI / TAICA — UR5 Kinematics + Transporter Network + Semantic Knowledge Graph

## Learning Objectives

- **Forward Kinematics (FK)**: Understand and implement forward kinematics for a 6-DoF robot arm using D-H parameters, including end-effector pose and Jacobian computation.
- **Inverse Kinematics (IK)**: Understand and implement iterative inverse kinematics using Jacobian-based methods to compute joint configurations for a target end-effector pose.
- **Application of IK in Robot Manipulation**: Understand how inverse kinematics is integrated into a complete manipulation pipeline by applying the implemented IK solver to the Transporter Network block insertion task (prepick → grasp → preplace → insertion). IK is a component of a larger robotic system, not an isolated mathematical function.
- **Semantic Representation and Interoperability with a Triple Store**: Represent robot specifications and kinematic results using the shared robotics vocabulary `<http://taica.course/hw3/ontology#>`, store them in an RDF triple store, and query them through SPARQL. Experience how a common semantic representation enables independently developed robotics programs to share, query, compare, and reuse robot knowledge.

## Overview

| Task | Content | Files you edit | Verification command | Points |
|---|---|---|---|---|
| 1 | Forward Kinematics | `fk.py` → `your_fk()` | `python fk.py` | 20 |
| 2 | Inverse Kinematics | `ik.py` → `your_ik()` | `python ik.py` | 40 |
| 3 | Transporter Network | (integration, no code change) | `python ravens/test.py ...` | 10 |
| 4 | Semantic Knowledge + Triple Store | 1 function in `semantic/ground_task1_fk.py` + 1 function in `semantic/ground_task2_ik.py` + `semantic/queries/q3_interop_compare.rq` | `bash semantic/run_task4.sh` | 30 |

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

The first run of Task 4 automatically downloads Apache Jena 4.10.0 (~30 MB, including the TDB2 triple store command-line tools). It is cached under `semantic/.cache/` and works offline afterwards.

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

## Task 4. Semantic Robot Knowledge and Triple Store (30 points)

Turn the *numbers* from Tasks 1–3 into *semantics*: the shared vocabulary `<http://taica.course/hw3/ontology#>` defines concepts that **evaluate all three tasks** — FK correctness, IK solvability, and insertion success — as machine-readable facts. Each task has its own grounding script producing its own knowledge graph; OWL reasoning then derives one evaluation class per task, everything is loaded into a TDB2 triple store, and SPARQL reads the evaluation back out — side by side with a **UR10 knowledge graph independently produced by the TA**.

```
ground_task1_fk.py        ──> task1_fk_graph.ttl        ─┐   Task 1 -> hw3:PassedFKComputation
ground_task2_ik.py        ──> task2_ik_graph.ttl        ─┤   Task 2 -> hw3:SolvedIKComputation
ground_task3_insertion.py ──> task3_insertion_graph.ttl ─┼─> OWL reasoning ─> TDB2 store ─> SPARQL
TA's UR10 graph (provided)    ta-robot-graph.ttl        ─┘   Task 3 -> hw3:SuccessfulEpisode
```

**Reusability across groups**: your instances live in your own namespace `http://taica.course/hw3/data/<group-id>#` (derived from `--group`), while every group shares the `hw3:` vocabulary and the same target URIs. Any number of submissions can therefore be merged into one triple store without URI collisions, and the same queries compare everyone's results — you can load another group's graphs next to yours and study their design.

**Step 4-1. Understand the shared vocabulary.** Open [semantic/ontology/hw3-ontology.ttl](semantic/ontology/hw3-ontology.ttl):
- Design rule: **reuse existing vocabularies wherever possible** — robots are `cora:Robot` (IEEE 1872 CORA), joints are `soma:RevoluteJoint`, poses are `soma:6DPose`, episodes are `soma:Episode` (SOMA/EASE), aligned to DUL upper-level terms; `hw3:` only mints what no standard covers (kinematic computations, D-H parameters, evaluation statuses)
- The three **shared targets** (`hw3:target_near` / `target_mid` / `target_far`) are the join keys for cross-graph comparison
- Section 4 defines one **inference-defined evaluation class per task** (`PassedFKComputation`, `SolvedIKComputation`, `SuccessfulEpisode`): no program ever asserts them directly; the OWL reasoner derives membership from the grounded statuses

Then open [semantic/ontology/ta-robot-graph.ttl](semantic/ontology/ta-robot-graph.ttl) (do not modify): results the TA published for the same targets, using a different arm (UR10) and a different IK program.

**Step 4-2. Implement the grounding (2 functions across 2 files).**

| File | Grounds | Your work |
|---|---|---|
| [semantic/ground_task1_fk.py](semantic/ground_task1_fk.py) | robot spec + FK evaluation vs ground truth (pose/Jacobian errors, PASS/FAIL) | TODO `robot_spec_to_triples()`; `fk_result_to_triples()` is the **worked example** — read it first |
| [semantic/ground_task2_ik.py](semantic/ground_task2_ik.py) | IK evaluation on the 3 shared targets (status + residual) | TODO `ik_result_to_triples()` |
| [semantic/ground_task3_insertion.py](semantic/ground_task3_insertion.py) | insertion episodes from the Task 3 results pkl (reward, SUCCESS/FAILURE) | none (TA-provided) — but it needs you to have **run Task 3** so `ravens/test.py` has written `block-insertion-easy-transporter-*.pkl` |

Notes: float literals must be written as `"..."^^xsd:double`; `solvesForTarget` must point to the shared target URI in the `hw3:` namespace (if you write it in `stu:`, the cross-graph join in Q3 will not find your results).

**Step 4-3. Complete the interoperability query.** Open [semantic/queries/q3_interop_compare.rq](semantic/queries/q3_interop_compare.rq) and complete the SPARQL query following the hints: for every shared target, list **each robot's IK status** (3 targets × 2 robots = 6 rows; the same query automatically scales to N robots when more groups' graphs are loaded). q1, q2, and q4 are provided — read them before writing q3.

**Step 4-4. Run and score with one command.**

```bash
conda activate taica-hw3
bash semantic/run_task4.sh --group <your-group-id>   # uses your your_fk / your_ik
# Before finishing Task 1/2 you can preview the pipeline with:
# bash semantic/run_task4.sh --reference
```

The script runs 7 steps: toolchain check → prepare Jena/TDB2 → the three grounding scripts → OWL reasoning (produces `semantic/output/inferred_graph.ttl`) → load the triple store (`semantic/store/`) → run q1–q4 (results saved to `semantic/output/q*.csv`) → scoring.

Expected output at the end (q4 is the semantic evaluation report of all three tasks):

```
---- q4_task_evaluation_report ----
| hw3:PassedFKComputation | 3  |
| hw3:SolvedIKComputation | 1  |
| hw3:SuccessfulEpisode   | 10 |

  [S1] q1 robot summary ................ OK  (+2)
  [S1] DH parameters (6 / 6 joints) .... OK  (+6)
  [S2] Task 1 FK evaluation (3/3 PASS) . OK  (+4.0)
  [S2] Task 2 IK statuses (3/3) ........ OK  (+4.0)
  [S2] q2 inferred SolvedIKComputation . OK  (+2)
  [S2] Task 3 episodes (10 SUCCESS) .... OK  (+2)
  [S3] q3 interop comparison matrix .... OK  (+10)
  Your Task 4 Score : 30.0 / 30.0
```

The correct Q3 result showcases the point of interoperability: `target_mid` is `OUT_OF_REACH` for your UR5 but `SOLVED` for the TA's UR10 — two pipelines that have never seen each other's code can answer "which target can only the UR10 reach?" through the shared vocabulary alone.

**Task 4 FAQ**
- `python` is not the taica-hw3 environment → `PYTHON=~/miniconda3/envs/taica-hw3/bin/python bash semantic/run_task4.sh`
- Jena download fails → manually extract apache-jena-4.10.0 and `export JENA_HOME=<path>` before running
- q2 is empty → reasoning did not take effect; check that the `hasIKStatus` literal is exactly `"SOLVED"` (case-sensitive, no extra whitespace)
- Task 3 episodes item FAILs → run Task 3 first; `ground_task3_insertion.py` reads the pkl that `ravens/test.py` writes under `ravens/`

---

## Grading

| Item | Points |
|---|---|
| Task 1: FK correctness (FK 10 + Jacobian 10, TA test cases) | 20 |
| Task 2: IK correctness (TA test cases, default arguments only) | 40 |
| Task 3: Transporter reward over 10 test episodes | 10 |
| Task 4: S1 spec grounding 10 + S2 result grounding 10 + S3 SPARQL interop 10 | 30 |
| **Total** | **100** |

## Submission

1. `fk.py` (with `your_fk` completed)
2. `ik.py` (with `your_ik` completed)
3. `semantic/ground_task1_fk.py` (with `robot_spec_to_triples()` completed)
4. `semantic/ground_task2_ik.py` (with `ik_result_to_triples()` completed)
5. `semantic/queries/q3_interop_compare.rq` (completed)
6. A short report: screenshots of all four tasks, plus an explanation based on your Task 4 query results of "why `target_mid` is semantically the same target for both arms, yet geometrically reachable by only one of them"

> Note: `semantic/output/`, `semantic/store/`, and `semantic/.cache/` are auto-generated — do not submit them.

## Reference

- https://github.com/google-research/ravens
- https://automaticaddison.com/the-ultimate-guide-to-jacobian-matrices-for-robotics/
- Apache Jena / TDB2: https://jena.apache.org/documentation/tdb2/
