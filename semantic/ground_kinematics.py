# -*- coding: utf-8 -*-
"""Task 4 — Semantic Robot Knowledge and Triple Store.

把「數值層」的機器人知識 (robot specification + kinematic results)
轉成共用語彙 <http://taica.course/hw3/ontology#> 的 RDF triples,
輸出 semantic/output/robot_graph.ttl,後續由 run_task4.sh:
    OWL 推理 (Java Jena) -> 載入 TDB2 triple store -> SPARQL 查詢 -> 評分

=============================================================================
你要做的事 (STUDENT TODO,共 2 個函式):
    1. robot_spec_to_triples() : 把 UR5 的 DH 參數 / 關節限制 / DoF 寫成 triples
    2. ik_result_to_triples()  : 把每個共用 target 的 IK 結果寫成 triples
fk_result_to_triples() 已完整實作,當作 triple 寫法的示範,請先讀懂它。
=============================================================================

執行 (需在 taica-hw3 conda 環境,且已完成 Task 1 的 your_fk 與 Task 2 的 your_ik):
    python semantic/ground_kinematics.py --group <你的組別代號>

尚未完成 Task 1/2 時,可先用參考解看整條 pipeline 的樣子:
    python semantic/ground_kinematics.py --reference
"""

import argparse
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
HW_ROOT = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, HW_ROOT)

import pybullet as p  # noqa: E402

from fk import your_fk, get_ur5_DH_params  # noqa: E402
from ik import your_ik, pybullet_ik  # noqa: E402
from pybullet_robot_envs.envs.ur5_envs.ur5_env import ur5Env  # noqa: E402

# ---------------------------------------------------------------------------
# 常數 (TA 提供,勿改)
# ---------------------------------------------------------------------------
HW3_NS = 'http://taica.course/hw3/ontology#'
STU_NS = 'http://taica.course/hw3/data/student#'

OUTPUT_TTL = os.path.join(HERE, 'output', 'robot_graph.ttl')

SIM_TIMESTEP = 1.0 / 240.0
UR5_MAX_REACH = 0.90          # UR5 工作空間半徑 (m),超過視為 OUT_OF_REACH
SHOULDER_HEIGHT = 0.0892      # DH d1: 肩關節高度 (m)
IK_SOLVED_THRESH = 0.02       # SOLVED 殘差門檻 (m)

# 與 ik.py 一致的關節限制,Task 4 會把它 ground 成 triples
JOINT_LIMITS = [
    [-3 * np.pi / 2, -np.pi / 2],   # joint1
    [-2.3562, -1.0],                # joint2
    [-17.0, 17.0],                  # joint3
    [-17.0, 17.0],                  # joint4
    [-17.0, 17.0],                  # joint5
    [-17.0, 17.0],                  # joint6
]

# 共用 target(與 ontology 的 hw3:target_* 完全相同的座標;
# URI 也必須用同一組,SPARQL 才能跨圖 join)
SHARED_TARGETS = [
    {'uri': 'target_near', 'position': [0.35, 0.28, 0.95]},
    {'uri': 'target_mid',  'position': [0.90, 0.13, 0.80]},
    {'uri': 'target_far',  'position': [1.80, 0.50, 0.95]},
]

HOME_JOINTS = (np.array([-1.0, -0.5, 0.5, -0.5, -0.5, 0.0]) * np.pi).tolist()


# ---------------------------------------------------------------------------
# 已完成的示範: FK 結果 -> triples
# ---------------------------------------------------------------------------
def fk_result_to_triples(case_index, joint_config, eef_pose_7d):
    """(示範,已完成) 把一筆 FK 結果轉成 Turtle 片段 (list of str).

    產出形如:
        stu:fk_case_0 a hw3:FKComputation ;
            hw3:producedBy "<group id>" ;
            hw3:computedForRobot stu:my_ur5 ;
            hw3:hasInputJointConfiguration "[...]" ;
            hw3:hasEndEffectorPose "[...]" .

    注意三件事,後面你自己寫的函式也要遵守:
      1. 實例放在 stu: namespace,類別/屬性用 hw3: namespace
      2. 數值列表用 JSON 字串 literal(語彙的 rdfs:comment 有規定格式)
      3. 每個實例都掛 hw3:producedBy 供 provenance 查詢
    """
    q_json = json.dumps([round(float(v), 6) for v in joint_config])
    pose_json = json.dumps([round(float(v), 6) for v in eef_pose_7d])
    return [
        'stu:fk_case_{} a hw3:FKComputation ;'.format(case_index),
        '    hw3:producedBy "{}" ;'.format(GROUP_ID),
        '    hw3:computedForRobot stu:my_ur5 ;',
        '    hw3:hasInputJointConfiguration "{}" ;'.format(
            q_json.replace('"', '\\"')),
        '    hw3:hasEndEffectorPose "{}" .'.format(
            pose_json.replace('"', '\\"')),
        '',
    ]


# ---------------------------------------------------------------------------
# STUDENT TODO 1: 機器人規格 -> triples
# ---------------------------------------------------------------------------
def robot_spec_to_triples(dh_params, joint_limits):
    """把 UR5 的規格 ground 成 triples,回傳 Turtle 片段 (list of str).

    必須包含:
      1. 機器人實例 stu:my_ur5,型別 hw3:RobotArm,
         掛上 hw3:producedBy "<GROUP_ID>"、hw3:hasDoF 6,
         並以 hw3:hasJoint 連到 6 個關節實例
      2. 6 個關節實例 stu:my_ur5_joint1 ~ joint6,型別 hw3:RevoluteJoint,
         每個都要有:
           - hw3:jointIndex     (1~6, integer)
           - hw3:dh_a           (double, 單位 m)
           - hw3:dh_d           (double, 單位 m)
           - hw3:dh_alpha       (double, 單位 rad)
           - hw3:hasJointLowerLimit / hw3:hasJointUpperLimit (double, rad)

    hint:
      - dh_params 是 get_ur5_DH_params() 的回傳值 (6 個 dict: a / d / alpha)
      - 浮點數 literal 必須是 xsd:double(Turtle 裸寫的 0.0892 是
        xsd:decimal,會與屬性值域衝突),寫法:
            '    hw3:dh_a "{}"^^xsd:double ;'.format(round(value, 6))
      - 參考 fk_result_to_triples() 與 ontology/ta-robot-graph.ttl 的寫法
        (助教的 UR10 圖就是這個函式「另一個程式的版本」的輸出)
    """
    lines = []

    # ------------------------- your code -------------------------

    raise NotImplementedError('TODO: implement robot_spec_to_triples()')

    # --------------------------------------------------------------

    return lines


# ---------------------------------------------------------------------------
# STUDENT TODO 2: IK 結果 -> triples
# ---------------------------------------------------------------------------
def ik_result_to_triples(target_uri, joint_config, ik_status, residual):
    """把一筆 IK 結果 ground 成 triples,回傳 Turtle 片段 (list of str).

    必須包含一個 IK 實例 (URI 建議 stu:ik_<target_uri>),型別
    hw3:IKComputation,並掛上:
      - hw3:producedBy         "<GROUP_ID>"
      - hw3:computedForRobot   stu:my_ur5
      - hw3:solvesForTarget    hw3:<target_uri>   <-- 注意是 hw3: namespace!
                                共用 target URI 是跨圖比較的 join key,
                                寫成 stu: 的話 Q3 會查不到你的結果
      - hw3:hasIKStatus        "SOLVED" / "OUT_OF_REACH" / ... (string)
      - hw3:hasResidual        殘差 (double, 寫法: "0.003"^^xsd:double)
      - hw3:hasJointConfiguration  JSON 字串 (參考 fk_result_to_triples)

    hint: 對照 ontology/ta-robot-graph.ttl 裡 ta:ik_ta_target_near 的寫法。
    """
    lines = []

    # ------------------------- your code -------------------------

    raise NotImplementedError('TODO: implement ik_result_to_triples()')

    # --------------------------------------------------------------

    return lines


# ---------------------------------------------------------------------------
# TA 提供: IK 結果分類 (數值層 -> 狀態字串)
# ---------------------------------------------------------------------------
def classify_ik_result(eef_pos_after_ik, target_pos, base_pos):
    """依殘差與工作空間幾何,判定 IK 狀態字串."""
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


# ---------------------------------------------------------------------------
# TA 提供: 模擬環境與求解流程
# ---------------------------------------------------------------------------
def _reset_arm(robot, joint_values):
    joint_ids = list(robot._joint_name_to_ids.values())
    for jid, val in zip(joint_ids, joint_values):
        p.resetJointState(robot.robot_id, jid, val)


def _sim_eef_pose(robot, joint_values):
    """無副作用地讀取指定關節角下的末端 pose (reset -> read -> restore)."""
    joint_ids = list(robot._joint_name_to_ids.values())
    saved = [p.getJointState(robot.robot_id, j)[0] for j in joint_ids]
    _reset_arm(robot, joint_values)
    pose = np.asarray(robot.get_eef_pose())
    _reset_arm(robot, saved)
    return pose


def run_pipeline(reference_mode):
    physics_client_id = p.connect(p.DIRECT)
    p.resetSimulation()
    p.setPhysicsEngineParameter(numSolverIterations=150)
    p.setTimeStep(SIM_TIMESTEP)
    p.setGravity(0, 0, -9.8)

    robot = ur5Env(physics_client_id, use_IK=1)
    base_pos = list(robot._base_position)
    for _ in range(240):
        p.stepSimulation()

    dh_params = get_ur5_DH_params()
    home_quat = np.asarray(robot.get_eef_pose())[3:]

    # ---------- FK: 用 fk 測資的前 3 組關節角 ----------
    fk_file = os.path.join(HW_ROOT, 'test_case', 'fk_test_case_easy.json')
    with open(fk_file, 'r') as f:
        fk_cases = json.load(f)['joint_poses'][:3]

    fk_records = []
    for i, q in enumerate(fk_cases):
        if reference_mode:
            pose = _sim_eef_pose(robot, q)
        else:
            pose, _ = your_fk(dh_params, q, base_pos)
        fk_records.append((i, q, list(pose)))
        print('[FK] case {} -> eef pos {}'.format(
            i, np.round(pose[:3], 4).tolist()))

    # ---------- IK: 共用 targets ----------
    ik_records = []
    for target in SHARED_TARGETS:
        target_pose_7d = list(target['position']) + list(home_quat)
        _reset_arm(robot, HOME_JOINTS)

        if reference_mode:
            joints = list(np.asarray(
                pybullet_ik(robot.robot_id, target_pose_7d))[:6])
            eef_pos = _sim_eef_pose(robot, joints)[:3]
        else:
            joints = list(your_ik(robot.robot_id, target_pose_7d,
                                  base_pos=base_pos))
            eef_pos, _ = your_fk(dh_params, joints, base_pos)
            eef_pos = eef_pos[:3]

        status, residual = classify_ik_result(
            eef_pos, target['position'], base_pos)
        ik_records.append((target['uri'], joints, status, residual))
        print('[IK] {} -> status={}, residual={:.4f} m'.format(
            target['uri'], status, residual))

    p.disconnect()
    return dh_params, fk_records, ik_records


def write_graph(dh_params, fk_records, ik_records):
    lines = [
        '@prefix hw3: <{}> .'.format(HW3_NS),
        '@prefix stu: <{}> .'.format(STU_NS),
        '@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .',
        '',
        '# Auto-generated by semantic/ground_kinematics.py',
        '# producedBy: {}'.format(GROUP_ID),
        '',
    ]
    lines += robot_spec_to_triples(dh_params, JOINT_LIMITS)
    for case_index, q, pose in fk_records:
        lines += fk_result_to_triples(case_index, q, pose)
    for target_uri, joints, status, residual in ik_records:
        lines += ik_result_to_triples(
            target_uri, joints, status, round(residual, 5))

    os.makedirs(os.path.dirname(OUTPUT_TTL), exist_ok=True)
    with open(OUTPUT_TTL, 'w') as f:
        f.write('\n'.join(lines) + '\n')
    print('[GROUND] knowledge graph written to {}'.format(OUTPUT_TTL))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--group', default='student-group-00',
                        help='provenance id written to hw3:producedBy')
    parser.add_argument('--reference', action='store_true',
                        help='use pybullet reference FK/IK instead of '
                             'your_fk/your_ik (pipeline smoke test only)')
    args = parser.parse_args()

    global GROUP_ID
    GROUP_ID = args.group

    dh_params, fk_records, ik_records = run_pipeline(args.reference)
    write_graph(dh_params, fk_records, ik_records)


GROUP_ID = 'student-group-00'

if __name__ == '__main__':
    main()
