"""Evidence-conditioned generation pipeline, ported from mvp/features.py,
mvp/factor_matching.py, mvp/evidence_package.py and mvp/generate_report.py.

CSV is parsed in-memory only — nothing here writes the raw CSV data to disk or DB.
Only the resulting prompt (see app/main.py) gets persisted.
"""

import json
import pathlib

import numpy as np
import pandas as pd
from statsmodels.tsa.seasonal import STL

SEASONAL_PERIOD = 5
FACTOR_LIBRARY_PATH = pathlib.Path(__file__).parent / "data" / "factor_library.json"

REQUIRED_COLUMNS = [
    "date",
    "revenue",
    "marketing_cost",
    "is_holiday_week",
    "competitor_price_change",
]


def compute_weekly_features(df: pd.DataFrame) -> list[dict | None]:
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

    features: list[dict | None] = []
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


def load_factor_library(path: pathlib.Path = FACTOR_LIBRARY_PATH) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _build_eval_context(feature_dict: dict | None, business_inputs: dict) -> dict:
    context = {
        "slope": feature_dict["trend"]["slope"] if feature_dict else None,
        "direction": feature_dict["trend"]["direction"] if feature_dict else None,
        "wow": feature_dict["growth"]["wow"] if feature_dict else None,
        "zscore": feature_dict["deviation"]["zscore"] if feature_dict else None,
        "residual_std": feature_dict["volatility"]["residual_std"] if feature_dict else None,
        "cv": feature_dict["volatility"]["cv"] if feature_dict else None,
    }
    context.update(business_inputs)
    return context


def match_factors(
    feature_dict: dict | None, business_inputs: dict, factor_library: list[dict]
) -> list[dict]:
    context = _build_eval_context(feature_dict, business_inputs)
    matched = []
    for factor in factor_library:
        try:
            is_match = eval(factor["trigger_condition"], {"__builtins__": {}}, context)
        except (TypeError, NameError):
            is_match = False
        if is_match:
            matched.append(
                {
                    "factor_name": factor["factor_name"],
                    "narrative_template": factor["narrative_template"],
                }
            )
    return matched


def build_evidence_package(time_series_dict: dict, matched_factors: list[dict]) -> dict:
    return {
        "time_series_dict": time_series_dict,
        "external_context": [],
        "relevant_factors": matched_factors,
    }


def build_prompt(evidence_package: dict) -> str:
    package_json = json.dumps(evidence_package, indent=2, ensure_ascii=False)
    return (
        "你是一位數據分析師，要根據以下 Evidence Package 寫一段營收解釋報告。\n\n"
        "嚴格規則：\n"
        "1. 只能引用 Evidence Package 裡出現過的數值與因子，不得引入未提及的臆測或外部知識。\n"
        "2. 如果 relevant_factors 是空的，必須誠實說明「查無相關因子」，不要硬掰因果關係。\n"
        "3. 報告用繁體中文，3-5句話，語氣像人工分析師寫的週報摘要。\n\n"
        f"Evidence Package：\n{package_json}\n\n"
        "請直接輸出報告內容，不要加其他說明文字。"
    )


def validate_columns(df: pd.DataFrame) -> None:
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"CSV 缺少必要欄位：{missing}")


def list_valid_weeks(df: pd.DataFrame) -> list[dict]:
    """回傳有足夠 rolling window 資料、可以產生 prompt 的週次清單。"""
    feats = compute_weekly_features(df)
    return [
        {"week_index": i, "week_date": str(df.loc[i, "date"])}
        for i in range(len(feats))
        if feats[i] is not None
    ]


def build_week_evidence_package(df: pd.DataFrame, week_index: int) -> dict:
    if week_index < 0 or week_index >= len(df):
        raise ValueError(f"week_index {week_index} 超出範圍")

    feats = compute_weekly_features(df)
    if feats[week_index] is None:
        raise ValueError(f"week {week_index} 的 feature 尚未有足夠資料（rolling window 不足）")

    library = load_factor_library()
    marketing_wow = df["marketing_cost"].pct_change()

    business_inputs = {
        "marketing_cost_wow": (
            float(marketing_wow.iloc[week_index])
            if not pd.isna(marketing_wow.iloc[week_index])
            else None
        ),
        "is_holiday_week": bool(df.loc[week_index, "is_holiday_week"]),
        "competitor_price_change": bool(df.loc[week_index, "competitor_price_change"]),
    }
    matched = match_factors(feats[week_index], business_inputs, library)
    return build_evidence_package(feats[week_index], matched)
