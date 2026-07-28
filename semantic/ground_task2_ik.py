# -*- coding: utf-8 -*-
"""Task 4 / Part 2 — Semantic evaluation of Task 2 (Inverse Kinematics).

Runs your_ik on the three SHARED targets (hw3:target_near / target_mid /
target_far), classifies each outcome (SOLVED / OUT_OF_REACH /
NO_CONVERGENCE), and grounds the IK evaluation into RDF
-> semantic/output/task2_ik_graph.ttl.

The OWL reasoner later derives hw3:SolvedIKComputation (the Task 2
evaluation class) from the grounded hasIKStatus, and the shared target
URIs make your results directly comparable with the TA's UR10 graph.

STUDENT TODO in this file: ik_result_to_triples()

Run (inside the taica-hw3 conda environment):
    python semantic/ground_task2_ik.py --group <your group id>
    python semantic/ground_task2_ik.py --reference    # preview before Task 2 is done
"""

import json

import numpy as np

import common
from common import HOME_JOINTS, SHARED_TARGETS

from fk import your_fk, get_ur5_DH_params  # noqa: E402
from ik import your_ik, pybullet_ik  # noqa: E402

OUTPUT_FILE = 'task2_ik_graph.ttl'

GROUP_ID = 'student-group-00'


# ---------------------------------------------------------------------------
# STUDENT TODO: IK evaluation result -> triples
# ---------------------------------------------------------------------------
def ik_result_to_triples(target_uri, joint_config, ik_status, residual):
    """Ground one IK result into triples; return Turtle lines (list of str).

    Must include one IK instance (suggested URI: stu:ik_<target_uri>) of
    type hw3:IKComputation, carrying:
      - hw3:producedBy         "<GROUP_ID>"
      - hw3:computedForRobot   stu:my_ur5
      - hw3:solvesForTarget    hw3:<target_uri>   <-- note: hw3: namespace!
                                The shared target URI is the join key for
                                cross-graph comparison; writing it in stu:
                                means Q3 will never find your results
      - hw3:hasIKStatus        "SOLVED" / "OUT_OF_REACH" / ... (string)
      - hw3:hasResidual        residual (double, e.g. "0.003"^^xsd:double)
      - hw3:hasJointConfiguration  JSON string (see fk_result_to_triples
                                in ground_task1_fk.py)

    Hint: compare with ta:ik_ta_target_near in ontology/ta-robot-graph.ttl.
    """
    lines = []

    # ------------------------- your code -------------------------

    raise NotImplementedError('TODO: implement ik_result_to_triples()')

    # --------------------------------------------------------------

    return lines


# ---------------------------------------------------------------------------
# TA-provided: evaluation flow
# ---------------------------------------------------------------------------
def main():
    args = common.make_arg_parser(__doc__).parse_args()
    global GROUP_ID
    GROUP_ID = args.group

    robot, base_pos = common.connect_sim()
    dh_params = get_ur5_DH_params()
    home_quat = np.asarray(robot.get_eef_pose())[3:]

    lines = []
    for target in SHARED_TARGETS:
        target_pose_7d = list(target['position']) + list(home_quat)
        common.reset_arm(robot, HOME_JOINTS)

        if args.reference:
            joints = list(np.asarray(
                pybullet_ik(robot.robot_id, target_pose_7d))[:6])
            eef_pos = common.sim_eef_pose(robot, joints)[:3]
        else:
            joints = list(your_ik(robot.robot_id, target_pose_7d,
                                  base_pos=base_pos))
            eef_pos, _ = your_fk(dh_params, joints, base_pos)
            eef_pos = eef_pos[:3]

        status, residual = common.classify_ik_result(
            eef_pos, target['position'], base_pos)
        print('[IK-EVAL] {} -> status={}, residual={:.4f} m'.format(
            target['uri'], status, residual))
        lines += ik_result_to_triples(
            target['uri'], joints, status, round(residual, 5))

    common.write_graph(OUTPUT_FILE, lines, GROUP_ID, 'ground_task2_ik.py')

    import pybullet as p
    p.disconnect()


if __name__ == '__main__':
    main()
