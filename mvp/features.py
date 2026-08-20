"""Phase 2: Grounded Evidence Encoding — STL 分解 → time_series_dict。

輸出格式對齊 ARE_MVP.md §4.2 的 `time_series_dict`。
"""

import numpy as np
import pandas as pd
from statsmodels.tsa.seasonal import STL

SEASONAL_PERIOD = 5  # period=13（季度週期）造成 STL trend 平滑 lag 過大（轉折點延後4週才反映），
# 實測 period=4/5 時 trend slope 能準確對上人為注入的 change point（見 Phase 0 DoD 驗證）


def compute_weekly_features(df: pd.DataFrame) -> list[dict]:
    """對 revenue 週序列做 STL 分解，逐週產出 time_series_dict。

    前 SEASONAL_PERIOD 週因 STL/rolling 統計量樣本不足，回傳 None 佔位。
    """
    revenue = df["revenue"].reset_index(drop=True)
    n = len(revenue)

    stl = STL(revenue, period=SEASONAL_PERIOD, robust=True)
    result = stl.fit()
    trend_component = result.trend
    resid_component = result.resid

    ma7 = revenue.rolling(window=7, min_periods=1).mean()
    trend_slope = trend_component.diff()
    wow = revenue.pct_change()
    residual_std = resid_component.rolling(window=13, min_periods=4).std()
    trend_mean_13 = trend_component.rolling(window=13, min_periods=4).mean()

    features: list[dict] = []
    for i in range(n):
        if i < 1 or pd.isna(trend_slope.iloc[i]) or pd.isna(residual_std.iloc[i]):
            features.append(None)
            continue

        slope = float(trend_slope.iloc[i])
        direction = "up" if slope > 0 else ("down" if slope < 0 else "flat")

        std_i = float(residual_std.iloc[i]) if residual_std.iloc[i] > 0 else np.nan
        zscore = (
            float((revenue.iloc[i] - trend_component.iloc[i]) / std_i)
            if std_i and not np.isnan(std_i)
            else None
        )
        cv = (
            float(std_i / trend_mean_13.iloc[i])
            if trend_mean_13.iloc[i] not in (0, None) and not pd.isna(trend_mean_13.iloc[i])
            else None
        )

        features.append(
            {
                "scale": "weekly",
                "trend": {
                    "direction": direction,
                    "slope": round(slope, 4),
                    "ma7": round(float(ma7.iloc[i]), 2),
                },
                "growth": {
                    "wow": round(float(wow.iloc[i]), 4) if not pd.isna(wow.iloc[i]) else None,
                },
                "volatility": {
                    "residual_std": round(std_i, 4) if std_i and not np.isnan(std_i) else None,
                    "cv": round(cv, 4) if cv is not None else None,
                },
                "deviation": {
                    "zscore": round(zscore, 4) if zscore is not None else None,
                },
            }
        )

    return features


if __name__ == "__main__":
    import pathlib

    csv_path = pathlib.Path(__file__).parent / "data" / "synthetic_weekly.csv"
    df = pd.read_csv(csv_path)
    feats = compute_weekly_features(df)

    change_point = 20
    print("第 18-22 週的 time_series_dict（驗證 DoD #1：trend.slope 應在第20週附近轉向，deviation.zscore 應顯著）：\n")
    for i in range(change_point - 2, change_point + 3):
        print(f"week {i} ({df.loc[i, 'date']}):", feats[i])
