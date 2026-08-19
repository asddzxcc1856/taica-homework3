# -*- coding: utf-8 -*-
"""Task 4 scoring script (TA-provided; grading uses the same code).

Total 30 points — grounding + reasoning + SHACL:

    S1 REUSE grounding structure ............... 10 pts
       ta-shapes-full.ttl 的 STRUCTURE:* shapes 對 output/data.ttl
       零違規 -> 滿分 (每個違規 -2)
    S2 REASONING (inference-defined classes) ... 6 pts
       output/inferred.ttl 中由推理導出的成員必須是:
       - hw3:SolvedIKComputation    = {ik_target_near}          (+3)
       - hw3:OutOfReachIKComputation = {ik_target_mid, _far}    (+3)
    S3 Problem detection on YOUR data .......... 6 pts
       TA problem shapes 在你的 data.ttl 上:
       - target_mid / target_far 被標 ARM_OUT_OF_RANGE (各 +2)
       - target_near 沒有任何問題旗標 (+1)
       - 零 JOINT_LIMIT_VIOLATION (+1)
    S4 YOUR shapes.ttl vs TA faulty trace ...... 8 pts
       用「你的」shapes.ttl 驗證助教給的有問題執行過程
       (ta-faulty-execution.ttl):
       - probe:ik_good 零違規 (+2)
       - probe:ik_out_of_range 被標 ARM_OUT_OF_RANGE (+2)
       - probe:ik_no_convergence 被標 NO_CONVERGENCE (+2)
       - probe:fk_bad 被標 FK_INACCURATE (+2)

Invoked automatically by STEP 6 of run_task4.sh.
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUTPUT = os.path.join(HERE, 'output')

RESULT_SPLIT = re.compile(r'(?:\ba|rdf:type)\s+sh:ValidationResult')


def parse_report(name):
    """Parse a SHACL validation report (Turtle) into [(focus, message)]."""
    path = os.path.join(OUTPUT, name)
    if not os.path.exists(path):
        return None
    with open(path) as f:
        txt = f.read()
    results = []
    for chunk in RESULT_SPLIT.split(txt)[1:]:
        focus = re.search(r'sh:focusNode\s+([^\s;]+)', chunk)
        msg = re.search(r'sh:resultMessage\s+"([^"]*)"', chunk)
        results.append((focus.group(1) if focus else '',
                        msg.group(1) if msg else ''))
    return results


def flagged(results, focus_key, msg_prefix=None):
    for focus, msg in results:
        if focus_key in focus and (msg_prefix is None
                                   or msg.startswith(msg_prefix)):
            return True
    return False


def inferred_types(subject_key):
    """Return the Turtle paragraph of `subject_key` in output/inferred.ttl
    (Jena TURTLE_PRETTY writes one subject block followed by a blank line)."""
    path = os.path.join(OUTPUT, 'inferred.ttl')
    if not os.path.exists(path):
        return ''
    with open(path) as f:
        txt = f.read()
    m = re.search(r'^\S*' + re.escape(subject_key) + r'\b.*?\n\n',
                  txt, re.S | re.M)
    return m.group(0) if m else ''


def main():
    total = 0.0
    report = []

    # ---------------- S1: grounding structure (10) ----------------
    ta = parse_report('ta-validation.ttl')
    if ta is None:
        report.append('[S1] ta-validation.ttl missing ........ FAIL (+0)')
        ta = []
    else:
        structural = [(f, m) for f, m in ta if m.startswith('STRUCTURE')]
        s1 = max(0.0, 10.0 - 2.0 * len(structural))
        total += s1
        if structural:
            report.append('[S1] grounding structure .............. PARTIAL (+{:g}) '
                          '({} STRUCTURE violation(s))'.format(s1, len(structural)))
            for f, m in structural[:5]:
                report.append('       - {} : {}'.format(f, m[:60]))
        else:
            report.append('[S1] grounding structure (0 violations) OK  (+10)')

    # ---------------- S2: reasoning-derived classes (6) ----------------
    near = inferred_types('ik_target_near')
    mid = inferred_types('ik_target_mid')
    far = inferred_types('ik_target_far')
    ok = ('SolvedIKComputation' in near
          and 'SolvedIKComputation' not in mid
          and 'SolvedIKComputation' not in far)
    total += 3 if ok else 0
    report.append('[S2] inferred SolvedIKComputation = {{near}} .. {} (+{})'.format(
        'OK ' if ok else 'FAIL', 3 if ok else 0))
    ok = ('OutOfReachIKComputation' in mid
          and 'OutOfReachIKComputation' in far
          and 'OutOfReachIKComputation' not in near)
    total += 3 if ok else 0
    report.append('[S2] inferred OutOfReach = {{mid, far}} ...... {} (+{})'.format(
        'OK ' if ok else 'FAIL', 3 if ok else 0))

    # ---------------- S3: problem detection on YOUR data (6) ----------------
    checks = [
        (flagged(ta, 'ik_target_mid', 'ARM_OUT_OF_RANGE'), 2,
         'target_mid flagged ARM_OUT_OF_RANGE'),
        (flagged(ta, 'ik_target_far', 'ARM_OUT_OF_RANGE'), 2,
         'target_far flagged ARM_OUT_OF_RANGE'),
        (not any('ik_target_near' in f and not m.startswith('STRUCTURE')
                 for f, m in ta), 1,
         'target_near clean (no problem flags)'),
        (not any(m.startswith('JOINT_LIMIT_VIOLATION') for _, m in ta), 1,
         'no JOINT_LIMIT_VIOLATION'),
    ]
    for ok, pts, label in checks:
        total += pts if ok else 0
        report.append('[S3] {} {} (+{})'.format(
            (label + ' ').ljust(40, '.'), 'OK ' if ok else 'FAIL',
            pts if ok else 0))

    # ---------------- S4: your shapes vs TA faulty trace (8) ----------------
    probe = parse_report('probe-validation.ttl')
    if probe is None:
        report.append('[S4] probe-validation.ttl missing ...... FAIL (+0)')
        probe = []
    checks = [
        (not any('ik_good' in f for f, _ in probe), 2,
         'faulty trace: good case clean'),
        (flagged(probe, 'ik_out_of_range', 'ARM_OUT_OF_RANGE'), 2,
         'faulty trace: out-of-range flagged'),
        (flagged(probe, 'ik_no_convergence', 'NO_CONVERGENCE'), 2,
         'faulty trace: no-convergence flagged'),
        (flagged(probe, 'fk_bad', 'FK_INACCURATE'), 2,
         'faulty trace: bad FK flagged'),
    ]
    for ok, pts, label in checks:
        total += pts if ok else 0
        report.append('[S4] {} {} (+{})'.format(
            (label + ' ').ljust(40, '.'), 'OK ' if ok else 'FAIL',
            pts if ok else 0))

    # ---------------- summary ----------------
    print('=' * 70)
    print('  Task 4 : Grounding (REUSE) + Reasoning + SHACL Validation')
    print('=' * 70)
    for line in report:
        print('  ' + line)
    print('-' * 70)
    print('  Your Task 4 Score : {:.1f} / 30.0'.format(total))
    print('=' * 70)
    sys.exit(0 if total >= 29.9 else 1)


if __name__ == '__main__':
    main()
