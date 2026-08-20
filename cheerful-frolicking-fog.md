## ARE MVP（論文對齊版）— 獨立腳本原型

## Context

`ARE md/ARE.md` 已改成對齊論文《Using LLMs for Explainable, Data-Driven Insight
Generation from Time Series》的三元件定位（弱監督因子萃取 / 接地證據編碼 / 接地生成 + 評估）。
`ARE md/ARE_MVP.md` 定義了 MVP 的簡化範圍：單一週粒度、STL 分解、人工整理的
factor_library（非弱監督萃取）、Evidence Package 固定 schema、evidence-conditioned
generation。

目前 `backend/` 裡的 `features.py` 用的是線性斜率＋z-score，不是規劃書指定的 STL，
且沒有 factor_library / evidence package / LLM 生成任何一塊。使用者要求：**先在
backend 之外，用獨立 Python 腳本把 MVP 核心邏輯做出來、驗證跑得通，之後才考慮要不要
整合進現有系統**。`fake data/data_col.json` 已經先規劃好了一份合成資料的欄位設計
（含 marketing_cost、factor 觸發欄位、ground-truth 用的 injected_event），本次要依照
這份規劃產生真正的資料檔。

## 目錄結構（新建 `mvp/`，完全不動 `backend/`）

```
mvp/
├── requirements.txt          # pandas, numpy, statsmodels, anthropic, python-dotenv
├── .env.example              # ANTHROPIC_API_KEY=
├── data/
│   └── synthetic_weekly.csv  # Phase 0 產出
├── generate_synthetic_data.py
├── features.py                # Phase 2：STL 分解 → time_series_dict
├── factor_library.json        # Phase 3：人工整理 5-6 條因子
├── factor_matching.py         # Phase 3：trigger_condition 比對邏輯
├── evidence_package.py        # 組裝 Evidence Package
├── generate_report.py         # Phase 4：呼叫 Anthropic API 生成解釋
├── run_pipeline.py            # CLI：串起 Phase 0→4，跑一週的完整流程
└── README.md                  # 對照 ARE_MVP.md 各 Phase 說明怎麼跑
```

## 各檔案設計

### 1. `generate_synthetic_data.py`（Phase 0）
- 依 `fake data/data_col.json` 的欄位造 52 週資料：
  `date, revenue, marketing_cost, other_cost, profit, is_holiday_week,
  competitor_price_change, injected_event, expected_anomaly`
- 基底：revenue 有穩定上升趨勢 + 週季節性小波動；marketing_cost 大致穩定。
- 注入一個已知 change point：例如第 20 週起 `marketing_cost` 驟降 20%，
  同時讓 revenue 斜率在該週後明顯轉負，該週 `injected_event="week20_marketing_cut"`、
  `expected_anomaly=True`。
- 另外在 1-2 週隨機標記 `is_holiday_week` / `competitor_price_change` 為 True，
  用來測試對應因子能不能被比對到。
- 輸出成 `mvp/data/synthetic_weekly.csv`。

### 2. `features.py`（Phase 2：Grounded Evidence Encoding）
- 用 `statsmodels.tsa.seasonal.STL` 對 revenue 週序列做分解（trend/seasonal/resid）。
- 計算規劃書 4.2 節格式的 `time_series_dict`：
  - `trend`: direction（依 STL trend 分量斜率變化）、slope、ma7
  - `growth`: wow（週對週成長率）
  - `volatility`: residual_std（STL resid 的標準差）、cv
  - `deviation`: zscore（該週值相對 STL trend 的偏離）
- 提供一個函式 `compute_weekly_features(df) -> list[dict]`，每週一筆，供後續逐週跑
  pipeline 使用。
- 驗證：跑在合成資料上，確認 `week20_marketing_cut` 附近 slope 有明顯轉向（對應
  ARE_MVP.md 的 DoD #1）。

### 3. `factor_library.json`（Phase 3）
- 5-6 條人工因子，格式照規劃書 4.1：`factor_name, trigger_condition,
  narrative_template, source_note`。內容對應合成資料能觸發到的情境，例如：
  - `marketing_budget_cut`：`marketing_cost_wow < -0.15`
  - `seasonal_holiday`：`is_holiday_week == True`
  - `competitor_pricing`：`competitor_price_change == True`
  - `positive_anomaly` / `negative_anomaly`：`deviation.zscore` 超過 ±2
  - `sustained_uptrend`：trend.slope 連續為正超過門檻

### 4. `factor_matching.py`（Phase 3）
- `match_factors(feature_dict, business_inputs, factor_library) -> list[dict]`
- 把 `trigger_condition` 字串用限制過的 `eval`（`{"__builtins__": {}}` + 白名單變數）
  對每週的 feature_dict + business_inputs（marketing_cost_wow、is_holiday_week 等）
  做比對，回傳符合的因子清單（含 narrative_template）。

### 5. `evidence_package.py`
- `build_evidence_package(time_series_dict, matched_factors) -> dict`
- 直接照規劃書 4.2 的 JSON schema 組裝，`external_context` 固定為 `[]`。

### 6. `generate_report.py`（Phase 4）
- 把 Evidence Package 序列化進 prompt，prompt 明確限制「只能引用 Evidence Package
  裡出現過的數值與因子，不得引入未提及的臆測」。
- 用 `anthropic` SDK（讀 `.env` 的 `ANTHROPIC_API_KEY`）呼叫，模型用
  `claude-sonnet-5`（沿用 backend `.env.example` 的 `AI_MODEL_NAME` 概念，但更新成
  現行模型 ID）。
- 回傳 `report_text`，連同 `matched_factors`、`evidence_package` 一起存成
  `mvp/data/report_<date>.json`，方便人工抽查「每句話是否能回溯到 Evidence
  Package」（DoD #3）。

### 7. `run_pipeline.py`
- CLI：`python run_pipeline.py --week 2024-01-20`（或 `--week-index 20`）
- 流程：讀 synthetic_weekly.csv → 算該週 features → 比對因子 → 組 Evidence
  Package → 呼叫 LLM → 印出並存檔報告。
- 印出時同時顯示 Evidence Package 原文，方便並排檢查（呼應規劃書 Phase 5 的「字典
  + 報告並排顯示」，先用終端機輸出取代前端）。

## 不做的事（本輪明確排除）
- 不動 `backend/`、不碰 FastAPI/Postgres。
- 不做 Phase 5 前端。
- 不做 Phase 6 正式的 pairwise 評估流程（先把 pipeline 跑通、報告品質可人工檢查即可）。
- 不做弱監督萃取（沿用 MVP 範圍：人工因子清單）。

## 驗證方式
1. `python generate_synthetic_data.py` 產生資料後，人工檢查 CSV 在第 20 週附近確實有
   marketing_cost 驟降、revenue 斜率轉向。
2. `python -c "from features import compute_weekly_features; ..."` 印出第 20 週附近的
   `trend.slope`，確認有轉向、且 `deviation.zscore` 在該週顯著（呼應 DoD #1）。
3. `python run_pipeline.py --week-index 20` 跑完整 pipeline，人工檢查輸出報告的每句話
   是否都能對應到印出的 Evidence Package 內容（DoD #3，人工抽查，非自動化）。
4. 額外跑一週沒有任何因子觸發的情況（例如平穩的第 5 週），確認系統誠實回報「查無相關
   因子」而不是硬掰因果推論（呼應規劃書第 8 節已知風險）。
