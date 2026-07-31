# -*- coding: utf-8 -*-
"""Task 4 scoring script (TA-provided; grading uses the same code).

Total 30 points:
    S1 Robot specification grounding ............. 8 pts
       - q1 finds your robot (hw3:hasDoF 6, 6 joints)          2 pts
       - all 6 joints' D-H parameters match the course table
         (tolerance 1e-3)                                      6 pts
    S2 Per-task evaluation grounding ............. 12 pts
       - Task 1: 3 FK cases grounded, all PASS                 4 pts
       - Task 2: IK statuses of the 3 shared targets correct   4 pts
       - Task 2: q2 (inferred SolvedIKComputation) contains
         your target_near row                                  2 pts
       - Task 3: at least one hw3:SuccessfulEpisode grounded   2 pts
    S3 SPARQL interoperability (Q3) .............. 10 pts
       - 9 rows (3 targets x 3 robots: yours + TA UR5 + TA UR10)
         with the correct status matrix

Invoked automatically by STEP 7 of run_task4.sh (requires JENA_HOME).
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
TA_UR5_ROBOT = 'http://taica.course/hw3/data/ta#ta_ur5'
TA_ROBOTS = (TA_ROBOT, TA_UR5_ROBOT)
TA_PROV = 'ta-reference-pipeline'

EXPECTED_DH = {  # jointIndex -> (a, d, alpha)
    1: (0.0, 0.0892, 1.570796),
    2: (-0.425, 0.0, 0.0),
    3: (-0.392, 0.0, 0.0),
    4: (0.0, 0.1093, 1.570796),
    5: (0.0, 0.09475, -1.570796),
    6: (0.0, 0.2023, 0.0),
}

EXPECTED_STATUS = {  # statuses your UR5 should report for the shared targets
    HW3 + 'target_near': 'SOLVED',
    HW3 + 'target_mid': 'OUT_OF_REACH',
    HW3 + 'target_far': 'OUT_OF_REACH',
}

EXPECTED_TA_STATUS = {  # statuses in the TA's UR10 graph (fixed values)
    HW3 + 'target_near': 'SOLVED',
    HW3 + 'target_mid': 'SOLVED',
    HW3 + 'target_far': 'OUT_OF_REACH',
}

EXPECTED_TA5_STATUS = {  # TA's UR5 graph: same arm as yours -> same statuses
    HW3 + 'target_near': 'SOLVED',
    HW3 + 'target_mid': 'OUT_OF_REACH',
    HW3 + 'target_far': 'OUT_OF_REACH',
}

EXPECTED_FK_CASES = 3


def read_csv(name):
    path = os.path.join(OUTPUT, name)
    if not os.path.exists(path):
        return []
    with open(path, 'r') as f:
        return list(csv.DictReader(f))


def tdbquery(query_text):
    """Run an ad-hoc grading query against the triple store; return CSV rows."""
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

    # ---------------- S1: robot spec grounding (8) ----------------
    s1 = 0.0
    q1 = read_csv('q1_robot_specs.csv')
    stu_rows = [r for r in q1 if r.get('producedBy') != TA_PROV]
    ta_rows = [r for r in q1 if r.get('producedBy') == TA_PROV]
    if (len(stu_rows) == 1 and stu_rows[0].get('dof') == '6'
            and stu_rows[0].get('jointCount') == '6' and len(ta_rows) == 2):
        s1 += 2.0
        report.append('[S1] q1 robot summary ................ OK  (+2)')
    else:
        report.append('[S1] q1 robot summary ................ FAIL (+0) '
                      '(expect exactly 1 student robot with dof=6, 6 joints, '
                      'alongside the two TA robots UR5 + UR10)')

    dh_rows = tdbquery(
        'PREFIX hw3: <{ns}>\n'
        'PREFIX cora: <http://purl.org/ieee1872-owl/cora-bare#>\n'
        'SELECT ?idx ?a ?d ?alpha WHERE {{\n'
        '  ?r a cora:Robot ; hw3:producedBy ?pb ; hw3:hasJoint ?j .\n'
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

    # ---------------- S2: per-task evaluation grounding (12) ----------------
    s2 = 0.0

    # Task 1: FK evaluation cases (expect 3, all PASS)
    fk_rows = tdbquery(
        'PREFIX hw3: <{ns}>\n'
        'SELECT ?c ?status WHERE {{\n'
        '  ?c a hw3:FKComputation ; hw3:producedBy ?pb ;\n'
        '     hw3:hasEvaluationStatus ?status .\n'
        '  FILTER(?pb != "{ta}")\n'
        '}}\n'.format(ns=HW3, ta=TA_PROV))
    fk_pass = sum(1 for r in fk_rows if r.get('status') == 'PASS')
    fk_pts = round(4.0 * min(fk_pass, EXPECTED_FK_CASES) / EXPECTED_FK_CASES, 1)
    s2 += fk_pts
    report.append('[S2] Task 1 FK evaluation ({}/{} PASS) . {} (+{})'.format(
        fk_pass, EXPECTED_FK_CASES,
        'OK ' if fk_pass >= EXPECTED_FK_CASES else 'PARTIAL', fk_pts))

    # Task 2: IK statuses on the shared targets
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
    ik_pts = round(4.0 * ik_ok / 3.0, 1)
    s2 += ik_pts
    report.append('[S2] Task 2 IK statuses ({}/3) ......... {} (+{})'.format(
        ik_ok, 'OK ' if ik_ok == 3 else 'PARTIAL', ik_pts))

    # Task 2: inference check via q2
    q2 = read_csv('q2_reachable_targets.csv')
    stu_solved = [r for r in q2
                  if r.get('target') == HW3 + 'target_near'
                  and r.get('robot') not in TA_ROBOTS]
    if stu_solved:
        s2 += 2.0
        report.append('[S2] q2 inferred SolvedIKComputation . OK  (+2)')
    else:
        report.append('[S2] q2 inferred SolvedIKComputation . FAIL (+0) '
                      '(your target_near row is missing — check hasIKStatus '
                      'literal and that reasoning ran)')

    # Task 3: successful insertion episodes grounded
    ep_rows = tdbquery(
        'PREFIX hw3: <{ns}>\n'
        'SELECT ?e WHERE {{\n'
        '  ?e a hw3:SuccessfulEpisode ; hw3:producedBy ?pb .\n'
        '  FILTER(?pb != "{ta}")\n'
        '}}\n'.format(ns=HW3, ta=TA_PROV))
    if ep_rows:
        s2 += 2.0
        report.append('[S2] Task 3 episodes ({} SUCCESS) ..... OK  (+2)'.format(
            len(ep_rows)))
    else:
        report.append('[S2] Task 3 episodes ................. FAIL (+0) '
                      '(run Task 3 first so ravens/test.py writes the '
                      'results pkl, then re-run this pipeline)')
    total += s2

    # ---------------- S3: interoperability query (10) ----------------
    s3 = 0.0
    q3 = read_csv('q3_interop_compare.csv')
    expected_rows = set()
    for t, s in EXPECTED_TA_STATUS.items():
        expected_rows.add((t, TA_ROBOT, s))
    for t, s in EXPECTED_TA5_STATUS.items():
        expected_rows.add((t, TA_UR5_ROBOT, s))
    stu_robots = {r['robot'] for r in q3 if r.get('robot')
                  and r['robot'] not in TA_ROBOTS}
    stu_robot = next(iter(stu_robots)) if len(stu_robots) == 1 else None
    for t, s in EXPECTED_STATUS.items():
        expected_rows.add((t, stu_robot, s))
    got_rows = {(r.get('target'), r.get('robot'), r.get('status'))
                for r in q3}
    if stu_robot and got_rows == expected_rows and len(q3) == 9:
        s3 = 10.0
        report.append('[S3] q3 interop comparison matrix .... OK  (+10)')
    else:
        matched = len(got_rows & expected_rows) if stu_robot else 0
        s3 = round(10.0 * matched / 9.0, 1)
        report.append('[S3] q3 interop comparison matrix .... {} (+{}) '
                      '({} / 9 expected rows)'.format(
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
