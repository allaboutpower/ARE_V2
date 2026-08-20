---
title: ARE MVP 開發規劃書

---

# ARE MVP — 開發規劃書

本文件是 ARE（Analytical Reasoning Engine）研究方法論的落地版，
依 *Using LLMs for Explainable, Data-Driven Insight Generation from
Time Series*（Mundhra, Sato dos Santos & Benedikt, 2026）的三元件框架，
收斂成一個可以實際動手做的 MVP 範圍。



# 1. MVP 要驗證的核心假設

只驗證一件事：**證據限定式生成（只能講 Evidence Package 裡有的東西）
產出的解釋，品質是否接近人工分析師寫的解釋。**

不在 MVP 階段驗證的事（先擱置，v2 再說）：
* 弱監督因子萃取本身準不準
* 外部情境檢索有沒有幫助
* 多粒度（日/週/月）並行是否比單一粒度好



# 2. 範圍界定

| 項目 | MVP 內 | 理由 |
|---|---|---|
| 時間粒度 | 單一粒度（週） | 先把單一路徑跑通，避免一開始就處理多維度組合 |
| 分解方法 | STL（statsmodels） | 成熟套件，不用自己刻分解演算法 |
| 結構化解釋因子 | 人工整理固定清單（5-10 條） | 弱監督萃取需要語料規模，MVP 沒有 |
| 外部情境檢索 | 不做 | 需要額外的檢索基礎設施，先確認核心邏輯有效再加 |
| 評估基準 | 小樣本人工 pairwise 比較 | 大規模自動化評估要等有穩定 pipeline 才划算 |
| 前端 | 字典 + 報告並排顯示 | 先能「看得到」就好，不用做互動介面 |

**明確排除**：預測模型、最佳化建議、非結構化資料輸入、即時串流資料。



# 3. 系統架構（論文三元件的 MVP 簡化版）

```
raw_data（時序）          factor_library.json（人工清單）
      │                            │
      ▼                            │
Data Preprocessing                 │
（清洗、補值、STL 分解）             │
      │                            │
      ▼                            │
Analytical Feature Extraction      │
（Trend/Growth/Volatility/Deviation │
  → 文字字典）                       │
      │                            │
      └────────► Evidence Package ◄┘
      （字典 + 比對到的因子，
        MVP 無 external_context）
                  │
                  ▼
        AI Reasoning
      （Evidence-Conditioned Generation）
                  │
                  ▼
             ai_reports
```

三個元件對應：

* Factor Library 比對 → 對應論文 Component (i)（MVP 用人工清單代替弱監督萃取）
* Evidence Package 組裝 → 對應論文 Component (ii) 前半（時序編碼部分）
* Evidence-Conditioned Generation → 對應論文 Component (ii) 後半（生成部分）
* 小樣本人工比較 → 對應論文 Component (iii)（縮小規模版）



# 4. 資料模型

## 4.1 資料表

```
raw_data
├── id
├── date
├── metric          -- revenue / cost / profit
└── value

analytical_features
├── id
├── raw_data_ref
├── scale           -- 固定為 "weekly"
└── feature_dict     -- JSONB，Step 3 產出的文字字典

factor_library      -- MVP 版：人工維護的靜態清單
├── id
├── factor_name
├── trigger_condition   -- 例如："marketing_cost_wow < -0.15"
├── narrative_template  -- 例如："行銷支出下降，可能導致付費流量減少"
└── source_note         -- 這條因子的依據（人工填寫，之後可回溯）

ai_reports
├── id
├── analytical_features_ref
├── matched_factors     -- 這次比對到哪些 factor_library.id
├── report_text
└── created_at
```

## 4.2 Evidence Package（餵給 LLM 的最終物件）

```json
{
  "time_series_dict": {
    "scale": "weekly",
    "trend": { "direction": "down", "slope": -0.31, "ma7": 114.8 },
    "growth": { "wow": -0.060 },
    "volatility": { "residual_std": 1.1, "cv": 0.09 },
    "deviation": { "zscore": -2.1 }
  },
  "external_context": [],
  "relevant_factors": [
    {
      "factor_name": "marketing_budget_cut",
      "narrative_template": "行銷支出下降，可能導致付費流量減少"
    }
  ]
}
```

`external_context` 欄位保留但 MVP 固定為空陣列，這樣 v2 加外部情境檢索時，
prompt 跟資料結構都不用改。



# 5. 開發階段

## Phase 0：合成測試資料

在碰真實資料前，先造一份「已知答案」的假資料，才能驗證分解跟特徵計算對不對：

* 一段有明顯週季節性 + 上升趨勢的序列
* 在某個已知時間點注入一次 change point（例如某週開始斜率驟降）
* 目標：跑完 STL 之後，Trend slope 的變化應該要能對上你人為注入的那個轉折點

## Phase 1：後端骨架

* FastAPI 專案初始化
* 定義 `analytical_features`、`factor_library`、`ai_reports` 的 Pydantic schema
* PostgreSQL migration（`analytical_features.feature_dict` 用 JSONB）

## Phase 2：特徵計算 pipeline

* `raw_series → STL → 四類統計量 → feature_dict`
* 先用 Phase 0 的合成資料驗證正確性，再接真實資料

## Phase 3：Factor Library 比對邏輯

* 手動整理 5-10 條因子（每條都要寫 `trigger_condition`，讓比對邏輯可以自動判斷）
* 寫比對函式：`feature_dict + 其他業務指標 → 符合的 factor 清單`

## Phase 4：LLM 生成

* 把 Evidence Package 序列化成 prompt
* prompt 裡明確限制：只能引用 Evidence Package 裡出現過的數值與因子，不得引入未提及的臆測
* 欄位順序、命名固定，確保之後能重現實驗

## Phase 5：前端

* Evidence Package（字典 + 因子）與生成報告並排顯示
* 每句報告旁可標示對應到哪個證據來源（選配，先不做也可以）

## Phase 6：小規模驗證

* 找 1-2 段已有歷史人工解釋、但沒被拿進 Factor Library 的區段（held-out）
* 讓系統針對同一段資料生成 GenX
* 找 1 位懂業務的人，對 GenX 與 AnX 做 pairwise 比較 + 簡短質化回饋



# 6. 技術棧

延續你目前的開發習慣：

* 後端：FastAPI
* 前端：Next.js
* 資料庫：PostgreSQL（JSONB 存 feature_dict / factor 比對結果）
* 特徵計算：Python（pandas、statsmodels.tsa.seasonal.STL）



# 7. 評估表（Phase 6 用）

| 指標 | GenX | AnX | 備註 |
|---|---|---|---|
| Readability | | | |
| Logical Consistency | | | 每句是否可回溯 Evidence Package |
| Persuasiveness | | | |
| 整體偏好 | | | pairwise：哪份更好 / 打平 |



# 8. 已知風險

* **Factor Library 覆蓋率不足**：人工清單條數有限，遇到沒被涵蓋的異常模式時，
  生成報告會只停留在「描述數字」層級，缺乏因果解釋——這是預期中的 MVP 限制，
  不是 bug。
* **沒有外部情境時的解釋深度**：純內部資料可能無法解釋由外部事件造成的異常，
  MVP 階段這類異常只能誠實標示「查無相關因子／情境」，不強行生成因果推論。
* **小樣本評估的代表性**：Phase 6 只做 1-2 段人工比較，結論僅供方向參考，
  不是統計顯著的結果。



# 9. MVP 完成的判準（Definition of Done）

1. 合成資料的 STL 分解結果能對上人為注入的 change point
2. Evidence Package 能穩定產出固定 schema 的 JSON
3. 生成報告中沒有任何一句話對應不到 Evidence Package 裡的項目（人工抽查）
4. 完成至少 1 組 GenX vs AnX 的 pairwise 比較，並記錄在第 7 節的評估表中
---
