# -*- coding: utf-8 -*-
"""Task 4 / Part 1 — Semantic evaluation of Task 1 (Forward Kinematics).

Runs your_fk on test cases from test_case/fk_test_case_easy.json, compares
the results against the course ground truth (pose error / Jacobian error /
PASS-FAIL status), and grounds BOTH the robot specification and the FK
evaluation into RDF -> semantic/output/task1_fk_graph.ttl.

The OWL reasoner later derives hw3:PassedFKComputation (the Task 1
evaluation class) from the grounded hasEvaluationStatus.

STUDENT TODO in this file: robot_spec_to_triples()
(fk_result_to_triples() is fully implemented as the worked example.)

Run:
    python semantic/ground_task1_fk.py --group <your group id>
    python semantic/ground_task1_fk.py --reference    # preview before Task 1 is done
"""

import json
import os

import numpy as np

import common
from common import (FK_JACOBIAN_ERROR_THRESH, FK_POSE_ERROR_THRESH,
                    HW_ROOT, JOINT_LIMITS)

from fk import your_fk, get_ur5_DH_params  # noqa: E402

OUTPUT_FILE = 'task1_fk_graph.ttl'
NUM_CASES = 3  # number of FK test cases to evaluate and ground

GROUP_ID = 'student-group-00'


# ---------------------------------------------------------------------------
# Worked example (already implemented): FK evaluation result -> triples
# ---------------------------------------------------------------------------
def fk_result_to_triples(case_index, joint_config, eef_pose_7d,
                         pose_error, jacobian_error, eval_status):
    """(Example, complete) Convert one evaluated FK result into Turtle lines.

    This grounds the EVALUATION of Task 1: the computed pose plus its errors
    against the course ground truth, and a PASS/FAIL status. The reasoner
    later derives hw3:PassedFKComputation from the status.

    Produces (STRUCTURED representation — no JSON-string literals):
        stu:fk_case_0 a hw3:FKComputation ;
            hw3:producedBy "<group id>" ;
            hw3:computedForRobot stu:my_ur5 ;
            hw3:hasInputJointConfiguration stu:fk_case_0_q ;   # object node
            hw3:hasEndEffectorPose stu:fk_case_0_ee ;          # object node
            hw3:hasPoseError "0.00001"^^xsd:double ;
            hw3:hasJacobianError "0.00002"^^xsd:double ;
            hw3:hasEvaluationStatus "PASS" .
        stu:fk_case_0_q a hw3:JointConfiguration ;             # 6x soma:JointState,
            hw3:hasJointState stu:fk_case_0_q_js1 , ... .      # each pointing at
        stu:fk_case_0_q_js1 a soma:JointState ;                # a joint individual
            hw3:isStateOfJoint stu:my_ur5_joint1 ;
            qudt:hasUnit unit:RAD ;
            soma:hasJointPosition "-3.14"^^xsd:double .
        stu:fk_case_0_ee a soma:6DPose ;                       # pos:Position +
            hw3:hasPositionComponent ... ;                     # quaternion, QUDT
            hw3:hasOrientationComponent ... .                  # units (see common.py)

    Three conventions your own functions must follow as well:
      1. Instances live in the stu: namespace; classes/properties in hw3:
      2. Numeric values are typed literals on STRUCTURED nodes (built with
         common.pose_to_ttl / common.joint_config_to_ttl) — never
         JSON-string literals; units are QUDT IRIs (unit:M / unit:RAD)
      3. Every instance carries hw3:producedBy for provenance queries
    """
    node = 'stu:fk_case_{}'.format(case_index)
    lines = [
        '{} a hw3:FKComputation ;'.format(node),
        '    hw3:producedBy "{}" ;'.format(GROUP_ID),
        '    hw3:computedForRobot stu:my_ur5 ;',
        '    hw3:hasInputJointConfiguration {}_q ;'.format(node),
        '    hw3:hasEndEffectorPose {}_ee ;'.format(node),
        '    hw3:hasPoseError "{}"^^xsd:double ;'.format(pose_error),
        '    hw3:hasJacobianError "{}"^^xsd:double ;'.format(jacobian_error),
        '    hw3:hasEvaluationStatus "{}" .'.format(eval_status),
        '',
    ]
    lines += common.joint_config_to_ttl('{}_q'.format(node), joint_config)
    lines += common.pose_to_ttl('{}_ee'.format(node), eef_pose_7d)
    return lines


# ---------------------------------------------------------------------------
# STUDENT TODO: robot specification -> triples
# ---------------------------------------------------------------------------
def robot_spec_to_triples(dh_params, joint_limits):
    """Ground the UR5 specification into triples; return Turtle lines (list of str).

    Must include:
      1. A robot instance stu:my_ur5 of type cora:Robot (the IEEE 1872
         CORA class — reused directly, NOT an hw3: invention), carrying
         hw3:producedBy "<GROUP_ID>" and hw3:hasDoF 6, and linked to the
         6 joint instances via hw3:hasJoint
      2. Six joint instances stu:my_ur5_joint1 ~ joint6 of type
         soma:RevoluteJoint (reused from SOMA), each with:
           - hw3:jointIndex     (1~6, integer)
           - hw3:dh_a           (double, meters)
           - hw3:dh_d           (double, meters)
           - hw3:dh_alpha       (double, radians)
           - hw3:hasJointLowerLimit / hw3:hasJointUpperLimit (double, radians)

    Hints:
      - dh_params is the return value of get_ur5_DH_params()
        (6 dicts with keys a / d / alpha)
      - Float literals MUST be xsd:double (a bare 0.0892 in Turtle is
        xsd:decimal, which conflicts with the property range):
            '    hw3:dh_a "{}"^^xsd:double ;'.format(round(value, 6))
      - See fk_result_to_triples() and ontology/ta-robot-graph.ttl for
        the writing style (the TA's UR10 graph is exactly what "another
        program's version" of this function produced)
    """
    lines = []

    # ------------------------- your code -------------------------

    raise NotImplementedError('TODO: implement robot_spec_to_triples()')

    # --------------------------------------------------------------

    return lines


# ---------------------------------------------------------------------------
# TA-provided: evaluation flow
# ---------------------------------------------------------------------------
def main():
    args = common.make_arg_parser(__doc__).parse_args()
    global GROUP_ID
    GROUP_ID = args.group

    dh_params = get_ur5_DH_params()

    fk_file = os.path.join(HW_ROOT, 'test_case', 'fk_test_case_easy.json')
    with open(fk_file, 'r') as f:
        gt = json.load(f)
    cases = gt['joint_poses'][:NUM_CASES]
    gt_poses = gt['poses'][:NUM_CASES]
    gt_jacobians = gt['jacobian'][:NUM_CASES]

    robot, base_pos = (None, None)
    if args.reference:
        robot, base_pos = common.connect_sim()
    else:
        base_pos = [-0.2, 0.13, 0.6]  # ur5Env default base position

    lines = robot_spec_to_triples(dh_params, JOINT_LIMITS)

    for i, q in enumerate(cases):
        if args.reference:
            # Preview mode: read the pose from the simulator. Note the sim
            # frame differs slightly from the DH ground truth, so statuses
            # here are NOT meaningful — implement your_fk for real results.
            pose = common.sim_eef_pose(robot, q)
            jacobian_error = -1.0
        else:
            pose, jacobian = your_fk(dh_params, q, base_pos)
            jacobian_error = round(float(np.linalg.norm(
                np.asarray(jacobian) - np.asarray(gt_jacobians[i]))), 6)

        pose_error = round(float(np.linalg.norm(
            np.asarray(pose) - np.asarray(gt_poses[i]))), 6)
        passed = (pose_error <= FK_POSE_ERROR_THRESH
                  and (jacobian_error < 0.0
                       or jacobian_error <= FK_JACOBIAN_ERROR_THRESH))
        status = 'PASS' if passed else 'FAIL'
        print('[FK-EVAL] case {} -> pose_err={:.6f} jac_err={:.6f} {}'.format(
            i, pose_error, jacobian_error, status))
        lines += fk_result_to_triples(
            i, q, list(pose), pose_error, jacobian_error, status)

    common.write_graph(OUTPUT_FILE, lines, GROUP_ID, 'ground_task1_fk.py')

    if args.reference and robot is not None:
        import pybullet as p
        p.disconnect()


if __name__ == '__main__':
    main()
