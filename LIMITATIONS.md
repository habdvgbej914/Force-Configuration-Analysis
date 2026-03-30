# FCAS Limitations / 气象分析系统局限性

## 1. Backtest Hindsight Bias / 回测后视偏差

All backtest judgments (C1-C6) were made with knowledge of what happened next.
Real-time forward-looking analysis (daily_scan.py) is the true test.

## 2. Input Quality Dependency / 输入质量依赖

The framework's output depends entirely on the quality of the six binary judgments.
When using Claude API for daily scanning, the judgments inherit LLM limitations:
search bias, narrative capture, recency bias, data gaps.

## 3. Structural Relations Fixed by Family / 结构关系固定于结构族

The five structural relations are determined by the structural family element,
which is derived from the binary code via the eight-family system.
The same binary code always maps to the same family and relations.
This means the framework cannot distinguish between different domains
that happen to produce the same binary code.

## 4. Intent Assessment Granularity / 意图评估粒度

The current intent system has five options (seek_profit, seek_position,
seek_protection, seek_output, assess_competition). Real-world intents
are more nuanced. The system may oversimplify complex decision contexts.

## 5. No Timing Mechanism / 无时机机制

The framework diagnoses the current state but does not predict when
conditions will change. A "dormant" assessment may last days or years.
The daily H4 scanning partially addresses this through repeated observation.

## 6. Sample Size / 样本量

SPY backtest has 25 events. Supported intent accuracy is 89% but
based on only 9 directional calls. More forward-looking data needed.

## 7. Single-Asset Testing / 单资产测试

Primary backtest is SPY only. GLD/SLV/COPX backtests exist from v0.1
but have not been updated to the intent-based system.