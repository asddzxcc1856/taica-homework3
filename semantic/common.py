# -*- coding: utf-8 -*-
"""Shared constants and helpers for the Task 4 grounding scripts (TA-provided).

The three per-task grounding scripts (ground_task1_fk.py, ground_task2_ik.py,
ground_task3_insertion.py) each produce their own knowledge graph, but they
all speak the same vocabulary <http://taica.course/hw3/ontology#> — that is
what lets one triple store and one set of SPARQL queries evaluate all three
tasks together.
"""

import argparse
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
HW_ROOT = os.path.abspath(os.path.join(HERE, '..'))
if HW_ROOT not in sys.path:
    sys.path.insert(0, HW_ROOT)

HW3_NS = 'http://taica.course/hw3/ontology#'


def stu_ns(group_id):
    """Per-group data namespace: http://taica.course/hw3/data/<group-id>#

    Reusability across submissions: every group publishes its instances
    under its OWN namespace while sharing the hw3: vocabulary and the
    shared target URIs. Any number of group graphs can therefore be loaded
    into one triple store without URI collisions, and one SPARQL query can
    compare every group's results (see q3, which generalizes from 2 robots
    to N robots automatically).
    """
    safe = ''.join(c if (c.isalnum() or c in '-_') else '-' for c in group_id)
    return 'http://taica.course/hw3/data/{}#'.format(safe)

OUTPUT_DIR = os.path.join(HERE, 'output')

SIM_TIMESTEP = 1.0 / 240.0
UR5_MAX_REACH = 0.90          # UR5 workspace radius (m); beyond => OUT_OF_REACH
SHOULDER_HEIGHT = 0.0892      # DH d1: shoulder height (m)
IK_SOLVED_THRESH = 0.02       # residual threshold for SOLVED (m)
FK_POSE_ERROR_THRESH = 0.005  # Task 1 pose error threshold (course value)
FK_JACOBIAN_ERROR_THRESH = 0.05  # Task 1 Jacobian error threshold (course value)

# Joint limits consistent with ik.py; grounded into triples in Task 4
JOINT_LIMITS = [
    [-3 * np.pi / 2, -np.pi / 2],   # joint1
    [-2.3562, -1.0],                # joint2
    [-17.0, 17.0],                  # joint3
    [-17.0, 17.0],                  # joint4
    [-17.0, 17.0],                  # joint5
    [-17.0, 17.0],                  # joint6
]

# Shared targets (exactly the same coordinates as hw3:target_* in the
# ontology; the URIs must also be the same set, otherwise SPARQL cannot
# join across graphs)
SHARED_TARGETS = [
    {'uri': 'target_near', 'position': [0.35, 0.28, 0.95]},
    {'uri': 'target_mid',  'position': [0.90, 0.13, 0.80]},
    {'uri': 'target_far',  'position': [1.80, 0.50, 0.95]},
]

HOME_JOINTS = (np.array([-1.0, -0.5, 0.5, -0.5, -0.5, 0.0]) * np.pi).tolist()


def make_arg_parser(description):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('--group', default='student-group-00',
                        help='provenance id written to hw3:producedBy')
    parser.add_argument('--reference', action='store_true',
                        help='use pybullet reference FK/IK instead of '
                             'your_fk/your_ik (pipeline smoke test only)')
    return parser


def connect_sim():
    """Start a DIRECT pybullet session with the course UR5; returns (robot, base_pos)."""
    import pybullet as p
    from pybullet_robot_envs.envs.ur5_envs.ur5_env import ur5Env

    physics_client_id = p.connect(p.DIRECT)
    p.resetSimulation()
    p.setPhysicsEngineParameter(numSolverIterations=150)
    p.setTimeStep(SIM_TIMESTEP)
    p.setGravity(0, 0, -9.8)

    robot = ur5Env(physics_client_id, use_IK=1)
    for _ in range(240):
        p.stepSimulation()
    return robot, list(robot._base_position)


def reset_arm(robot, joint_values):
    import pybullet as p
    joint_ids = list(robot._joint_name_to_ids.values())
    for jid, val in zip(joint_ids, joint_values):
        p.resetJointState(robot.robot_id, jid, val)


def sim_eef_pose(robot, joint_values):
    """Read the end-effector pose at given joint angles without side effects
    (reset -> read -> restore)."""
    import pybullet as p
    joint_ids = list(robot._joint_name_to_ids.values())
    saved = [p.getJointState(robot.robot_id, j)[0] for j in joint_ids]
    reset_arm(robot, joint_values)
    pose = np.asarray(robot.get_eef_pose())
    reset_arm(robot, saved)
    return pose


def classify_ik_result(eef_pos_after_ik, target_pos, base_pos):
    """Determine the IK status string from residual and workspace geometry."""
    target_pos = np.asarray(target_pos, dtype=float)
    shoulder = np.asarray(base_pos, dtype=float) + [0.0, 0.0, SHOULDER_HEIGHT]
    dist = float(np.linalg.norm(target_pos - shoulder))
    residual = float(np.linalg.norm(
        np.asarray(eef_pos_after_ik, dtype=float) - target_pos))

    if residual < IK_SOLVED_THRESH:
        return 'SOLVED', residual
    if dist > UR5_MAX_REACH:
        return 'OUT_OF_REACH', residual
    return 'NO_CONVERGENCE', residual


def write_graph(filename, lines, group_id, script_name):
    """Write a Turtle knowledge graph with the shared prefixes.

    The stu: prefix is bound to THIS group's namespace, so the same
    triple-writing code (stu:my_ur5, stu:ik_target_near, ...) yields
    group-unique URIs — submissions from different groups can be merged
    into one store and cross-queried.
    """
    header = [
        '@prefix hw3:  <{}> .'.format(HW3_NS),
        '@prefix stu:  <{}> .'.format(stu_ns(group_id)),
        '@prefix cora: <http://purl.org/ieee1872-owl/cora-bare#> .',
        '@prefix soma: <http://www.ease-crc.org/ont/SOMA.owl#> .',
        '@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .',
        '',
        '# Auto-generated by semantic/{}'.format(script_name),
        '# producedBy: {}'.format(group_id),
        '',
    ]
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, 'w') as f:
        f.write('\n'.join(header + lines) + '\n')
    print('[GROUND] knowledge graph written to {}'.format(path))
    return path
