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
| 4 | Semantic Knowledge + Triple Store | 2 functions in `semantic/ground_kinematics.py` + `semantic/queries/q3_interop_compare.rq` | `bash semantic/run_task4.sh` | 30 |

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

Turn the *numbers* from Task 1/2 into *semantics*: represent the robot specification (D-H parameters, joint limits, DoF) and the kinematic results (FK poses, IK statuses) as RDF using the shared vocabulary, run OWL reasoning, load everything into a TDB2 triple store, and query it with SPARQL — side by side with a **UR10 knowledge graph independently produced by the TA**.

```
your UR5 pipeline ──ground──> robot_graph.ttl ──┐
                                                ├─> OWL reasoning ─> TDB2 store ─> SPARQL
TA's UR10 pipeline (provided) ta-robot-graph.ttl┘
```

**Step 4-1. Understand the shared vocabulary.** Open [semantic/ontology/hw3-ontology.ttl](semantic/ontology/hw3-ontology.ttl):
- All classes/properties are defined in the namespace `http://taica.course/hw3/ontology#` (prefix `hw3:`)
- The three **shared targets** (`hw3:target_near` / `target_mid` / `target_far`) are the join keys for cross-graph comparison
- `hw3:SolvedIKComputation` is an **inference-defined** class: no program ever asserts it directly; the OWL reasoner derives it from "`IKComputation` and `hasIKStatus "SOLVED"`"

Then open [semantic/ontology/ta-robot-graph.ttl](semantic/ontology/ta-robot-graph.ttl) (do not modify): results the TA published for the same targets, using a different arm (UR10) and a different IK program.

**Step 4-2. Implement the grounding (2 functions).** Open [semantic/ground_kinematics.py](semantic/ground_kinematics.py):
- `fk_result_to_triples()` is **already implemented** as a worked example of how to write triples — read it first
- TODO 1 `robot_spec_to_triples()`: ground the UR5's D-H parameters / joint limits / DoF into triples
- TODO 2 `ik_result_to_triples()`: ground the IK result for each shared target into triples
- Notes: float literals must be written as `"..."^^xsd:double`; `solvesForTarget` must point to the shared target URI in the `hw3:` namespace (if you write it in `stu:`, the cross-graph join in Q3 will not find your results)

**Step 4-3. Complete the interoperability query.** Open [semantic/queries/q3_interop_compare.rq](semantic/queries/q3_interop_compare.rq) and complete the SPARQL query following the hints: for every shared target, list **each robot's IK status** (3 targets × 2 robots = 6 rows). q1 and q2 are provided — read them before writing q3.

**Step 4-4. Run and score with one command.**

```bash
conda activate taica-hw3
bash semantic/run_task4.sh                # uses your your_fk / your_ik
# Before finishing Task 1/2 you can preview the pipeline with:
# bash semantic/run_task4.sh --reference
```

The script runs 7 steps: toolchain check → prepare Jena/TDB2 → grounding → OWL reasoning (produces `semantic/output/inferred_graph.ttl`) → load the triple store (`semantic/store/`) → run q1–q3 (results saved to `semantic/output/q*.csv`) → scoring.

Expected output at the end:

```
  [S1] q1 robot summary ................ OK  (+4)
  [S1] DH parameters (6 / 6 joints) ..... OK (+6)
  [S2] IK status of shared targets (3/3)  OK (+6)
  [S2] q2 inferred SolvedIKComputation . OK  (+4)
  [S3] q3 interop comparison matrix .... OK  (+10)
  Your Task 4 Score : 30.0 / 30.0
```

The correct Q3 result showcases the point of interoperability: `target_mid` is `OUT_OF_REACH` for your UR5 but `SOLVED` for the TA's UR10 — two pipelines that have never seen each other's code can answer "which target can only the UR10 reach?" through the shared vocabulary alone.

**Task 4 FAQ**
- `python` is not the taica-hw3 environment → `PYTHON=~/miniconda3/envs/taica-hw3/bin/python bash semantic/run_task4.sh`
- Jena download fails → manually extract apache-jena-4.10.0 and `export JENA_HOME=<path>` before running
- q2 is empty → reasoning did not take effect; check that the `hasIKStatus` literal is exactly `"SOLVED"` (case-sensitive, no extra whitespace)

---

## Bonus Demo. Semantic Gate (not graded, recommended)

Task 4's reasoning plugged back into Task 3's simulator: with `SEMANTIC_AUDIT=1`, every Ravens pick-and-place action passes a semantic audit before execution — the pick target must be derived by the reasoner as `hw3:ExecutableGraspTarget` (semantically graspable **and** kinematically reachable by IK), otherwise the action is refused with an explanation:

```bash
conda activate taica-hw3
python semantic/demo_semantic_gate.py
```

Three demo cases: pick the block (ALLOW, reward 1.0), pick the fixture (REFUSE: semantic exclusion), pick an empty spot outside the workspace (REFUSE: no known object).

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
3. `semantic/ground_kinematics.py` (with the 2 TODO functions completed)
4. `semantic/queries/q3_interop_compare.rq` (completed)
5. A short report: screenshots of all four tasks, plus an explanation based on your Task 4 query results of "why `target_mid` is semantically the same target for both arms, yet geometrically reachable by only one of them"

> Note: `semantic/output/`, `semantic/store/`, and `semantic/.cache/` are auto-generated — do not submit them.

## Reference

- https://github.com/google-research/ravens
- https://automaticaddison.com/the-ultimate-guide-to-jacobian-matrices-for-robotics/
- Apache Jena / TDB2: https://jena.apache.org/documentation/tdb2/
