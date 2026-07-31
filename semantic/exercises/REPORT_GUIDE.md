# Extension Exercises — 報告撰寫範圍與 GT 範例

本文件定義四個練習**應該推出的結論範圍**與**報告撰寫 scope**,並給每題一份
GT(ground-truth)範例答案供你遵循。GT 數據來自 TA 參考解的實跑結果;
你自己的數值可能略有差異(solver 超參數不同),**結論的推理方式**才是評分重點。

## 撰寫 scope(每題共通)

- 每題 **150–300 字** + 你的查詢結果表(截圖或貼表格皆可)。
- 必須涵蓋該題的**核心結論(C)**;**進階結論(A)** 選寫、可加分。
- 每個結論都要指出**證據在圖中的哪裡**(哪個 triple pattern、哪一列結果)——
  「因為圖上有 X,經過 Y 推理,所以 Z」是標準句型。
- **不要寫(X)** 清單裡的說法會被扣分:它們是常見的過度推論。

---

## Exercise 1 · Joint Limit Audit

### 你應該推出的結論

**核心(必寫)**
- **C1 審計結果**:全部 18 列(3 個 IK computation × 6 joints)`audit = OK`
  → 語意層證實 solver 輸出與機器人規格一致(審計「通過」也是結論!)。
- **C2 邊界證據**:`target_far` 的 joint1 = −4.712389(= lower limit)、
  joint2 = −2.3562(= lower limit)**恰好等於限位** → 這是 solver 的
  clip 在 OUT_OF_REACH 時把解推到限位邊界的直接證據。
- **C3 join 機制**:這個審計連接了兩張**獨立 grounding** 的圖
  (Task 1 的機器人規格 vs Task 2 的執行結果),唯一的橋是
  `hw3:isStateOfJoint`——若關節角還是 JSON 字串,這個 join 不可能成立。
- **C4 分層原則**:數值比較(`?angle < ?lower`)放在 SPARQL FILTER,
  不是 OWL——OWL 無法比較數值。

**進階(選寫加分)**
- A1:暫時停用 `ik.py` 的 `np.clip` 重跑,展示 audit 能精確定位
  「哪個 IK computation 的哪個 joint 違規」。
- A2:討論「值恰等於限位」的語意(閉區間 → 不算違規,但值得標記)。
- A3:同一模式可推廣到速度/力矩限制審計(只要 grounding 有該欄位)。

**不要寫(X)**
- ✗「OWL 推理發現了違規」——比較是 SPARQL 做的。
- ✗「0 違規代表 IK 完全正確」——審計只證明限位一致性,不證明到達目標
  (target_mid/far 全部 OK 但狀態是 OUT_OF_REACH)。

### GT 範例答案

> 我的查詢沿 `IKComputation → hasJointConfiguration → hasJointState
> —isStateOfJoint→ Joint(limits)` 把 Task 2 的執行結果 join 回 Task 1 的
> 機器人規格,對 18 筆 JointState 逐一與 `hasJointLowerLimit/UpperLimit`
> 比較(SPARQL FILTER;數值比較不屬於 OWL)。結果 18 列全部 OK,代表
> solver 輸出與規格一致。值得注意的是 `ik_target_far` 的 joint1(−4.712389)
> 與 joint2(−2.3562)恰好等於下限——這是 solver 在目標超出工作空間時
> 將解 clip 在限位邊界的證據,與其 `OUT_OF_REACH` 狀態互相印證。
> 這個審計之所以可能,是因為關節角被 ground 成結構化的 `soma:JointState`
> 並以 `isStateOfJoint` 指回關節個體;若是 JSON 字串,規格與結果無法 join。
> 但 0 違規只證明「限位一致性」,不代表 IK 到達了目標。

---

## Exercise 2 · Trajectory Convergence Analysis

### 你應該推出的結論

**核心(必寫)**
- **C1 是否收斂**:`target_near` 首樣本殘差 0.084313 → 末樣本 0.000527,
  trend = DECREASING → 收斂;且與 `hasIKStatus = "SOLVED"` 一致。
- **C2 需要幾次 iteration**:near 9 次;mid / far 跑滿 1000 次
  (`hasTotalIterationCount` = max_iters)→ 未收斂,與 OUT_OF_REACH 一致。
- **C3 哪個 target 收斂較慢**:依 `hasTotalIterationCount` 排序,
  near ≪ mid = far;「SOLVED 快、OUT_OF_REACH 耗盡迭代」是規律,不是巧合。
- **C4 震盪偵測(ex2b)**:far 的首末殘差**反增**(1.536 → 1.953,
  NOT_DECREASING);沿 `dul:directlyPrecedes` 自我 join 相鄰樣本,
  找到 2 對殘差上升的相鄰對 → DLS 對邊界外目標在工作空間邊界震盪。
- **C5 方法論**:圖保存了**演算法過程**(不只結果),所以「過程問題」
  (收斂性、單調性、速度)都變成可查詢的問題;`directlyPrecedes` 把
  「相鄰比較」變成一個 self-join。

**進階(選寫加分)**
- A1:mid 的殘差 0.633 → 0.557 有下降但永遠不足——幾何上到不了,
  與 Ex3 的臂長證據呼應。
- A2:討論降採樣(每軌跡 ≤ 6 樣本、保頭尾)的影響:單調性結論只在
  保留樣本之間成立。
- A3:估收斂率(相鄰樣本殘差比)並與 DLS 的理論行為對照。

**不要寫(X)**
- ✗「far 殘差上升代表 solver 有 bug」——那是對不可達目標的預期行為。
- ✗ 用樣本數(≤6)推論演算法複雜度——樣本是降採樣後的。

### GT 範例答案

> 軌跡在圖中是一條 linked list:樣本帶 `hasSampleIndex`,相鄰以
> `dul:directlyPrecedes` 相連。我用子查詢取每條軌跡的首(index 0)/末
> (MAX index)樣本比較殘差:`target_near` 0.084313 → 0.000527(DECREASING),
> 9 次迭代收斂,與 SOLVED 一致;`target_mid`/`target_far` 跑滿 1000 次
> 未收斂,與 OUT_OF_REACH 一致——收斂快慢直接由 `hasTotalIterationCount`
> 排序可得。ex2b 沿 `directlyPrecedes` 對相鄰樣本 self-join 並
> FILTER(?rNext > ?r),在 far 軌跡找到 2 對殘差反增的相鄰樣本
> (1.536→1.954、1.9537→1.9547):這不是 solver 錯誤,而是 DLS 對
> 工作空間外目標在邊界震盪的預期行為。這題的重點是:因為 grounding
> 保存了求解過程,「是否收斂/多快/是否單調」全部變成 SPARQL 問題。

---

## Exercise 3 · Cross-Robot Capability Comparison & Failure Diagnosis

### 你應該推出的結論

**核心(必寫)**
- **C1 比較矩陣**:3 targets × **3 robots**(你的 UR5、ta_ur5、ta_ur10)= 9 列。
  `target_near` 三台皆 SOLVED、`target_far` 三台皆 OUT_OF_REACH、
  `target_mid` 分歧(兩台 UR5 OUT_OF_REACH / UR10 SOLVED)。
- **C2 幾何解釋**:查詢內彙總 `SUM(ABS(?dh_a))` 得臂長估計
  UR5 ≈ 0.817 m vs UR10 ≈ 1.184 m——`target_mid` 的距離落在兩者之間,
  **link length(DH 參數)決定 workspace boundary**。
- **C3 失敗歸因(ex3b)**:三台機器人是對照實驗——
  你的 UR5 vs ta_ur5 = 同臂異解(狀態不一致 → **演算法問題**);
  ta_ur5 vs ta_ur10 = 同解異臂(狀態不一致 → **物理限制**)。
  預期診斷:near = OK、mid = PHYSICAL LIMIT of UR5、far = BEYOND BOTH ARMS;
  三列 mid/far 都不是演算法問題,是**手臂本身到不了**。
- **C4 互通機制**:共用 target URI 當 join key + `cora:Robot` 泛化
  → 三支獨立 pipeline 零 schema mapping 直接可比,查詢自動擴展到 N 台。

**進階(選寫加分)**
- A1:殘差量級對照(UR10 在 mid 0.0038 m vs UR5 0.557 m,差三個數量級)。
- A2:SUM|a| 是近似(忽略 d 偏移與姿態約束)的誠實討論。
- A3:故意讓你的 solver 變差(如 max_iters=5)重跑,展示 near 列翻成
  ALGORITHM ISSUE 而 mid/far 診斷不變——歸因邏輯的正確性驗證。

**不要寫(X)**
- ✗「armLength 是精確的工作空間半徑」。
- ✗ 沒有 ta_ur5 對照就把 mid 的失敗說成演算法問題——**對照組才是
  歸因的證據**,單看自己的狀態無法區分兩種原因。

### GT 範例答案

> store 裡有三台機器人:我的 UR5、TA 的 UR5(同臂、TA 參考解)與 TA 的
> UR10(同解、長臂)。ex3 矩陣(3×3 = 9 列)顯示 near 三台皆 SOLVED、
> far 三台皆 OUT_OF_REACH、mid 分歧:兩台 UR5 OUT_OF_REACH、UR10 SOLVED。
> 查詢內對 `dh_a` 彙總得臂長 0.817 vs 1.184 m,mid 落在兩者之間——
> 分歧由 link length 決定。ex3b 把歸因寫成巢狀 IF:我的狀態與 ta_ur5
> 一致(同臂異解無分歧)→ 排除演算法問題;mid 列 ta_ur10 SOLVED →
> 診斷為 PHYSICAL LIMIT of UR5;far 列三台皆失敗 → BEYOND BOTH ARMS。
> 若我的 IK 有 bug,near 列會變 ALGORITHM ISSUE 而 mid/far 不變——
> 對照組設計(同臂異解 / 同解異臂)讓「該修演算法還是該換手臂」
> 成為圖上可推理的問題,而這一切不需要任何格式轉換。

---

## Exercise 4 · Semantic Gate(加分項目)

### 你應該推出的結論

**核心(必寫)**
- **C1 推導鏈**:寫出 reasoner 導出成員的四步——
  (1) 場景事實 `objectA a GraspableObject`、`isKinematicallyReachable true`;
  (2) hasValue recognition:reachable=true → 進入匿名 Restriction 類;
  (3) intersectionRecognition:同時滿足兩個運算元 → 進入交集類;
  (4) equivalentClass:→ `objectA a ExecutableGraspTarget` ⇒ **ALLOW**。
- **C2 REFUSE 的解釋 = 缺哪個前提**:objectB 缺 `GraspableObject` type
  (第 3 步不成立)→ 語意排除;objectC 的 reachable = false
  (第 2 步不成立)→ 幾何排除。**每個判決都能指出缺失前提**。
- **C3 成員從未被 assert**:場景圖只有 graspable/reachable 事實;
  把你的等價公理刪掉重跑,推導集合變空——證明 ALLOW 是推理產物。
- **C4 分工**:`isKinematicallyReachable` 這個布林是**數值層**產生的;
  OWL 只做**概念分類**——門檻判斷不進 OWL。

**進階(選寫加分)**
- A1:`equivalentClass` vs `subClassOf` 的差別——等價才有「條件成立
  ⇒ 自動分類」的雙向推導;subClassOf 只有單向蘊含。
- A2:若要擴充第三個條件,為何要開**新類**而不是在原類上加第二條
  等價公理(兩條等價公理會使兩種定義互相等價,失去收緊效果)。
- A3:把同樣的規則套回 Task 3 場景圖(`stu:ell_block`/`stu:insertion_fixture`)
  ,說明 gate 對真實 insertion 場景的判決。

**不要寫(X)**
- ✗ 在場景圖手動 assert `a hw3:ExecutableGraspTarget`——會被視為未完成推理。
- ✗ 嘗試在 OWL 公理裡做數值比較。

### GT 範例答案

> 我定義的規則是 `ExecutableGraspTarget ≡ GraspableObject ⊓
> (isKinematicallyReachable value true)`。場景圖只含事實,不含任何
> ExecutableGraspTarget 的 assert。reasoner 對 objectA 的推導鏈為:
> 事實(GraspableObject、reachable=true)→ hasValue recognition(進入
> Restriction 匿名類)→ intersectionRecognition(同時滿足兩運算元)→
> equivalentClass 導出 `objectA a ExecutableGraspTarget` ⇒ ALLOW。
> objectB 被拒是因為缺 `GraspableObject` type(語意排除,第 3 步不成立);
> objectC 被拒是因為 reachable=false(幾何排除,第 2 步不成立)——
> 每個 REFUSE 都可指出缺失的前提,判決因此可解釋。我另外驗證:
> 把等價公理註解掉重跑,推導集合為空,證明成員完全是推理產物。
> 其中 reachable 布林由數值層(IK)產生,OWL 只負責概念分類——
> 這是本作業「數值判斷留在數值層、概念分類交給 OWL」的分層原則。
