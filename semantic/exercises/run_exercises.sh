#!/usr/bin/env bash
# Task 4 Extension Exercises — run ex1~ex3 against the TDB2 triple store.
# Prerequisite: bash semantic/run_task4.sh has been run (builds semantic/store/).
# Exercise 4 (Semantic Gate Extension) lives in hw3_semantic/exercises/.
set -euo pipefail
cd "$(dirname "$0")/.."   # -> semantic/

JENA_VERSION=4.10.0
JENA_HOME="${JENA_HOME:-$PWD/.cache/apache-jena-$JENA_VERSION}"
[ -d "$JENA_HOME/lib" ] || { echo "ERROR: Jena not found at $JENA_HOME — run 'bash semantic/run_task4.sh' first." >&2; exit 1; }
[ -d store ] || { echo "ERROR: triple store not found — run 'bash semantic/run_task4.sh' first." >&2; exit 1; }

for q in exercises/ex1_joint_limit_audit.rq \
         exercises/ex2_trajectory_convergence.rq \
         exercises/ex2b_monotonicity_check.rq \
         exercises/ex3_cross_robot_comparison.rq; do
    echo
    echo "==== $(basename "$q") ===="
    "$JENA_HOME/bin/tdb2.tdbquery" --loc store --query "$q"
done
