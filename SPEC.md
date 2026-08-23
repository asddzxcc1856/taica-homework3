# HW3 Student Specification — UR5 Kinematics, FSM Manipulation, and Semantic Knowledge Graphs

NYCU Physical AI / TAICA
**Total: 100 points**

For a more visual walkthrough, see the [student guide](docs/hw3-student-guide.html). This document is the authoritative task specification.

## Learning objectives

By completing this homework, you will:

1. Implement forward kinematics for a 6-DoF robot arm using classic D-H parameters, including an end-effector pose and a 6×6 geometric Jacobian.
2. Implement iterative Jacobian-based inverse kinematics.
3. Integrate your FK and IK into a deterministic UR5 pick-and-place pipeline.
4. Ground robot specifications and kinematic execution data as structured RDF using standard robotics ontologies.
5. Validate execution semantics with SHACL.

## Task overview

| Task | Content | Files you edit | Verification | Points |
|---|---|---|---|---:|
| 1 | Forward Kinematics | `fk.py` — `your_fk()` | `python fk.py` | 20 |
| 2 | Inverse Kinematics | `ik.py` — `your_ik()` | `python ik.py` | 40 |
| 3 | FSM Manipulation Pipeline | No code change | `python fsm_task.py` | 10 |
| 4 | Semantic Grounding + SHACL | `semantic/ground_execution.py`, `semantic/shapes.ttl` | `bash semantic/run_task4.sh` | 30 |

---

## 1. Environment setup

### Requirements

| Component | Requirement |
|---|---|
| Operating system | Linux / Ubuntu 20.04 or later recommended |
| Python | Python 3.7 in a conda environment |
| Python packages | `pybullet`, `numpy`, `scipy` |
| Java | JDK 11 or later for Task 4 |
| Disk space | Less than 1 GB |

Create and activate the environment:

```bash
conda create --name taica-hw3 python=3.7 -y
conda activate taica-hw3
pip install pybullet numpy scipy
```

Install Java for Task 4:

```bash
sudo apt-get -y install openjdk-11-jdk
java -version && javac -version
```

Run all commands from the repository root. The first Task 4 run downloads Apache Jena 4.10.0 into `semantic/.cache/`; it is reused on later runs.

---

## 2. Task 1 — Forward Kinematics (20 points)

Open `fk.py` and implement:

```python
your_fk(DH_params, q, base_pos)
```

The function takes six sets of D-H parameters, six joint angles, and the robot base position. It must return:

- `pose_7d`: `[x, y, z, qx, qy, qz, qw]`
- `jacobian`: a 6×6 geometric Jacobian

Use the provided `get_ur5_DH_params()` table. It follows the URDF in this repository and may differ from other published UR5 specifications.

Requirements:

- Use the classic D-H convention.
- Do not call PyBullet APIs to calculate FK or the Jacobian.
- Do not change the supplied adjustment block at the end of the function.
- For each revolute joint, use the preceding frame axis: the linear Jacobian component is `z(i-1) × (p_end − p(i-1))`, and the angular component is `z(i-1)`.

Verify with:

```bash
python fk.py
python fk.py -g         # optional GUI
python fk.py -g -vp     # GUI with pose visualization
```

The easy, medium, and hard visible test cases should report zero errors for both pose and Jacobian. Hidden test cases are used for grading.

---

## 3. Task 2 — Inverse Kinematics (40 points)

Open `ik.py` and implement:

```python
your_ik(robot_id, new_pose, base_pos, ...)
```

Use your own `your_fk()` and Jacobian in an iterative solver. Damped least squares or a pseudo-inverse approach is appropriate.

Requirements:

- Solve for both position and orientation error.
- Use stable defaults for damping, step rate, iteration count, and stopping threshold. Grading calls the function with default arguments.
- Respect the supplied joint limits.
- You may inspect `pybullet_ik()` as a reference, but you must not call PyBullet IK APIs in your implementation.

Verify with:

```bash
python ik.py
```

All visible test cases should have zero errors; mean positional error should be in the 10⁻³ range. If the solver is unstable, review damping, step size, stopping conditions, and warm starts.

---

## 4. Task 3 — FSM Manipulation Pipeline (10 points)

This task uses your FK and IK functions without requiring changes to `fsm_task.py`. The provided deterministic finite state machine runs ten seeded UR5 pick-and-place episodes:

```text
MOVE_TO_PREPICK → DESCEND_TO_PICK → GRASP → LIFT
  → MOVE_TO_PREPLACE → DESCEND_TO_PLACE → RELEASE → RETREAT
  → VERIFY → SUCCESS / FAILURE
```

Every motion state applies two checks:

| Check | Requirement | Failure |
|---|---|---|
| IK validation | The achieved end-effector position is within 3 cm of the commanded target. | `IK_MISS in <STATE>` |
| FK validation | Your FK on measured joint angles agrees with the simulator's end-effector position within 1 cm. | `FK_MISMATCH in <STATE>` |

`DESCEND_TO_PICK` continues until the suction gripper contacts the block. `GRASP` and `RELEASE` toggle the suction constraint. During `VERIFY`, the block must be within 6 cm of the goal marker.

Run:

```bash
python fsm_task.py
python fsm_task.py -g    # optional GUI
```

A full solution produces ten successful episodes and a score of `10.000 / 10.000`. Other possible failures include `NO_CONTACT`, `GRASP_FAILED`, and `PLACE_MISS`.

---

## 5. Task 4 — Semantic Grounding (REUSE) + SHACL Validation (30 points)

Convert the numerical FK/IK execution process into structured RDF, then use SHACL to identify invalid or problematic executions.

### 5.1 Reuse standard vocabularies

Read `semantic/ontology/hw3-ontology.ttl`. Reuse the following representations:

| Concept | Representation |
|---|---|
| Robot | `cora:Robot` (IEEE 1872 CORA) |
| Joint and joint state | `soma:RevoluteJoint`, `soma:JointState` |
| Pose | `soma:6DPose`, including a `pos:Position` and quaternion orientation |
| Units | QUDT IRIs such as `unit:M` and `unit:RAD` |
| Numeric values | Typed `xsd:double` literals on structured RDF nodes |

Do not encode poses or joint configurations as JSON strings. Use the serializers in `semantic/common.py`, especially `pose_to_ttl` and `joint_config_to_ttl`.

### 5.2 Grounding implementation

Open `semantic/ground_execution.py`.

| Function | Purpose | Status |
|---|---|---|
| `fk_computation_to_triples()` | Grounds an FK execution, its input configuration, EE pose, and errors | Worked example |
| `robot_spec_to_triples()` | Grounds all six joints, D-H parameters, and limits | TODO |
| `ik_computation_to_triples()` | Grounds status, residual, target distance, and structured IK joint configuration | TODO |

The script executes your FK on three test cases and your IK on the fixed near, mid, and far targets. It writes the semantic execution graph to `semantic/output/data.ttl`.

### 5.3 SHACL implementation

Open `semantic/shapes.ttl`. The FK accuracy shape is a worked example: pose error greater than `0.005` produces `FK_INACCURATE`.

Add two shapes targeted at `hw3:IKComputation`:

1. `hw3:hasTargetDistance` must be at most `0.90`; the message must start with `ARM_OUT_OF_RANGE:`.
2. `hw3:hasResidual` must be at most `0.02`; the message must start with `NO_CONVERGENCE:`.

Use `sh:maxInclusive`, not `sh:maxExclusive`. Values exactly equal to 0.90, 0.02, and 0.005 are conforming.

### 5.4 Run and score

```bash
conda activate taica-hw3
bash semantic/run_task4.sh --group <your-group-id>
```

The script:

1. Checks the toolchain and Apache Jena.
2. Generates `data.ttl` through grounding.
3. Runs your shapes against your data and the 24-record TA dataset.
4. Runs the full TA shapes against your data.
5. Scores the validation output against `semantic/ta-answer-key.json`.

With a correct implementation, `target_mid` and `target_far` are flagged `ARM_OUT_OF_RANGE`, while `target_near` remains clean. The TA dataset contains 24 records, including exact-boundary values; its per-record flags must match the answer key exactly.

For structural violations, inspect `semantic/output/ta-validation.ttl`. For answer-key mismatches, the scorer prints `expected [...] , got [...]` for each incorrect record.

---

## 6. Grading

| Item | Points |
|---|---:|
| Task 1: FK correctness (pose 10 + Jacobian 10) | 20 |
| Task 2: IK correctness | 40 |
| Task 3: Ten seeded FSM pick-and-place episodes | 10 |
| Task 4: Grounding structure (12) + problem detection (8) + TA dataset validation (10) | 30 |
| **Total** | **100** |

## 7. Submission

Submit:

1. `fk.py` with `your_fk()` completed.
2. `ik.py` with `your_ik()` completed.
3. `semantic/ground_execution.py` with both TODO functions completed.
4. `semantic/shapes.ttl` with both required problem shapes completed.
5. A short report with screenshots for all four tasks and an explanation of findings in `output/validation.ttl` and `output/probe-validation.ttl`.

Do not submit generated directories: `semantic/output/`, `semantic/store/`, or `semantic/.cache/`.
