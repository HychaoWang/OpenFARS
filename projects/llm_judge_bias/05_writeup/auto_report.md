# Auto-generated Report

## Question
Normalizing student answers into structured steps before judging reduces verbosity bias and improves agreement with gold labels by at least 2%.

## Method
- Dataset(s): GSM8K_subset_200
- Models: gpt-judge-baseline, gpt-judge-normalized
- Variables: ['normalization_prompt', 'rubric']
- Controls: baseline_judge_prompt_v0

## Results
- Baseline accuracy: 0.730
- Normalized accuracy: 0.755
- Bias gap verbose vs concise: 0.050
- Token usage: 120000
- Compute hours: 1.2

## Discussion
- Gain vs. baseline: 0.025
- Budget within limits: True
- Status: success

## Next Steps
- Expand sample size and test alternate normalization prompts.
- Add statistical significance testing over multiple seeds.
- Capture human spot-checks for judge reliability.
