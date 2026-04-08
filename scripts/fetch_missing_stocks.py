"""
scripts/fetch_missing_stocks.py — 补充缺失标的的历史数据

目标: 600547.SH (山东黄金) 和 601899.SH (紫金矿业)
输出: data/json/shandong_gold_weekly.json, zijin_weekly.json
      data/json/shandong_gold_quarterly.json, zijin_quarterly.json (如积分够)

格式严格匹配现有 data/json/*_weekly.json / *_quarterly.json
"""

import os
import sys
import json
from datetime import datetime

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT_DIR   = os.path.dirname(_SCRIPT_DIR)
sys.path.insert(0, _ROOT_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(_ROOT_DIR, '.env'))

import tushare as ts

TOKEN = os.getenv('TUSHARE_TOKEN', '47c200afe3a46dbe8713e776571cdfd7fa715cb025880ff6c4d98d5b')
ts.set_token(TOKEN)
pro = ts.pro_api()

DATA_DIR = os.path.join(_ROOT_DIR, 'data', 'json')
os.makedirs(DATA_DIR, exist_ok=True)

TARGETS = [
    {'ts_code': '600547.SH', 'alias': 'shandong_gold', 'name': '山东黄金'},
    {'ts_code': '601899.SH', 'alias': 'zijin',         'name': '紫金矿业'},
]

START_DATE = '20150101'
END_DATE   = '20260408'


# ============================================================
# 周线数据
# ============================================================

def fetch_weekly(ts_code, alias, name):
    print(f"\n[{name}] 获取周线数据...")
    try:
        df = pro.weekly(
            ts_code=ts_code,
            start_date=START_DATE,
            end_date=END_DATE,
            fields='ts_code,trade_date,open,high,low,close,vol,amount'
        )
    except Exception as e:
        print(f"  [ERROR] {e}")
        return False

    if df is None or df.empty:
        print(f"  [WARN] 无数据返回")
        return False

    print(f"  原始记录: {len(df)} 行")

    # Tushare 返回降序（最新在前），转升序
    df = df.sort_values('trade_date').reset_index(drop=True)

    records = []
    prev_close = None
    for _, row in df.iterrows():
        date_str = row['trade_date']
        # trade_date 格式: "20260327" → "2026-03-27"
        date_fmt = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"

        close = float(row['close']) if row['close'] is not None else None

        # 成交量: Tushare weekly vol 单位是手(100股) → 转换为股数
        vol_raw = float(row['vol']) if row['vol'] is not None else None
        volume = vol_raw * 100 if vol_raw is not None else None

        # 成交额: amount 单位是千元 → 转换为亿元
        amount_raw = float(row['amount']) if row['amount'] is not None else None
        turnover_billion = round(amount_raw / 1e5, 4) if amount_raw is not None else None

        # 周收益率
        if close is not None and prev_close is not None and prev_close != 0:
            weekly_return_pct = round((close - prev_close) / prev_close, 6)
        else:
            weekly_return_pct = None

        records.append({
            'date': date_fmt,
            'close': close,
            'volume': volume,
            'turnover_billion': turnover_billion,
            'turnover_pct': None,           # 换手率需要流通股本，跳过
            'weekly_return_pct': weekly_return_pct,
            'margin_balance_billion': None, # 需要单独接口
            'northbound_holding': None,     # 需要单独接口
        })
        prev_close = close

    out_path = os.path.join(DATA_DIR, f'{alias}_weekly.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    print(f"  保存: {out_path} ({len(records)} 条)")
    print(f"  日期范围: {records[0]['date']} ~ {records[-1]['date']}")
    return True


# ============================================================
# 季度财务数据
# ============================================================

def fetch_quarterly(ts_code, alias, name):
    print(f"\n[{name}] 获取季度财务数据...")

    # 尝试 fina_indicator（财务指标，含毛利率、ROE等）
    try:
        df = pro.fina_indicator(
            ts_code=ts_code,
            start_date=START_DATE,
            end_date=END_DATE,
            fields='ts_code,end_date,grossprofit_margin,debt_to_assets,rd_exp,total_revenue'
        )
        if df is None or df.empty:
            raise ValueError("empty")
        print(f"  fina_indicator: {len(df)} 行")
    except Exception as e:
        print(f"  [WARN] fina_indicator 失败: {e}")
        df = None

    # 尝试 income（利润表）
    try:
        df_inc = pro.income(
            ts_code=ts_code,
            start_date=START_DATE,
            end_date=END_DATE,
            fields='ts_code,end_date,total_revenue,n_income_attr_p,operate_profit'
        )
        if df_inc is None or df_inc.empty:
            raise ValueError("empty")
        print(f"  income: {len(df_inc)} 行")
    except Exception as e:
        print(f"  [WARN] income 失败: {e}")
        df_inc = None

    if df is None and df_inc is None:
        print(f"  [SKIP] 季度数据不可用（积分不足或接口受限）")
        return False

    # 构建记录：以 end_date 为 key，合并两个表
    from collections import defaultdict
    quarterly = defaultdict(dict)

    if df_inc is not None:
        df_inc = df_inc.sort_values('end_date')
        for _, row in df_inc.iterrows():
            d = str(row['end_date'])
            date_fmt = f"{d[:4]}-{d[4:6]}-{d[6:8]}" if len(d) == 8 else d
            rev = float(row['total_revenue']) / 1e9 if row.get('total_revenue') else None
            profit = float(row['n_income_attr_p']) / 1e9 if row.get('n_income_attr_p') else None
            quarterly[date_fmt]['date'] = date_fmt
            quarterly[date_fmt]['revenue_billion'] = round(rev, 4) if rev else None
            quarterly[date_fmt]['net_profit_billion'] = round(profit, 4) if profit else None

    if df is not None:
        df = df.sort_values('end_date')
        for _, row in df.iterrows():
            d = str(row['end_date'])
            date_fmt = f"{d[:4]}-{d[4:6]}-{d[6:8]}" if len(d) == 8 else d
            gm = float(row['grossprofit_margin']) if row.get('grossprofit_margin') else None
            da = float(row['debt_to_assets']) if row.get('debt_to_assets') else None
            quarterly[date_fmt]['date'] = date_fmt
            quarterly[date_fmt]['gross_margin_pct'] = round(gm, 4) if gm else None
            quarterly[date_fmt]['debt_ratio_pct'] = round(da, 4) if da else None

    # 填充缺失字段（与现有格式一致）
    records = []
    for date_fmt in sorted(quarterly.keys()):
        q = quarterly[date_fmt]
        records.append({
            'date': q.get('date', date_fmt),
            'revenue_billion': q.get('revenue_billion'),
            'net_profit_billion': q.get('net_profit_billion'),
            'operating_cashflow_billion': None,
            'revenue_yoy_pct': None,
            'net_profit_yoy_pct': None,
            'gross_margin_pct': q.get('gross_margin_pct'),
            'debt_ratio_pct': q.get('debt_ratio_pct'),
            'rd_ratio_pct': None,
            'pe_ratio': None,
            'pb_ratio': None,
            'institutional_holding_pct': None,
        })

    out_path = os.path.join(DATA_DIR, f'{alias}_quarterly.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    print(f"  保存: {out_path} ({len(records)} 条)")
    return True


# ============================================================
# 主流程
# ============================================================

results = {}
for t in TARGETS:
    ok_w = fetch_weekly(t['ts_code'], t['alias'], t['name'])
    ok_q = fetch_quarterly(t['ts_code'], t['alias'], t['name'])
    results[t['ts_code']] = {'weekly': ok_w, 'quarterly': ok_q, 'alias': t['alias']}

print("\n\n====== 结果汇总 ======")
for code, r in results.items():
    print(f"{code}: weekly={'OK' if r['weekly'] else 'FAIL'}, quarterly={'OK' if r['quarterly'] else 'FAIL'}")
    if r['weekly']:
        print(f"  alias: '{r['alias']}'")
        print(f"  → 更新 fetch_tushare.py: CODE_TO_ALIAS['{code}'] = '{r['alias']}'")

print("\n[手动操作] 请根据以上结果更新 fetch_tushare.py 中的 CODE_TO_ALIAS 映射。")
print("[手动操作] 或直接运行: python3 scripts/update_aliases.py")
