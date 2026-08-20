# ARE MVP — 獨立腳本原型
Analytical Reasoning Engine專案實作AI數據分析的過程中，透過將硬性條件套上分析評論語句，讓模型使用 **證據限定式生成產出的解釋** 進而提升AI分析的可解釋性、一致性、可重現性。
>Using LLMs for Explainable, Data-Driven Insight Generation from Time Series（Mundhra, Sato dos Santos & Benedikt, 2026）

此mvp版本只實作

```factor_library.json``` ```generate_synthetic_data.py ``` ```features.py``` ```factor_matching.py```
```evidence_package.py``` ```generate_report.py``` 

專案實作方法：
透過手動建立或是AI training，將過往分析報告中常出現的評論例如“第二十周週趨勢下降2.8%” 建立程式判斷條件
```if(trend growth<2.8%) do{return txt}```
使AI在分析資料時，不會產生直接接觸raw data也不需要參與分析過程，只需要在最後reasoning的部分，根據手上的證據json檔，去做出口語化的組織，降低AI出現幻覺、隨機誤差的情形。

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

# 結果比較
Ai 生成的趨勢分析報告確實都使用有通過條件的證據

### AI 讀取prompt後生成的分析報告

```
本週營收呈下降趨勢，斜率為 -0.823，七日移動平均落在 1143.92，週增率僅 -0.02%，變動幅度不大；殘差標準差為 7.19、
變異係數 0.0065，顯示波動度偏低、走勢尚稱平穩，偏離程度（Z 分數 0.95）也仍在正常範圍內。就已知因子而言，
行銷支出下降可能是潛在影響因素之一，可能導致付費流量減少，惟目前無外部情境資料可進一步佐證。整體來看，
本週營收微幅走弱但趨勢平穩，建議持續觀察行銷投放對流量轉換的影響。
```

| 報告句子 | 對應 Evidence Package |
|---|---|
| 斜率為 -0.823 | `trend.slope = -0.823` ✅ |
| 七日移動平均 1143.92 | `trend.ma7 = 1143.92` ✅ |
| 週增率 -0.02% | `growth.wow = -0.0002` ✅ |
| 殘差標準差 7.19 | `volatility.residual_std = 7.1864` ✅ |
| 變異係數 0.0065 | `volatility.cv = 0.0065` ✅ |
| Z分數 0.95 | `deviation.zscore = 0.9498` ✅ |
| 行銷支出下降可能導致付費流量減少 | `relevant_factors[0].narrative_template` ✅ |
| 「無外部情境資料可進一步佐證」 | `external_context = []`，誠實標示查無外部情境 ✅ |
| 「建議持續觀察行銷投放對流量轉換的影響」 | 這句是建議性結語，沒有引入新數值/新因果，算是從 factor narrative 合理延伸，沒有硬掰 |

## 已知限制

- STL 的 `SEASONAL_PERIOD` 是針對這份合成資料調出來的（`period=5`），換資料大機率要重調
- `positive_anomaly`/`negative_anomaly` 因子會被 STL 殘差雜訊零星觸發
- `sustained_uptrend` 判斷門檻寬鬆，幾乎每週都觸發
- 目前只用固定隨機種子（`seed=42`）的合成資料驗證過，未涵蓋真實資料或多組隨機情境
