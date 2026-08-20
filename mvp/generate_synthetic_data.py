"""Phase 0: 產生合成週資料，含已知 change point，供 STL/特徵計算驗證用。

欄位依 `fake data/data_col.json` 規劃：
- core_time_series: date, revenue, marketing_cost, other_cost, profit
- factor_trigger_inputs: is_holiday_week, competitor_price_change
- ground_truth_only: injected_event, expected_anomaly（僅供驗證，不進 Evidence Package）
"""

import numpy as np
import pandas as pd

N_WEEKS = 52
CHANGE_POINT_WEEK = 20  # 0-indexed；第 20 週起 marketing_cost 驟降、revenue 斜率轉負
MARKETING_CUT_RATIO = 0.20
SEED = 42


def generate(n_weeks: int = N_WEEKS, seed: int = SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    dates = pd.date_range("2025-01-06", periods=n_weeks, freq="W-MON")
    week_idx = np.arange(n_weeks)

    # revenue: 上升趨勢 + 週季節性小波動 + 雜訊；第 20 週後斜率轉負
    base_slope = 8.0
    post_cut_slope = -4.0
    trend = np.where(
        week_idx < CHANGE_POINT_WEEK,
        1000 + base_slope * week_idx,
        1000 + base_slope * CHANGE_POINT_WEEK
        + post_cut_slope * (week_idx - CHANGE_POINT_WEEK),
    )
    seasonal = 15 * np.sin(2 * np.pi * week_idx / 52 * 4)
    noise = rng.normal(0, 8, n_weeks)
    revenue = trend + seasonal + noise

    # marketing_cost: 大致穩定，第 20 週起驟降 20%
    marketing_cost = np.full(n_weeks, 200.0) + rng.normal(0, 5, n_weeks)
    marketing_cost[CHANGE_POINT_WEEK:] *= (1 - MARKETING_CUT_RATIO)

    other_cost = np.full(n_weeks, 300.0) + rng.normal(0, 10, n_weeks)
    profit = revenue - marketing_cost - other_cost

    is_holiday_week = np.zeros(n_weeks, dtype=bool)
    competitor_price_change = np.zeros(n_weeks, dtype=bool)
    holiday_weeks = rng.choice(n_weeks, size=2, replace=False)
    competitor_weeks = rng.choice(
        [w for w in range(n_weeks) if w not in holiday_weeks], size=1, replace=False
    )
    is_holiday_week[holiday_weeks] = True
    competitor_price_change[competitor_weeks] = True

    injected_event = np.full(n_weeks, None, dtype=object)
    expected_anomaly = np.zeros(n_weeks, dtype=bool)
    injected_event[CHANGE_POINT_WEEK] = "week20_marketing_cut"
    expected_anomaly[CHANGE_POINT_WEEK] = True

    df = pd.DataFrame(
        {
            "date": dates.strftime("%Y-%m-%d"),
            "revenue": revenue.round(2),
            "marketing_cost": marketing_cost.round(2),
            "other_cost": other_cost.round(2),
            "profit": profit.round(2),
            "is_holiday_week": is_holiday_week,
            "competitor_price_change": competitor_price_change,
            "injected_event": injected_event,
            "expected_anomaly": expected_anomaly,
        }
    )
    return df


if __name__ == "__main__":
    import pathlib

    df = generate()
    out_path = pathlib.Path(__file__).parent / "data" / "synthetic_weekly.csv"
    df.to_csv(out_path, index=False)
    print(f"寫入 {out_path}（{len(df)} 週）")

    window = df.iloc[CHANGE_POINT_WEEK - 2 : CHANGE_POINT_WEEK + 3][
        ["date", "revenue", "marketing_cost", "injected_event", "expected_anomaly"]
    ]
    print("\n第 20 週附近資料：")
    print(window.to_string(index=False))