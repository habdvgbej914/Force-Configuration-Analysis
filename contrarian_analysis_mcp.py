"""
Contrarian Opportunity Analysis System
MCP Server Implementation v0.1
逆向机会分析系统 MCP服务器
"""

import os
import json
from datetime import datetime
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

HISTORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "analysis_history.json")
DEEP_HISTORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "deep_analysis_history.json")

app = FastMCP("contrarian-analysis-server")

# Five analytical dimensions / 五个分析维度
FIVE_PHASES = ["origin", "visibility", "growth", "constraint", "foundation"]

# Six criteria in three-layer structure / 三层结构的六条判断依据
CRITERIA = {
    "c1": {
        "layer": "environment",
        "label_en": "Trend Alignment",
        "label_zh": "趋势方向",
        "question_en": "Is this domain aligned or misaligned with the era's macro trend?",
        "question_zh": "这个领域和时代趋势是顺还是逆？",
        "positive": "aligned",
        "negative": "misaligned",
        "phase_prompts": {
            "origin": "Is the fundamental problem becoming more urgent or less relevant?",
            "visibility": "Current level of public attention and capital interest.",
            "growth": "Are new application scenarios extending or contracting?",
            "constraint": "Policy, tech bottlenecks, standards: tightening or loosening?",
            "foundation": "Maturity of talent, supply chains, supporting industries."
        }
    },
    "c2": {
        "layer": "environment",
        "label_en": "Energy State",
        "label_zh": "能量状态",
        "question_en": "Is this domain currently accumulating or dissipating energy?",
        "question_zh": "这个领域当下是在积蓄还是在消散？",
        "positive": "accumulating",
        "negative": "dissipating",
        "phase_prompts": {
            "origin": "Is core technology or capability being deepened or lost?",
            "visibility": "Are people quietly building, or retreating?",
            "growth": "Are new entrants and research increasing or decreasing?",
            "constraint": "Is industry consensus forming, or becoming chaotic?",
            "foundation": "Are capital, talent, resources flowing in or out?"
        }
    },
    "c3": {
        "layer": "participant",
        "label_en": "Incumbent Alignment",
        "label_zh": "玩家匹配度",
        "question_en": "Are incumbents matched or mismatched with the domain's nature?",
        "question_zh": "现有玩家的做法和领域本质是匹配还是错位？",
        "positive": "matched",
        "negative": "mismatched",
        "phase_prompts": {
            "origin": "Do incumbents understand the fundamental problem?",
            "visibility": "Relationship between market noise and actual value.",
            "growth": "Natural growth rhythm or force-accelerating?",
            "constraint": "Are barriers real or sustained by capital burn?",
            "foundation": "Are their resources sustainable or temporary?"
        }
    },
    "c4": {
        "layer": "participant",
        "label_en": "Personal Sustainability",
        "label_zh": "个人持续力",
        "question_en": "Can you sustain through the dormancy period?",
        "question_zh": "你自己能不能撑过蛰伏周期？",
        "positive": "can sustain",
        "negative": "cannot sustain",
        "phase_prompts": {
            "origin": "Can your motivation sustain you through zero return?",
            "visibility": "How much attention and resources can you mobilize?",
            "growth": "Are your skills developing or stagnating?",
            "constraint": "What are your stop-loss lines?",
            "foundation": "How long can your finances and support sustain you?"
        }
    },
    "c5": {
        "layer": "foundation",
        "label_en": "Fundamental Solidity",
        "label_zh": "基本面虚实",
        "question_en": "Are the fundamentals solid or hollow?",
        "question_zh": "基本面是实的还是虚的？",
        "positive": "solid",
        "negative": "hollow",
        "phase_prompts": {
            "origin": "Is the demand real or manufactured by narrative?",
            "visibility": "Gap between discussion and actual paying behavior.",
            "growth": "How complete is the organic value chain?",
            "constraint": "Does a validated business model exist?",
            "foundation": "Are population, habits, infrastructure mature?"
        }
    },
    "c6": {
        "layer": "foundation",
        "label_en": "Domain Weight",
        "label_zh": "领域轻重",
        "question_en": "Is this domain heavy or light?",
        "question_zh": "这个领域是重还是轻？",
        "positive": "heavy",
        "negative": "light",
        "phase_prompts": {
            "origin": "Core value from long-term accumulation or short-term creativity?",
            "visibility": "How long for results to become visible?",
            "growth": "Is capability accumulation fast or slow?",
            "constraint": "Natural barrier: technical, qualifications, or networks?",
            "foundation": "Minimum resource threshold to operate?"
        }
    }
}

# Layer synthesis logic / 层级综合逻辑
LAYER_SYNTHESIS = {
    "environment": {
        "label": "Momentum / 势",
        "criteria": ["c1", "c2"],
        "interpretations": {
            (1, 1): "Strongest momentum. Trend aligned and energy accumulating.",
            (1, 0): "Momentum weakening. Trend aligned but energy dissipating. Possible contrarian timing.",
            (0, 1): "Counter-trend but energy accumulating quietly. Potential contrarian opportunity.",
            (0, 0): "Not worth entering. Counter-trend and dissipating."
        }
    },
    "participant": {
        "label": "Feasibility / 可行性",
        "criteria": ["c3", "c4"],
        "interpretations": {
            (0, 1): "Highest feasibility. Incumbents misaligned and you can sustain.",
            (1, 1): "Limited but possible. Incumbents aligned, space tight, but you can sustain.",
            (0, 0): "Opportunity exists but not for you. Cannot sustain through dormancy.",
            (1, 0): "Not feasible. Incumbents aligned and you cannot sustain."
        }
    },
    "foundation": {
        "label": "Substance / 质",
        "criteria": ["c5", "c6"],
        "interpretations": {
            (1, 1): "Most stable. Solid fundamentals and heavy domain. High barrier, lasting advantage.",
            (1, 0): "Real demand but low barriers. Easy to enter, easy to be displaced.",
            (0, 1): "Highest risk. Heavy domain but hollow fundamentals.",
            (0, 0): "Not worth serious consideration. Hollow and light."
        }
    }
}

# Cross-layer matrix / 跨层矩阵
CROSS_LAYER = {
    ("strong", "solid"): "Best window. Competition may have started. Feasibility layer decisive.",
    ("strong", "hollow"): "Potential bubble. High heat but weak foundation. Extreme caution.",
    ("weak", "solid"): "Undervalued opportunity. Key question: when does momentum inflection arrive?",
    ("weak", "hollow"): "Not worth entering. No momentum, no substance, no foothold."
}


# ============================================================
# Analysis Engine / 分析引擎
# ============================================================

def synthesize_layer(layer_name, criterion_states):
    """Synthesize two criteria within a layer / 综合同一层内的两个判断依据"""
    layer = LAYER_SYNTHESIS[layer_name]
    c_ids = layer["criteria"]
    states = tuple(criterion_states[c] for c in c_ids)
    return {
        "layer": layer_name,
        "label": layer["label"],
        "states": dict(zip(c_ids, states)),
        "interpretation": layer["interpretations"].get(states, "Undetermined.")
    }


def generate_binary_code(states):
    """Generate 6-bit code. Top to bottom: c2 c1 c4 c3 c6 c5 / 生成6位编码"""
    return "".join(str(states.get(c, 0)) for c in ["c2", "c1", "c4", "c3", "c6", "c5"])


def detect_mislocation(criterion_states, layer_syntheses):
    """Detect Form-Flow Mislocation / 检测形流错位"""
    env_sum = sum(layer_syntheses["environment"]["states"].values())
    found_sum = sum(layer_syntheses["foundation"]["states"].values())

    if found_sum >= 1 and env_sum == 0:
        return {
            "type": "form_without_flow",
            "description": "Established infrastructure but no market attention. Classic undervalued opportunity."
        }
    elif env_sum >= 1 and found_sum == 0:
        return {
            "type": "flow_without_form",
            "description": "Growing attention but no crystallized solution. Bubble risk - validate fundamentals."
        }
    elif env_sum >= 1 and found_sum >= 1:
        return {
            "type": "no_mislocation_positive",
            "description": "Both form and flow present. Mainstream opportunity - competition likely active."
        }
    else:
        return {
            "type": "no_mislocation_negative",
            "description": "Neither form nor flow. No substance, no momentum."
        }


def run_analysis(domain, criterion_states):
    """Run the complete analysis pipeline / 运行完整分析流程"""
    layers = {
        name: synthesize_layer(name, criterion_states)
        for name in ["environment", "participant", "foundation"]
    }

    env_s = sum(layers["environment"]["states"].values())
    found_s = sum(layers["foundation"]["states"].values())
    momentum = "strong" if env_s >= 1 else "weak"
    substance = "solid" if found_s >= 1 else "hollow"
    cross = CROSS_LAYER.get((momentum, substance), "Undetermined.")
    mislocation = detect_mislocation(criterion_states, layers)
    code = generate_binary_code(criterion_states)

    return {
        "domain": domain,
        "binary_code": code,
        "timestamp": datetime.now().isoformat(),
        "layers": {
            n: {"label": l["label"], "interpretation": l["interpretation"]}
            for n, l in layers.items()
        },
        "cross_layer": {
            "momentum": momentum,
            "substance": substance,
            "interpretation": cross
        },
        "mislocation": mislocation
    }


# ============================================================
# History / 历史记录
# ============================================================

def load_history():
    """Load analysis history / 加载分析历史"""
    try:
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_history(result):
    """Save analysis to history / 保存分析到历史"""
    history = load_history()
    history.append({
        "domain": result["domain"],
        "binary_code": result["binary_code"],
        "mislocation": result["mislocation"]["type"],
        "momentum": result["cross_layer"]["momentum"],
        "substance": result["cross_layer"]["substance"],
        "timestamp": result["timestamp"]
    })
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def load_deep_history():
    """Load deep analysis history / 加载深度分析历史"""
    try:
        with open(DEEP_HISTORY_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_deep_history(record):
    """Save deep analysis to history with full reasoning chain / 保存深度分析到历史，含完整推理链"""
    history = load_deep_history()
    history.append(record)
    with open(DEEP_HISTORY_FILE, "w") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


# ============================================================
# MCP Tools / MCP工具
# ============================================================

@app.tool()
def get_framework_guide() -> str:
    """Get the complete analysis framework guide with all 6 criteria and 5 dimensions.
    获取完整的分析框架指南，包含6个判断依据和5个维度。"""
    lines = [
        "CONTRARIAN OPPORTUNITY ANALYSIS FRAMEWORK",
        "逆向机会分析框架",
        "=" * 50, "",
        "Six criteria in three layers. Each criterion assessed across five dimensions.",
        "Each criterion outputs binary: Positive(1) or Negative(0).",
        "Six bits = 64 possible situations.", ""
    ]

    for layer_name, layer in LAYER_SYNTHESIS.items():
        lines.append(f"\n{'─' * 40}")
        lines.append(f"LAYER: {layer['label']}")

        for c_id in layer["criteria"]:
            c = CRITERIA[c_id]
            lines.append(f"\n  [{c_id}] {c['label_en']} / {c['label_zh']}")
            lines.append(f"  Q: {c['question_en']}")
            lines.append(f"     {c['question_zh']}")
            lines.append(f"  Positive(1): {c['positive']} | Negative(0): {c['negative']}")
            lines.append(f"  Five dimensions to assess:")
            for p in FIVE_PHASES:
                lines.append(f"    - {p}: {c['phase_prompts'][p]}")

    lines.extend([
        "", "=" * 50,
        "HOW TO USE:",
        "1. Research the domain across all 6 criteria x 5 dimensions",
        "2. Make a binary judgment (0 or 1) for each criterion",
        "3. For thorough analysis: call deep_scan with all 30 assessments + 6 judgments",
        "   For fast screening: call quick_scan with just 6 judgments",
        "4. Translate result into business language recommendation",
        "",
        "deep_scan records the full reasoning chain for review and comparison.",
        "quick_scan is for rapid multi-domain screening.",
        "",
        "RULE: Never use metaphysical terms in output. Business language only."
    ])

    return "\n".join(lines)


@app.tool()
def quick_scan(
    domain: str,
    trend_aligned: bool,
    energy_accumulating: bool,
    incumbents_misaligned: bool,
    can_sustain: bool,
    fundamentals_solid: bool,
    domain_heavy: bool
) -> str:
    """Quick 6-bit contrarian opportunity scan for a domain.
    快速6位逆向机会扫描。

    Args:
        domain: name of the domain to analyze / 要分析的领域名称
        trend_aligned: aligned with macro trends? / 与宏观趋势一致？
        energy_accumulating: energy accumulating? / 能量在积蓄？
        incumbents_misaligned: incumbent approaches wrong? / 现有玩家做法错位？
        can_sustain: can survive dormancy? / 能撑过蛰伏期？
        fundamentals_solid: fundamentals real? / 基本面扎实？
        domain_heavy: high-barrier domain? / 高壁垒领域？
    """
    states = {
        "c1": int(trend_aligned),
        "c2": int(energy_accumulating),
        "c3": 0 if incumbents_misaligned else 1,
        "c4": int(can_sustain),
        "c5": int(fundamentals_solid),
        "c6": int(domain_heavy)
    }

    result = run_analysis(domain, states)
    save_history(result)

    lines = [
        f"CONTRARIAN ANALYSIS: {domain}",
        f"Binary Code: {result['binary_code']}",
        ""
    ]

    for name in ["environment", "participant", "foundation"]:
        l = result["layers"][name]
        lines.extend([f"{l['label']}:", f"  {l['interpretation']}", ""])

    cl = result["cross_layer"]
    lines.extend([
        f"Cross-Layer: Momentum={cl['momentum']} x Substance={cl['substance']}",
        f"  {cl['interpretation']}",
        ""
    ])

    ml = result["mislocation"]
    lines.extend([
        f"Form-Flow Analysis: {ml['type']}",
        f"  {ml['description']}"
    ])

    return "\n".join(lines)


@app.tool()
def deep_scan(
    domain: str,
    c1_judgment: bool,
    c1_origin: str, c1_visibility: str, c1_growth: str, c1_constraint: str, c1_foundation: str,
    c2_judgment: bool,
    c2_origin: str, c2_visibility: str, c2_growth: str, c2_constraint: str, c2_foundation: str,
    c3_judgment_misaligned: bool,
    c3_origin: str, c3_visibility: str, c3_growth: str, c3_constraint: str, c3_foundation: str,
    c4_judgment: bool,
    c4_origin: str, c4_visibility: str, c4_growth: str, c4_constraint: str, c4_foundation: str,
    c5_judgment: bool,
    c5_origin: str, c5_visibility: str, c5_growth: str, c5_constraint: str, c5_foundation: str,
    c6_judgment: bool,
    c6_origin: str, c6_visibility: str, c6_growth: str, c6_constraint: str, c6_foundation: str
) -> str:
    """Deep 6-bit analysis with full 30-dimension reasoning chain recorded.
    深度6位分析，记录完整的30维度推理链。

    For each criterion (c1-c6), provide:
    - A binary judgment (True/False)
    - Five dimension assessments (origin, visibility, growth, constraint, foundation)

    对每条判断依据(c1-c6)，提供：
    - 一个二进制判断(True/False)
    - 五个维度评估(origin, visibility, growth, constraint, foundation)

    Args:
        domain: domain being analyzed / 被分析的领域
        c1_judgment: C1 trend aligned? / C1趋势是否一致？
        c1_origin: C1 origin dimension assessment / C1根本原因维度评估
        c1_visibility: C1 visibility assessment / C1感知程度评估
        c1_growth: C1 growth assessment / C1生长扩张评估
        c1_constraint: C1 constraint assessment / C1边界收敛评估
        c1_foundation: C1 foundation assessment / C1承载基础评估
        c2_judgment: C2 energy accumulating? / C2能量是否积蓄？
        c2_origin: C2 origin assessment
        c2_visibility: C2 visibility assessment
        c2_growth: C2 growth assessment
        c2_constraint: C2 constraint assessment
        c2_foundation: C2 foundation assessment
        c3_judgment_misaligned: C3 incumbents misaligned? / C3现有玩家是否错位？
        c3_origin: C3 origin assessment
        c3_visibility: C3 visibility assessment
        c3_growth: C3 growth assessment
        c3_constraint: C3 constraint assessment
        c3_foundation: C3 foundation assessment
        c4_judgment: C4 can sustain? / C4能否持续？
        c4_origin: C4 origin assessment
        c4_visibility: C4 visibility assessment
        c4_growth: C4 growth assessment
        c4_constraint: C4 constraint assessment
        c4_foundation: C4 foundation assessment
        c5_judgment: C5 fundamentals solid? / C5基本面是否扎实？
        c5_origin: C5 origin assessment
        c5_visibility: C5 visibility assessment
        c5_growth: C5 growth assessment
        c5_constraint: C5 constraint assessment
        c5_foundation: C5 foundation assessment
        c6_judgment: C6 domain heavy? / C6领域是否重？
        c6_origin: C6 origin assessment
        c6_visibility: C6 visibility assessment
        c6_growth: C6 growth assessment
        c6_constraint: C6 constraint assessment
        c6_foundation: C6 foundation assessment
    """
    # Build criterion states / 构建判断状态
    states = {
        "c1": int(c1_judgment),
        "c2": int(c2_judgment),
        "c3": 0 if c3_judgment_misaligned else 1,
        "c4": int(c4_judgment),
        "c5": int(c5_judgment),
        "c6": int(c6_judgment)
    }

    # Build reasoning chain / 构建推理链
    params = locals()
    reasoning_chain = {}
    for c_id in ["c1", "c2", "c3", "c4", "c5", "c6"]:
        criterion = CRITERIA[c_id]
        reasoning_chain[c_id] = {
            "criterion": f"{criterion['label_en']} / {criterion['label_zh']}",
            "question": criterion["question_en"],
            "judgment": states[c_id],
            "judgment_label": criterion["positive"] if states[c_id] == 1 else criterion["negative"],
            "dimensions": {
                phase: params[f"{c_id}_{phase}"]
                for phase in FIVE_PHASES
            }
        }

    # Run structural analysis / 运行结构分析
    result = run_analysis(domain, states)

    # Save to quick history / 保存到快速历史
    save_history(result)

    # Save full deep record / 保存完整深度记录
    deep_record = {
        "domain": domain,
        "binary_code": result["binary_code"],
        "timestamp": result["timestamp"],
        "reasoning_chain": reasoning_chain,
        "layers": result["layers"],
        "cross_layer": result["cross_layer"],
        "mislocation": result["mislocation"]
    }
    save_deep_history(deep_record)

    # Format output / 格式化输出
    lines = [
        f"DEEP CONTRARIAN ANALYSIS: {domain}",
        f"Binary Code: {result['binary_code']}",
        f"{'=' * 50}",
        ""
    ]

    # Reasoning chain per criterion / 每条依据的推理链
    for c_id in ["c1", "c2", "c3", "c4", "c5", "c6"]:
        rc = reasoning_chain[c_id]
        symbol = "+" if rc["judgment"] == 1 else "-"
        lines.append(f"[{c_id}] {rc['criterion']}")
        lines.append(f"  Judgment: [{symbol}] {rc['judgment_label']}")
        for phase in FIVE_PHASES:
            lines.append(f"    {phase}: {rc['dimensions'][phase]}")
        lines.append("")

    # Layer synthesis / 层级综合
    lines.append(f"{'─' * 50}")
    lines.append("LAYER SYNTHESIS:")
    for name in ["environment", "participant", "foundation"]:
        l = result["layers"][name]
        lines.extend([f"  {l['label']}: {l['interpretation']}"])

    # Cross-layer / 跨层
    lines.append("")
    cl = result["cross_layer"]
    lines.append(f"CROSS-LAYER: Momentum={cl['momentum']} x Substance={cl['substance']}")
    lines.append(f"  {cl['interpretation']}")

    # Mislocation / 错位
    lines.append("")
    ml = result["mislocation"]
    lines.append(f"FORM-FLOW: {ml['type']}")
    lines.append(f"  {ml['description']}")

    lines.extend([
        "",
        f"{'=' * 50}",
        f"Full reasoning chain saved to deep_analysis_history.json",
        f"完整推理链已保存至 deep_analysis_history.json"
    ])

    return "\n".join(lines)


@app.tool()
def get_analysis_history() -> str:
    """View past analysis results (quick + deep) / 查看历史分析结果（快速+深度）。"""
    history = load_history()
    deep_history = load_deep_history()

    if not history and not deep_history:
        return "No analysis history yet. / 暂无分析历史。"

    lines = ["ANALYSIS HISTORY / 分析历史", "=" * 40]

    if history:
        lines.append("\n--- Quick Scans ---")
        for i, h in enumerate(history):
            lines.append(f"\n{i + 1}. {h['domain']}")
            lines.append(f"   Code: {h['binary_code']} | Mislocation: {h['mislocation']}")
            lines.append(f"   Momentum: {h['momentum']} | Substance: {h['substance']}")
            lines.append(f"   Time: {h['timestamp']}")

    if deep_history:
        lines.append(f"\n--- Deep Analyses ({len(deep_history)} records) ---")
        for i, h in enumerate(deep_history):
            lines.append(f"\n{i + 1}. {h['domain']}")
            lines.append(f"   Code: {h['binary_code']} | Mislocation: {h['mislocation']['type']}")
            lines.append(f"   Momentum: {h['cross_layer']['momentum']} | Substance: {h['cross_layer']['substance']}")
            lines.append(f"   Criteria chain: {' '.join(f'{c}={v['judgment']}' for c,v in h['reasoning_chain'].items())}")
            lines.append(f"   Time: {h['timestamp']}")

    return "\n".join(lines)


# ============================================================
# MCP Prompt Template / MCP提示词模板
# ============================================================

@app.prompt("analyze-opportunity")
def analyze_opportunity_prompt() -> str:
    """Standard prompt for contrarian opportunity analysis.
    逆向机会分析标准提示词。"""
    return """You are using the Contrarian Opportunity Analysis System.

Steps:
1. Call get_framework_guide to understand the 6 criteria and 5 dimensions
2. Research the domain the user wants to analyze
3. For each of 6 criteria, assess all 5 dimensions thoroughly, then make a binary judgment
4. Call deep_scan with all 30 dimension assessments and 6 binary judgments (for full reasoning chain)
   OR call quick_scan with just the 6 binary judgments (for fast screening)
5. Translate the result into a clear, actionable business recommendation

Use deep_scan for thorough analysis. Use quick_scan only when comparing many domains quickly.

CRITICAL: Never use metaphysical terminology in output. Business language only.
重要：永远不要在输出中使用玄学术语。只用商业语言。"""


# ============================================================
# Entry Point / 入口
# ============================================================

if __name__ == "__main__":
    app.run()