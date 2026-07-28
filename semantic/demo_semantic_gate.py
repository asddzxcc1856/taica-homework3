# -*- coding: utf-8 -*-
"""Bonus Demo — Ravens x Semantic Gate (run inside the taica-hw3 conda env).

Demonstrates the semantic gate in the real Ravens PyBullet environment with
the block-insertion-easy task and the built-in oracle agent (no TF checkpoint
download needed):

    Case 1: oracle picks the L-shaped block -> ALLOW, action executes, reward 1.0
    Case 2: adversarial pick on the fixture -> REFUSE (reachable but not
            semantically graspable)
    Case 3: adversarial pick far away       -> REFUSE (no known object there /
            outside the workspace)

Prerequisites:
    1. Run `bash semantic/run_task4.sh` once (downloads Apache Jena)
    2. Finish your_ik in Task 2 (or temporarily keep the pybullet_ik
       stand-in line below)

Run:
    python semantic/demo_semantic_gate.py
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HW_ROOT = os.path.abspath(os.path.join(HERE, '..'))
RAVENS_ROOT = os.path.join(HW_ROOT, 'ravens', 'ravens')

# Import order matters: ravens inner packages first, then the hw3 root;
# remove semantic/ itself so it cannot shadow the hw3 modules
# (environment.py re-adds it when SEMANTIC_AUDIT=1).
while HERE in sys.path:
    sys.path.remove(HERE)
sys.path.insert(0, HW_ROOT)
sys.path.insert(0, RAVENS_ROOT)

os.environ['SEMANTIC_AUDIT'] = '1'  # enable the semantic gate

import numpy as np  # noqa: E402
import pybullet as p  # noqa: E402

import environments.environment as envmod  # noqa: E402
from environments.environment import Environment  # noqa: E402
import tasks  # noqa: E402
from ik import pybullet_ik  # noqa: E402

# Stand-in reference solver until Task 2 is done; comment this line out
# afterwards to use your own your_ik.
envmod.your_ik = pybullet_ik


def banner(msg):
    print()
    print('#' * 78)
    print('# ' + msg)
    print('#' * 78)


def main():
    assets_root = os.path.join(RAVENS_ROOT, 'environments', 'assets')
    env = Environment(assets_root, disp=False, hz=480)
    task = tasks.names['block-insertion-easy']()
    task.mode = 'test'

    failures = []

    banner('Case 1: oracle picks the L-shaped block (expect ALLOW + reward 1.0)')
    env.seed(0)
    env.set_task(task)
    obs = env.reset()
    agent = task.oracle(env)
    act = agent.act(obs, None)
    obs, reward, done, info = env.step(act)
    verdict = env.semantic_auditor.last_verdict
    print('==> allowed={}, reward={}, done={}'.format(
        verdict['allowed'], reward, done))
    if not verdict['allowed'] or reward < 0.99:
        failures.append('Case 1 failed')

    banner('Case 2: adversarial pick on the fixture (expect REFUSE: semantic)')
    env.seed(1)
    obs = env.reset()
    fixture_id = env.obj_ids['fixed'][0]
    fpos, frot = p.getBasePositionAndOrientation(fixture_id)
    bad_act = {'pose0': (fpos, frot),
               'pose1': ((0.6, 0.3, 0.02), (0.0, 0.0, 0.0, 1.0))}
    obs, reward, done, info = env.step(bad_act)
    verdict = env.semantic_auditor.last_verdict
    print('==> allowed={}, reward={}'.format(verdict['allowed'], reward))
    if verdict['allowed'] or 'semantic exclusion' not in verdict['reason']:
        failures.append('Case 2 failed')

    banner('Case 3: adversarial pick far outside workspace (expect REFUSE)')
    env.seed(2)
    obs = env.reset()
    far_act = {'pose0': ((5.0, 5.0, 0.02), (0.0, 0.0, 0.0, 1.0)),
               'pose1': ((0.6, 0.3, 0.02), (0.0, 0.0, 0.0, 1.0))}
    obs, reward, done, info = env.step(far_act)
    verdict = env.semantic_auditor.last_verdict
    print('==> allowed={}, reward={}'.format(verdict['allowed'], reward))
    if verdict['allowed']:
        failures.append('Case 3 failed')

    banner('SEMANTIC GATE DEMO ' + ('PASSED' if not failures else 'FAILED'))
    for msg in failures:
        print('  [FAIL] ' + msg)
    sys.exit(0 if not failures else 1)


if __name__ == '__main__':
    main()
