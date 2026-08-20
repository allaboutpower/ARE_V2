---
title: ARE（Analytical Reasoning Engine）專案說明
---

# ARE — Analytical Reasoning Engine 專案說明

> 本文件整理 ARE 專案的動機、理論依據、MVP 實作內容與目前驗證結果，
> 供上傳 GitHub / 對外說明時使用。細節規劃見 [ARE_MVP.md](ARE_MVP.md)，
> 程式碼與逐步操作說明見 [mvp/README.md](mvp/README.md)。

---

## 1. 簡介

企業每週都會產出大量時序型業務指標（營收、成本、流量……），但「數字本身」
不等於「解釋」。目前常見的兩種做法都有明顯缺點：

* **純人工分析**：品質好、有因果推論，但耗時、無法規模化，且高度依賴分析師的
  經驗與當下記憶。
* **純 LLM 生成**：規模化沒問題，但容易「幻覺」——講出資料裡根本沒有的因果關係，
  或引用未經查證的外部知識，在商業決策場景中風險很高。

**ARE（Analytical Reasoning Engine）** 的目標是取兩者之長：用結構化的時序分析
把「證據」準備好，再用 LLM 做「證據限定式生成（evidence-conditioned
generation）」——LLM 只能根據給定的證據組織語言、生成解釋，不能引入證據之外
的臆測。這樣既有 LLM 的自然語言表達能力，又把幻覺的風險限制在「證據準不準」
這個更容易被稽核的問題上，而不是「LLM 有沒有亂講」。

本專案目前的落地版本是一個 **MVP**：只驗證一件事——
**證據限定式生成產出的解釋，品質是否接近人工分析師寫的解釋。**
其餘機制（弱監督因子萃取、外部情境檢索、多粒度分析等）刻意先擱置到 v2。

---

## 2. 論文引用概念

MVP 的架構依據論文
*Using LLMs for Explainable, Data-Driven Insight Generation from Time Series*
（Mundhra, Sato dos Santos & Benedikt, 2026）中提出的三元件框架設計，並將其
收斂為一個可以實際動手實作的最小版本。

論文的三個核心元件，以及 MVP 如何對應（簡化）實作：

| 論文元件 | 概念 | MVP 對應做法 |
|---|---|---|
| **(i) Factor Library / 弱監督因子萃取** | 從歷史語料中弱監督地萃取「可能造成時序變化的結構化因子」，形成可重複使用的因子庫 | 用**人工整理的固定清單**（6 條，`factor_library.json`）取代弱監督萃取；每條因子明確定義 `trigger_condition`（可程式化判斷的觸發條件）與 `narrative_template`（敘述模板），保留可回溯性（`source_note`） |
| **(ii) Grounded Evidence Encoding（時序編碼 + 生成）** | 把時序訊號轉換成 LLM 可讀的結構化「證據」，並基於證據做「證據限定式生成」，避免生成內容超出已知證據範圍 | 前半：STL 分解 + Trend/Growth/Volatility/Deviation 四類統計量，組成 `time_series_dict`；後半：把 `time_series_dict` + 比對到的因子組成 **Evidence Package**，作為 prompt 的唯一資訊來源，並在 prompt 中明確限制「只能引用 Evidence Package 裡出現過的數值與因子」 |
| **(iii) 評估（人機比較）** | 以人工分析師的解釋作為基準，評估 LLM 生成解釋的品質 | 縮小規模版：針對 held-out 週次，做 1-2 組 **GenX（生成報告）vs AnX（人工報告）** 的 pairwise 比較與質化回饋 |

論文中「證據限定式生成」是核心設計理念，也是 MVP 唯一要驗證的假設：
**只要限制 LLM 只能講證據裡有的東西，生成的解釋品質是否就能接近人工水準？**
外部情境檢索、多粒度並行、弱監督因子萃取準確度等問題，論文框架中也有涉及，
但 MVP 階段刻意不驗證，留給 v2。

---

## 3. 實作部分介紹

### 3.1 範圍界定

| 項目 | MVP 內 | 理由 |
|---|---|---|
| 時間粒度 | 單一粒度（週） | 先把單一路徑跑通 |
| 分解方法 | STL（`statsmodels`） | 成熟套件，不自己刻分解演算法 |
| 結構化解釋因子 | 人工整理固定清單（6 條） | 弱監督萃取需要語料規模，MVP 沒有 |
| 外部情境檢索 | 不做（欄位保留為空陣列） | 需要額外檢索基礎設施，先驗證核心邏輯 |
| 評估基準 | 小樣本人工 pairwise 比較 | 大規模自動化評估要等 pipeline 穩定 |
| 前端 | 終端機輸出 / JSON | 先能「看得到」即可 |

明確排除：預測模型、最佳化建議、非結構化資料輸入、即時串流資料。

### 3.2 系統架構

```
raw_data（合成週序列）        factor_library.json（人工整理的因子清單）
      │                            │
      ▼                            │
generate_synthetic_data.py         │
      │                            │
      ▼                            │
features.py（STL 分解 → time_series_dict）
      │                            │
      └──► factor_matching.py ◄────┘
                  │
                  ▼
      evidence_package.py（組裝 Evidence Package）
                  │
                  ▼
      generate_report.py（Evidence-Conditioned Generation）
                  │
                  ▼
          report_<date>.json
```

MVP 目前是獨立於 `backend/` 的 Python 腳本原型（放在 `mvp/` 目錄），
先把核心邏輯做出來、驗證跑得通，之後才考慮是否整合進正式系統。

### 3.3 各模組實作重點

**Phase 0 — 合成測試資料（`generate_synthetic_data.py`）**
在碰真實資料前先造一份「已知答案」的假資料：52 週的營收序列，帶週季節性與
上升趨勢；在第 20 週（0-indexed）人為注入一次 change point ——
`marketing_cost` 驟降 20%，同時 revenue 的趨勢斜率由 `+8.0` 轉為 `-4.0`。
這樣才能驗證「STL 分解算出來的轉折點，是否真的對上人為注入的事件」。

**Phase 2 — 特徵計算（`features.py`）**
對 `revenue` 做 STL 分解（`period=5`，實測後選定，能讓 trend slope 準確對上
change point，`period=13` 會有 4 週的延遲），逐週計算四類統計量並組成
`time_series_dict`：

* `trend`：方向（up/down/flat）、STL trend 分量的斜率、7 期移動平均
* `growth`：週增率（week-over-week）
* `volatility`：STL 殘差的滾動標準差、變異係數（CV）
* `deviation`：Z 分數（(實際值 - 趨勢值) / 殘差標準差），衡量單週偏離趨勢的程度

**Phase 3 — Factor Library 比對（`factor_matching.py`）**
`factor_library.json` 定義 6 條因子，每條都有可程式判斷的 `trigger_condition`
（例如 `marketing_cost_wow < -0.15`），比對邏輯用限制過的 `eval()`——白名單變數、
清空 `__builtins__`——把 `time_series_dict` 攤平的統計量與業務輸入
（`marketing_cost_wow`、`is_holiday_week`、`competitor_price_change`）
一起丟進去判斷，回傳符合的因子清單。

**Evidence Package 組裝（`evidence_package.py`）**
把 `time_series_dict` + 比對到的因子組成固定 schema 的 JSON（對齊
[ARE_MVP.md §4.2](ARE_MVP.md)），`external_context` 欄位固定為 `[]`——
保留這個欄位是為了 v2 加外部情境檢索時，prompt 和資料結構都不用改。

**Phase 4 — 報告生成（`generate_report.py`）**
把 Evidence Package 序列化進 prompt，並在 prompt 中明確要求：

1. 只能引用 Evidence Package 裡出現過的數值與因子，不得引入未提及的臆測。
2. `relevant_factors` 為空時必須誠實說明「查無相關因子」，不能硬掰因果關係。
3. 用繁體中文寫 3–5 句話，語氣像人工分析師的週報摘要。

因為目前沒有 `ANTHROPIC_API_KEY`，Phase 4 用「手動貼上模式」代替 API 自動呼叫：
腳本產出 prompt 存成 `.txt`，人工複製貼到 claude.ai / ChatGPT 網頁版，
再把回覆存回 `.txt`，由腳本組成最終的 `report_<date>.json`（同時保留
Evidence Package，方便人工核對「報告有沒有講到證據以外的東西」）。
`build_prompt()` 的邏輯已經寫好，未來要接 API 只需加一個呼叫分支，
prompt 組裝與輸出格式完全不用改。

---

## 4. 結果

### 4.1 Phase 0-3 驗證結果

* **STL 分解對上注入的轉折點**：第 20 週附近 `trend.slope` 由正轉負，
  與人為注入的行銷預算削減事件時間點吻合。
* **Factor 比對無誤判**：第 20 週的 `feature_dict` + `marketing_cost_wow`
  正確比對到 `marketing_budget_cut` 因子。
* **Evidence Package schema 穩定**：欄位結構對齊 ARE_MVP.md §4.2 規劃，
  每次組裝都是固定 schema 的 JSON。

### 4.2 實際生成範例（2025-05-26 週，week index 20）

Evidence Package：

```json
{
  "time_series_dict": {
    "scale": "weekly",
    "trend": { "direction": "down", "slope": -0.823, "ma7": 1143.92 },
    "growth": { "wow": -0.0002 },
    "volatility": { "residual_std": 7.1864, "cv": 0.0065 },
    "deviation": { "zscore": 0.9498 }
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

生成報告（人工貼到 LLM 網頁版取得的回覆）：

> 本週營收呈下降趨勢，斜率為 -0.823，七日移動平均落在 1143.92，週增率僅
> -0.02%，變動幅度不大；殘差標準差為 7.19、變異係數 0.0065，顯示波動度偏低、
> 走勢尚稱平穩，偏離程度（Z 分數 0.95）也仍在正常範圍內。就已知因子而言，
> 行銷支出下降可能是潛在影響因素之一，可能導致付費流量減少，惟目前無外部
> 情境資料可進一步佐證。整體來看，本週營收微幅走弱但趨勢平穩，建議持續
> 觀察行銷投放對流量轉換的影響。

人工抽查這份報告，每一句話都能回溯到 Evidence Package 裡的欄位
（斜率、MA7、週增率、殘差標準差、CV、Z 分數、`marketing_budget_cut` 因子），
沒有出現證據以外的臆測，符合 DoD #3 的要求。

### 4.3 Definition of Done 對照

| 判準 | 狀態 |
|---|---|
| 1. 合成資料的 STL 分解結果對上人為注入的 change point | ✅ 完成 |
| 2. Evidence Package 能穩定產出固定 schema 的 JSON | ✅ 完成 |
| 3. 生成報告中沒有一句話對應不到 Evidence Package（人工抽查） | ✅ 通過（單一樣本） |
| 4. 完成至少 1 組 GenX vs AnX 的 pairwise 比較 | ⏳ 未做，需要真人評分與人工分析師的對照報告 |

### 4.4 整體進度

| Phase | 狀態 |
|---|---|
| 0 合成資料 | 完成，STL 轉折點對上第 20 週 |
| 2 特徵計算 | 完成 |
| 3 Factor 比對 | 完成，6 條因子驗證無誤判 |
| Evidence Package | 完成，schema 對齊規劃書 §4.2 |
| 4 報告生成 | 手動貼上模式可用；API 自動呼叫待補 |
| 5 前端 | 未做（MVP 範圍先用終端機輸出） |
| 6 Pipeline 串接（`run_pipeline.py`） | 未做 |
| 6 正式 pairwise 評估 | 未做，需要真人評分 |

### 4.5 已知限制

* `SEASONAL_PERIOD=5` 是針對這份合成資料調出來的，換成真實資料大機率要重調。
* `positive_anomaly` / `negative_anomaly` 因子會被 STL 殘差雜訊零星觸發（誤報）。
* `sustained_uptrend` 判斷門檻寬鬆，幾乎每週都會觸發，區辨力不足。
* 目前只用固定隨機種子（`seed=42`）的合成資料驗證過一次，尚未涵蓋真實資料
  或多組隨機情境，也還沒有大樣本的人機比較評估。

### 4.6 尚未做的事（MVP 範圍排除，v2 再談）

* 弱監督因子萃取（沿用人工清單）
* 外部情境檢索（`external_context` 欄位保留但固定為空）
* 多粒度（日/週/月）並行分析
* 正式的、大樣本的 GenX vs AnX pairwise 評估
