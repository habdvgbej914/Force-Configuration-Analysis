"""
Contrarian Auto-Verifier / 逆向自动验证器
Automatically checks past predictions against actual market prices.
Runs alongside daily_scan.py to maintain a living track record.

用法: python3 verify_predictions.py
也可在daily_scan.py之后自动调用
"""

import os
import json
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv
import requests

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
SCAN_HISTORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "daily_scan_history.json")
VERIFICATION_REPORT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "verification_report.json")

# Ticker map: price_estimate strings to yfinance tickers
# Some records may have price as text, we need the ticker to fetch actual price
TICKER_MAP = {
    "GLD": "GLD",
    "SLV": "SLV",
    "SPY": "SPY",
    "QQQ": "QQQ",
    "XLE": "XLE",
    "COPX": "COPX"
}

HORIZONS = {
    "1w": 7,
    "1m": 30,
    "3m": 90
}


def load_scan_history():
    """Load scan history / 加载扫描历史"""
    try:
        with open(SCAN_HISTORY_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_scan_history(history):
    """Save scan history / 保存扫描历史"""
    with open(SCAN_HISTORY_FILE, "w") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def get_price_on_date(ticker, target_date):
    """Get closing price on or near a specific date / 获取某日期的收盘价"""
    try:
        start = target_date - timedelta(days=5)
        end = target_date + timedelta(days=5)
        data = yf.download(ticker, start=start.strftime("%Y-%m-%d"),
                          end=end.strftime("%Y-%m-%d"), progress=False)
        if data.empty:
            return None

        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        # Find closest trading day on or after target
        available = data.index[data.index >= pd.Timestamp(target_date)]
        if len(available) > 0:
            return float(data.loc[available[0], "Close"])

        # If no date on/after, use closest before
        available = data.index[data.index < pd.Timestamp(target_date)]
        if len(available) > 0:
            return float(data.loc[available[-1], "Close"])

        return None
    except Exception as e:
        print(f"  Error fetching {ticker} price for {target_date}: {e}")
        return None


def parse_entry_price(price_str):
    """Extract numeric price from price_estimate string / 从价格字符串提取数值"""
    if not price_str or price_str == "N/A":
        return None

    # Remove common prefixes/suffixes
    clean = price_str.replace("$", "").replace(",", "").replace("~", "").strip()

    # Handle ranges like "$82-$84"
    if "-" in clean:
        parts = clean.split("-")
        try:
            return (float(parts[0].strip().replace("$", "")) +
                    float(parts[1].strip().replace("$", ""))) / 2
        except ValueError:
            pass

    # Handle parenthetical like "~4800 (down 2% weekly)"
    clean = clean.split("(")[0].strip()
    clean = clean.split(" ")[0].strip()

    try:
        return float(clean)
    except ValueError:
        return None


def grade_prediction(signal, return_pct):
    """Grade a prediction based on signal and actual return / 评估预测"""
    if return_pct is None:
        return "PENDING"

    if signal in ["STRONG BUY", "BUY"]:
        if return_pct > 0:
            return "CORRECT"
        else:
            return "WRONG"
    elif signal == "AVOID":
        if return_pct <= 0:
            return "CORRECT"
        else:
            return "MISSED"
    elif signal == "WATCH":
        if return_pct <= 5:
            return "CORRECT"
        else:
            return "MISSED"
    elif signal in ["HOLD", "CAUTION"]:
        return "NEUTRAL"
    else:
        return "NEUTRAL"


def verify_predictions():
    """Main verification logic / 主验证逻辑"""
    today = datetime.now().date()
    history = load_scan_history()

    if not history:
        print("No scan history found. Run daily_scan.py first.")
        return

    print(f"{'=' * 70}")
    print(f"CONTRARIAN AUTO-VERIFIER / 逆向自动验证器")
    print(f"Date: {today}")
    print(f"Total records to check: {len(history)}")
    print(f"{'=' * 70}")

    updated_count = 0
    newly_verified = []

    for record in history:
        ticker = record.get("ticker", "")
        scan_date_str = record.get("date", "")
        signal = record.get("signal", "")
        verification = record.get("verification", {})

        if not ticker or not scan_date_str:
            continue

        # Get yfinance ticker
        yf_ticker = TICKER_MAP.get(ticker)
        if not yf_ticker:
            continue

        try:
            scan_date = datetime.strptime(scan_date_str, "%Y-%m-%d").date()
        except ValueError:
            continue

        # Parse entry price
        entry_price = parse_entry_price(record.get("price_estimate", ""))

        # If we couldn't parse entry price, try to fetch it
        if entry_price is None:
            entry_price = get_price_on_date(yf_ticker, scan_date)
            if entry_price:
                record["entry_price_actual"] = entry_price

        if entry_price is None:
            continue

        # Check each horizon / 检查每个周期
        for horizon_label, days in HORIZONS.items():
            target_date = scan_date + timedelta(days=days)
            date_key = f"{horizon_label}_date"
            price_key = f"{horizon_label}_price"
            return_key = f"{horizon_label}_return"
            grade_key = f"{horizon_label}_grade"

            # Skip if already verified / 已验证则跳过
            if verification.get(return_key) is not None:
                continue

            # Skip if target date is in the future / 未来日期跳过
            if target_date > today:
                continue

            # Fetch actual price / 获取实际价格
            actual_price = get_price_on_date(yf_ticker, target_date)
            if actual_price is None:
                continue

            # Calculate return / 计算收益率
            return_pct = round((actual_price - entry_price) / entry_price * 100, 2)

            # Grade / 评分
            grade = grade_prediction(signal, return_pct)

            # Update record / 更新记录
            verification[date_key] = target_date.strftime("%Y-%m-%d")
            verification[price_key] = actual_price
            verification[return_key] = return_pct
            verification[grade_key] = grade

            record["verification"] = verification
            updated_count += 1

            icon = {"CORRECT": "✅", "WRONG": "❌", "MISSED": "⚠️",
                    "NEUTRAL": "⚪", "PENDING": "⏳"}.get(grade, "⚪")

            newly_verified.append({
                "ticker": ticker,
                "scan_date": scan_date_str,
                "horizon": horizon_label,
                "signal": signal,
                "entry_price": entry_price,
                "actual_price": actual_price,
                "return_pct": return_pct,
                "grade": grade,
                "icon": icon
            })

            print(f"  {icon} {ticker} {scan_date_str} | {horizon_label}: "
                  f"Entry ${entry_price:.2f} → ${actual_price:.2f} = {return_pct:+.2f}% "
                  f"| Signal: {signal} | Grade: {grade}")

    # Save updated history / 保存更新后的历史
    save_scan_history(history)

    # Generate verification report / 生成验证报告
    report = generate_report(history)
    with open(VERIFICATION_REPORT_FILE, "w") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # Print report / 打印报告
    print(f"\n{'=' * 70}")
    print("VERIFICATION SUMMARY / 验证总结")
    print(f"{'=' * 70}")
    print(f"  Records updated this run: {updated_count}")

    if report["total_verified"] > 0:
        print(f"\n  OVERALL STATS / 总体统计:")
        print(f"    Total verified predictions: {report['total_verified']}")
        print(f"    Correct: {report['correct']}")
        print(f"    Wrong: {report['wrong']}")
        print(f"    Missed: {report['missed']}")
        print(f"    Neutral: {report['neutral']}")
        if report["actionable_total"] > 0:
            print(f"    Actionable accuracy: {report['actionable_accuracy']:.1f}%")

        for horizon in ["1w", "1m", "3m"]:
            h_stats = report["by_horizon"].get(horizon, {})
            if h_stats.get("total", 0) > 0:
                print(f"\n  {horizon.upper()} HORIZON:")
                print(f"    BUY signals: {h_stats['buy_total']} | "
                      f"Correct: {h_stats['buy_correct']} | "
                      f"Accuracy: {h_stats['buy_accuracy']:.1f}%")
                if h_stats['buy_total'] > 0:
                    print(f"    Avg return: {h_stats['buy_avg_return']:+.2f}%")

        for ticker in report["by_ticker"]:
            t_stats = report["by_ticker"][ticker]
            if t_stats["total"] > 0:
                print(f"\n  {ticker}:")
                print(f"    Predictions: {t_stats['total']} | "
                      f"Correct: {t_stats['correct']} | "
                      f"Avg return (BUY): {t_stats['buy_avg_return']:+.2f}%")

    # Send Telegram if there are new verifications / 有新验证时发Telegram
    if newly_verified:
        send_verification_telegram(newly_verified, report)

    return report


def generate_report(history):
    """Generate comprehensive verification report / 生成综合验证报告"""
    report = {
        "generated": datetime.now().isoformat(),
        "total_records": len(history),
        "total_verified": 0,
        "correct": 0,
        "wrong": 0,
        "missed": 0,
        "neutral": 0,
        "actionable_total": 0,
        "actionable_accuracy": 0,
        "by_horizon": {},
        "by_ticker": {}
    }

    for horizon in ["1w", "1m", "3m"]:
        report["by_horizon"][horizon] = {
            "total": 0, "buy_total": 0, "buy_correct": 0,
            "buy_wrong": 0, "buy_avg_return": 0, "buy_accuracy": 0,
            "returns": []
        }

    for record in history:
        ticker = record.get("ticker", "")
        signal = record.get("signal", "")
        verification = record.get("verification", {})

        if ticker not in report["by_ticker"]:
            report["by_ticker"][ticker] = {
                "total": 0, "correct": 0, "wrong": 0,
                "buy_avg_return": 0, "buy_returns": []
            }

        for horizon in ["1w", "1m", "3m"]:
            grade = verification.get(f"{horizon}_grade")
            return_pct = verification.get(f"{horizon}_return")

            if grade is None or grade == "PENDING":
                continue

            report["total_verified"] += 1
            report["by_horizon"][horizon]["total"] += 1
            report["by_ticker"][ticker]["total"] += 1

            if grade == "CORRECT":
                report["correct"] += 1
                report["by_ticker"][ticker]["correct"] += 1
            elif grade == "WRONG":
                report["wrong"] += 1
                report["by_ticker"][ticker]["wrong"] += 1
            elif grade == "MISSED":
                report["missed"] += 1
            elif grade == "NEUTRAL":
                report["neutral"] += 1

            if signal in ["STRONG BUY", "BUY"]:
                h = report["by_horizon"][horizon]
                h["buy_total"] += 1
                if grade == "CORRECT":
                    h["buy_correct"] += 1
                if return_pct is not None:
                    h["returns"].append(return_pct)
                    report["by_ticker"][ticker]["buy_returns"].append(return_pct)

    # Calculate averages / 计算平均值
    actionable = report["correct"] + report["wrong"]
    report["actionable_total"] = actionable
    report["actionable_accuracy"] = (report["correct"] / actionable * 100) if actionable > 0 else 0

    for horizon in ["1w", "1m", "3m"]:
        h = report["by_horizon"][horizon]
        h["buy_accuracy"] = (h["buy_correct"] / h["buy_total"] * 100) if h["buy_total"] > 0 else 0
        h["buy_avg_return"] = (sum(h["returns"]) / len(h["returns"])) if h["returns"] else 0

    for ticker in report["by_ticker"]:
        t = report["by_ticker"][ticker]
        t["buy_avg_return"] = (sum(t["buy_returns"]) / len(t["buy_returns"])) if t["buy_returns"] else 0

    return report


def send_verification_telegram(newly_verified, report):
    """Send verification results to Telegram / 发送验证结果到Telegram"""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return

    lines = ["📋 *Verification Update*", ""]

    for v in newly_verified:
        lines.append(
            f"{v['icon']} {v['ticker']} ({v['scan_date']}) {v['horizon']}: "
            f"{v['return_pct']:+.1f}% | {v['signal']} → {v['grade']}"
        )

    if report["actionable_total"] > 0:
        lines.extend([
            "",
            f"📊 *Running Stats:*",
            f"  Accuracy: {report['actionable_accuracy']:.1f}% ({report['correct']}/{report['actionable_total']})"
        ])

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": "\n".join(lines),
            "parse_mode": "Markdown"
        }, timeout=30)
        print("  Verification Telegram sent.")
    except Exception as e:
        print(f"  Telegram error: {e}")


if __name__ == "__main__":
    verify_predictions()