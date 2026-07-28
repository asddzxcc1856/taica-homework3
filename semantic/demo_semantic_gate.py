# -*- coding: utf-8 -*-
"""Bonus Demo — Ravens × Semantic Gate (需在 taica-hw3 conda 環境執行).

用真實的 Ravens PyBullet 環境 + block-insertion-easy + oracle agent
(不需下載 TF checkpoint) 展示語意閘門的三種行為:

    Case 1: oracle 抓 L 型積木  -> ALLOW,動作執行,reward = 1.0
    Case 2: 惡意動作抓 fixture  -> REFUSE (可達但語意上不可抓取)
    Case 3: 惡意動作抓遠處空點  -> REFUSE (場景中無此物件 / 超出工作空間)

前置需求:
    1. 先跑過一次 `bash semantic/run_task4.sh`(會下載 Apache Jena)
    2. 完成 Task 2 的 your_ik(或暫時保留下方的 pybullet_ik 代打那一行)

執行:
    python semantic/demo_semantic_gate.py
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HW_ROOT = os.path.abspath(os.path.join(HERE, '..'))
RAVENS_ROOT = os.path.join(HW_ROOT, 'ravens', 'ravens')

# 匯入順序: ravens 內層套件 -> hw3 根目錄;並移除 semantic/ 自身避免遮蔽
while HERE in sys.path:
    sys.path.remove(HERE)
sys.path.insert(0, HW_ROOT)
sys.path.insert(0, RAVENS_ROOT)

os.environ['SEMANTIC_AUDIT'] = '1'  # 開啟語意審查閘門

import numpy as np  # noqa: E402
import pybullet as p  # noqa: E402

import environments.environment as envmod  # noqa: E402
from environments.environment import Environment  # noqa: E402
import tasks  # noqa: E402
from ik import pybullet_ik  # noqa: E402

# 尚未完成 Task 2 時用參考解代打;完成後請註解掉這行改用你的 your_ik
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

    banner('SEMANTIC GATE DEMO ' + ('PASSED ✓' if not failures else 'FAILED ✗'))
    for msg in failures:
        print('  [FAIL] ' + msg)
    sys.exit(0 if not failures else 1)


if __name__ == '__main__':
    main()
