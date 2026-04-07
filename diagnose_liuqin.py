"""
diagnose_liuqin.py - 六亲回测诊断
用法: python3 diagnose_liuqin.py < liuqin_backtest_results.json
"""
import json
import sys
from collections import defaultdict

data = json.load(sys.stdin)
if isinstance(data, dict):
    data = data.get('results', [])

LIUQIN = ['qicai', 'guangui', 'zisun', 'xiongdi', 'fumu']
LIUQIN_NAMES = {'qicai': '妻财(用神)', 'guangui': '官鬼(忌神)',
                 'zisun': '子孙(元神)', 'xiongdi': '兄弟(鼠神)', 'fumu': '父母(仇神)'}

# ============================================================
# 1. 各子神得分桶 vs 1W收益
# ============================================================
print("=" * 60)
print("1. 子神得分与1W收益相关性")
print("=" * 60)

for lq in LIUQIN:
    score_key = f'{lq}_score'
    buckets = defaultdict(list)
    for r in data:
        s = r.get(score_key)
        ret = r.get('1W')
        if s is None or ret is None:
            continue
        if s < 0:       buckets['A_neg'].append(ret)
        elif s == 0:    buckets['B_zero(不现)'].append(ret)
        elif s < 1.5:   buckets['C_0~1.5'].append(ret)
        elif s < 2.5:   buckets['D_1.5~2.5'].append(ret)
        else:           buckets['E_gt2.5'].append(ret)

    print(f"\n  {LIUQIN_NAMES[lq]}")
    print(f"  {'得分区间':<15} {'N':>5} {'1W avg':>9}")
    for key in sorted(buckets.keys()):
        vals = buckets[key]
        label = key[2:]  # strip sort prefix
        avg = sum(vals) / len(vals)
        print(f"  {label:<15} {len(vals):>5} {avg:>+8.3f}%")

# ============================================================
# 2. 各标签下子神平均得分
# ============================================================
print()
print("=" * 60)
print("2. 各标签下子神平均得分")
print("=" * 60)

label_lq = defaultdict(lambda: defaultdict(list))
for r in data:
    lab = r['label']
    for lq in LIUQIN:
        s = r.get(f'{lq}_score')
        if s is not None:
            label_lq[lab][lq].append(s)

labels_order = ['STRONGLY_FAVORABLE', 'FAVORABLE', 'PARTIAL_GOOD',
                'NEUTRAL', 'PARTIAL_BAD', 'UNFAVORABLE']
header = f"  {'标签':<22}" + "".join(f"{'  '+lq:>12}" for lq in ['qicai','guangui','zisun','xiongdi','fumu'])
print(header)
print("  " + "-" * 80)
for lab in labels_order:
    if lab not in label_lq:
        continue
    r1w_group = [r['1W'] for r in data if r['label'] == lab and r.get('1W') is not None]
    avg1w = sum(r1w_group)/len(r1w_group) if r1w_group else 0
    row = f"  {lab:<22}"
    for lq in ['qicai','guangui','zisun','xiongdi','fumu']:
        vals = label_lq[lab][lq]
        avg = sum(vals)/len(vals) if vals else 0
        row += f"{avg:>+12.2f}"
    print(row + f"   1W={avg1w:>+.3f}%")

# ============================================================
# 3. 妻财现 vs 不现
# ============================================================
print()
print("=" * 60)
print("3. 妻财现/不现 vs 1W收益")
print("=" * 60)

buckets = defaultdict(list)
for r in data:
    ret = r.get('1W')
    if ret is None: continue
    s = r.get('qicai_score', 0)
    key = '现(score≠0)' if s != 0 else '不现(score=0)'
    buckets[key].append(ret)

for k in ['现(score≠0)', '不现(score=0)']:
    vals = buckets[k]
    avg = sum(vals)/len(vals) if vals else 0
    print(f"  妻财{k}: N={len(vals)}, 1W avg={avg:+.3f}%")

# ============================================================
# 4. STRONGLY_FAVORABLE 样本 reasoning 抽样
# ============================================================
print()
print("=" * 60)
print("4. STRONGLY_FAVORABLE 前10条 reasoning")
print("=" * 60)

sf = [r for r in data if r['label'] == 'STRONGLY_FAVORABLE']
for r in sf[:10]:
    print(f"  1W={r.get('1W',0):>+7.3f}%  score={r['total_score']:>5.1f}  {r['reasoning'][:90]}")

# ============================================================
# 5. PARTIAL_GOOD vs STRONGLY_FAVORABLE 子神对比
# ============================================================
print()
print("=" * 60)
print("5. PARTIAL_GOOD vs STRONGLY_FAVORABLE 子神均值对比")
print("=" * 60)

for lab in ['STRONGLY_FAVORABLE', 'PARTIAL_GOOD']:
    group = [r for r in data if r['label'] == lab]
    r1w = [r['1W'] for r in group if r.get('1W') is not None]
    avg1w = sum(r1w)/len(r1w) if r1w else 0
    print(f"\n  {lab} (N={len(group)}, 1W avg={avg1w:+.3f}%)")
    for lq in LIUQIN:
        vals = [r[f'{lq}_score'] for r in group if r.get(f'{lq}_score') is not None]
        n_zero = sum(1 for v in vals if v == 0)
        avg = sum(vals)/len(vals) if vals else 0
        print(f"    {LIUQIN_NAMES[lq]:<12} avg={avg:>+.2f}  不现率={n_zero/len(vals)*100:.0f}%")
