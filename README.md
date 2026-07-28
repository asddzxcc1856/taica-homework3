# HW3 — Robot Manipulation × Semantic Robot Knowledge

NYCU Physical AI / TAICA — UR5 運動學 + Transporter Network + 語意知識圖譜

## Learning Objectives

- **Forward Kinematics (FK)**:以 D-H 參數實作 6-DoF 手臂的正向運動學,計算末端執行器姿態與 Jacobian 矩陣。
- **Inverse Kinematics (IK)**:以 Jacobian-based 迭代法實作逆向運動學,由目標末端姿態解出關節組態。
- **Application of IK in Robot Manipulation**:將自己的 IK 整合進 Transporter Network 的 block insertion 任務,理解 IK 是完整操作 pipeline(prepick → grasp → preplace → insertion)中的一個元件,而不是孤立的數學函式。
- **Semantic Representation and Interoperability with a Triple Store**:用共用的機器人語彙 `<http://taica.course/hw3/ontology#>` 表達機器人規格與運動學計算結果,存入 RDF triple store,以 SPARQL 查詢。體驗「獨立開發的機器人程式,因為共用語意表示,而能互相分享、查詢、比較、重用知識」。

## 總覽

| Task | 內容 | 你要改的檔案 | 驗證指令 | 配分 |
|---|---|---|---|---|
| 1 | Forward Kinematics | `fk.py` → `your_fk()` | `python fk.py` | 20 |
| 2 | Inverse Kinematics | `ik.py` → `your_ik()` | `python ik.py` | 40 |
| 3 | Transporter Network | (整合,不改檔) | `python ravens/test.py ...` | 10 |
| 4 | Semantic Knowledge + Triple Store | `semantic/ground_kinematics.py` 2 個函式 + `semantic/queries/q3_interop_compare.rq` | `bash semantic/run_task4.sh` | 30 |

---

## Step 0. 環境安裝

**Step 0-1.** 建立 conda 環境並安裝 Python 依賴:

```bash
cd hw3
cd ravens
conda create --name taica-hw3 python=3.7 -y
conda activate taica-hw3
sudo apt-get update
sudo apt-get -y install gcc libgl1-mesa-dev
pip install -r requirements.txt
pip install opencv-python==4.5.5.64 transforms3d
cd ..
```

**Step 0-2.**(可選,Task 3 需要 GPU 時)安裝 CUDA 10.1 / cuDNN 7.6.5:

```bash
conda install cudatoolkit==10.1.243 -y
conda install cudnn==7.6.5 -y
```

**Step 0-3.**(Task 4 需要)安裝 JDK 11+,並確認:

```bash
sudo apt-get -y install openjdk-11-jdk
java -version && javac -version
```

Task 4 第一次執行時會自動下載 Apache Jena 4.10.0(約 30 MB,含 TDB2 triple store 工具),下載後快取在 `semantic/.cache/`,之後離線可用。

---

## Task 1. Forward Kinematics(20 分)

**Step 1-1.** 打開 [fk.py](fk.py),閱讀 `get_ur5_DH_params()` 的 D-H 參數表(依本專案的 `ur5.urdf`,與官方 spec 略有不同,一律以這張表為準)。

**Step 1-2.** 實作 `your_fk(DH_params, q, base_pos)`:
- 輸入:6 組 D-H 參數、6 個關節角 `q`、基座位置 `base_pos`
- 輸出:`(pose_7d, jacobian)` — 末端 7d 姿態 `[x, y, z, qx, qy, qz, qw]` 與 6×6 幾何 Jacobian
- **禁止使用任何 pybullet API**;函式尾端的 `adjustment` 區塊不要動

**Step 1-3.** 驗證(easy / medium / hard 三份測資;評分時會換成 ta1/ta2):

```bash
python fk.py          # 加 -g 開 GUI、-vp 顯示座標軸
```

預期輸出(每份測資 Error Count 皆為 0):

```
============================ Task 1 : Forward Kinematic ============================
- Testcase file : fk_test_case_easy.json
- Your Score Of Forward Kinematic : ... Error Count :    0 /  ...
- Your Score Of Jacobian Matrix   : ... Error Count :    0 /  ...
```

## Task 2. Inverse Kinematics(40 分)

**Step 2-1.** 打開 [ik.py](ik.py),實作 `your_ik(robot_id, new_pose, base_pos, ...)`:
- 用你的 `your_fk` 與 Jacobian 做迭代法(如 damped least squares / pseudo-inverse)
- 注意 delta x 的計算與 step rate 等超參數;評分只用**預設參數**呼叫,請把預設值調到最好
- 檔案內的 `pybullet_ik()` 是參考解,可用來對照行為,但你的實作不可呼叫 pybullet IK API

**Step 2-2.** 驗證:

```bash
python ik.py
```

預期輸出:三份測資 Error Count 皆為 0、Mean Error 在 1e-3 量級。

## Task 3. Transporter Network Manipulation Pipeline(10 分)

IK 在 pipeline 中的位置(請對照 [ravens/ravens/environments/environment.py](ravens/ravens/environments/environment.py) 的 `movep()` → `solve_ik()` → **`your_ik()`**):

```
Transporter Network → Predict Pick / Place Poses → IK → Joint Configuration
→ Robot Motion → Prepick → Grasp → Preplace → Insertion
```

**Step 3-1.** 下載測試資料與模型權重,放到指定位置:
- dataset:https://drive.google.com/file/d/1Jh8hAvraT1Zt1YfSNRT_lMJXbsK4Wcse/view → 解壓後整個 `block-insertion-easy-test/` 放到 `ravens/` 下
- checkpoint:https://drive.google.com/file/d/1cmFbqTzuu6IUJPlx1eOq2djRSubfM94H/view → 整個 `checkpoints/` 放到 `ravens/` 下

**Step 3-2.** 執行(用你的 IK 跑 10 筆測試):

```bash
cd ravens
CUDA_VISIBLE_DEVICES=-1 python ravens/test.py --assets_root=./ravens/environments/assets/ --disp=True --task=block-insertion-easy --agent=transporter --n_demos=1000 --n_steps=20000
```

預期輸出:10 筆 `Total Reward: 1.0 Done: True`。

---

## Task 4. Semantic Robot Knowledge and Triple Store(30 分)

把 Task 1/2 的「數值」轉成「語意」:機器人規格(D-H 參數、關節限制、DoF)與運動學結果(FK 姿態、IK 狀態)以共用語彙表示成 RDF,經 OWL 推理後載入 TDB2 triple store,用 SPARQL 查詢——並與**助教獨立產生的 UR10 知識圖**放在同一個 store 裡交叉比較。

```
你的 UR5 pipeline ──ground──> robot_graph.ttl ──┐
                                                ├─> OWL 推理 ─> TDB2 store ─> SPARQL
助教的 UR10 pipeline(已提供)ta-robot-graph.ttl ──┘
```

**Step 4-1. 讀懂共用語彙。** 打開 [semantic/ontology/hw3-ontology.ttl](semantic/ontology/hw3-ontology.ttl):
- 所有類別/屬性都定義在 namespace `http://taica.course/hw3/ontology#`(prefix `hw3:`)
- 三個**共用 target**(`hw3:target_near` / `target_mid` / `target_far`)是跨圖比較的 join key
- `hw3:SolvedIKComputation` 是**推理定義**的類別:沒有任何程式直接寫入,由 OWL reasoner 依「`IKComputation` 且 `hasIKStatus "SOLVED"`」推導

再打開 [semantic/ontology/ta-robot-graph.ttl](semantic/ontology/ta-robot-graph.ttl)(勿改):這是助教用另一支手臂(UR10)與另一套 IK 程式,對同一組 target 發佈的結果。

**Step 4-2. 實作 grounding(2 個函式)。** 打開 [semantic/ground_kinematics.py](semantic/ground_kinematics.py):
- `fk_result_to_triples()` **已完成**,是 triple 寫法的示範,請先讀懂
- TODO 1 `robot_spec_to_triples()`:把 UR5 的 D-H 參數 / 關節限制 / DoF 寫成 triples
- TODO 2 `ik_result_to_triples()`:把每個共用 target 的 IK 結果寫成 triples
- 注意:浮點數 literal 要寫 `"..."^^xsd:double`;`solvesForTarget` 要指向 `hw3:` namespace 的共用 target URI(寫成 `stu:` 的話跨圖查詢會 join 不到)

**Step 4-3. 完成互操作性查詢。** 打開 [semantic/queries/q3_interop_compare.rq](semantic/queries/q3_interop_compare.rq),依提示完成 SPARQL:對每個共用 target 列出**兩支手臂各自的 IK 狀態**(3 targets × 2 robots = 6 列)。q1、q2 已提供,可先讀懂再寫 q3。

**Step 4-4. 一鍵執行與評分。**

```bash
conda activate taica-hw3
bash semantic/run_task4.sh                # 用你的 your_fk / your_ik
# 尚未完成 Task 1/2 前,可先看 pipeline 長相:
# bash semantic/run_task4.sh --reference
```

腳本依序執行 7 步:工具鏈檢查 → 準備 Jena/TDB2 → grounding → OWL 推理(產出 `semantic/output/inferred_graph.ttl`)→ 載入 triple store(`semantic/store/`)→ 執行 q1–q3(結果存 `semantic/output/q*.csv`)→ 評分。

預期輸出結尾:

```
  [S1] q1 robot summary ................ OK  (+4)
  [S1] DH parameters (6 / 6 joints) ..... OK (+6)
  [S2] IK status of shared targets (3/3)  OK (+6)
  [S2] q2 inferred SolvedIKComputation . OK  (+4)
  [S3] q3 interop comparison matrix .... OK  (+10)
  Your Task 4 Score : 30.0 / 30.0
```

其中 q3 的正確結果會呈現互操作性的重點:`target_mid` 對你的 UR5 是 `OUT_OF_REACH`、對助教的 UR10 卻是 `SOLVED`——兩支從未見過彼此程式碼的 pipeline,靠共用語彙就能回答「哪個目標只有 UR10 搆得到?」

**Task 4 常見問題**
- `python` 不是 taica-hw3 環境 → `PYTHON=~/miniconda3/envs/taica-hw3/bin/python bash semantic/run_task4.sh`
- Jena 下載失敗 → 手動解壓 apache-jena-4.10.0 後 `export JENA_HOME=<路徑>` 再執行
- q2 是空的 → 表示推理沒生效,檢查 `hasIKStatus` 的 literal 是否恰為 `"SOLVED"`(大小寫、無多餘空白)

---

## Bonus Demo. Semantic Gate(不計分,建議體驗)

把 Task 4 的推理接回 Task 3 的模擬器:設 `SEMANTIC_AUDIT=1` 後,Ravens 每個 pick-and-place 動作執行前都會經過語意審查——pick 目標必須被 reasoner 推導為 `hw3:ExecutableGraspTarget`(語意上可抓取 **且** 幾何上 IK 可達),否則拒絕執行並給出理由:

```bash
conda activate taica-hw3
python semantic/demo_semantic_gate.py
```

三個示範情境:抓積木(ALLOW、reward 1.0)、抓固定座(REFUSE:語意排除)、抓工作空間外空點(REFUSE:查無物件)。

---

## 評分標準

| 項目 | 配分 |
|---|---|
| Task 1:FK 正確性(FK 10 + Jacobian 10,TA 測資) | 20 |
| Task 2:IK 正確性(TA 測資,只用預設參數) | 40 |
| Task 3:Transporter 10 筆測試 reward | 10 |
| Task 4:S1 規格 grounding 10 + S2 結果 grounding 10 + S3 SPARQL 互操作 10 | 30 |
| **總分** | **100** |

## 繳交內容

1. `fk.py`(完成 `your_fk`)
2. `ik.py`(完成 `your_ik`)
3. `semantic/ground_kinematics.py`(完成 2 個 TODO 函式)
4. `semantic/queries/q3_interop_compare.rq`(完成查詢)
5. 簡短報告:附上四個 Task 的執行截圖,並用 Task 4 的查詢結果說明「為何 `target_mid` 語意上對兩支手臂是同一個目標,幾何上卻只有一支搆得到」

> 注意:`semantic/output/`、`semantic/store/`、`semantic/.cache/` 為自動生成,無需繳交。

## Reference

- https://github.com/google-research/ravens
- https://automaticaddison.com/the-ultimate-guide-to-jacobian-matrices-for-robotics/
- Apache Jena / TDB2:https://jena.apache.org/documentation/tdb2/
