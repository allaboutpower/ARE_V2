"""Phase 3: Factor Library 比對邏輯 — trigger_condition 字串比對。"""

import json
import pathlib

FACTOR_LIBRARY_PATH = pathlib.Path(__file__).parent / "factor_library.json"


def load_factor_library(path: pathlib.Path = FACTOR_LIBRARY_PATH) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _build_eval_context(feature_dict: dict, business_inputs: dict) -> dict:
    """把 feature_dict（time_series_dict）攤平成 trigger_condition 可用的變數。"""
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
    feature_dict: dict, business_inputs: dict, factor_library: list[dict]
) -> list[dict]:
    """對單週的 feature_dict + business_inputs 比對 factor_library，回傳符合的因子清單。

    trigger_condition 用限制過的 eval：僅允許白名單變數，__builtins__ 清空。
    """
    context = _build_eval_context(feature_dict, business_inputs)
    matched = []
    for factor in factor_library:
        try:
            is_match = eval(
                factor["trigger_condition"], {"__builtins__": {}}, context
            )
        except (TypeError, NameError):
            # 例如 zscore 為 None 時比較運算會丟 TypeError，視為不符合
            is_match = False
        if is_match:
            matched.append(
                {
                    "factor_name": factor["factor_name"],
                    "narrative_template": factor["narrative_template"],
                }
            )
    return matched


if __name__ == "__main__":
    import pandas as pd

    from features import compute_weekly_features

    csv_path = pathlib.Path(__file__).parent / "data" / "synthetic_weekly.csv"
    df = pd.read_csv(csv_path)
    feats = compute_weekly_features(df)
    library = load_factor_library()

    marketing_wow = df["marketing_cost"].pct_change()

    print("第 18-22 週比對到的因子（驗證：第20週應比對到 marketing_budget_cut）：\n")
    for i in range(18, 23):
        if feats[i] is None:
            continue
        business_inputs = {
            "marketing_cost_wow": (
                float(marketing_wow.iloc[i]) if not pd.isna(marketing_wow.iloc[i]) else None
            ),
            "is_holiday_week": bool(df.loc[i, "is_holiday_week"]),
            "competitor_price_change": bool(df.loc[i, "competitor_price_change"]),
        }
        matched = match_factors(feats[i], business_inputs, library)
        print(f"week {i} ({df.loc[i, 'date']}):", [m["factor_name"] for m in matched])
