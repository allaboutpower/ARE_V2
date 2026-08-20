# ARE MVP — 獨立腳本原型

驗證 [ARE_MVP.md](../ARE_MVP.md) 定義的核心假設：**證據限定式生成（只能講 Evidence Package
裡有的東西）產出的解釋，品質是否接近人工分析師寫的解釋。**

本目錄是獨立於 `backend/` 的 Python 腳本原型，先把核心邏輯做出來、驗證跑得通，
之後才考慮要不要整合進現有系統。

## 架構

```
raw_data（合成時序）        factor_library.json（人工整理的因子清單）
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

## 安裝

```bash
cd mvp
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
cp .env.example .env   # 有 ANTHROPIC_API_KEY 的話填進去
```

## 逐步執行

### Phase 0：合成測試資料
```bash
./venv/bin/python generate_synthetic_data.py
```
產出 `data/synthetic_weekly.csv`（52 週），在第 20 週人為注入一次行銷預算削減事件
（`marketing_cost` 驟降 20%），作為有已知答案的驗證樣本。

### Phase 2：特徵計算（STL）
```bash
./venv/bin/python features.py
```
對 `revenue` 做 STL 分解，計算 `trend`/`growth`/`volatility`/`deviation` 四類統計量。
驗證：第 20 週附近 `trend.slope` 應由正轉負，對上人為注入的轉折點。

### Phase 3：Factor Library 比對
```bash
./venv/bin/python factor_matching.py
```
`factor_library.json` 是 6 條人工整理的因子（MVP 階段用固定清單代替弱監督萃取）。
驗證：第 20 週應比對到 `marketing_budget_cut`。

### Evidence Package 組裝
```bash
./venv/bin/python evidence_package.py
```
把 `time_series_dict` + `matched_factors` 組成固定 schema 的 JSON（見 ARE_MVP.md §4.2）。
`external_context` 固定為 `[]`（MVP 不做外部情境檢索）。

### Phase 4：報告生成

**有 `ANTHROPIC_API_KEY`**：在 `generate_report.py` 加 API 呼叫分支（尚未實作，
prompt 組裝邏輯已經在 `build_prompt()` 裡，接上 anthropic SDK 即可）。

**沒有 API key（手動貼上模式）**：
```bash
# 1. 產生 prompt，存成 txt
./venv/bin/python generate_report.py --week-index 20

# 2. 把印出來的內容複製貼到 claude.ai 或 ChatGPT 網頁版（免費）
#    把回覆存成一個 .txt 檔，例如 data/reply_week20.txt

# 3. 存回最終報告
./venv/bin/python generate_report.py --week-index 20 --response-file data/reply_week20.txt
```
產出 `data/report_<date>.json`，包含 Evidence Package + 報告文字，方便人工核對
「報告有沒有講到 Evidence Package 以外的東西」（DoD #3）。

## 目前狀態

| Phase | 狀態 |
|---|---|
| 0 合成資料 | 完成，STL 轉折點對上第20週 |
| 2 特徵計算 | 完成 |
| 3 Factor 比對 | 完成，6 條因子驗證無誤判 |
| Evidence Package | 完成，schema 對齊規劃書 §4.2 |
| 4 報告生成 | 手動貼上模式可用；API 自動呼叫待補 |
| 5 前端 | 未做（MVP 範圍先用終端機輸出） |
| 6 Pipeline 串接（`run_pipeline.py`） | 未做 |
| 6 正式 pairwise 評估 | 未做，需要真人評分 |

## 已知限制

- STL 的 `SEASONAL_PERIOD` 是針對這份合成資料調出來的（`period=5`），換資料大機率要重調
- `positive_anomaly`/`negative_anomaly` 因子會被 STL 殘差雜訊零星觸發
- `sustained_uptrend` 判斷門檻寬鬆，幾乎每週都觸發
- 目前只用固定隨機種子（`seed=42`）的合成資料驗證過，未涵蓋真實資料或多組隨機情境

## 不做的事（MVP 範圍排除，v2 再說）

- 弱監督因子萃取（沿用人工清單）
- 外部情境檢索
- 多粒度（日/週/月）並行
- 修改 `backend/`
