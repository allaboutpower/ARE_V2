"""組裝 Evidence Package —— 餵給 LLM 的最終物件，schema 對齊 ARE_MVP.md §4.2。"""


def build_evidence_package(time_series_dict: dict, matched_factors: list[dict]) -> dict:
    """組裝 Evidence Package。

    `external_context` 固定為 []（MVP 不做外部情境檢索，
    保留欄位是為了 v2 加檢索時 prompt/資料結構不用改）。
    """
    return {
        "time_series_dict": time_series_dict,
        "external_context": [],
        "relevant_factors": matched_factors,
    }


if __name__ == "__main__":
    import json
    import pathlib

    import pandas as pd

    from factor_matching import load_factor_library, match_factors
    from features import compute_weekly_features

    csv_path = pathlib.Path(__file__).parent / "data" / "synthetic_weekly.csv"
    df = pd.read_csv(csv_path)
    feats = compute_weekly_features(df)
    library = load_factor_library()
    marketing_wow = df["marketing_cost"].pct_change()

    week = 20
    business_inputs = {
        "marketing_cost_wow": float(marketing_wow.iloc[week]),
        "is_holiday_week": bool(df.loc[week, "is_holiday_week"]),
        "competitor_price_change": bool(df.loc[week, "competitor_price_change"]),
    }
    matched = match_factors(feats[week], business_inputs, library)
    package = build_evidence_package(feats[week], matched)

    print(f"第 {week} 週（{df.loc[week, 'date']}）的 Evidence Package：\n")
    print(json.dumps(package, indent=2, ensure_ascii=False))
