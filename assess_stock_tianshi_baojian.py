"""
assess_stock_tianshi_baojian.py — 基于《御定奇门宝鉴》"占求财"原文的天时评估

替换 stock_positioning.py 中的 assess_stock_tianshi() 函数。

原文依据（宝鉴卷四·占求财）：
  "凡求财之说，其事不一。当分体用，以生门主之。
   生门所落之宫分为体，生门天盘所落之星为用。
   用生体则吉，体生用则不吉。
   用旺体衰，体虽克用，不为大吉。体旺用衰，用虽克体，亦无大害。
   大抵看生门所落之宫分，再看上下二盘格局，吉凶何如。
   吉格吉星，所求如意。有一不吉，所求仅半。休囚不吉，所求全无。"

设计四维度：
  D1. 生门体用关系 — 生门落宫(体) vs 天盘星(用) 的五行生克
  D2. 生门旺相休囚 — 生门落宫五行在当月的时令状态
  D3. 标的宫位格局 — 标的日干所在宫位的格局吉凶 + 三奇
  D4. 标的宫位星门 — 标的宫位的九星吉凶 + 八门吉凶 + 门迫

最终判断按宝鉴逻辑（非简单加分）：
  - "吉格吉星，所求如意" → FAVORABLE
  - "有一不吉，所求仅半" → PARTIAL  
  - "休囚不吉，所求全无" → UNFAVORABLE

v1 2026-04-04 — 初版，替换palace scoring
"""

from fcas_engine_v2 import (
    GONG_WUXING, STAR_WUXING, GATE_WUXING, GATE_JIXIONG,
    GATE_SHENG, GATE_KAI, GATE_XIU,
    STAR_NAMES, GATE_NAMES, GONG_GUA_NAMES, WUXING_NAMES,
    shengke, calc_wangshuai, tg_wuxing,
    REL_BIHE, REL_WOSHENG, REL_WOKE, REL_SHENGWO, REL_KEWO,
    WS_WANG, WS_XIANG, WS_XIU, WS_QIU, WS_SI,
    TG_YI, TG_BING, TG_DING,
    get_nayin,
    TIANGAN_NAMES,
)

from stock_positioning import (
    STOCK_POSITIONING, find_stock_palace, _STEM_NAME_TO_IDX,
    _DUIGONG,
)

# ============================================================
# WS labels for debug output
# ============================================================
WS_NAMES = {WS_WANG: "旺", WS_XIANG: "相", WS_XIU: "休", WS_QIU: "囚", WS_SI: "废"}

# ============================================================
# Star classification (same as stock_positioning.py)
# ============================================================
_STAR_DAJI    = {3, 4, 5}     # 天冲/天辅/天禽
_STAR_XIAOJI  = {2, 7}        # 天冲→idx2=天冲? Let me verify
# Actually from fcas_engine_v2.py:
# STAR_PENG=0 STAR_RUI=1 STAR_CHONG=2 STAR_FU=3 STAR_QIN=4
# STAR_XIN=5→天心? No: line 111 shows order
# Let me use the same classification as stock_positioning.py already uses:
# _STAR_DAJI = {3, 4, 5} = 天辅(3), 天禽(4), 天心(5) — 三大吉星 ✓
# _STAR_XIAOJI = {2, 7} = 天冲(2), 天任(7→actually 8?) 
# Need to be careful. The classification is already validated in stock_positioning.py.
# I'll import from there.
from stock_positioning import _STAR_DAJI, _STAR_XIAOJI, _STAR_DAXIONG, _STAR_XIAOXIONG

# Three Wonders (三奇)
SANQI = {TG_YI, TG_BING, TG_DING}


def _find_gate_palace(ju, gate_id):
    """Find which palace a specific gate occupies in the current ju."""
    for p in range(1, 10):
        if ju.gates.get(p) == gate_id:
            return p
    # 中宫寄坤: gate might be at P5 mapped to P2
    if ju.gates.get(5) == gate_id:
        return 5
    return None


def _d1_shengmen_tiyu(ju):
    """
    维度1: 生门体用关系
    
    原文: "生门所落之宫分为体，生门天盘所落之星为用"
    
    Returns: (score, detail_str)
      score: +2(用生体), +1(比和/体克用-weak), 0(neutral), 
             -1(体生用=泄), -2(用克体=凶)
    """
    shengmen_palace = _find_gate_palace(ju, GATE_SHENG)
    if shengmen_palace is None:
        return 0, "生门未找到"
    
    # 体 = 生门落宫五行
    ti_wx = GONG_WUXING.get(shengmen_palace)
    
    # 用 = 生门所在宫位天盘上的星
    star = ju.stars.get(shengmen_palace)
    if star is None or ti_wx is None:
        return 0, "数据不全"
    
    yong_wx = STAR_WUXING.get(star)
    if yong_wx is None:
        return 0, "星五行未知"
    
    # 以"用"为主语看"体": 用对体的关系
    # 原文: "用生体则吉" → 用生体 means 用is生ing体, i.e. 用→体 = 用生体
    # In shengke(yong, ti): if REL_WOSHENG → 用生体 → 吉
    rel = shengke(yong_wx, ti_wx)
    
    star_name = STAR_NAMES.get(star, "?")
    gong_name = GONG_GUA_NAMES.get(shengmen_palace, "?")
    
    if rel == REL_WOSHENG:    # 用生体 → 吉
        return 2, f"生门落{gong_name}({WUXING_NAMES[ti_wx]})，{star_name}({WUXING_NAMES[yong_wx]})生之，用生体=吉"
    elif rel == REL_BIHE:     # 比和 → 平
        return 1, f"生门落{gong_name}，{star_name}比和，平"
    elif rel == REL_WOKE:     # 用克体 → 凶
        return -2, f"生门落{gong_name}({WUXING_NAMES[ti_wx]})，{star_name}({WUXING_NAMES[yong_wx]})克之，用克体=凶"
    elif rel == REL_SHENGWO:  # 体生用 → 不吉（泄）
        return -1, f"生门落{gong_name}({WUXING_NAMES[ti_wx]})生{star_name}({WUXING_NAMES[yong_wx]})，体生用=泄"
    elif rel == REL_KEWO:     # 体克用 → 小吉
        return 1, f"生门落{gong_name}({WUXING_NAMES[ti_wx]})克{star_name}({WUXING_NAMES[yong_wx]})，体克用=小吉"
    
    return 0, "关系未定"


def _d2_shengmen_wangshuai(ju):
    """
    维度2: 生门落宫的旺相休囚
    
    原文: "用旺体衰，体虽克用，不为大吉"
          "休囚不吉，所求全无"
    
    Returns: (score, ws_value, detail_str)
    """
    shengmen_palace = _find_gate_palace(ju, GATE_SHENG)
    if shengmen_palace is None:
        return 0, None, "生门未找到"
    
    gong_wx = GONG_WUXING.get(shengmen_palace)
    if gong_wx is None:
        return 0, None, "宫五行未知"
    
    month_br = ju.month_branch
    ws = calc_wangshuai(gong_wx, month_br)
    
    gong_name = GONG_GUA_NAMES.get(shengmen_palace, "?")
    ws_name = WS_NAMES.get(ws, "?")
    
    if ws == WS_WANG:
        return 2, ws, f"生门{gong_name}({WUXING_NAMES[gong_wx]})当月{ws_name}，大吉"
    elif ws == WS_XIANG:
        return 1, ws, f"生门{gong_name}({WUXING_NAMES[gong_wx]})当月{ws_name}，有气"
    elif ws == WS_XIU:
        return 0, ws, f"生门{gong_name}({WUXING_NAMES[gong_wx]})当月{ws_name}，平"
    elif ws == WS_QIU:
        return -1, ws, f"生门{gong_name}({WUXING_NAMES[gong_wx]})当月{ws_name}，无力"
    elif ws == WS_SI:
        return -2, ws, f"生门{gong_name}({WUXING_NAMES[gong_wx]})当月{ws_name}，大凶"
    
    return 0, ws, "旺衰未定"


def _d3_stock_palace_geju(ju, stock_palace, all_geju):
    """
    维度3: 标的宫位的格局
    
    原文: "吉格吉星，所求如意。有一不吉，所求仅半"
    
    检查:
    - 标的宫位有无三奇（乙丙丁）
    - 标的宫位有无吉格/凶格
    
    Returns: (score, has_sanqi, ji_count, xiong_count, detail_str)
    """
    if stock_palace is None:
        return 0, False, 0, 0, "标的宫位未找到"
    
    # Check 三奇
    h_stem = ju.heaven.get(stock_palace)
    has_sanqi = h_stem in SANQI if h_stem is not None else False
    
    # Count local geju
    local = [g for g in all_geju if g.palace == stock_palace]
    ji_geju = [g for g in local if g.jixiong == 1]
    xiong_geju = [g for g in local if g.jixiong == 0]
    
    score = 0
    details = []
    
    gong_name = GONG_GUA_NAMES.get(stock_palace, "?")
    
    if has_sanqi:
        qi_name = TIANGAN_NAMES.get(h_stem, "?")
        score += 2
        details.append(f"{gong_name}宫得{qi_name}奇")
    
    # 吉格按severity加分，凶格按severity减分
    for g in ji_geju:
        score += (g.severity + 1)
        details.append(f"[吉]{g.name}")
    for g in xiong_geju:
        score -= (g.severity + 1)
        details.append(f"[凶]{g.name}")
    
    if not details:
        details.append(f"{gong_name}宫无格局")
    
    return score, has_sanqi, len(ji_geju), len(xiong_geju), "；".join(details)


def _d4_stock_palace_xingmen(ju, stock_palace, stock_stem_idx):
    """
    维度4: 标的宫位的星门状态
    
    检查:
    - 九星吉凶 × 旺衰
    - 八门吉凶 × 旺衰
    - 门迫（宫克门）
    - 宫与本命干的关系
    
    Returns: (score, detail_str)
    """
    if stock_palace is None:
        return 0, "标的宫位未找到"
    
    month_br = ju.month_branch
    gong_wx = GONG_WUXING.get(stock_palace)
    score = 0
    details = []
    gong_name = GONG_GUA_NAMES.get(stock_palace, "?")
    
    # --- Star ---
    star = ju.stars.get(stock_palace)
    if star is not None:
        sw = STAR_WUXING.get(star)
        ws = calc_wangshuai(sw, month_br) if sw else None
        hq = ws in (WS_WANG, WS_XIANG) if ws is not None else False
        star_name = STAR_NAMES.get(star, "?")
        ws_name = WS_NAMES.get(ws, "?") if ws is not None else "?"
        
        if star in _STAR_DAJI:
            delta = 3 if hq else 1
            score += delta
            details.append(f"{star_name}(大吉/{ws_name})+{delta}")
        elif star in _STAR_XIAOJI:
            delta = 2 if hq else 1
            score += delta
            details.append(f"{star_name}(小吉/{ws_name})+{delta}")
        elif star in _STAR_DAXIONG:
            delta = -3 if hq else 0
            score += delta
            # 原文: "大凶无气变为吉" → 休囚时凶星不凶
            details.append(f"{star_name}(大凶/{ws_name}){delta:+d}")
        elif star in _STAR_XIAOXIONG:
            delta = -2 if hq else 0
            score += delta
            details.append(f"{star_name}(小凶/{ws_name}){delta:+d}")
    
    # --- Gate ---
    # 中宫寄坤(阳遁→P2, 阴遁→P8): P5 has no gate, use tianqin_host's gate
    tianqin_host = getattr(ju, 'tianqin_host', 2)
    gate = ju.gates.get(stock_palace) if stock_palace != 5 else ju.gates.get(tianqin_host)
    if gate is not None:
        gj = GATE_JIXIONG.get(gate, -1)
        gw = GATE_WUXING.get(gate)
        gws = calc_wangshuai(gw, month_br) if gw else None
        ghq = gws in (WS_WANG, WS_XIANG) if gws is not None else False
        gate_name = GATE_NAMES.get(gate, "?")
        gws_name = WS_NAMES.get(gws, "?") if gws is not None else "?"
        
        if gj == 1:  # 吉门
            delta = 3 if ghq else 1
            score += delta
            details.append(f"{gate_name}(吉/{gws_name})+{delta}")
        elif gj == 0:  # 凶门
            delta = -3 if ghq else 0
            score += delta
            details.append(f"{gate_name}(凶/{gws_name}){delta:+d}")
        else:  # 中平门
            details.append(f"{gate_name}(平)")
        
        # 门迫: 宫克门
        if gong_wx and gw and shengke(gong_wx, gw) == REL_WOKE:
            if gj == 1:
                score -= 2  # 吉门被迫，吉不就
                details.append("门迫(吉门受制-2)")
            elif gj == 0:
                score += 2  # 凶门被迫，凶不起
                details.append("门迫(凶门减凶+2)")
    
    # --- 宫与本命干关系 ---
    if stock_stem_idx is not None and gong_wx is not None:
        stem_wx = tg_wuxing(stock_stem_idx)
        pal_rel = shengke(stem_wx, gong_wx)
        stem_name = TIANGAN_NAMES.get(stock_stem_idx, "?")
        
        if pal_rel == REL_SHENGWO:    # 宫生干 = 得助
            score += 2
            details.append(f"宫生{stem_name}(得助+2)")
        elif pal_rel == REL_KEWO:     # 宫克干 = 受制
            score -= 2
            details.append(f"宫克{stem_name}(受制-2)")
        elif pal_rel == REL_WOSHENG:  # 干生宫 = 泄
            score -= 1
            details.append(f"{stem_name}生宫(泄-1)")
        elif pal_rel == REL_WOKE:     # 干克宫 = 消耗
            score -= 1
            details.append(f"{stem_name}克宫(耗-1)")
        # 比和 = 0

    # --- 纳音微调 (天盘干 + 地盘干 → 纳音五行 × 宫位五行) ---
    # 权重极小(±0.3)，仅作细化补充（邵雍"天地之道直而已"，不堆叠）
    if gong_wx is not None:
        heaven_stem = ju.heaven.get(stock_palace)
        ground_stem = ju.ground.get(stock_palace)
        if heaven_stem is not None and ground_stem is not None:
            # 需要天盘干+地盘干对应地支方可查纳音；此处用宫位对应地支近似
            # 实际纳音需完整干支对，暂用天盘干×宫卦地支（坎1→子0, 坤2→丑1…）
            _GONG_TO_DZ = {1: 0, 2: 1, 3: 3, 4: 4, 6: 10, 7: 9, 8: 2, 9: 6}
            approx_dz = _GONG_TO_DZ.get(stock_palace)
            if approx_dz is not None:
                nayin = get_nayin(heaven_stem, approx_dz)
                if nayin:
                    ny_wx, ny_name = nayin
                    ny_rel = shengke(ny_wx, gong_wx)
                    if ny_rel == REL_WOSHENG:   # 纳音生宫五行
                        score += 0.3
                        details.append(f"纳音{ny_name}生宫(+0.3)")
                    elif ny_rel == REL_WOKE:    # 纳音克宫五行
                        score -= 0.3
                        details.append(f"纳音{ny_name}克宫(-0.3)")

    return score, "；".join(details) if details else f"{gong_name}宫无星门数据"


# ============================================================
# Main assessment function
# ============================================================

def assess_stock_tianshi_baojian(ju, stock_code, all_geju):
    """
    基于宝鉴"占求财"的per-stock天时评估。
    
    替换原有的 assess_stock_tianshi()。
    
    判断逻辑（严格按宝鉴）:
    1. D1+D2 决定"求财大环境"（生门状态）
    2. D3+D4 决定"标的具体处境"（标的宫位状态）
    3. 综合判断按宝鉴原则:
       - 生门旺相 + 吉格吉星 → FAVORABLE
       - 有一不吉 → PARTIAL
       - 休囚 + 凶格 → UNFAVORABLE
    
    Returns: (assessment, score, detail_dict)
    """
    cfg = STOCK_POSITIONING.get(stock_code)
    if cfg is None:
        return "NEUTRAL", 0, {"error": "未知标的"}
    
    stem_idx = _STEM_NAME_TO_IDX.get(cfg["stem"])
    
    # --- Find stock palace ---
    stock_palace, plate_name = find_stock_palace(ju, stock_code)
    
    # --- Check fuyin/fanyin ---
    tp = gp = None
    if stem_idx is not None:
        for p in range(1, 10):
            if ju.heaven.get(p) == stem_idx:
                tp = p
            if ju.ground.get(p) == stem_idx:
                gp = p
    
    special = None
    if tp is not None and gp is not None:
        if tp == gp:
            special = "伏吟"
        elif _DUIGONG.get(tp) == gp:
            special = "反吟"
    
    # --- D1: 生门体用 ---
    d1_score, d1_detail = _d1_shengmen_tiyu(ju)
    
    # --- D2: 生门旺衰 ---
    d2_score, d2_ws, d2_detail = _d2_shengmen_wangshuai(ju)
    
    # --- D3: 标的宫位格局 ---
    d3_score, has_sanqi, ji_count, xiong_count, d3_detail = _d3_stock_palace_geju(
        ju, stock_palace, all_geju
    )
    
    # --- D4: 标的宫位星门 ---
    d4_score, d4_detail = _d4_stock_palace_xingmen(ju, stock_palace, stem_idx)
    
    # ============================================================
    # 综合判断 — 按宝鉴逻辑 v2
    #
    # 修正1: FAVORABLE前提=标的宫位九星旺相
    #   原文: "吉星更能逢旺相，万举万全功必成"
    #   九星旺相是必要条件，不需要四维度全吉
    #
    # 修正2: 伏吟=反复/停滞，不分吉凶
    #   原文: "只宜收敛货财，养威畜锐" — 策略建议，非吉凶
    #
    # 修正3: 3-way分类只在明确吉/凶时分方向
    #   邵雍: "有效方向性信号≈30%"
    # ============================================================
    
    # 生门环境 (D1+D2)
    shengmen_env = d1_score + d2_score
    
    # 标的处境 (D3+D4)  
    stock_env = d3_score + d4_score
    
    # 总分
    total_score = shengmen_env + stock_env
    
    # --- 关键条件提取 ---
    shengmen_good = d2_ws in (WS_WANG, WS_XIANG) if d2_ws is not None else False
    shengmen_bad = d2_ws in (WS_QIU, WS_SI) if d2_ws is not None else False
    
    # 标的宫位九星旺相检查 — FAVORABLE的必要条件
    star_at_stock = ju.stars.get(stock_palace) if stock_palace else None
    star_wangshuai_good = False
    if star_at_stock is not None:
        sw = STAR_WUXING.get(star_at_stock)
        if sw is not None:
            ws = calc_wangshuai(sw, ju.month_branch)
            star_wangshuai_good = ws in (WS_WANG, WS_XIANG)
    
    # 标的宫位九星本身是吉还是凶
    star_is_ji = star_at_stock in _STAR_DAJI or star_at_stock in _STAR_XIAOJI if star_at_stock is not None else False
    star_is_xiong = star_at_stock in _STAR_DAXIONG if star_at_stock is not None else False
    
    stock_bad = stock_env <= -3
    
    # --- 判断逻辑 ---
    
    # FAVORABLE: 九星旺相（必要） + 生门不休囚 + 标的宫位不凶
    # 原文: "吉星更能逢旺相，万举万全功必成"
    if star_wangshuai_good and not shengmen_bad and not stock_bad:
        if star_is_ji and shengmen_good:
            # 吉星旺相 + 生门旺相 = 最佳
            assessment = "FAVORABLE"
        elif star_is_ji:
            # 吉星旺相 + 生门平 = 良好
            assessment = "FAVORABLE"
        elif not star_is_xiong:
            # 非凶星旺相 + 环境不差 = 偏好
            assessment = "PARTIAL_GOOD"
        else:
            # 凶星虽旺相但力强则凶重 — 原文"大凶无气变为吉"反推
            assessment = "PARTIAL_BAD"
    
    # UNFAVORABLE: 生门休囚 + 凶格/凶星
    # 原文: "休囚不吉，所求全无"
    elif shengmen_bad and stock_bad:
        assessment = "UNFAVORABLE"
    elif shengmen_bad and star_is_xiong and star_wangshuai_good:
        # 生门休囚 + 凶星旺相 = 凶上加凶
        assessment = "UNFAVORABLE"
    
    # PARTIAL_BAD: 有一个明确不利因素
    elif shengmen_bad:
        assessment = "PARTIAL_BAD"
    elif stock_bad and not star_wangshuai_good:
        assessment = "PARTIAL_BAD"
    
    # PARTIAL_GOOD: 有一个明确有利因素但不完整
    elif star_wangshuai_good and stock_bad:
        # 星旺但环境凶 — 原文"有一不吉，所求仅半"
        assessment = "PARTIAL_GOOD"
    elif shengmen_good and stock_env >= 1:
        assessment = "PARTIAL_GOOD"
    
    # NEUTRAL: 其他
    else:
        assessment = "NEUTRAL"
    
    # --- 伏吟/反吟 ---
    # 伏吟: 不改变吉凶判断，只标记状态=反复/停滞
    # 原文: "只宜收敛货财，养威畜锐" — 策略建议，非吉凶覆盖
    if special == "伏吟":
        assessment = "STAGNANT"  # 统一为STAGNANT，不分吉凶
    elif special == "反吟":
        assessment = "VOLATILE"
    
    detail = {
        "stock": cfg["name"],
        "stock_palace": stock_palace,
        "plate": plate_name,
        "tp": tp,
        "gp": gp,
        "special": special,
        "shengmen_palace": _find_gate_palace(ju, GATE_SHENG),
        "d1_shengmen_tiyu": {"score": d1_score, "detail": d1_detail},
        "d2_shengmen_wangshuai": {"score": d2_score, "ws": WS_NAMES.get(d2_ws, "?"), "detail": d2_detail},
        "d3_stock_geju": {"score": d3_score, "sanqi": has_sanqi, "ji": ji_count, "xiong": xiong_count, "detail": d3_detail},
        "d4_stock_xingmen": {"score": d4_score, "detail": d4_detail},
        "shengmen_env": shengmen_env,
        "stock_env": stock_env,
        "total_score": total_score,
    }
    
    return assessment, total_score, detail


# ============================================================
# Quick test / demo
# ============================================================
if __name__ == "__main__":
    from datetime import datetime
    from fcas_engine_v2 import paipan, evaluate_all_geju
    
    # Test with a sample datetime
    dt = datetime(2026, 4, 4, 10, 0)
    ju = paipan(dt)
    all_geju = evaluate_all_geju(ju)
    
    print(f"=== 天时评估测试 {dt} ===")
    print(f"局: {'阳' if ju.is_yangdun else '阴'}遁{ju.ju_number}局")
    print()
    
    for code in STOCK_POSITIONING:
        assessment, score, detail = assess_stock_tianshi_baojian(ju, code, all_geju)
        name = detail.get("stock", code)
        palace = detail.get("stock_palace", "?")
        sm_palace = detail.get("shengmen_palace", "?")
        sp = detail.get("special", "")
        sp_str = f" [{sp}]" if sp else ""
        
        print(f"{name}({code}): {assessment} (score={score}){sp_str}")
        print(f"  标的宫={palace} | 生门宫={sm_palace}")
        print(f"  D1体用: {detail['d1_shengmen_tiyu']['detail']}")
        print(f"  D2旺衰: {detail['d2_shengmen_wangshuai']['detail']}")
        print(f"  D3格局: {detail['d3_stock_geju']['detail']}")
        print(f"  D4星门: {detail['d4_stock_xingmen']['detail']}")
        print()
