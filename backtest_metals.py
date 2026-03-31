"""
FCAS Backtest: Precious Metals & Base Metals
气象分析系统回测：贵金属与有色金属
Tests GLD (Gold ETF) and COPX (Copper Miners ETF)

用法: python3 backtest_metals.py
"""

import yfinance as yf
import pandas as pd
import json
import os

from contrarian_analysis_mcp import run_analysis, _analyze_intent

POSITIVE_INTENTS = {"strongly_supported", "supported_with_resistance", "supported_but_weak", "contested"}
NEGATIVE_INTENTS = {"not_viable", "challenged"}

# ============================================================
# GLD (Gold) Test Cases
# C3 = Internal Harmony (1=coordinated, 0=dissonant)
# ============================================================

GLD_CASES = [
    {
        "date": "2008-10-24",
        "label": "Financial Crisis Gold Selloff / 金融危机黄金抛售",
        "judgments": {"c1": 1, "c2": 1, "c3": 0, "c4": 1, "c5": 1, "c6": 1},
        # C3=0: liquidity crisis, forced selling across all assets, market internally broken
    },
    {
        "date": "2009-09-01",
        "label": "QE Gold Rally Start / QE黄金牛市启动",
        "judgments": {"c1": 1, "c2": 1, "c3": 1, "c4": 1, "c5": 1, "c6": 1},
        # C3=1: QE flowing smoothly into gold, monetary system functioning as designed
    },
    {
        "date": "2011-09-06",
        "label": "Gold Bubble Peak / 黄金泡沫顶部",
        "judgments": {"c1": 1, "c2": 1, "c3": 0, "c4": 1, "c5": 1, "c6": 1},
        # C3=0: parabolic move, speculative excess, internal market distorted
    },
    {
        "date": "2013-04-15",
        "label": "Gold Crash / 黄金崩盘",
        "judgments": {"c1": 0, "c2": 0, "c3": 0, "c4": 1, "c5": 1, "c6": 1},
        # C3=0: panic selling, ETF liquidation, internal chaos
    },
    {
        "date": "2015-12-17",
        "label": "First Fed Rate Hike / 首次加息",
        "judgments": {"c1": 0, "c2": 1, "c3": 1, "c4": 1, "c5": 1, "c6": 1},
        # C3=1: gold market orderly at bottom, central banks quietly accumulating
    },
    {
        "date": "2018-08-16",
        "label": "Gold Bear Market Low / 黄金熊市低点",
        "judgments": {"c1": 0, "c2": 1, "c3": 1, "c4": 1, "c5": 1, "c6": 1},
        # C3=1: orderly market, price near production cost, rational pricing
    },
    {
        "date": "2020-03-19",
        "label": "COVID Gold Selloff / 疫情黄金抛售",
        "judgments": {"c1": 1, "c2": 1, "c3": 0, "c4": 1, "c5": 1, "c6": 1},
        # C3=0: forced liquidation, margin calls, internal market dislocated
    },
    {
        "date": "2020-08-06",
        "label": "Gold All-Time High / 黄金历史新高",
        "judgments": {"c1": 1, "c2": 1, "c3": 0, "c4": 1, "c5": 1, "c6": 1},
        # C3=0: euphoric, overextended, internal positioning distorted
    },
    {
        "date": "2022-09-28",
        "label": "Strong Dollar Gold Selloff / 强美元黄金抛售",
        "judgments": {"c1": 0, "c2": 1, "c3": 1, "c4": 1, "c5": 1, "c6": 1},
        # C3=1: orderly selloff driven by dollar strength, central banks buying steadily
    },
    {
        "date": "2023-10-06",
        "label": "Pre-Rally Base / 大涨前底部",
        "judgments": {"c1": 1, "c2": 1, "c3": 1, "c4": 1, "c5": 1, "c6": 1},
        # C3=1: market well-functioning, BRICS buying visible, orderly base building
    },
    {
        "date": "2024-03-08",
        "label": "Gold Breakout / 黄金突破",
        "judgments": {"c1": 1, "c2": 1, "c3": 1, "c4": 1, "c5": 1, "c6": 1},
        # C3=1: clean breakout, institutional + central bank demand coordinated
    },
    {
        "date": "2025-10-15",
        "label": "Gold After Tariff Surge / 关税后黄金飙升",
        "judgments": {"c1": 1, "c2": 1, "c3": 0, "c4": 1, "c5": 1, "c6": 1},
        # C3=0: overcrowded trade, speculative excess building
    },
    {
        "date": "2026-01-29",
        "label": "Gold Peak ~$2800 / 黄金高点约$2800",
        "judgments": {"c1": 1, "c2": 1, "c3": 0, "c4": 1, "c5": 1, "c6": 1},
        # C3=0: maximum bullishness, internal positioning extremely one-sided
    },
    {
        "date": "2026-03-10",
        "label": "Gold Correction Iran War / 黄金回调伊朗冲突",
        "judgments": {"c1": 1, "c2": 0, "c3": 0, "c4": 1, "c5": 1, "c6": 1},
        # C3=0: profit taking, forced selling, internal disruption
    },
]

# ============================================================
# COPX (Copper) Test Cases
# ============================================================

COPX_CASES = [
    {
        "date": "2020-03-23",
        "label": "COVID Copper Crash / 疫情铜价崩盘",
        "judgments": {"c1": 0, "c2": 1, "c3": 0, "c4": 1, "c5": 1, "c6": 1},
        # C3=0: demand destruction, supply chains broken
    },
    {
        "date": "2021-05-10",
        "label": "Copper All-Time High / 铜价历史新高",
        "judgments": {"c1": 1, "c2": 1, "c3": 0, "c4": 1, "c5": 1, "c6": 1},
        # C3=0: speculative excess, supercycle euphoria
    },
    {
        "date": "2022-07-15",
        "label": "Copper Recession Fear Crash / 铜价衰退恐惧暴跌",
        "judgments": {"c1": 0, "c2": 0, "c3": 0, "c4": 1, "c5": 1, "c6": 1},
        # C3=0: China lockdowns, global recession fears, demand chain disrupted
    },
    {
        "date": "2023-10-23",
        "label": "Copper Low Before AI Demand / AI需求前铜价低点",
        "judgments": {"c1": 1, "c2": 1, "c3": 1, "c4": 1, "c5": 1, "c6": 1},
        # C3=1: market orderly, supply deficit recognized, price rational
    },
    {
        "date": "2024-05-20",
        "label": "Copper Squeeze / 铜价逼空",
        "judgments": {"c1": 1, "c2": 1, "c3": 0, "c4": 1, "c5": 1, "c6": 1},
        # C3=0: short squeeze, speculative distortion
    },
    {
        "date": "2025-03-13",
        "label": "Copper Tariff Fear / 铜关税恐惧",
        "judgments": {"c1": 1, "c2": 0, "c3": 0, "c4": 1, "c5": 1, "c6": 1},
        # C3=0: tariff disruption, demand uncertainty
    },
    {
        "date": "2026-03-10",
        "label": "Copper Iran War Selloff / 铜伊朗冲突抛售",
        "judgments": {"c1": 1, "c2": 0, "c3": 0, "c4": 1, "c5": 1, "c6": 1},
        # C3=0: war fear, recession fears, internal disruption
    },
]


def run_single_backtest(ticker, cases, label):
    print(f"\nDownloading {ticker} data...")
    data = yf.download(ticker, start="2008-01-01", end="2026-03-28", progress=False)
    if data.empty:
        print(f"ERROR: Could not download {ticker} data.")
        return []
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    print(f"Downloaded {len(data)} trading days.\n")

    results = []
    print(f"{'=' * 85}")
    print(f"FCAS BACKTEST: {label} ({ticker})")
    print(f"{'=' * 85}")

    for case in cases:
        date_str = case["date"]
        target_date = pd.Timestamp(date_str)
        available_dates = data.index[data.index >= target_date]
        if len(available_dates) == 0:
            print(f"\nSkipping {date_str}: no data")
            continue
        actual_date = available_dates[0]
        entry_price = float(data.loc[actual_date, "Close"])

        horizons = {"1w": 5, "2w": 10, "1m": 21, "3m": 63, "6m": 126}
        returns = {}
        entry_idx = data.index.get_loc(actual_date)
        for h_label, days in horizons.items():
            if entry_idx + days < len(data):
                fp = float(data.iloc[entry_idx + days]["Close"])
                returns[h_label] = round((fp - entry_price) / entry_price * 100, 2)
            else:
                returns[h_label] = None

        analysis = run_analysis(f"{ticker} @ {date_str}", case["judgments"])
        config = analysis["configuration"]
        intent = _analyze_intent(config, "seek_profit")
        intent_assessment = intent["overall"]
        intent_short = intent_assessment.upper().replace("_", " ")

        # Grade based on intent
        grades = {}
        for h in ["1w", "1m", "3m"]:
            ret = returns.get(h)
            if ret is None:
                grades[h] = "PENDING"
            elif intent_assessment in POSITIVE_INTENTS:
                grades[h] = "CORRECT" if ret > 0 else "WRONG"
            elif intent_assessment in NEGATIVE_INTENTS:
                grades[h] = "CORRECT" if ret <= 0 else "MISSED"
            else:
                grades[h] = "NEUTRAL"

        print(f"\n{'─' * 80}")
        print(f"📅 {date_str} | {case['label']}")
        print(f"   Price: ${entry_price:.2f} | Binary: {analysis['binary_code']}")
        print(f"   Config: {config['configuration_name']} / {config['configuration_zh']}")
        print(f"   Profit Intent: {intent_short}")
        print(f"     {intent['guidance']}")

        ret_str = "   Returns: "
        for h in ["1w", "2w", "1m", "3m", "6m"]:
            v = returns.get(h)
            ret_str += f" {h}={'N/A' if v is None else f'{v:+.1f}%'} |"
        print(ret_str.rstrip("|"))

        grade_str = "   Grades:  "
        for h in ["1w", "1m", "3m"]:
            g = grades[h]
            icon = {"CORRECT": "✅", "WRONG": "❌", "MISSED": "⚠️", "NEUTRAL": "⚪", "PENDING": "⏳"}[g]
            grade_str += f" {h}={icon}{g} |"
        print(grade_str.rstrip("|"))

        results.append({
            "ticker": ticker, "date": date_str, "label": case["label"],
            "entry_price": entry_price, "binary": analysis["binary_code"],
            "configuration": config["configuration_name"],
            "intent_assessment": intent_assessment,
            "returns": returns, "grades": grades,
        })

    return results


def print_summary(results, ticker, label):
    print(f"\n{'=' * 85}")
    print(f"SUMMARY: {label} ({ticker})")
    print(f"{'=' * 85}")

    for horizon in ["1w", "1m", "3m"]:
        pos = [r for r in results if r["intent_assessment"] in POSITIVE_INTENTS and r["grades"][horizon] != "PENDING"]
        if pos:
            correct = len([r for r in pos if r["grades"][horizon] == "CORRECT"])
            wrong = len([r for r in pos if r["grades"][horizon] == "WRONG"])
            avg = sum(r["returns"][horizon] for r in pos if r["returns"].get(horizon) is not None) / len(pos)
            acc = correct / len(pos) * 100
            print(f"\n  {horizon.upper()} — Supported intents:")
            print(f"    Total: {len(pos)} | Correct: {correct} | Wrong: {wrong} | Accuracy: {acc:.1f}% | Avg: {avg:+.2f}%")

    for horizon in ["1w", "1m", "3m"]:
        neg = [r for r in results if r["intent_assessment"] in NEGATIVE_INTENTS and r["grades"][horizon] != "PENDING"]
        if neg:
            correct = len([r for r in neg if r["grades"][horizon] == "CORRECT"])
            missed = len([r for r in neg if r["grades"][horizon] == "MISSED"])
            avg = sum(r["returns"][horizon] for r in neg if r["returns"].get(horizon) is not None) / len(neg)
            acc = correct / len(neg) * 100
            print(f"\n  {horizon.upper()} — Unsupported intents:")
            print(f"    Total: {len(neg)} | Correct: {correct} | Missed: {missed} | Accuracy: {acc:.1f}% | Avg: {avg:+.2f}%")

    neutral = [r for r in results if r["intent_assessment"] not in POSITIVE_INTENTS | NEGATIVE_INTENTS and r["returns"].get("3m") is not None]
    if neutral:
        print(f"\n  Neutral intents:")
        for r in neutral:
            print(f"    {r['date']} {r['label']}: {r['intent_assessment']} → 3m={r['returns']['3m']:+.1f}%")


def main():
    print("=" * 85)
    print("FCAS BACKTEST: PRECIOUS METALS & BASE METALS")
    print("=" * 85)

    gld_results = run_single_backtest("GLD", GLD_CASES, "Gold")
    print_summary(gld_results, "GLD", "Gold")

    copx_results = run_single_backtest("COPX", COPX_CASES, "Copper Miners")
    print_summary(copx_results, "COPX", "Copper Miners")

    # Combined
    all_results = gld_results + copx_results
    print(f"\n{'=' * 85}")
    print("COMBINED METALS SUMMARY")
    print(f"{'=' * 85}")

    for horizon in ["1w", "1m", "3m"]:
        pos = [r for r in all_results if r["intent_assessment"] in POSITIVE_INTENTS and r["grades"][horizon] != "PENDING"]
        if pos:
            correct = len([r for r in pos if r["grades"][horizon] == "CORRECT"])
            avg = sum(r["returns"][horizon] for r in pos if r["returns"].get(horizon) is not None) / len(pos)
            acc = correct / len(pos) * 100
            print(f"  {horizon.upper()} Supported: {len(pos)} trades | Correct: {correct} | Accuracy: {acc:.1f}% | Avg: {avg:+.2f}%")

    from collections import Counter
    print(f"\n  Intent Distribution:")
    i_counts = Counter(r["intent_assessment"] for r in all_results)
    for ia, count in i_counts.most_common():
        print(f"    {ia}: {count}")

    output_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backtest_metals_results.json")
    with open(output_file, "w") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"\nFull results saved to {output_file}")


if __name__ == "__main__":
    main()