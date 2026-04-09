"""
scripts/compare_chaoshen_backtest.py — 超神修正 vs 简化方法 回测对比

目的：用实际回测数据判断"超神修正"是否改善天时层预测能力。
方法：对同一组(date, stock, 收益率)，分别用两种排盘跑天时评估，对比SPREAD。

  A组（含超神）: paipan() 正常调用 — 超神时用上一节气局数
  B组（无超神）: paipan() 跳过超神 — 始终用当前节气局数

运行方式：
  cd ~/Desktop/自主项目/fcas
  python3 scripts/compare_chaoshen_backtest.py

依赖：fcas_engine_v2.py, assess_stock_tianshi_baojian.py, stock_positioning.py,
      liuqin_backtest_results.json（含1W/4W/13W收益率）
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from datetime import datetime, timedelta
from collections import defaultdict
import inspect
import fcas_engine_v2 as engine
from fcas_engine_v2 import (
    paipan, evaluate_all_geju,
    get_current_term, get_day_ganzhi, get_sanyuan, get_ju_number,
)
from assess_stock_tianshi_baojian import assess_stock_tianshi_baojian

# ============================================================
# 构建跳过超神的 paipan 版本（源码级patch）
# ============================================================

def _build_patched_paipan():
    """构建一个跳过超神的paipan函数。
    
    方法：读取paipan()源码，将 if _chaoshen: 整个if/else块替换为
    直接用当前节气局数，然后编译执行。
    """
    source = inspect.getsource(paipan)
    lines = source.split('\n')
    
    # 去掉公共缩进
    min_indent = float('inf')
    for line in lines:
        if line.strip():
            min_indent = min(min_indent, len(line) - len(line.lstrip()))
    if min_indent == float('inf'):
        min_indent = 0
    lines = [line[min_indent:] for line in lines]
    
    new_lines = []
    skip_mode = False
    
    for line in lines:
        stripped = line.strip()
        
        if stripped == 'if _chaoshen:':
            skip_mode = True
            new_lines.append('    ju.chaoshen = False')
            new_lines.append('    ju.ju_number = get_ju_number(term_idx, sanyuan, is_yangdun)')
            continue
        
        if skip_mode:
            if not stripped:
                continue  # 跳过空行
            indent = len(line) - len(line.lstrip())
            if indent <= 4:
                if stripped == 'else:' or stripped.startswith('ju.ju_number'):
                    continue  # 跳过else行和else块内赋值
                else:
                    skip_mode = False
                    new_lines.append(line)
            else:
                continue  # 跳过if/else块内的缩进行
        else:
            new_lines.append(line)
    
    patched_source = '\n'.join(new_lines)
    exec_globals = engine.__dict__.copy()
    exec(compile(patched_source, '<patched_paipan>', 'exec'), exec_globals)
    return exec_globals['paipan']


print("构建无超神版paipan...")
try:
    paipan_B = _build_patched_paipan()
    
    # 验证：2024-05-06是已知的超神日
    test_dt = datetime(2024, 5, 6, 10, 0)
    ju_A = paipan(test_dt)
    ju_B = paipan_B(test_dt)
    print(f"  验证 2024-05-06:")
    print(f"    A: {ju_A.term_name} 局{ju_A.ju_number} chaoshen={ju_A.chaoshen}")
    print(f"    B: {ju_B.term_name} 局{ju_B.ju_number} chaoshen={getattr(ju_B, 'chaoshen', '?')}")
    
    if ju_A.chaoshen and ju_A.ju_number != ju_B.ju_number:
        print("  ✓ patch验证通过：A/B局数不同")
    elif not ju_A.chaoshen:
        print("  ⚠ 此日非超神日，换一个日期验证...")
    else:
        print("  ⚠ 局数相同，patch可能有问题")
        
except Exception as e:
    import traceback
    print(f"  ✗ patch失败: {e}")
    traceback.print_exc()
    print("\n退出。")
    sys.exit(1)

# ============================================================
# 加载回测数据
# ============================================================
RESULTS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            'liuqin_backtest_results.json')

print(f"\n加载回测数据...")
with open(RESULTS_FILE) as f:
    records = json.load(f)

dates = sorted(set(r['date'] for r in records))
stocks = sorted(set(r['stock_code'] for r in records))
print(f"  记录: {len(records)}, 日期: {len(dates)}, 标的: {len(stocks)}")

# ============================================================
# A/B 对比评估
# ============================================================
print("\n开始A/B对比...")

cache_A = {}  # date_str -> (ju, all_geju)
cache_B = {}

results_A = []
results_B = []
diff_label_count = 0
diff_ju_dates = set()
total = 0
errors = 0

for i, rec in enumerate(records):
    date_str = rec['date']
    stock_code = rec['stock_code']
    ret_13w = rec.get('13W')
    ret_1w = rec.get('1W')

    if ret_13w is None:
        continue

    dt = datetime.strptime(date_str, '%Y-%m-%d')
    pan_dt = datetime(dt.year, dt.month, dt.day, 10, 0)

    try:
        # 方法A：含超神
        if date_str not in cache_A:
            ju_a = paipan(pan_dt)
            geju_a = evaluate_all_geju(ju_a)
            cache_A[date_str] = (ju_a, geju_a)
        ju_a, geju_a = cache_A[date_str]
        label_a, score_a, _ = assess_stock_tianshi_baojian(ju_a, stock_code, geju_a)

        # 方法B：无超神
        if date_str not in cache_B:
            ju_b = paipan_B(pan_dt)
            geju_b = evaluate_all_geju(ju_b)
            cache_B[date_str] = (ju_b, geju_b)
        ju_b, geju_b = cache_B[date_str]
        label_b, score_b, _ = assess_stock_tianshi_baojian(ju_b, stock_code, geju_b)

        if ju_a.ju_number != ju_b.ju_number:
            diff_ju_dates.add(date_str)
        if label_a != label_b:
            diff_label_count += 1

        results_A.append({'label': label_a, '13W': ret_13w, '1W': ret_1w, 'date': date_str})
        results_B.append({'label': label_b, '13W': ret_13w, '1W': ret_1w, 'date': date_str})
        total += 1

    except Exception as e:
        errors += 1
        if errors <= 5:
            print(f"  [ERROR] {date_str} {stock_code}: {e}")

    if (i + 1) % 1000 == 0:
        print(f"  {i+1}/{len(records)} ...")

print(f"\n完成: {total}条处理, {errors}条错误")
print(f"局数不同日期: {len(diff_ju_dates)}/{len(dates)} ({len(diff_ju_dates)/len(dates)*100:.1f}%)")
print(f"标签不同记录: {diff_label_count}/{total} ({diff_label_count/total*100:.1f}%)")

# ============================================================
# SPREAD计算
# ============================================================

FAV_LABELS = {'FAVORABLE', 'PARTIAL_GOOD'}
ADV_LABELS = {'UNFAVORABLE', 'PARTIAL_BAD'}

def calc_stats(results, period='13W'):
    fav = [r[period] for r in results if r['label'] in FAV_LABELS and r.get(period) is not None]
    adv = [r[period] for r in results if r['label'] in ADV_LABELS and r.get(period) is not None]
    avg_fav = sum(fav) / len(fav) if fav else 0
    avg_adv = sum(adv) / len(adv) if adv else 0
    spread = avg_fav - avg_adv if fav and adv else 0
    by_label = defaultdict(list)
    for r in results:
        if r.get(period) is not None:
            by_label[r['label']].append(r[period])
    return {'fav_n': len(fav), 'adv_n': len(adv),
            'avg_fav': avg_fav, 'avg_adv': avg_adv,
            'spread': spread, 'by_label': by_label}

# ============================================================
# 输出报告
# ============================================================

print("\n" + "=" * 72)
print(" 超神修正 vs 简化方法 — 天时层SPREAD对比")
print("=" * 72)

for period in ['1W', '13W']:
    s_a = calc_stats(results_A, period)
    s_b = calc_stats(results_B, period)
    diff = s_a['spread'] - s_b['spread']

    print(f"\n--- {period} ---")
    print(f"  {'':30} {'A(含超神)':>14} {'B(无超神)':>14} {'A-B':>10}")
    print(f"  {'FAV数量':30} {s_a['fav_n']:>14} {s_b['fav_n']:>14}")
    print(f"  {'ADV数量':30} {s_a['adv_n']:>14} {s_b['adv_n']:>14}")
    print(f"  {'FAV均值':30} {s_a['avg_fav']:>+13.2f}% {s_b['avg_fav']:>+13.2f}%")
    print(f"  {'ADV均值':30} {s_a['avg_adv']:>+13.2f}% {s_b['avg_adv']:>+13.2f}%")
    print(f"  {'SPREAD (FAV-ADV)':30} {s_a['spread']:>+13.2f}% {s_b['spread']:>+13.2f}% {diff:>+9.2f}%")

    all_labels = sorted(set(list(s_a['by_label'].keys()) + list(s_b['by_label'].keys())))
    print(f"\n  标签明细:")
    print(f"  {'标签':20} {'A: N':>6} {'A: 均值':>10} {'B: N':>6} {'B: 均值':>10}")
    for lb in all_labels:
        a_vals = s_a['by_label'].get(lb, [])
        b_vals = s_b['by_label'].get(lb, [])
        a_avg = sum(a_vals) / len(a_vals) if a_vals else 0
        b_avg = sum(b_vals) / len(b_vals) if b_vals else 0
        print(f"  {lb:20} {len(a_vals):>6} {a_avg:>+9.2f}% {len(b_vals):>6} {b_avg:>+9.2f}%")

# 超神子集
print(f"\n{'=' * 72}")
print(f" 超神子集（仅{len(diff_ju_dates)}个局数不同的日期）")
print("=" * 72)

sub_A = [r for r in results_A if r['date'] in diff_ju_dates]
sub_B = [r for r in results_B if r['date'] in diff_ju_dates]

if sub_A:
    print(f"  子集记录: {len(sub_A)}")
    for period in ['1W', '13W']:
        ss_a = calc_stats(sub_A, period)
        ss_b = calc_stats(sub_B, period)
        diff = ss_a['spread'] - ss_b['spread']
        print(f"  {period}: A={ss_a['spread']:+.2f}%(F{ss_a['fav_n']}/A{ss_a['adv_n']}) "
              f"B={ss_b['spread']:+.2f}%(F{ss_b['fav_n']}/A{ss_b['adv_n']}) "
              f"差异={diff:+.2f}%")

# ============================================================
# 结论
# ============================================================
s13_a = calc_stats(results_A, '13W')
s13_b = calc_stats(results_B, '13W')
final_diff = s13_a['spread'] - s13_b['spread']

print(f"\n{'=' * 72}")
print("结论:")
if final_diff > 0.5:
    print(f"  ✓ 方法A（含超神修正）13W SPREAD高出 {final_diff:+.2f}%")
    print(f"    → 超神修正有效，保持当前实现。")
elif final_diff < -0.5:
    print(f"  ⚠ 方法B（无超神）13W SPREAD高出 {-final_diff:+.2f}%")
    print(f"    → 超神修正降低预测力，考虑回退。")
else:
    print(f"  ○ 两种方法差异不大（{final_diff:+.2f}%），保持当前实现。")
print("=" * 72)
