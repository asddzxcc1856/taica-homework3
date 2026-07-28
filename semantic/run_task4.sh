#!/usr/bin/env bash
# =============================================================================
# TAICA HW3 — Task 4 one-command runner
#
#   STEP 1  Check the toolchain (java / javac / python)
#   STEP 2  Prepare Apache Jena 4.10.0 (incl. TDB2 triple store CLI tools)
#   STEP 3  Grounding: run the three per-task evaluation scripts
#           (ground_task1_fk.py / ground_task2_ik.py / ground_task3_insertion.py)
#           -> output/task{1,2,3}_*.ttl
#   STEP 4  OWL reasoning: Java Jena loads ontology + your graph + TA's graph,
#           materializes deductions -> output/inferred_graph.ttl
#   STEP 5  Load the TDB2 triple store (semantic/store/)
#   STEP 6  Run queries/q*.rq against the store, save results to output/q*.csv
#   STEP 7  Run score_semantic.py for scoring
#
# Usage (from the hw3 root or from semantic/):
#   bash semantic/run_task4.sh                     # uses your your_fk / your_ik
#   bash semantic/run_task4.sh --reference         # preview with reference solvers
#   bash semantic/run_task4.sh --group my-group-05 # set the provenance id
#
# Environment variables:
#   PYTHON     python interpreter (default: python; must be the taica-hw3 env)
#   JENA_HOME  an already-extracted apache-jena directory
#              (default: auto-download into semantic/.cache)
# =============================================================================
set -euo pipefail
cd "$(dirname "$0")"

JENA_VERSION=4.10.0
PYTHON="${PYTHON:-python}"
GROUND_ARGS=("$@")

echo "== STEP 1/7 | Checking toolchain =="
for tool in java javac; do
    command -v "$tool" >/dev/null 2>&1 || { echo "ERROR: '$tool' not found (JDK 11+ required)" >&2; exit 1; }
done
command -v "$PYTHON" >/dev/null 2>&1 || { echo "ERROR: python '$PYTHON' not found" >&2; exit 1; }
java -version 2>&1 | head -1
"$PYTHON" -c "import numpy, pybullet; print('python + numpy + pybullet OK')"

echo
echo "== STEP 2/7 | Preparing Apache Jena ${JENA_VERSION} (with TDB2 tools) =="
if [ -z "${JENA_HOME:-}" ]; then
    JENA_HOME="$PWD/.cache/apache-jena-$JENA_VERSION"
fi
if [ ! -d "$JENA_HOME/lib" ]; then
    echo "Jena not found at $JENA_HOME — downloading (~30 MB) ..."
    mkdir -p .cache
    TARBALL=".cache/apache-jena-$JENA_VERSION.tar.gz"
    MIRRORS=(
        "https://repo1.maven.org/maven2/org/apache/jena/apache-jena/$JENA_VERSION/apache-jena-$JENA_VERSION.tar.gz"
        "https://archive.apache.org/dist/jena/binaries/apache-jena-$JENA_VERSION.tar.gz"
    )
    ok=0
    for url in "${MIRRORS[@]}"; do
        echo "Fetching $url"
        if curl -fL -C - --retry 5 --retry-delay 2 -o "$TARBALL" "$url"; then ok=1; break; fi
        echo "WARN: mirror failed, trying next ..."
    done
    [ "$ok" -eq 1 ] || { echo "ERROR: could not download Apache Jena" >&2; exit 1; }
    tar -xzf "$TARBALL" -C .cache
fi
export JENA_HOME
echo "JENA_HOME = $JENA_HOME ($(ls "$JENA_HOME/lib"/*.jar | wc -l) jars)"

echo
echo "== STEP 3/7 | Grounding: per-task evaluation -> RDF graphs =="
if [ -n "${GROUND_SCRIPT:-}" ]; then          # overridable for TA testing
    "$PYTHON" "$GROUND_SCRIPT" ${GROUND_ARGS[@]+"${GROUND_ARGS[@]}"}
else
    for s in ground_task1_fk.py ground_task2_ik.py ground_task3_insertion.py; do
        echo "---- $s ----"
        "$PYTHON" "$s" ${GROUND_ARGS[@]+"${GROUND_ARGS[@]}"}
    done
fi

echo
echo "== STEP 4/7 | OWL reasoning (Java Jena) -> inferred_graph.ttl =="
CLASSES=java_semantic_engine/target/classes
SRC=java_semantic_engine/src/main/java/course/taica/hw3/SemanticReasoner.java
if [ ! -f "$CLASSES/course/taica/hw3/SemanticReasoner.class" ] || [ "$SRC" -nt "$CLASSES/course/taica/hw3/SemanticReasoner.class" ]; then
    echo "[JAVAC] compiling SemanticReasoner.java ..."
    mkdir -p "$CLASSES"
    javac -cp "$JENA_HOME/lib/*" -d "$CLASSES" "$SRC"
fi
java -cp "$CLASSES:$JENA_HOME/lib/*" course.taica.hw3.SemanticReasoner \
    output/inferred_graph.ttl - \
    ontology/hw3-ontology.ttl \
    output/task1_fk_graph.ttl output/task2_ik_graph.ttl output/task3_insertion_graph.ttl \
    ontology/ta-robot-graph.ttl

echo
echo "== STEP 5/7 | Loading the TDB2 triple store (semantic/store/) =="
rm -rf store
"$JENA_HOME/bin/tdb2.tdbloader" --loc store output/inferred_graph.ttl

echo
echo "== STEP 6/7 | SPARQL queries against the triple store =="
for q in queries/q1_robot_specs.rq queries/q2_reachable_targets.rq queries/q3_interop_compare.rq queries/q4_task_evaluation_report.rq; do
    name="$(basename "$q" .rq)"
    echo
    echo "---- $name ----"
    "$JENA_HOME/bin/tdb2.tdbquery" --loc store --query "$q"
    "$JENA_HOME/bin/tdb2.tdbquery" --loc store --query "$q" --results=CSV > "output/$name.csv"
done

echo
echo "== STEP 7/7 | Scoring Task 4 =="
"$PYTHON" score_semantic.py
