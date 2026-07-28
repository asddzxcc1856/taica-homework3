#!/usr/bin/env bash
# =============================================================================
# TAICA HW3 — Task 4 一鍵執行腳本
#
#   STEP 1  檢查工具鏈 (java / javac / python)
#   STEP 2  準備 Apache Jena 4.10.0 (含 TDB2 triple store 指令列工具)
#   STEP 3  Grounding: 執行 ground_kinematics.py 產生 output/robot_graph.ttl
#   STEP 4  OWL 推理: Java Jena 讀入 本體 + 你的圖 + 助教的圖,
#           materialize 推論結果 -> output/inferred_graph.ttl
#   STEP 5  載入 TDB2 triple store (semantic/store/)
#   STEP 6  對 triple store 執行 queries/q*.rq,結果存 output/q*.csv
#   STEP 7  執行 score_semantic.py 評分
#
# 用法 (在 hw3 根目錄或 semantic/ 下皆可):
#   bash semantic/run_task4.sh                     # 用你的 your_fk / your_ik
#   bash semantic/run_task4.sh --reference         # 用參考解試跑 pipeline
#   bash semantic/run_task4.sh --group my-group-05 # 指定 provenance id
#
# 環境變數:
#   PYTHON     指定 python 直譯器 (預設: python;需為 taica-hw3 conda 環境)
#   JENA_HOME  指定已解壓的 apache-jena 目錄 (預設: 自動下載到 semantic/.cache)
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
echo "== STEP 3/7 | Grounding: numeric kinematics -> RDF (robot_graph.ttl) =="
GROUND_SCRIPT="${GROUND_SCRIPT:-ground_kinematics.py}"   # TA 測試時可覆寫
"$PYTHON" "$GROUND_SCRIPT" ${GROUND_ARGS[@]+"${GROUND_ARGS[@]}"}

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
    ontology/hw3-ontology.ttl output/robot_graph.ttl ontology/ta-robot-graph.ttl

echo
echo "== STEP 5/7 | Loading the TDB2 triple store (semantic/store/) =="
rm -rf store
"$JENA_HOME/bin/tdb2.tdbloader" --loc store output/inferred_graph.ttl

echo
echo "== STEP 6/7 | SPARQL queries against the triple store =="
for q in queries/q1_robot_specs.rq queries/q2_reachable_targets.rq queries/q3_interop_compare.rq; do
    name="$(basename "$q" .rq)"
    echo
    echo "---- $name ----"
    "$JENA_HOME/bin/tdb2.tdbquery" --loc store --query "$q"
    "$JENA_HOME/bin/tdb2.tdbquery" --loc store --query "$q" --results=CSV > "output/$name.csv"
done

echo
echo "== STEP 7/7 | Scoring Task 4 =="
"$PYTHON" score_semantic.py
