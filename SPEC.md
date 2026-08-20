# HW3 規格書（Student Spec）— UR5 Kinematics × FSM Manipulation × Semantic Knowledge Graph

NYCU Physical AI / TAICA · 總分 100 分

> 本文件是作業的**正式規格**：目標、每一步驟的細節、安裝流程、評分規則、繳交項目。
> 圖文版引導手冊（含語意欄位的下游用途說明）另見 [docs/hw3-student-guide.html](docs/hw3-student-guide.html)。

---

## 1. 作業目標

完成本作業後，你應該能夠：

1. **Forward Kinematics（FK）**：用 classic D-H 參數實作 6-DoF 機械手臂的正向運動學，計算末端執行器（end-effector）的 7 維 pose 與 6×6 幾何 Jacobian。
2. **Inverse Kinematics（IK）**：以 Jacobian-based 迭代法（例如 Damped Least Squares）實作逆向運動學，從目標 pose 解出關節角度。
3. **IK/FK 在完整操作管線中的角色**：理解運動學不是孤立的數學函式——一個確定性的 **Finite State Machine** 會用「你的」IK 解算每一段移動、並在每次狀態轉移用「你的」FK 與模擬器互相驗證，完成 pick-and-place。
4. **語意接地（Semantic Grounding，REUSE 原則）**：把 FK/IK 的**執行過程數據**轉成結構化 RDF，重用現有標準機器人本體（IEEE 1872 CORA、SOMA、IEEE 1872 POS、QUDT 單位），而不是自創字串格式。
5. **SHACL 驗證**：撰寫 SHACL shapes，直接從語意化資料的數值中發現 IK/FK 執行過程的問題狀態（手臂超出範圍、未收斂），且你的驗證結果必須與助教的標準答案逐筆一致。

### 任務總覽

| Task | 內容 | 你要改的檔案 | 驗證指令 | 配分 |
|---|---|---|---|---|
| 1 | Forward Kinematics | `fk.py` 的 `your_fk()` | `python fk.py` | 20 |
| 2 | Inverse Kinematics | `ik.py` 的 `your_ik()` | `python ik.py` | 40 |
| 3 | FSM Manipulation Pipeline | 無（整合驗證，助教提供） | `python fsm_task.py` | 10 |
| 4 | Semantic Grounding + SHACL | `semantic/ground_execution.py` 2 個函式 + `semantic/shapes.ttl` 2 個 shapes | `bash semantic/run_task4.sh` | 30 |

---

## 2. 環境安裝（每一步都要做，依序執行）

### 需求一覽

| 項目 | 版本 / 說明 |
|---|---|
| 作業系統 | Linux（Ubuntu 20.04+ 建議）；其他平台需能裝 PyBullet |
| Python | **3.7**（透過 conda 建立，不要用系統 Python） |
| Python 套件 | `pybullet`、`numpy`、`scipy`（無深度學習框架、無資料集、無 checkpoint） |
| Java | **JDK 11+**（只有 Task 4 需要，供 Apache Jena 的 `shacl` CLI 使用） |
| 網路 | 第一次跑 Task 4 需下載 Apache Jena 4.10.0（約 30 MB），之後離線可用 |
| 磁碟 | < 1 GB |

### Step 0-1. 安裝 Miniconda（已裝過可跳過）

```bash
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh    # 一路同意，裝到 ~/miniconda3
source ~/.bashrc
conda --version                            # 驗證：印出 conda 版本即成功
```

### Step 0-2. 建立 Python 3.7 環境

```bash
conda create --name taica-hw3 python=3.7 -y
conda activate taica-hw3
python --version                           # 驗證：Python 3.7.x
```

之後**每次**做這份作業前都要 `conda activate taica-hw3`。

### Step 0-3. 安裝 Python 套件

```bash
pip install pybullet numpy scipy
```

驗證（三個 import 都不能報錯）：

```bash
python -c "import pybullet, numpy, scipy; print('pybullet', pybullet.getAPIVersion(), 'OK')"
```

### Step 0-4. 安裝 JDK 11+（Task 4 需要）

```bash
sudo apt-get -y install openjdk-11-jdk
java -version && javac -version            # 驗證：兩者皆印出 11 以上版本
```

### Step 0-5. 取得作業並確認檔案結構

```bash
cd hw3        # 作業根目錄（也就是本 SPEC.md 所在目錄）
```

你應該看到：

```
hw3/
├── fk.py                     # Task 1：你要實作 your_fk()
├── ik.py                     # Task 2：你要實作 your_ik()
├── fsm_task.py               # Task 3：助教提供，不需修改
├── test_case/                # Task 1/2 的 easy/medium/hard 測資（評分另有隱藏測資）
├── hw3_utils/, pybullet_planning/, pybullet_robot_envs/   # 助教提供的模擬環境，勿改
├── semantic/                 # Task 4
│   ├── ground_execution.py   #   ← 你要完成 2 個 TODO 函式
│   ├── shapes.ttl            #   ← 你要完成 2 個 TODO shapes
│   ├── common.py             #   序列化 helpers（助教提供）
│   ├── ontology/hw3-ontology.ttl        # REUSE 詞彙定義
│   ├── ta-faulty-execution.ttl          # 助教提供的 24 筆執行紀錄資料集
│   ├── ta-answer-key.json               # 上述資料集的標準答案
│   ├── ta-shapes-full.ttl               # 助教完整 SHACL（自動評分用）
│   ├── score_semantic.py                # 評分程式（你可以自己跑）
│   └── run_task4.sh                     # Task 4 一鍵執行
└── docs/hw3-student-guide.html          # 圖文版引導手冊
```

### Step 0-6. Task 4 工具鏈冒煙測試（可選，但建議）

第一次執行 `bash semantic/run_task4.sh` 時，STEP 1 會檢查 java/python/pybullet、STEP 2 會自動下載並快取 Apache Jena 到 `semantic/.cache/`。在你還沒實作 `your_fk` 前，STEP 3 會停在 `NotImplementedError` —— 這是正常的；只要 STEP 1、STEP 2 通過，環境就緒。

若 Jena 下載失敗：自行下載解壓 `apache-jena-4.10.0`，執行前 `export JENA_HOME=<解壓路徑>`。

---

## 3. Task 1 — Forward Kinematics（20 分）

**Step 1-1. 讀 D-H 表。** 打開 `fk.py`，`get_ur5_DH_params()` 是本作業 `ur5.urdf` 對應的 **classic D-H convention** 參數表。它與官方 UR5 規格略有差異——一律以這張表為準。

**Step 1-2. 實作 `your_fk(DH_params, q, base_pos)`。**

- **輸入**：6 組 D-H 參數、6 個關節角 `q`、基座位置 `base_pos`
- **輸出**：`(pose_7d, jacobian)` —— 末端 pose `[x, y, z, qx, qy, qz, qw]` 與 6×6 幾何 Jacobian
- **限制**：
  - 禁止呼叫任何 pybullet API（`p.getLinkState` 等都不行）
  - 函式尾端的 `adjustment` 區塊勿動（它把最後一個 frame 對齊到模擬器的 EE frame）
- **提示**：逐關節累乘 classic D-H 齊次變換；幾何 Jacobian 的線速度列為 `z_{i-1} × (p_end − p_{i-1})`、角速度列為 `z_{i-1}`

**Step 1-3. 驗證。**

```bash
python fk.py            # 跑 easy / medium / hard 三份測資
python fk.py -g         # GUI 模式：手臂會逐測資擺出對應姿態
python fk.py -g -vp     # 再加上末端 pose 視覺化
```

通過標準：三份測資的 **Error Count 皆為 0**（pose 與 Jacobian 各半）。評分使用**隱藏測資**（ta1/ta2），但難度分布與公開測資相同——差異只在關節角度覆蓋範圍。

---

## 4. Task 2 — Inverse Kinematics（40 分）

**Step 2-1. 實作 `ik.py` 的 `your_ik(robot_id, new_pose, base_pos, ...)`。**

- 用你的 `your_fk` 與其 Jacobian 做**迭代法**（建議 Damped Least Squares；pseudo-inverse 亦可）
- 每次迭代：算目前 pose → 算 6 維誤差 Δx（位置差 + 姿態差，姿態用 quaternion 差轉軸角）→ `Δq = Jᵀ(JJᵀ + λ²I)⁻¹ Δx × step_rate` → 更新 q 並 clip 到關節限位
- **評分只用預設參數呼叫你的函式**——把 `max_iters`、`stop_thresh`、damping、step rate 的預設值調到你最好的組合
- 同檔案的 `pybullet_ik()` 可拿來對照行為，但你的實作**不得呼叫 pybullet 的 IK API**

**Step 2-2. 驗證。**

```bash
python ik.py
```

通過標準：三份測資 Error Count 皆 0、Mean Error 在 1e-3（公尺）量級。三個難度的差異在**相鄰目標點的步距**（easy ≈ 6.1 mm、medium ≈ 15 mm、hard ≈ 25.5 mm，門檻 0.02 m）——步距越大，warm-start 越遠，迭代參數越吃緊。

---

## 5. Task 3 — FSM Manipulation Pipeline（10 分）

不用寫程式；這是你 Task 1/2 成果的**整合驗證**。`fsm_task.py`（助教提供）用確定性 FSM 跑 10 個 seeded pick-and-place 回合：

```
MOVE_TO_PREPICK → DESCEND_TO_PICK → GRASP → LIFT
    → MOVE_TO_PREPLACE → DESCEND_TO_PLACE → RELEASE → RETREAT
    → VERIFY → SUCCESS / FAILURE
```

每個移動狀態做**兩重驗證**：

| 驗證 | 內容 | 容差 | 失敗訊息 |
|---|---|---|---|
| IK | `your_ik` 解算 → 位置控制執行 → 實際末端位置 vs 指令 | ≤ 3 cm | `IK_MISS in <狀態>` |
| FK | `your_fk(量測到的關節角)` vs 模擬器末端位置 | ≤ 1 cm | `FK_MISMATCH in <狀態>` |

其他狀態：`DESCEND_TO_PICK` 逐步下降直到吸盤回報接觸（否則 `NO_CONTACT`）、`GRASP`/`RELEASE` 開關吸附約束（失敗為 `GRASP_FAILED`）、`VERIFY` 要求方塊落在目標 6 cm 內（否則 `PLACE_MISS`）。

**執行：**

```bash
python fsm_task.py        # 評分模式（headless），10 回合
python fsm_task.py -g     # GUI 模式：看 FSM 驅動手臂全程
```

通過標準：`10/10 SUCCESS`。失敗訊息會指出**管線中的哪個狀態、哪種驗證**壞掉——用它定位你的運動學問題（例如只在長距離移動的狀態 `IK_MISS`，通常是迭代次數或 step rate 不足）。

---

## 6. Task 4 — Semantic Grounding（REUSE）+ SHACL Validation（30 分）

把你 FK/IK 執行過程的「數字」變成「語意」，再讓語意層自己發現哪裡出了問題。你實作**兩件事**：

```
                         (1) grounding
your_fk / your_ik  ──>  ground_execution.py  ──>  output/data.ttl
  執行過程                （2 個 TODO 函式）
                                                  (2) SHACL
                          shapes.ttl（2 個 TODO shapes） vs data.ttl               → validation.ttl
                          shapes.ttl                     vs ta-faulty-execution.ttl → probe-validation.ttl
                                                            （助教 24 筆資料集，逐筆對答案）
```

### Step 4-1. 理解 REUSE 詞彙

打開 `semantic/ontology/hw3-ontology.ttl`。設計規則：**能重用現有標準詞彙就重用**——

| 概念 | 重用的標準詞彙 |
|---|---|
| 機器人 | `cora:Robot`（IEEE 1872 CORA） |
| 關節 | `soma:RevoluteJoint`；關節狀態 `soma:JointState` + `soma:hasJointPosition` |
| Pose | `soma:6DPose` = `pos:Position`（IEEE 1872 POS）位置元件 + quaternion 元件 |
| 單位 | QUDT IRI：`unit:M`、`unit:RAD` |

`hw3:` 命名空間只鑄造標準沒涵蓋的概念（FK/IK 計算事件、D-H 參數、狀態、距離）。**結構化表示、禁止 JSON 字串**：所有數值都是帶型別的 `xsd:double` literal，掛在結構化節點上。`semantic/common.py` 已提供序列化 helpers（`pose_to_ttl` / `joint_config_to_ttl`）——直接用。

### Step 4-2. GROUNDING — 實作 ontology-API 函式

打開 `semantic/ground_execution.py`：

| 函式 | 負責把什麼轉成 triples | 狀態 |
|---|---|---|
| `fk_computation_to_triples()` | 一次 FK 執行：輸入關節組態、EE pose、pose/Jacobian 誤差 | **worked example，先讀懂它** |
| `robot_spec_to_triples()` | 機器人規格：6 個關節的 D-H 參數 + 關節限位 | **TODO 1** |
| `ik_computation_to_triples()` | 一次 IK 執行：status、殘差、`hw3:hasTargetDistance`、結構化關節組態 | **TODO 2** |

執行流程（助教已寫好 `main()`）：跑你的 `your_fk`（3 筆測資 vs ground truth）與 `your_ik`（3 個固定目標 near/mid/far），全部寫進 **`output/data.ttl`**。

### Step 4-3. SHACL — 撰寫驗證 shapes

打開 `semantic/shapes.ttl`。FK 準確度 shape（`hasPoseError ≤ 0.005` 否則 `FK_INACCURATE`）是 worked example；你要照樣新增兩個：

| TODO | targetClass | 條件 | 違反時 `sh:message` 開頭 |
|---|---|---|---|
| 1 | `hw3:IKComputation` | `hw3:hasTargetDistance ≤ 0.90`（UR5 reach，公尺） | `ARM_OUT_OF_RANGE:` |
| 2 | `hw3:IKComputation` | `hw3:hasResidual ≤ 0.02`（課程收斂門檻，公尺） | `NO_CONVERGENCE:` |

**兩條硬規則**（評分程式依此判定）：

1. `sh:message` **必須以指定前綴開頭**（前綴比對）
2. 門檻必須用 **`sh:maxInclusive`（含等於）**——助教資料集裡有恰等於 0.90 / 0.02 / 0.005 的邊界案例，它們是**合格**的；寫成 `maxExclusive` 或抄錯門檻值會在邊界筆現形

### Step 4-4. 助教資料集 + 標準答案（S3 的評分方式）

`semantic/ta-faulty-execution.ttl` 是助教提供的 **24 筆** IK/FK 執行紀錄（11 筆有問題、13 筆乾淨，含邊界值與 3 筆雙旗標案例）；`semantic/ta-answer-key.json` 是標準答案。評分時用**你的** `shapes.ttl` 驗證這 24 筆，結果**逐筆**與答案比對：該筆的旗標集合必須與答案**完全一致**（不多報 false positive、不漏報 false negative）才算對。

S3 = 8 ×（有問題案例答對率）+ 2 ×（乾淨案例答對率）。答錯時評分報告會印出 `expected [...] , got [...]` 告訴你錯在哪幾筆。

### Step 4-5. 一鍵執行與評分

```bash
conda activate taica-hw3
bash semantic/run_task4.sh --group <你的組別編號>
```

五個步驟：工具鏈檢查 → 準備 Jena → grounding（`data.ttl`）→ SHACL 三份驗證報告 → 評分。滿分輸出：

```
  [S1] grounding structure (0 violations) OK  (+12)
  [S2] target_mid flagged ARM_OUT_OF_RANGE .... OK  (+2)
  [S2] target_far flagged ARM_OUT_OF_RANGE .... OK  (+2)
  [S2] target_near clean (no problem flags) ... OK  (+2)
  [S2] no JOINT_LIMIT_VIOLATION ............... OK  (+2)
  [S3] TA dataset vs answer key: faulty 11/11, clean 13/13 OK  (+10)
  Your Task 4 Score : 30.0 / 30.0
```

評分依據 `semantic/ta-shapes-full.ttl`（助教完整 SHACL）：`STRUCTURE:*` shapes 檢查你的 grounding（型別、必要屬性、`xsd:double`、每組態恰 6 個 `soma:JointState`）、問題 shapes 從你的數值重新發現問題、SHACL-SPARQL shape 交叉檢查每個關節角是否超限。

### Task 4 常見問題

| 症狀 | 處置 |
|---|---|
| `python` 不是 taica-hw3 環境 | `PYTHON=~/miniconda3/envs/taica-hw3/bin/python bash semantic/run_task4.sh` |
| Jena 下載失敗 | 手動解壓 apache-jena-4.10.0，`export JENA_HOME=<路徑>` |
| S1 出現 STRUCTURE 違規 | 打開 `output/ta-validation.ttl`，每筆 `sh:resultMessage` 都寫明缺哪個屬性/型別（經典錯誤：裸值 `0.0892` 而非 `"0.0892"^^xsd:double`） |
| S3 有 mismatch | 看評分印出的 `expected/got`；確認 message 前綴、`sh:maxInclusive`、門檻值三件事 |

---

## 7. 評分

| 項目 | 分數 |
|---|---|
| Task 1：FK 正確性（FK 10 + Jacobian 10，隱藏測資） | 20 |
| Task 2：IK 正確性（隱藏測資，只用預設參數呼叫） | 40 |
| Task 3：FSM 10 回合 pick-and-place 成功率 | 10 |
| Task 4：S1 grounding 結構 12 + S2 自身資料問題偵測 8 + S3 助教資料集對答案 10 | 30 |
| **總分** | **100** |

## 8. 繳交項目

1. `fk.py`（`your_fk` 完成）
2. `ik.py`（`your_ik` 完成）
3. `semantic/ground_execution.py`（兩個 TODO 函式完成）
4. `semantic/shapes.ttl`（兩個問題 shapes 完成）
5. 簡短報告：四個任務的執行截圖，加上說明你的 SHACL 驗證在 `output/validation.ttl` 與助教資料集（`output/probe-validation.ttl`）各發現了什麼

> `semantic/output/`、`semantic/.cache/` 為自動生成，**不要繳交**。

## 9. 參考資料

- Jacobian 教學：https://automaticaddison.com/the-ultimate-guide-to-jacobian-matrices-for-robotics/
- SHACL 規格：https://www.w3.org/TR/shacl/
- Apache Jena：https://jena.apache.org/
