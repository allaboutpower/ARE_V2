"""Phase 4: Evidence-Conditioned Generation。

沒有 ANTHROPIC_API_KEY 時的替代方案 —— 手動貼上模式：
1. 產生 prompt，存成 mvp/data/prompt_<date>.txt
2. 使用者自行複製貼到 claude.ai / ChatGPT 網頁版（免費），把回覆存成一個 .txt 檔
3. 用 --response-file 指向那個檔案，組成最終的 report_<date>.json

未來有 API key 時，只要在這支檔案加一個 --api 分支呼叫 anthropic SDK 即可，
prompt 組裝、Evidence Package、輸出格式完全不用改。
"""

import argparse
import json
import pathlib

import pandas as pd

from evidence_package import build_evidence_package
from factor_matching import load_factor_library, match_factors
from features import compute_weekly_features

DATA_DIR = pathlib.Path(__file__).parent / "data"


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


def get_week_evidence_package(df: pd.DataFrame, week_index: int) -> dict:
    feats = compute_weekly_features(df)
    library = load_factor_library()
    marketing_wow = df["marketing_cost"].pct_change()

    if feats[week_index] is None:
        raise ValueError(f"week {week_index} 的 feature 尚未有足夠資料（rolling window 不足）")

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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--week-index", type=int, required=True)
    parser.add_argument(
        "--response-file",
        type=str,
        default=None,
        help="手動從 claude.ai/ChatGPT 貼回的回覆存成的 .txt 檔路徑",
    )
    args = parser.parse_args()

    csv_path = DATA_DIR / "synthetic_weekly.csv"
    df = pd.read_csv(csv_path)
    week_date = df.loc[args.week_index, "date"]

    evidence_package = get_week_evidence_package(df, args.week_index)
    prompt = build_prompt(evidence_package)

    if args.response_file is None:
        prompt_path = DATA_DIR / f"prompt_{week_date}.txt"
        prompt_path.write_text(prompt, encoding="utf-8")
        print(f"Prompt 已存到 {prompt_path}")
        print(
            f"\n把裡面的內容複製貼到 claude.ai 或 ChatGPT 網頁版，"
            f"把回覆存成一個 .txt 檔，再用：\n"
            f"  python generate_report.py --week-index {args.week_index} "
            f"--response-file <你存的檔案路徑>\n"
            f"來完成這週的報告。"
        )
        print("\n--- Prompt 內容 ---\n")
        print(prompt)
    else:
        report_text = pathlib.Path(args.response_file).read_text(encoding="utf-8").strip()
        report_path = DATA_DIR / f"report_{week_date}.json"
        report_path.write_text(
            json.dumps(
                {
                    "week_date": week_date,
                    "evidence_package": evidence_package,
                    "matched_factors": evidence_package["relevant_factors"],
                    "report_text": report_text,
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        print(f"報告已存到 {report_path}")


if __name__ == "__main__":
    main()
