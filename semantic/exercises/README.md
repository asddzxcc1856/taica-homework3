# Task 4 Extension Exercises — Advanced Semantic Reasoning

Task 4 基礎要求你完成 Knowledge Graph Grounding、OWL Reasoning、Triple Store
Loading 與 SPARQL Query。本延伸練習要求你利用已建立的 Semantic Graph 進行
**Robot Capability Analysis、Trajectory Analysis、Cross-Robot Reasoning 與
Semantic Decision Making**。

先決條件:已跑完 `bash semantic/run_task4.sh`(建好 `semantic/store/`)。
執行方式:完成 `ex*.rq` 後 `bash semantic/exercises/run_exercises.sh`。

四個練習構成漸進式 Semantic Robot Learning Path:

```text
Exercise 1        Exercise 2         Exercise 3            Exercise 4
Data Validation → Process          → Knowledge          → Autonomous
                  Understanding      Interoperability     Decision Making
```

| Exercise | Semantic Skill | 使用技術 |
|---|---|---|
| 1 · Joint Limit Audit | Robot State Validation | SPARQL FILTER |
| 2 · Trajectory Convergence | Algorithm Process Understanding | RDF Sequence + Aggregation |
| 3 · Cross Robot Comparison | Interoperability | Shared Ontology + JOIN |
| 4 · Semantic Gate(加分) | Decision Reasoning | OWL EquivalentClass |

---

## Exercise 1 · Joint Limit Audit

**目的**:利用 Semantic Knowledge Graph 檢查 IK solver 產生的 joint
configuration 是否符合 robot joint limit。

需要結合的語意資訊(都已在圖中):

```text
IK Solution ─▶ Joint Configuration ─▶ JointState
                                        │ hw3:isStateOfJoint
                                        ▼
                            Joint (hasJointLowerLimit / hasJointUpperLimit)
```

```turtle
stu:my_ur5_joint1 a soma:RevoluteJoint ;
    hw3:hasJointLowerLimit "-4.712389"^^xsd:double ;
    hw3:hasJointUpperLimit "-1.570796"^^xsd:double .

stu:ik_target_mid_q_js1 a soma:JointState ;
    hw3:isStateOfJoint stu:my_ur5_joint1 ;
    soma:hasJointPosition "-5.2"^^xsd:double .   # 若出現這種值 → Violation
```

**任務**:撰寫 SPARQL(`ex1_joint_limit_audit.rq`)找出——
超過 upper limit 的 joint、低於 lower limit 的 joint、
以及哪個 IK computation 產生非法 configuration。

**預期結果格式**:

| Robot | Joint | Value | Limit | Result |
|---|---|---|---|---|
| UR5 | Joint1 | -5.2 | [-4.71, -1.57] | Violation |

(注意:參考 solver 會把解 clip 在限位內,違規列可能為 0——
這代表審計「通過」;想製造違規可暫時停用 ik.py 的 `np.clip`。)

**學習重點**:Semantic Layer 可以連接 Robot Model 與 Execution Result,
進行資料審計。

---

## Exercise 2 · Trajectory Convergence Analysis

**目的**:利用 IK solver trajectory 知識分析收斂行為。

```text
IKComputation ─▶ SolverTrajectory ─▶ TrajectorySample
                                       ├── atSolverIteration
                                       ├── hasSampleResidual
                                       └── hasEndEffectorPose
Sample0 ─dul:directlyPrecedes─▶ Sample1 ─▶ Sample2 ─▶ ...
```

**任務**:撰寫 SPARQL(`ex2_trajectory_convergence.rq`)回答——

1. **是否收斂?** 比較 initial residual 與 final residual
   (例:iteration 0 residual 0.084 → 末樣本 residual 0.003)。
2. **哪個 target 收斂較慢?** 依 `hw3:hasTotalIterationCount` 排序比較。
3. **需要多少 iteration?** 對樣本取 `MAX(?iteration)` 或直接讀
   `hasTotalIterationCount`。

Bonus(`ex2b_monotonicity_check.rq`):沿 `dul:directlyPrecedes` 找出
「殘差不減反增」的相鄰樣本對,討論震盪現象。

**學習重點**:Semantic Representation 不只保存結果,也能保存演算法過程。

---

## Exercise 3 · Cross Robot Capability Comparison

**目的**:利用共享 ontology 比較不同 Robot 的能力。

共用 target `hw3:target_mid` 是 join key:

```text
              target_mid
             /          \
           UR5          UR10
       OUT_OF_REACH    SOLVED
```

**任務**:撰寫 SPARQL(`ex3_cross_robot_comparison.rq`)列出
Robot / Target / IK Status,並回答分析問題:

> 為什麼 same target + different robot = different result?

從圖中的 DH 參數找證據(提示:對每台 robot 彙總 `SUM(ABS(?dh_a))`
近似臂長),可能原因:link length、DH parameter、workspace boundary。

**預期結果**:

| Robot | Target | Status |
|---|---|---|
| UR5 | target_mid | OUT_OF_REACH |
| UR10 | target_mid | SOLVED |

**學習重點**:Ontology 提供跨 Robot interoperability,使不同來源資料
可以直接比較。

---

## Exercise 4 · Semantic Gate(加分項目)

**目的**:將 Semantic Reasoning 從資料分析延伸到 Robot Decision Making——
由你定義 gate 的推理規則,讓 OWL reasoner 裁決哪些抓取動作可以執行。

```text
GraspableObject(感知層) ⊓ isKinematicallyReachable=true(數值層)
        │  ← 你定義的 equivalentClass 推理規則
        ▼
ExecutableGraspTarget  →  ALLOW;其餘 → REFUSE(附可解釋理由)
```

**與 Task 1–3 grounding 的銜接**(引導):gate 的兩個條件各來自一層——
graspability 是感知層知識、reachability 由 IK/執行結果 ground。
Task 3 的 grounding 已把 insertion 場景物件
(`stu:ell_block` graspable/reachable、`stu:insertion_fixture` 不可抓)
寫進圖中——完成本練習的規則後,同樣的推理也適用於那個真實場景。

**任務**:
1. 在 `exercises/ex4-semantic-gate.ttl` 的 STUDENT TODO 區定義
   equivalentClass 推理規則(詞彙與類宣告已在
   `ontology/hw3-ontology.ttl` §3b 提供;寫法參考 §4 的三個評估類)。
2. 注意:`ExecutableGraspTarget` 的成員**絕不手動 assert**——
   場景圖只有 graspable/reachable 事實,成員全由 reasoner 從你的規則導出
   (概念分類交給 OWL,數值判斷留在數值層)。
3. 用 `python semantic/exercises/ex4_semantic_gate.py` 測試,並在報告解釋
   每個 REFUSE 的理由。

**測試案例**:

| Case | Graspable | Reachable | 結果 |
|---|---|---|---|
| Object A(桌上積木) | ✓ | ✓ | **ALLOW** |
| Object B(固定 fixture) | ✗ | ✓ | **REFUSE**(語意排除) |
| Object C(工作空間外積木) | ✓ | ✗ | **REFUSE**(幾何排除) |

**學習重點**:OWL EquivalentClass 推理直接驅動 ALLOW / REFUSE 決策,
且每個判決都有可解釋的推理鏈。
