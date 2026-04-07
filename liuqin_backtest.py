"""
liuqin_backtest.py - 符化六亲回测脚本
=========================================

使用方法 (本地):
  cd ~/Desktop/自主项目/fcas/
  python liuqin_backtest.py

依赖:
  - fcas_engine_v2.py (排盘引擎，需在同目录)
  - assess_fuhua_liuqin.py (六亲评估模块，需在同目录)
  - data/json/ 目录下的标的数据文件

逻辑:
  1. 遍历574周(或可用周数)
  2. 每周对8标的排盘 + 符化六亲评估
  3. 记录评估标签 + 1W/4W/13W实际收益
  4. 输出JSON结果 + 统计摘要
"""

import json
import os
import sys
from datetime import datetime, timedelta

# 动态导入，兼容不同环境
try:
    from fcas_engine_v2 import paipan
    print("[OK] fcas_engine_v2.paipan 导入成功")
except ImportError:
    try:
        from fcas_engine import paipan
        print("[OK] fcas_engine.paipan 导入成功 (旧版)")
    except ImportError:
        print("[ERROR] 找不到排盘引擎! 请确认 fcas_engine_v2.py 在当前目录")
        sys.exit(1)

from assess_fuhua_liuqin import (
    assess_stock_liuqin, assess_all_stocks_liuqin,
    STOCK_INFO, PALACE_WUXING, get_seasonal_strength
)


# ============================================================
# 配置
# ============================================================

# 8个核心回测标的
BACKTEST_STOCKS = [
    '000651.SZ', '000063.SZ', '000858.SZ', '600276.SH',
    '600036.SH', '600547.SH', '601318.SH', '601857.SH',
]

# 数据目录
DATA_DIR = 'data/json'

# 输出文件
OUTPUT_FILE = 'liuqin_backtest_results.json'

# 回测参数
HORIZONS = {
    '1W': 1,     # 1周
    '4W': 4,     # 4周
    '13W': 13,   # 13周(一季)
}

# 地支列表 (用于月支推导)
DIZHI = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']

# 月支对应 (简化: 1月=寅, 2月=卯, ...)
MONTH_TO_BRANCH = {
    1: '寅', 2: '卯', 3: '辰', 4: '巳', 5: '午', 6: '未',
    7: '申', 8: '酉', 9: '戌', 10: '亥', 11: '子', 12: '丑',
}


# ============================================================
# 数据加载
# ============================================================

CODE_TO_ALIAS = {
    '000651.SZ': 'gree',
    '000063.SZ': 'zte',
    '000858.SZ': 'wuliangye',
    '600276.SH': 'hengrui',
    '600036.SH': 'cmb',
    '601318.SH': 'ping_an',
    '601857.SH': 'petrochina',
    '601012.SH': 'longi',
}

def load_stock_data(stock_code):
    """加载标的周数据"""
    alias = CODE_TO_ALIAS.get(stock_code)
    possible_names = []
    if alias:
        possible_names.append(f"{alias}_weekly.json")
        possible_names.append(f"{alias}.json")
    possible_names += [
        f"{stock_code}_weekly.json",
        f"{stock_code}.json",
        f"{stock_code}_data.json",
    ]

    for name in possible_names:
        path = os.path.join(DATA_DIR, name)
        if os.path.exists(path):
            with open(path, 'r') as f:
                data = json.load(f)
            print(f"  [OK] 加载 {name}: {len(data)} 条记录")
            return data

    print(f"  [WARN] 未找到 {stock_code} 的数据文件")
    return None


def get_week_dates(data):
    """
    从数据中提取周日期列表
    假设数据格式: [{"date": "2014-01-06", "close": 12.34, ...}, ...]
    或: {"2014-01-06": {"close": 12.34}, ...}
    """
    if isinstance(data, list):
        dates = []
        for item in data:
            if isinstance(item, dict) and 'date' in item:
                dates.append(item['date'])
            elif isinstance(item, dict) and 'Date' in item:
                dates.append(item['Date'])
        return sorted(dates)
    elif isinstance(data, dict):
        return sorted(data.keys())
    return []


def get_close_price(data, date_str):
    """获取指定日期的收盘价"""
    if isinstance(data, list):
        for item in data:
            d = item.get('date') or item.get('Date')
            if d == date_str:
                return float(item.get('close') or item.get('Close') or item.get('adj_close', 0))
    elif isinstance(data, dict):
        entry = data.get(date_str, {})
        if isinstance(entry, dict):
            return float(entry.get('close') or entry.get('Close') or entry.get('adj_close', 0))
        elif isinstance(entry, (int, float)):
            return float(entry)
    return None


# ============================================================
# 引擎接口探测
# ============================================================

def probe_engine_interface():
    """探测排盘引擎返回的数据格式"""
    print("\n" + "=" * 60)
    print("排盘引擎接口探测")
    print("=" * 60)

    test_dt = datetime(2025, 1, 6, 10, 0)
    try:
        ju = paipan(test_dt)
    except Exception as e:
        print(f"[ERROR] paipan() 调用失败: {e}")
        return None

    print(f"  paipan() 返回类型: {type(ju).__name__}")

    # 探测关键属性
    attrs_to_check = [
        'heaven', 'ground', 'gates', 'stars', 'deities',
        'month_branch', 'kongwang', 'zhifu_star', 'zhifu_palace',
        'zhishi_gate', 'zhishi_palace', 'day_gz', 'hour_gz',
        'ju_number', 'is_yangdun',
    ]

    for attr in attrs_to_check:
        if hasattr(ju, attr):
            val = getattr(ju, attr)
            if isinstance(val, dict):
                print(f"  ju.{attr}: dict, keys={list(val.keys())[:5]}, sample={list(val.items())[:2]}")
            elif isinstance(val, (list, tuple)):
                print(f"  ju.{attr}: {type(val).__name__}, len={len(val)}, sample={val[:3]}")
            else:
                print(f"  ju.{attr}: {type(val).__name__} = {val}")
        else:
            print(f"  ju.{attr}: [NOT FOUND]")

    return ju


def get_month_branch_from_date(dt):
    """从日期推导月支 (简化方法)"""
    # 注意: 真正的月支要看节气，这里用简化的月份对应
    # 实际排盘中ju.month_branch应该是准确的
    month = dt.month
    return MONTH_TO_BRANCH.get(month, '寅')


def get_kongwang_palaces(ju):
    """
    从ju对象获取空亡宫位集合

    kongwang可能是:
    - 地支列表 ['午', '未'] → 需要转换为宫位
    - 宫位列表 [9, 2] → 直接用
    - 其他格式
    """
    if not hasattr(ju, 'kongwang'):
        return set()

    kw = ju.kongwang
    if not kw:
        return set()

    # 地支→宫位映射
    DIZHI_TO_PALACE = {
        '子': 1, '丑': 8, '寅': 8, '卯': 3,
        '辰': 4, '巳': 4, '午': 9, '未': 2,
        '申': 2, '酉': 7, '戌': 6, '亥': 6,
    }
    # 四隅宫有两个地支，都映射到同一宫

    result = set()
    if isinstance(kw, (list, tuple)):
        for item in kw:
            if isinstance(item, str) and item in DIZHI_TO_PALACE:
                result.add(DIZHI_TO_PALACE[item])
            elif isinstance(item, int) and 1 <= item <= 9:
                result.add(item)
    elif isinstance(kw, str):
        # 可能是如 '午未' 这种格式
        for ch in kw:
            if ch in DIZHI_TO_PALACE:
                result.add(DIZHI_TO_PALACE[ch])

    return result


# ============================================================
# 主回测逻辑
# ============================================================

def run_backtest():
    """执行回测"""
    print("\n" + "=" * 60)
    print("符化六亲回测 (liuqin_backtest.py)")
    print("=" * 60)

    # 1. 探测引擎
    test_ju = probe_engine_interface()
    if test_ju is None:
        print("[ABORT] 引擎探测失败，退出")
        return

    # 2. 加载数据
    print("\n--- 加载标的数据 ---")
    stock_data = {}
    for code in BACKTEST_STOCKS:
        data = load_stock_data(code)
        if data:
            stock_data[code] = data

    if not stock_data:
        print("[ABORT] 没有可用的标的数据")
        return

    # 3. 确定回测日期范围
    # 取所有标的的公共日期
    all_dates_sets = []
    for code, data in stock_data.items():
        dates = get_week_dates(data)
        all_dates_sets.append(set(dates))

    if not all_dates_sets:
        print("[ABORT] 无法提取日期")
        return

    common_dates = sorted(set.intersection(*all_dates_sets))
    print(f"\n公共日期数: {len(common_dates)}")
    if len(common_dates) < 14:
        print("[ABORT] 公共日期太少")
        return

    print(f"日期范围: {common_dates[0]} ~ {common_dates[-1]}")

    # 留13周余量给13W horizon
    eval_dates = common_dates[:-13]
    print(f"可评估日期数: {len(eval_dates)}")

    # 4. 遍历每周
    results = []
    errors = 0
    total = len(eval_dates) * len(BACKTEST_STOCKS)

    print(f"\n--- 开始回测 ({len(eval_dates)}周 × {len(BACKTEST_STOCKS)}标的 = {total}条) ---")

    for i, date_str in enumerate(eval_dates):
        # 转换日期
        try:
            dt = datetime.strptime(date_str, '%Y-%m-%d')
        except:
            try:
                dt = datetime.strptime(date_str, '%Y/%m/%d')
            except:
                errors += 1
                continue

        # 设定排盘时间: 周一上午10点 (模拟开盘分析)
        # 如果date是周五收盘，取下周一
        weekday = dt.weekday()
        if weekday >= 5:  # 周末
            dt = dt + timedelta(days=(7 - weekday))
        pan_dt = dt.replace(hour=10, minute=0)

        # 排盘
        try:
            ju = paipan(pan_dt)
        except Exception as e:
            if errors < 5:
                print(f"  [ERROR] 排盘失败 {date_str}: {e}")
            errors += 1
            continue

        # 获取月支
        DIZHI_IDX_TO_STR = {
            0: '子', 1: '丑', 2: '寅', 3: '卯', 4: '辰', 5: '巳',
            6: '午', 7: '未', 8: '申', 9: '酉', 10: '戌', 11: '亥',
        }
        if hasattr(ju, 'month_branch') and ju.month_branch is not None:
            mb = ju.month_branch
            if isinstance(mb, int):
                month_branch = DIZHI_IDX_TO_STR.get(mb, get_month_branch_from_date(dt))
            else:
                month_branch = mb
        else:
            month_branch = get_month_branch_from_date(dt)

        # 获取空亡宫位
        kw_palaces = get_kongwang_palaces(ju)

        # 对每个标的评估
        for code in BACKTEST_STOCKS:
            if code not in stock_data:
                continue

            try:
                assessment = assess_stock_liuqin(
                    ju, code, month_branch, kw_palaces
                )
            except Exception as e:
                if errors < 5:
                    print(f"  [ERROR] 评估失败 {date_str} {code}: {e}")
                errors += 1
                continue

            if not assessment:
                continue

            # 获取收益数据
            date_idx = common_dates.index(date_str)
            current_price = get_close_price(stock_data[code], date_str)

            returns = {}
            for horizon_name, horizon_weeks in HORIZONS.items():
                future_idx = date_idx + horizon_weeks
                if future_idx < len(common_dates):
                    future_date = common_dates[future_idx]
                    future_price = get_close_price(stock_data[code], future_date)
                    if current_price and future_price and current_price > 0:
                        ret = (future_price - current_price) / current_price * 100
                        returns[horizon_name] = round(ret, 4)

            # 记录结果
            record = {
                'date': date_str,
                'stock_code': code,
                'stock_name': assessment.get('stock_name', ''),
                'effective_gan': assessment.get('effective_gan', ''),
                'label': assessment.get('label', 'UNKNOWN'),
                'total_score': assessment.get('total_score', 0),
                'reasoning': assessment.get('reasoning', ''),
            }
            record.update(returns)

            # 精简六亲详情
            for lq_key in ['qicai', 'guangui', 'zisun', 'xiongdi', 'fumu']:
                lq_data = assessment.get(lq_key, {})
                if isinstance(lq_data, dict):
                    record[f'{lq_key}_score'] = lq_data.get('score', 0)
                    record[f'{lq_key}_palace'] = lq_data.get('palace', 0)
                    record[f'{lq_key}_gan'] = lq_data.get('gan', '')

            results.append(record)

        # 进度报告
        if (i + 1) % 50 == 0 or i == 0:
            print(f"  进度: {i+1}/{len(eval_dates)}周 ({len(results)}条结果, {errors}错误)")

    print(f"\n--- 回测完成 ---")
    print(f"总结果: {len(results)} 条")
    print(f"总错误: {errors}")

    # 5. 保存结果
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(results, f, ensure_ascii=False, indent=None)
    print(f"结果已保存: {OUTPUT_FILE}")

    # 6. 统计分析
    print_statistics(results)

    return results


def print_statistics(results):
    """打印统计摘要"""
    if not results:
        print("[WARN] 无结果可统计")
        return

    print("\n" + "=" * 60)
    print("统计摘要")
    print("=" * 60)

    # 按标签分组
    from collections import defaultdict
    label_groups = defaultdict(list)
    for r in results:
        label_groups[r['label']].append(r)

    # 标签分布
    print("\n--- 标签分布 ---")
    for label in sorted(label_groups.keys()):
        count = len(label_groups[label])
        pct = count / len(results) * 100
        print(f"  {label:25s}: {count:5d} ({pct:5.1f}%)")

    # 各标签的平均收益
    print("\n--- 各标签平均收益 ---")
    print(f"  {'标签':25s} {'N':>6s} {'1W%':>8s} {'4W%':>8s} {'13W%':>8s}")
    print("  " + "-" * 55)

    for label in ['STRONGLY_FAVORABLE', 'FAVORABLE', 'PARTIAL_GOOD',
                   'NEUTRAL', 'PARTIAL_BAD', 'UNFAVORABLE']:
        group = label_groups.get(label, [])
        if not group:
            continue
        n = len(group)

        avgs = {}
        for h in ['1W', '4W', '13W']:
            vals = [r[h] for r in group if h in r and r[h] is not None]
            if vals:
                avgs[h] = sum(vals) / len(vals)
            else:
                avgs[h] = None

        line = f"  {label:25s} {n:6d}"
        for h in ['1W', '4W', '13W']:
            if avgs.get(h) is not None:
                line += f" {avgs[h]:>7.2f}%"
            else:
                line += f" {'N/A':>8s}"
        print(line)

    # SPREAD (最佳 - 最差)
    print("\n--- SPREAD (FAVORABLE+ vs UNFAVORABLE+) ---")
    fav_group = []
    unfav_group = []
    for r in results:
        if r['label'] in ('STRONGLY_FAVORABLE', 'FAVORABLE'):
            fav_group.append(r)
        elif r['label'] in ('PARTIAL_BAD', 'UNFAVORABLE'):
            unfav_group.append(r)

    for h in ['1W', '4W', '13W']:
        fav_vals = [r[h] for r in fav_group if h in r and r[h] is not None]
        unfav_vals = [r[h] for r in unfav_group if h in r and r[h] is not None]

        fav_avg = sum(fav_vals) / len(fav_vals) if fav_vals else None
        unfav_avg = sum(unfav_vals) / len(unfav_vals) if unfav_vals else None

        if fav_avg is not None and unfav_avg is not None:
            spread = fav_avg - unfav_avg
            print(f"  {h}: FAV+={fav_avg:+.2f}%({len(fav_vals)}) "
                  f"UNFAV+={unfav_avg:+.2f}%({len(unfav_vals)}) "
                  f"SPREAD={spread:+.2f}%")
        else:
            print(f"  {h}: 数据不足")

    # Per-stock区分度检查
    print("\n--- Per-stock区分度 ---")
    from collections import Counter
    stock_label_dist = defaultdict(lambda: Counter())
    for r in results:
        stock_label_dist[r['stock_code']][r['label']] += 1

    print(f"  {'标的':15s} {'FAV':>5s} {'PG':>5s} {'NEU':>5s} {'PB':>5s} {'UNFAV':>5s}")
    for code in BACKTEST_STOCKS:
        dist = stock_label_dist.get(code, Counter())
        fav = dist.get('STRONGLY_FAVORABLE', 0) + dist.get('FAVORABLE', 0)
        pg = dist.get('PARTIAL_GOOD', 0)
        neu = dist.get('NEUTRAL', 0)
        pb = dist.get('PARTIAL_BAD', 0)
        unfav = dist.get('UNFAVORABLE', 0)
        name = STOCK_INFO.get(code, {}).get('name', code)
        print(f"  {name:15s} {fav:5d} {pg:5d} {neu:5d} {pb:5d} {unfav:5d}")


# ============================================================
# 入口
# ============================================================

if __name__ == '__main__':
    run_backtest()
