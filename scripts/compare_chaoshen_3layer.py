"""
scripts/compare_chaoshen_3layer.py — 超神修正 三层交叉A/B对比

目的：在三层交叉（天时×人事×六亲）框架下，对比超神修正vs简化方法的效果。

方法：
  A组（含超神）: paipan() 含超神修正 → 生成天时标签A + 六亲标签A
  B组（无超神）: paipan() 跳过超神  → 生成天时标签B + 六亲标签B
  人事层：不受排盘影响 → A/B共用

  对比：三层交叉组合的13W SPREAD
  - 全量：A vs B的总体SPREAD
  - 张力 vs 同向：A vs B的"变之与应"效应
  - 超神子集：仅差异日期的表现

运行方式：
  cd ~/Desktop/自主项目/fcas
  python3 scripts/compare_chaoshen_3layer.py

依赖：fcas_engine_v2.py, assess_stock_tianshi_baojian.py, assess_fuhua_liuqin.py,
      stock_positioning.py, cross_validate_3layer_results.json
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import inspect
from datetime import datetime, timedelta
from collections import defaultdict

import fcas_engine_v2 as engine
from fcas_engine_v2 import paipan, evaluate_all_geju
from assess_stock_tianshi_baojian import assess_stock_tianshi_baojian
from assess_fuhua_liuqin import assess_stock_liuqin

# ============================================================
# 方向归类 (与cross_validate_3layer.py保持一致)
# ============================================================
T_FAV_LABELS = {'FAVORABLE', 'PARTIAL_GOOD'}
T_ADV_LABELS = {'UNFAVORABLE', 'PARTIAL_BAD'}

L_FAV_LABELS = {'STRONGLY_FAVORABLE', 'FAVORABLE'}
L_ADV_LABELS = {'UNFAVORABLE', 'PARTIAL_BAD'}

def t_direction(label):
    if label in T_FAV_LABELS: return 'T_FAV'
    if label in T_ADV_LABELS: return 'T_ADV'
    return 'T_NEU'

def l_direction(label):
    if label in L_FAV_LABELS: return 'L_FAV'
    if label in L_ADV_LABELS: return 'L_ADV'
    return 'L_NEU'

# ============================================================
# 构建无超神版paipan (monkey-patch，和compare_chaoshen_backtest.py相同)
# ============================================================

def _build_patched_paipan():
    source = inspect.getsource(paipan)
    lines = source.split('\n')
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
                continue
            indent = len(line) - len(line.lstrip())
            if indent <= 4:
                if stripped == 'else:' or stripped.startswith('ju.ju_number'):
                    continue
                else:
                    skip_mode = False
                    new_lines.append(line)
            else:
                continue
        else:
            new_lines.append(line)

    patched_source = '\n'.join(new_lines)
    exec_globals = engine.__dict__.copy()
    exec(compile(patched_source, '<patched_paipan>', 'exec'), exec_globals)
    return exec_globals['paipan']


print("构建无超神版paipan...")
paipan_B = _build_patched_paipan()

# 验证
test_dt = datetime(2024, 5, 6, 10, 0)
ju_A = paipan(test_dt)
ju_B = paipan_B(test_dt)
assert ju_A.chaoshen and ju_A.ju_number != ju_B.ju_number, "patch验证失败"
print(f"  ✓ 验证通过: A=局{ju_A.ju_number}(超神) B=局{ju_B.ju_number}")

# ============================================================
# 加载已有三层交叉数据 (获取人事标签和收益率)
# ============================================================
print("\n加载三层交叉数据...")
CROSS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          'cross_validate_3layer_results.json')

with open(CROSS_FILE) as f:
    cross_data = json.load(f)

cross_records = cross_data['records']
print(f"  三层交叉记录: {len(cross_records)}")

# 建索引: (stock_code, date) → h_dir, r13w, r1w
renshi_lookup = {}
for r in cross_records:
    key = (r['stock_code'], r['date'])
    renshi_lookup[key] = {
        'h_dir': r['h_dir'],
        'h_label': r['h_label'],
        'r13w': r.get('r13w'),
        'r1w': r.get('r1w'),
    }

dates = sorted(set(r['date'] for r in cross_records))
stocks = sorted(set(r['stock_code'] for r in cross_records))
print(f"  日期: {len(dates)}, 标的: {len(stocks)}")

# 中石油排除标记
LIUQIN_EXCLUDE = {'601857.SH'}

# ============================================================
# 对每条记录跑A/B评估
# ============================================================
print("\n开始三层A/B对比...")

cache_A = {}  # date -> (ju, geju)
cache_B = {}

results_A = []
results_B = []
diff_ju_dates = set()
total = 0
errors = 0

for i, rec in enumerate(cross_records):
    date_str = rec['date']
    stock_code = rec['stock_code']
    key = (stock_code, date_str)

    h_info = renshi_lookup.get(key)
    if h_info is None or h_info['r13w'] is None:
        continue

    h_dir = h_info['h_dir']
    r13w = h_info['r13w']
    r1w = h_info.get('r1w')

    dt = datetime.strptime(date_str, '%Y-%m-%d')
    pan_dt = datetime(dt.year, dt.month, dt.day, 10, 0)

    try:
        # 方法A
        if date_str not in cache_A:
            ju_a = paipan(pan_dt)
            geju_a = evaluate_all_geju(ju_a)
            cache_A[date_str] = (ju_a, geju_a)
        ju_a, geju_a = cache_A[date_str]

        # 天时A
        t_label_a, _, _ = assess_stock_tianshi_baojian(ju_a, stock_code, geju_a)
        t_dir_a = t_direction(t_label_a)

        # 六亲A
        if stock_code in LIUQIN_EXCLUDE:
            l_dir_a = 'L_NEU'
        else:
            lq_a = assess_stock_liuqin(ju_a, stock_code, ju_a.month_branch,
                                        set(ju_a.kongwang) if ju_a.kongwang else set())
            l_label_a = lq_a['label'] if lq_a else 'NEUTRAL'
            l_dir_a = l_direction(l_label_a)

        # 方法B
        if date_str not in cache_B:
            ju_b = paipan_B(pan_dt)
            geju_b = evaluate_all_geju(ju_b)
            cache_B[date_str] = (ju_b, geju_b)
        ju_b, geju_b = cache_B[date_str]

        # 天时B
        t_label_b, _, _ = assess_stock_tianshi_baojian(ju_b, stock_code, geju_b)
        t_dir_b = t_direction(t_label_b)

        # 六亲B
        if stock_code in LIUQIN_EXCLUDE:
            l_dir_b = 'L_NEU'
        else:
            lq_b = assess_stock_liuqin(ju_b, stock_code, ju_b.month_branch,
                                        set(ju_b.kongwang) if ju_b.kongwang else set())
            l_label_b = lq_b['label'] if lq_b else 'NEUTRAL'
            l_dir_b = l_direction(l_label_b)

        if ju_a.ju_number != ju_b.ju_number:
            diff_ju_dates.add(date_str)

        combo_a = f"{t_dir_a}×{h_dir}×{l_dir_a}"
        combo_b = f"{t_dir_b}×{h_dir}×{l_dir_b}"

        results_A.append({'t_dir': t_dir_a, 'h_dir': h_dir, 'l_dir': l_dir_a,
                          'combo': combo_a, 'r13w': r13w, 'r1w': r1w, 'date': date_str})
        results_B.append({'t_dir': t_dir_b, 'h_dir': h_dir, 'l_dir': l_dir_b,
                          'combo': combo_b, 'r13w': r13w, 'r1w': r1w, 'date': date_str})
        total += 1

    except Exception as e:
        errors += 1
        if errors <= 5:
            print(f"  [ERROR] {date_str} {stock_code}: {e}")

    if (i + 1) % 1000 == 0:
        print(f"  {i+1}/{len(cross_records)} ...")

print(f"\n完成: {total}条, 错误: {errors}")
print(f"局数不同日期: {len(diff_ju_dates)}/{len(dates)}")

# ============================================================
# 分析函数
# ============================================================

def analyze(results, label=""):
    """分析三层交叉的张力效应"""
    # 张力 vs 同向
    tension = []
    aligned_fav = []
    aligned_adv = []

    for r in results:
        dirs = {r['t_dir'].split('_')[1], r['h_dir'].split('_')[1], r['l_dir'].split('_')[1]}
        if 'FAV' in dirs and 'ADV' in dirs:
            tension.append(r)
        if r['t_dir'] == 'T_FAV' and r['h_dir'] == 'H_FAV' and r['l_dir'] == 'L_FAV':
            aligned_fav.append(r)
        if r['t_dir'] == 'T_ADV' and r['h_dir'] == 'H_ADV' and r['l_dir'] == 'L_ADV':
            aligned_adv.append(r)

    def avg13(recs):
        vals = [r['r13w'] for r in recs if r.get('r13w') is not None]
        return (sum(vals)/len(vals)*100 if vals else 0), len(vals)

    r_tension, n_tension = avg13(tension)
    r_aligned_fav, n_aligned_fav = avg13(aligned_fav)
    r_aligned_adv, n_aligned_adv = avg13(aligned_adv)
    r_all, n_all = avg13(results)

    return {
        'label': label,
        'total': n_all,
        'tension': (n_tension, r_tension),
        'aligned_fav': (n_aligned_fav, r_aligned_fav),
        'aligned_adv': (n_aligned_adv, r_aligned_adv),
        'all_avg': r_all,
    }

# ============================================================
# 输出报告
# ============================================================

print("\n" + "=" * 72)
print(" 超神修正 三层交叉A/B对比 (天时×人事×六亲)")
print("=" * 72)

a = analyze(results_A, "A(含超神)")
b = analyze(results_B, "B(无超神)")

print(f"\n--- 全量数据 ({a['total']}条) ---")
print(f"  {'':30} {'A(含超神)':>16} {'B(无超神)':>16} {'A-B':>10}")

for name, key in [("含张力(≥1FAV+1ADV)", 'tension'),
                   ("三层全FAV(同向)", 'aligned_fav'),
                   ("三层全ADV(同向)", 'aligned_adv')]:
    n_a, r_a = a[key]
    n_b, r_b = b[key]
    diff = r_a - r_b
    print(f"  {name:<30} {r_a:>+7.2f}%(N={n_a:<4}) {r_b:>+7.2f}%(N={n_b:<4}) {diff:>+9.2f}%")

print(f"  {'全部样本':<30} {a['all_avg']:>+7.2f}%{'':>10} {b['all_avg']:>+7.2f}%")

# 张力-同向差距
tension_gap_a = a['tension'][1] - a['aligned_fav'][1] if a['aligned_fav'][0] > 0 else 0
tension_gap_b = b['tension'][1] - b['aligned_fav'][1] if b['aligned_fav'][0] > 0 else 0
print(f"\n  张力-全FAV差距:   A={tension_gap_a:+.2f}%   B={tension_gap_b:+.2f}%")

# ============================================================
# 三层组合明细（N>=20）
# ============================================================
print(f"\n--- 三层组合明细 (N>=20) ---")
print(f"  {'组合':<35} {'A: 13W%':>10} {'B: 13W%':>10} {'差异':>8}  {'A_N':>4} {'B_N':>4}")
print(f"  {'-' * 75}")

combos_A = defaultdict(list)
combos_B = defaultdict(list)
for r in results_A:
    combos_A[r['combo']].append(r['r13w'] * 100 if r.get('r13w') else None)
for r in results_B:
    combos_B[r['combo']].append(r['r13w'] * 100 if r.get('r13w') else None)

all_combos = sorted(set(list(combos_A.keys()) + list(combos_B.keys())))
for combo in all_combos:
    vals_a = [v for v in combos_A.get(combo, []) if v is not None]
    vals_b = [v for v in combos_B.get(combo, []) if v is not None]
    if len(vals_a) < 20 and len(vals_b) < 20:
        continue
    avg_a = sum(vals_a)/len(vals_a) if vals_a else 0
    avg_b = sum(vals_b)/len(vals_b) if vals_b else 0
    diff = avg_a - avg_b
    print(f"  {combo:<35} {avg_a:>+9.2f}% {avg_b:>+9.2f}% {diff:>+7.2f}%  {len(vals_a):>4} {len(vals_b):>4}")

# ============================================================
# 超神子集分析
# ============================================================
print(f"\n{'=' * 72}")
print(f" 超神子集 (仅{len(diff_ju_dates)}个差异日期)")
print("=" * 72)

sub_A = [r for r in results_A if r['date'] in diff_ju_dates]
sub_B = [r for r in results_B if r['date'] in diff_ju_dates]

if sub_A:
    sa = analyze(sub_A, "A子集")
    sb = analyze(sub_B, "B子集")
    print(f"  记录数: {len(sub_A)}")
    print(f"  {'':30} {'A(含超神)':>16} {'B(无超神)':>16} {'A-B':>10}")
    for name, key in [("含张力", 'tension'),
                       ("三层全FAV", 'aligned_fav'),
                       ("全部", 'all_avg')]:
        if key == 'all_avg':
            print(f"  {name:<30} {sa[key]:>+7.2f}%{'':>10} {sb[key]:>+7.2f}%{'':>10} {sa[key]-sb[key]:>+9.2f}%")
        else:
            n_a, r_a = sa[key]
            n_b, r_b = sb[key]
            diff = r_a - r_b
            print(f"  {name:<30} {r_a:>+7.2f}%(N={n_a:<4}) {r_b:>+7.2f}%(N={n_b:<4}) {diff:>+9.2f}%")

# ============================================================
# 结论
# ============================================================
print(f"\n{'=' * 72}")
print("结论:")

tension_n_a, tension_r_a = a['tension']
tension_n_b, tension_r_b = b['tension']
tension_diff = tension_r_a - tension_r_b

all_diff = a['all_avg'] - b['all_avg']

print(f"  全量13W均值差异: {all_diff:+.2f}%")
print(f"  含张力13W差异:   {tension_diff:+.2f}% (A: N={tension_n_a}, B: N={tension_n_b})")
print(f"  张力效应(张力-全FAV): A={tension_gap_a:+.2f}% B={tension_gap_b:+.2f}%")

if tension_diff > 1.0:
    print(f"\n  ✓ 方法A（含超神）在张力组合中显著更优 ({tension_diff:+.2f}%)")
    print(f"    → 保持超神修正。")
elif tension_diff < -1.0:
    print(f"\n  ⚠ 方法B（无超神）在张力组合中显著更优 ({-tension_diff:+.2f}%)")
    print(f"    → 考虑回退超神修正。")
else:
    print(f"\n  ○ 两种方法在三层交叉中差异有限 ({tension_diff:+.2f}%)")
    if tension_gap_a > tension_gap_b + 0.5:
        print(f"    但方法A的张力效应更强，保持超神修正。")
    elif tension_gap_b > tension_gap_a + 0.5:
        print(f"    方法B的张力效应更强，考虑回退。")
    else:
        print(f"    保持当前实现（保守决策）。")

print("=" * 72)
