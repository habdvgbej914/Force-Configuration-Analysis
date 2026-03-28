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
        "3. Call quick_scan with your 6 judgments",
        "4. Translate result into business language recommendation",
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
def get_analysis_history() -> str:
    """View past analysis results / 查看历史分析结果。"""
    history = load_history()
    if not history:
        return "No analysis history yet. / 暂无分析历史。"

    lines = ["ANALYSIS HISTORY / 分析历史", "=" * 40]
    for i, h in enumerate(history):
        lines.append(f"\n{i + 1}. {h['domain']}")
        lines.append(f"   Code: {h['binary_code']} | Mislocation: {h['mislocation']}")
        lines.append(f"   Momentum: {h['momentum']} | Substance: {h['substance']}")
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
3. For each of 6 criteria, assess the 5 dimensions, then make a binary judgment
4. Call quick_scan with your 6 binary judgments
5. Translate the result into a clear, actionable business recommendation

CRITICAL: Never use metaphysical terminology in output. Business language only.
重要：永远不要在输出中使用玄学术语。只用商业语言。"""


# ============================================================
# Entry Point / 入口
# ============================================================

if __name__ == "__main__":
    app.run()