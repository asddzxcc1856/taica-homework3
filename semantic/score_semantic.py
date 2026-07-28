# -*- coding: utf-8 -*-
"""Task 4 評分腳本 (TA 提供,評分時使用相同程式).

滿分 30 分:
    S1 Robot specification grounding ... 10 分
       - q1 查得到你的機器人 (hw3:hasDoF 6、6 個關節)      4 分
       - 6 個關節的 DH 參數與課程 DH 表一致 (tol 1e-3)      6 分
    S2 Kinematic result grounding ...... 10 分
       - 3 個共用 target 的 IK 狀態全部正確                 6 分
       - q2 (推理後的 SolvedIKComputation) 含你的 target_near 4 分
    S3 SPARQL interoperability (Q3) .... 10 分
       - 6 列 (3 targets × 2 robots) 且狀態矩陣正確

執行方式: 由 run_task4.sh 的 STEP 7 自動呼叫 (需要 JENA_HOME 環境變數)。
"""

import csv
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUTPUT = os.path.join(HERE, 'output')
STORE = os.path.join(HERE, 'store')

HW3 = 'http://taica.course/hw3/ontology#'
TA_ROBOT = 'http://taica.course/hw3/data/ta#ta_ur10'
TA_PROV = 'ta-reference-pipeline'

EXPECTED_DH = {  # jointIndex -> (a, d, alpha)
    1: (0.0, 0.0892, 1.570796),
    2: (-0.425, 0.0, 0.0),
    3: (-0.392, 0.0, 0.0),
    4: (0.0, 0.1093, 1.570796),
    5: (0.0, 0.09475, -1.570796),
    6: (0.0, 0.2023, 0.0),
}

EXPECTED_STATUS = {  # 你的 UR5 對共用 target 應得到的狀態
    HW3 + 'target_near': 'SOLVED',
    HW3 + 'target_mid': 'OUT_OF_REACH',
    HW3 + 'target_far': 'OUT_OF_REACH',
}

EXPECTED_TA_STATUS = {  # 助教 UR10 圖中的狀態 (固定值)
    HW3 + 'target_near': 'SOLVED',
    HW3 + 'target_mid': 'SOLVED',
    HW3 + 'target_far': 'OUT_OF_REACH',
}


def read_csv(name):
    path = os.path.join(OUTPUT, name)
    if not os.path.exists(path):
        return []
    with open(path, 'r') as f:
        return list(csv.DictReader(f))


def tdbquery(query_text):
    """對 triple store 執行一條臨時 grading query,回傳 CSV rows."""
    jena_home = os.environ.get('JENA_HOME', '')
    tool = os.path.join(jena_home, 'bin', 'tdb2.tdbquery')
    qfile = os.path.join(OUTPUT, '_grading_tmp.rq')
    with open(qfile, 'w') as f:
        f.write(query_text)
    out = subprocess.check_output(
        [tool, '--loc', STORE, '--query', qfile, '--results=CSV'],
        universal_newlines=True)
    return list(csv.DictReader(out.splitlines()))


def close(a, b, tol=1e-3):
    try:
        return abs(float(a) - float(b)) <= tol
    except (TypeError, ValueError):
        return False


def main():
    total = 0.0
    report = []

    # ---------------- S1: robot spec grounding (10) ----------------
    s1 = 0.0
    q1 = read_csv('q1_robot_specs.csv')
    stu_rows = [r for r in q1 if r.get('producedBy') != TA_PROV]
    ta_rows = [r for r in q1 if r.get('producedBy') == TA_PROV]
    if (len(stu_rows) == 1 and stu_rows[0].get('dof') == '6'
            and stu_rows[0].get('jointCount') == '6' and len(ta_rows) == 1):
        s1 += 4.0
        report.append('[S1] q1 robot summary ................ OK  (+4)')
    else:
        report.append('[S1] q1 robot summary ................ FAIL (+0) '
                      '(expect exactly 1 student robot with dof=6, 6 joints, '
                      'alongside the TA robot)')

    dh_rows = tdbquery(
        'PREFIX hw3: <{ns}>\n'
        'SELECT ?idx ?a ?d ?alpha WHERE {{\n'
        '  ?r a hw3:RobotArm ; hw3:producedBy ?pb ; hw3:hasJoint ?j .\n'
        '  ?j hw3:jointIndex ?idx ; hw3:dh_a ?a ; hw3:dh_d ?d ;\n'
        '     hw3:dh_alpha ?alpha .\n'
        '  FILTER(?pb != "{ta}")\n'
        '}} ORDER BY ?idx\n'.format(ns=HW3, ta=TA_PROV))
    dh_ok = 0
    for row in dh_rows:
        try:
            idx = int(float(row['idx']))
        except (TypeError, ValueError):
            continue
        exp = EXPECTED_DH.get(idx)
        if exp and close(row['a'], exp[0]) and close(row['d'], exp[1]) \
                and close(row['alpha'], exp[2]):
            dh_ok += 1
    s1 += min(6.0, dh_ok)
    report.append('[S1] DH parameters ({} / 6 joints) ..... {} (+{})'.format(
        dh_ok, 'OK' if dh_ok == 6 else 'PARTIAL', min(6, dh_ok)))
    total += s1

    # ---------------- S2: IK result grounding (10) ----------------
    s2 = 0.0
    ik_rows = tdbquery(
        'PREFIX hw3: <{ns}>\n'
        'SELECT ?target ?status WHERE {{\n'
        '  ?ik a hw3:IKComputation ; hw3:producedBy ?pb ;\n'
        '      hw3:solvesForTarget ?target ; hw3:hasIKStatus ?status .\n'
        '  FILTER(?pb != "{ta}")\n'
        '}}\n'.format(ns=HW3, ta=TA_PROV))
    got_status = {r['target']: r['status'] for r in ik_rows}
    ik_ok = sum(1 for t, s in EXPECTED_STATUS.items()
                if got_status.get(t) == s)
    s2 += ik_ok * 2.0
    report.append('[S2] IK status of shared targets ({}/3)  {} (+{})'.format(
        ik_ok, 'OK' if ik_ok == 3 else 'PARTIAL', ik_ok * 2))

    q2 = read_csv('q2_reachable_targets.csv')
    stu_solved = [r for r in q2
                  if r.get('target') == HW3 + 'target_near'
                  and TA_ROBOT not in r.get('robot', '')]
    if stu_solved:
        s2 += 4.0
        report.append('[S2] q2 inferred SolvedIKComputation . OK  (+4)')
    else:
        report.append('[S2] q2 inferred SolvedIKComputation . FAIL (+0) '
                      '(your target_near row is missing — check hasIKStatus '
                      'literal and that reasoning ran)')
    total += s2

    # ---------------- S3: interoperability query (10) ----------------
    s3 = 0.0
    q3 = read_csv('q3_interop_compare.csv')
    expected_rows = set()
    for t, s in EXPECTED_TA_STATUS.items():
        expected_rows.add((t, TA_ROBOT, s))
    stu_robots = {r['robot'] for r in q3 if r.get('robot')
                  and r['robot'] != TA_ROBOT}
    stu_robot = next(iter(stu_robots)) if len(stu_robots) == 1 else None
    for t, s in EXPECTED_STATUS.items():
        expected_rows.add((t, stu_robot, s))
    got_rows = {(r.get('target'), r.get('robot'), r.get('status'))
                for r in q3}
    if stu_robot and got_rows == expected_rows and len(q3) == 6:
        s3 = 10.0
        report.append('[S3] q3 interop comparison matrix .... OK  (+10)')
    else:
        matched = len(got_rows & expected_rows) if stu_robot else 0
        s3 = round(10.0 * matched / 6.0, 1)
        report.append('[S3] q3 interop comparison matrix .... {} (+{}) '
                      '({} / 6 expected rows)'.format(
                          'PARTIAL' if matched else 'FAIL', s3, matched))
    total += s3

    # ---------------- summary ----------------
    print('=' * 70)
    print('  Task 4 : Semantic Robot Knowledge and Triple Store')
    print('=' * 70)
    for line in report:
        print('  ' + line)
    print('-' * 70)
    print('  Your Task 4 Score : {:.1f} / 30.0'.format(total))
    print('=' * 70)
    sys.exit(0 if total >= 29.9 else 1)


if __name__ == '__main__':
    main()
