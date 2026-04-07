"""
cross_validate_liuqin_tianshi.py
================================
六亲v2 × 天时v6 交叉验证

用法:
  cd ~/Desktop/自主项目/fcas
  python3 cross_validate_liuqin_tianshi.py

需要:
  - liuqin_backtest_results.json (六亲v2回测结果)
  - tianshi_v6_backtest_results.json (天时v6回测结果)
"""

import json
from collections import defaultdict

# ============================================================
# 加载数据
# ============================================================

print("加载数据...")
with open('liuqin_backtest_results.json') as f:
    lq_data = json.load(f)
print(f"  六亲v2: {len(lq_data)} 条")

with open('tianshi_v6_backtest_results.json') as f:
    tv6_data = json.load(f)
print(f"  天时v6: {len(tv6_data)} 条")

# ============================================================
# 建立索引: (date, stock_code) → record
# ============================================================

lq_idx = {}
for r in lq_data:
    key = (r['date'], r['stock_code'])
    lq_idx[key] = r

tv6_idx = {}
for r in tv6_data:
    key = (r['date'], r['stock_code'])
    tv6_idx[key] = r

# 找公共键
common_keys = set(lq_idx.keys()) & set(tv6_idx.keys())
print(f"  公共记录: {len(common_keys)} 条")

if len(common_keys) == 0:
    print("[ABORT] 无公共记录")
    exit(1)

# ============================================================
# 合并
# ============================================================

merged = []
for key in common_keys:
    lq = lq_idx[key]
    tv = tv6_idx[key]
    
    record = {
        'date': key[0],
        'stock_code': key[1],
        'stock_name': lq.get('stock_name', ''),
        'lq_label': lq['label'],
        'lq_score': lq['total_score'],
        'tv6_label': tv['label'],
        'tv6_score': tv.get('score', 0),
        # 收益: 优先用六亲的(有1W/4W/13W), fallback到天时的
        '1W': lq.get('1W') if lq.get('1W') is not None else tv.get('return_1w'),
        '13W': lq.get('13W') if lq.get('13W') is not None else tv.get('return_13w'),
    }
    merged.append(record)

merged.sort(key=lambda x: (x['date'], x['stock_code']))
print(f"  合并记录: {len(merged)} 条")

# ============================================================
# 交叉分析
# ============================================================

# 简化标签: 天时v6
def simplify_tv6(label):
    if label in ('FAVORABLE',):
        return 'T_FAV'
    elif label in ('PARTIAL_GOOD',):
        return 'T_PG'
    elif label in ('NEUTRAL',):
        return 'T_NEU'
    elif label in ('PARTIAL_BAD', 'UNFAVORABLE'):
        return 'T_UNFAV'
    elif label in ('STAGNANT', 'VOLATILE'):
        return 'T_SPECIAL'
    return 'T_OTHER'

# 简化标签: 六亲
def simplify_lq(label):
    if label in ('STRONGLY_FAVORABLE', 'FAVORABLE'):
        return 'L_FAV'
    elif label in ('PARTIAL_GOOD',):
        return 'L_PG'
    elif label in ('NEUTRAL',):
        return 'L_NEU'
    elif label in ('PARTIAL_BAD', 'UNFAVORABLE'):
        return 'L_UNFAV'
    return 'L_OTHER'

# 交叉表
cross_groups = defaultdict(list)
for r in merged:
    t_label = simplify_tv6(r['tv6_label'])
    l_label = simplify_lq(r['lq_label'])
    cross_key = f"{t_label}×{l_label}"
    cross_groups[cross_key].append(r)

print("\n" + "=" * 70)
print("交叉验证: 天时v6 × 六亲v2")
print("=" * 70)

print(f"\n{'交叉类别':25s} {'N':>5s} {'1W%':>8s} {'13W%':>8s}")
print("-" * 50)

# 排序: 按13W降序
sorted_keys = sorted(cross_groups.keys(), 
                     key=lambda k: sum(r['13W'] for r in cross_groups[k] if r.get('13W') is not None) / max(1, len([r for r in cross_groups[k] if r.get('13W') is not None])),
                     reverse=True)

for cross_key in sorted_keys:
    group = cross_groups[cross_key]
    n = len(group)
    
    r1 = [r['1W'] for r in group if r.get('1W') is not None]
    r13 = [r['13W'] for r in group if r.get('13W') is not None]
    
    avg_1w = sum(r1)/len(r1) if r1 else 0
    avg_13w = sum(r13)/len(r13) if r13 else 0
    
    print(f"  {cross_key:25s} {n:5d} {avg_1w:+7.2f}% {avg_13w:+7.2f}%")

# ============================================================
# 关键问题: 双FAV vs 双UNFAV
# ============================================================

print("\n" + "=" * 70)
print("关键对比")
print("=" * 70)

def get_stats(keys_list):
    """合并多个交叉键的数据"""
    all_records = []
    for k in keys_list:
        all_records.extend(cross_groups.get(k, []))
    if not all_records:
        return None, None, 0
    r1 = [r['1W'] for r in all_records if r.get('1W') is not None]
    r13 = [r['13W'] for r in all_records if r.get('13W') is not None]
    return (sum(r1)/len(r1) if r1 else None,
            sum(r13)/len(r13) if r13 else None,
            len(all_records))

# 双利好
fav_fav_1w, fav_fav_13w, fav_fav_n = get_stats(['T_FAV×L_FAV', 'T_PG×L_FAV'])
# 双利空
unfav_unfav_1w, unfav_unfav_13w, unfav_unfav_n = get_stats(['T_UNFAV×L_UNFAV', 'T_UNFAV×L_PG'])
# 天时好×六亲差 (变之与应常反对)
fav_unfav_1w, fav_unfav_13w, fav_unfav_n = get_stats(['T_FAV×L_UNFAV', 'T_PG×L_UNFAV'])
# 天时差×六亲好
unfav_fav_1w, unfav_fav_13w, unfav_fav_n = get_stats(['T_UNFAV×L_FAV', 'T_UNFAV×L_PG'])

print(f"\n  {'组合':25s} {'N':>5s} {'1W%':>8s} {'13W%':>8s}")
print("  " + "-" * 48)

for name, n, r1, r13 in [
    ('双FAV (T+×L+)', fav_fav_n, fav_fav_1w, fav_fav_13w),
    ('双UNFAV (T-×L-)', unfav_unfav_n, unfav_unfav_1w, unfav_unfav_13w),
    ('反对:T+×L-', fav_unfav_n, fav_unfav_1w, fav_unfav_13w),
    ('反对:T-×L+', unfav_fav_n, unfav_fav_1w, unfav_fav_13w),
]:
    r1s = f"{r1:+7.2f}%" if r1 is not None else "   N/A"
    r13s = f"{r13:+7.2f}%" if r13 is not None else "   N/A"
    print(f"  {name:25s} {n:5d} {r1s} {r13s}")

if fav_fav_13w is not None and unfav_unfav_13w is not None:
    spread_13w = fav_fav_13w - unfav_unfav_13w
    print(f"\n  13W SPREAD (双FAV - 双UNFAV): {spread_13w:+.2f}%")

# ============================================================
# "变之与应常反对" 验证
# ============================================================

print("\n" + "=" * 70)
print("邵雍'变之与应常反对'验证: 天时与六亲方向相反时的表现")
print("=" * 70)

# T_ADV(天时凶) × L_FAV(六亲吉) — 类似之前的T_ADV×H_FAV
tadv_lfav = []
for r in merged:
    tv = r['tv6_label']
    lq = r['lq_label']
    if tv in ('UNFAVORABLE', 'PARTIAL_BAD') and lq in ('STRONGLY_FAVORABLE', 'FAVORABLE'):
        tadv_lfav.append(r)

tfav_lunfav = []
for r in merged:
    tv = r['tv6_label']
    lq = r['lq_label']
    if tv in ('FAVORABLE', 'PARTIAL_GOOD') and lq in ('UNFAVORABLE', 'PARTIAL_BAD'):
        tfav_lunfav.append(r)

# 同向
tfav_lfav = []
for r in merged:
    tv = r['tv6_label']
    lq = r['lq_label']
    if tv in ('FAVORABLE', 'PARTIAL_GOOD') and lq in ('STRONGLY_FAVORABLE', 'FAVORABLE'):
        tfav_lfav.append(r)

print(f"\n  {'模式':30s} {'N':>5s} {'1W%':>8s} {'13W%':>8s}")
print("  " + "-" * 55)

for name, group in [
    ('T_ADV×L_FAV (反对:天凶地吉)', tadv_lfav),
    ('T_FAV×L_UNFAV (反对:天吉地凶)', tfav_lunfav),
    ('T_FAV×L_FAV (同向:天地皆吉)', tfav_lfav),
]:
    if not group:
        print(f"  {name:30s}     0      N/A      N/A")
        continue
    r1 = [r['1W'] for r in group if r.get('1W') is not None]
    r13 = [r['13W'] for r in group if r.get('13W') is not None]
    a1 = sum(r1)/len(r1) if r1 else 0
    a13 = sum(r13)/len(r13) if r13 else 0
    print(f"  {name:30s} {len(group):5d} {a1:+7.2f}% {a13:+7.2f}%")

# ============================================================
# Per-stock交叉效果
# ============================================================

print("\n" + "=" * 70)
print("Per-stock: 六亲FAV+ vs UNFAV+ 的13W差距")
print("=" * 70)

stock_names = {}
for r in merged:
    stock_names[r['stock_code']] = r.get('stock_name', r['stock_code'])

print(f"\n  {'标的':12s} {'FAV+ 13W%':>10s}(N) {'UNFAV+ 13W%':>12s}(N) {'SPREAD':>8s}")
print("  " + "-" * 55)

for code in sorted(set(r['stock_code'] for r in merged)):
    fav = [r for r in merged if r['stock_code']==code and r['lq_label'] in ('STRONGLY_FAVORABLE','FAVORABLE')]
    unfav = [r for r in merged if r['stock_code']==code and r['lq_label'] in ('PARTIAL_BAD','UNFAVORABLE')]
    
    f13 = [r['13W'] for r in fav if r.get('13W') is not None]
    u13 = [r['13W'] for r in unfav if r.get('13W') is not None]
    
    fa = sum(f13)/len(f13) if f13 else None
    ua = sum(u13)/len(u13) if u13 else None
    
    name = stock_names.get(code, code)[:10]
    fas = f"{fa:+7.2f}%({len(f13)})" if fa is not None else "  N/A"
    uas = f"{ua:+7.2f}%({len(u13)})" if ua is not None else "  N/A"
    sp = f"{fa-ua:+7.2f}%" if fa is not None and ua is not None else "  N/A"
    print(f"  {name:12s} {fas:>14s} {uas:>14s} {sp:>8s}")

# 保存合并结果
with open('cross_liuqin_tianshi_results.json', 'w') as f:
    json.dump(merged, f, ensure_ascii=False)
print(f"\n合并结果已保存: cross_liuqin_tianshi_results.json ({len(merged)}条)")
