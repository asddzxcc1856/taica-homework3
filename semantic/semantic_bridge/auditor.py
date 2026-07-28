# -*- coding: utf-8 -*-
"""SemanticTaskAuditor — semantic gate for Ravens actions (TA-provided bonus).

After the Transporter Network (or oracle) produces a pick-and-place action,
and BEFORE it is executed:
    1. Scan the scene objects (env.obj_ids) and compute IK reachability for
       each of them (numeric layer)
    2. Symbol grounding: graspable (semantic) + reachable (geometric) -> RDF
    3. Call the Java Jena OWL reasoner to derive hw3:ExecutableGraspTarget
    4. If the pick target is not in the inferred set -> refuse the action
       with an explainable reason

Enable by setting the environment variable SEMANTIC_AUDIT=1 before running
ravens (see the Bonus section of the README).
Python 3.7 compatible (runs inside the taica-hw3 conda environment).
"""

import glob
import json
import os
import subprocess

import numpy as np
import pybullet as p

BRIDGE_DIR = os.path.dirname(os.path.abspath(__file__))
SEM_ROOT = os.path.dirname(BRIDGE_DIR)

BASE_TTL = os.path.join(SEM_ROOT, 'ontology', 'hw3-ontology.ttl')
KB_TTL = os.path.join(SEM_ROOT, 'output', 'ravens_knowledge_base.ttl')
INFERRED_TTL = os.path.join(SEM_ROOT, 'output', 'ravens_inferred_graph.ttl')
QUERY_RQ = os.path.join(SEM_ROOT, 'queries', 'executable_tasks.rq')

JAVA_DIR = os.path.join(SEM_ROOT, 'java_semantic_engine')
JAVA_SRC = os.path.join(JAVA_DIR, 'src', 'main', 'java',
                        'course', 'taica', 'hw3', 'SemanticReasoner.java')
JAVA_CLASSES = os.path.join(JAVA_DIR, 'target', 'classes')
JAVA_MAIN = 'course.taica.hw3.SemanticReasoner'

HW3_NS = 'http://taica.course/hw3/ontology#'
KB_NS = 'http://taica.course/hw3/data/ravens#'

# Semantic-layer annotation: decide "semantically graspable" from the URDF
# body name. Note that ravens' ell.urdf and fixture.urdf share the same
# <robot name="ell.urdf">, so objects in the 'fixed' category (anchored
# bases) are always treated as non-graspable; name rules apply to 'rigid'
# objects only.
GRASPABLE_NAME_RULES = [
    ('ell', True),
    ('block', True),
    ('cup', True),
    ('fixture', False),
    ('workspace', False),
    ('plane', False),
]


def _match_graspable(name):
    lowered = name.lower()
    for key, graspable in GRASPABLE_NAME_RULES:
        if key in lowered:
            return graspable
    return False


def _sanitize(name):
    return ''.join(c if c.isalnum() else '_' for c in name)


def _jena_lib():
    """Return the classpath wildcard for the Jena jars."""
    jena_home = os.environ.get('JENA_HOME')
    if jena_home and os.path.isdir(os.path.join(jena_home, 'lib')):
        return os.path.join(jena_home, 'lib', '*')
    candidates = sorted(glob.glob(
        os.path.join(SEM_ROOT, '.cache', 'apache-jena-*', 'lib')))
    if candidates:
        return os.path.join(candidates[-1], '*')
    raise RuntimeError(
        'Apache Jena not found. Run `bash semantic/run_task4.sh` once '
        '(it downloads Jena to semantic/.cache), or set JENA_HOME.')


class SemanticTaskAuditor(object):

    def __init__(self, base_pos=(0.0, 0.0, 0.0), workspace_radius=0.90,
                 pick_match_radius=0.10, fk_residual_thresh=0.05, verbose=True):
        self.base_pos = np.asarray(base_pos, dtype=float)
        self.workspace_radius = workspace_radius
        self.pick_match_radius = pick_match_radius
        self.fk_residual_thresh = fk_residual_thresh
        self.verbose = verbose
        self.last_verdict = None  # most recent verdict, for tests / reports

    # ------------------------------------------------------------------
    # Numeric layer: side-effect-free FK residual check
    # (reset -> read -> restore)
    # ------------------------------------------------------------------
    def _fk_residual(self, robot_id, joint_indices, q, ee_link, target_pos):
        saved = [p.getJointState(robot_id, j)[:2] for j in joint_indices]
        for j, qi in zip(joint_indices, q):
            p.resetJointState(robot_id, j, qi)
        eef_pos = np.asarray(p.getLinkState(robot_id, ee_link)[4])
        for j, (pos_s, vel_s) in zip(joint_indices, saved):
            p.resetJointState(robot_id, j, pos_s, targetVelocity=vel_s)
        return float(np.linalg.norm(eef_pos - np.asarray(target_pos)))

    def _classify_object(self, env, solve_ik, body_id):
        pos, _ = p.getBasePositionAndOrientation(body_id)
        pos = np.asarray(pos, dtype=float)
        dist = float(np.linalg.norm(pos - self.base_pos))
        if dist > self.workspace_radius:
            return 'OUT_OF_REACH', False, dist

        target_pose = list(pos) + [0.0, 0.0, 0.0, 1.0]
        joints = solve_ik(target_pose)
        residual = self._fk_residual(
            env.ur5, env.joints, list(joints), env.ee_tip, pos)
        if residual < self.fk_residual_thresh:
            return 'SOLVED', True, residual
        return 'NO_CONVERGENCE', False, residual

    def _collect_scene_objects(self, env, solve_ik):
        objects = []
        for category in ('rigid', 'fixed'):
            for body_id in env.obj_ids[category]:
                name = p.getBodyInfo(body_id)[1].decode('utf-8')
                pos, _ = p.getBasePositionAndOrientation(body_id)
                status, reachable, residual = self._classify_object(
                    env, solve_ik, body_id)
                graspable = (category != 'fixed') and _match_graspable(name)
                objects.append({
                    'body_id': body_id,
                    'kb_id': '{}_{}_{}'.format(
                        _sanitize(name), category, body_id),
                    'label': '{} ({})'.format(name, category),
                    'category': category,
                    'position': [round(float(v), 5) for v in pos],
                    'graspable': graspable,
                    'ik_status': status,
                    'reachable': reachable,
                    'residual': round(float(residual), 5),
                })
        return objects

    # ------------------------------------------------------------------
    # Semantic layer: grounding -> TTL (using the shared hw3: vocabulary)
    # ------------------------------------------------------------------
    def _write_kb(self, objects):
        lines = [
            '@prefix hw3: <{}> .'.format(HW3_NS),
            '@prefix kb:  <{}> .'.format(KB_NS),
            '@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .',
            '',
            '# Auto-generated by semantic_bridge.auditor — DO NOT EDIT',
            '',
            'kb:ravens_ur5 a hw3:RobotArm ;',
            '    hw3:producedBy "ravens-semantic-gate" ;',
            '    hw3:hasDoF 6 .',
            '',
        ]
        for obj in objects:
            types = ['hw3:PhysicalObject']
            if obj['graspable']:
                types.append('hw3:GraspableObject')
            reachable = 'true' if obj['reachable'] else 'false'
            lines += [
                'kb:{} a {} ;'.format(obj['kb_id'], ' , '.join(types)),
                '    hw3:hasObjectLabel "{}" ;'.format(obj['label']),
                '    hw3:isKinematicallyReachable {} .'.format(reachable),
                '',
                'kb:ik_task_{} a hw3:IKComputation ;'.format(obj['kb_id']),
                '    hw3:producedBy "ravens-semantic-gate" ;',
                '    hw3:computedForRobot kb:ravens_ur5 ;',
                '    hw3:solvesForObject kb:{} ;'.format(obj['kb_id']),
                '    hw3:hasIKStatus "{}" ;'.format(obj['ik_status']),
                '    hw3:hasResidual "{}"^^xsd:double .'.format(obj['residual']),
                '',
            ]
        os.makedirs(os.path.dirname(KB_TTL), exist_ok=True)
        with open(KB_TTL, 'w') as f:
            f.write('\n'.join(lines))

    # ------------------------------------------------------------------
    # Reasoning layer: compile (if needed) and run the Jena reasoner
    # ------------------------------------------------------------------
    def _run_reasoner(self):
        lib_cp = _jena_lib()
        class_file = os.path.join(
            JAVA_CLASSES, 'course', 'taica', 'hw3', 'SemanticReasoner.class')
        if (not os.path.exists(class_file)
                or os.path.getmtime(JAVA_SRC) > os.path.getmtime(class_file)):
            os.makedirs(JAVA_CLASSES, exist_ok=True)
            subprocess.check_call(
                ['javac', '-cp', lib_cp, '-d', JAVA_CLASSES, JAVA_SRC])

        cp = os.pathsep.join([JAVA_CLASSES, lib_cp])
        out = subprocess.run(
            ['java', '-cp', cp, JAVA_MAIN,
             INFERRED_TTL, QUERY_RQ, BASE_TTL, KB_TTL],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            universal_newlines=True, check=True)

        executable = set()
        for line in out.stdout.splitlines():
            if line.startswith('RESULT|'):
                uri = line.split('|')[1]
                executable.add(uri.split('#')[-1])
        return executable

    # ------------------------------------------------------------------
    # Gate main flow
    # ------------------------------------------------------------------
    def _match_object(self, objects, pick_pos):
        best, best_d = None, self.pick_match_radius
        for obj in objects:
            d = float(np.linalg.norm(
                np.asarray(obj['position'][:2]) - np.asarray(pick_pos[:2])))
            if d < best_d:
                best, best_d = obj, d
        return best

    def audit_action(self, env, action, solve_ik):
        """Audit a Ravens pick-and-place action. Returns a verdict dict."""
        pick_pos = np.asarray(action['pose0'][0], dtype=float)

        objects = self._collect_scene_objects(env, solve_ik)
        self._write_kb(objects)
        executable = self._run_reasoner()
        target = self._match_object(objects, pick_pos)

        if target is None:
            allowed = False
            reason = ('no known scene object within {:.2f} m of pick position '
                      '{}'.format(self.pick_match_radius,
                                  np.round(pick_pos, 3).tolist()))
        elif target['kb_id'] in executable:
            allowed = True
            reason = ('kb:{} is an inferred hw3:ExecutableGraspTarget '
                      '(graspable AND reachable)'.format(target['kb_id']))
        elif not target['graspable']:
            allowed = False
            reason = ('kb:{} is kinematically reachable BUT not '
                      'hw3:GraspableObject (semantic exclusion)'
                      .format(target['kb_id']))
        else:
            allowed = False
            reason = ('kb:{} is hw3:GraspableObject BUT ik_status={} '
                      '(geometric exclusion)'.format(
                          target['kb_id'], target['ik_status']))

        if self.verbose:
            print('[SEMANTIC-AUDIT] scene objects:')
            for obj in objects:
                print('  - kb:{:<22s} graspable={:<5s} ik_status={:<15s} '
                      'residual={:.4f}'.format(
                          obj['kb_id'], str(obj['graspable']),
                          obj['ik_status'], obj['residual']))
            print('[SEMANTIC-AUDIT] ExecutableGraspTarget = {}'.format(
                sorted(executable)))
            print('[SEMANTIC-AUDIT] verdict: {} — {}'.format(
                'ALLOW' if allowed else 'REFUSE', reason))

        verdict = {
            'allowed': allowed,
            'reason': reason,
            'target': target,
            'executable': sorted(executable),
            'objects': objects,
        }
        self.last_verdict = verdict
        return verdict
