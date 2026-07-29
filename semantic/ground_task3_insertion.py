# -*- coding: utf-8 -*-
"""Task 4 / Part 3 — Semantic evaluation of Task 3 (Transporter block insertion).

Reads the results file that ravens/test.py writes after running Task 3
(block-insertion-easy-transporter-*.pkl under ravens/) and grounds every
test episode — reward and SUCCESS/FAILURE outcome — into RDF
-> semantic/output/task3_insertion_graph.ttl.

The insertion episodes are where your IK is verified inside the FULL
manipulation pipeline (prepick -> grasp -> preplace -> insertion); the OWL
reasoner later derives hw3:SuccessfulEpisode (the Task 3 evaluation class)
from the grounded outcome.

No student TODO in this file (TA-provided), but it only has data to ground
AFTER you have run Task 3.

Run:
    python semantic/ground_task3_insertion.py --group <your group id>
"""

import glob
import os
import pickle

import common
from common import HW_ROOT

OUTPUT_FILE = 'task3_insertion_graph.ttl'
SUCCESS_REWARD = 0.999  # an episode counts as SUCCESS iff reward >= this

GROUP_ID = 'student-group-00'


# ---------------------------------------------------------------------------
# TA-provided: Task 3 episode -> triples
# ---------------------------------------------------------------------------
def episode_to_triples(index, reward, outcome):
    """Ground one Transporter Network test episode (Task 3)."""
    return [
        'stu:episode_{} a soma:Episode ;'.format(index),
        '    hw3:producedBy "{}" ;'.format(GROUP_ID),
        '    hw3:performsTask "block-insertion-easy" ;',
        '    hw3:manipulatesObject stu:ell_block ;',
        '    hw3:episodeIndex {} ;'.format(index),
        '    hw3:hasReward "{}"^^xsd:double ;'.format(round(float(reward), 4)),
        '    hw3:hasOutcome "{}" .'.format(outcome),
        '',
    ]


def scene_to_triples(block_reachable):
    """Ground the insertion scene's object semantics (TA-provided).

    These facts feed Task 4's semantic-gate reasoning:
      - graspability   : perception-layer knowledge (the L block is the
                         manipulated object; the fixture is a fixed target)
      - reachability   : grounded from EXECUTION — a successful insertion
                         episode proves the block is kinematically reachable
    """
    reachable = 'true' if block_reachable else 'false'
    return [
        '# Scene semantics of the insertion task (feeds the Task 4 semantic gate)',
        'stu:ell_block a hw3:GraspableObject ;',
        '    rdfs:label "L-shaped block (ell.urdf, rigid)" ;',
        '    hw3:isKinematicallyReachable {} .'.format(reachable),
        '',
        '# reachable placement target, but NOT graspable (no GraspableObject type)',
        'stu:insertion_fixture rdfs:label "fixture (ell.urdf, fixed)" ;',
        '    hw3:isKinematicallyReachable {} .'.format(reachable),
        '',
    ]


def find_results_file():
    """Locate the newest Task 3 results pkl written by ravens/test.py."""
    pkls = sorted(glob.glob(
        os.path.join(HW_ROOT, 'ravens', '*block-insertion*.pkl')))
    return pkls[-1] if pkls else None


def main():
    args = common.make_arg_parser(__doc__).parse_args()
    global GROUP_ID
    GROUP_ID = args.group

    lines = []
    results_file = find_results_file()
    if results_file is None:
        print('[TASK3-EVAL] no Task 3 results file found under ravens/ — '
              'run Task 3 first (ravens/test.py writes '
              'block-insertion-easy-transporter-*.pkl). '
              'Writing an empty graph for now.')
        lines = ['# No Task 3 results available yet — run Task 3 first.', '']
    else:
        with open(results_file, 'rb') as f:
            results = pickle.load(f)
        print('[TASK3-EVAL] grounding {} episodes from {}'.format(
            len(results), os.path.basename(results_file)))
        block_reachable = any(
            float(r) >= SUCCESS_REWARD for r, _info in results)
        lines += scene_to_triples(block_reachable)
        for i, (total_reward, _info) in enumerate(results):
            outcome = ('SUCCESS' if float(total_reward) >= SUCCESS_REWARD
                       else 'FAILURE')
            print('[TASK3-EVAL] episode {} -> reward={} {}'.format(
                i, total_reward, outcome))
            lines += episode_to_triples(i, total_reward, outcome)

    common.write_graph(OUTPUT_FILE, lines, GROUP_ID,
                       'ground_task3_insertion.py')


if __name__ == '__main__':
    main()
