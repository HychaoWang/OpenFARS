# Project Brief: LLM-as-a-Judge Bias Calibration (GSM8K)

## Scope
- **Domain**: LLM-as-a-judge bias calibration for math reasoning solutions (GSM8K).
- **Goal**: Reduce positional and verbosity bias in automatic grading while keeping accuracy ≥ baseline.
- **Output**: Short report + reproducible scripts + logs.

## Constraints
- **Budget**: ≤ 4 GPU hours (or CPU equivalence) and ≤ 200k tokens for prompting per run.
- **Time**: Single pass should finish within 4 wall-clock hours.
- **Safety**: No high-risk domains; only public math data.

## Primary Metric
- **Accuracy agreement** between calibrated judge and reference labels on GSM8K (exact match correctness), with confidence intervals.

## Secondary Metrics
- Bias gap between long vs. short answers; variance across random seeds.
- Cost metrics: token usage and runtime.

## Failure Criteria
- No measurable agreement improvement over baseline judge.
- Budget overrun or missing logs for configs, seeds, and prompts.
- Inability to reproduce scores within ±1% on rerun.

## MVP Experiment
- Compare baseline judge vs. calibrated judge (prompt debiasing + normalization) on a 200-sample GSM8K subset; report accuracy, bias gap, and cost.
