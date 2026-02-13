# OpenFARS Minimal Pipeline

This repo implements a lightweight, file-driven scaffold inspired by FARS to run an end-to-end research loop (`ideate -> plan -> run -> write`). The sample project targets **LLM-as-a-judge bias calibration on GSM8K**, using **LLM API inference only (no training/fine-tuning)**.

## Layout
- `projects/<project_name>/` — a self-contained workspace (see `projects/llm_judge_bias/`).
- `schemas/` — JSON schemas for hypotheses and plans.
- `src/pipeline.py` — orchestrates ideation, review, planning, experiment, and report generation.

## Project Directory Convention
- `00_brief/` research brief and constraints
- `01_lit/` literature notes and caches
- `02_hypotheses/` structured hypotheses (`hypotheses.json`)
- `03_plan/` experiment plan (`plan.json`)
- `04_runs/` execution configs, logs, and metrics
- `05_writeup/` reports and figures
- `meta/` audit trails and cost tracking

## Quickstart (auto workflow)
1. Ensure Python 3.10+ is available.
2. To run fully automatically with DeepSeek:
   - `DEEPSEEK_API_KEY` (your key)
   - `DEEPSEEK_API_URL` (full chat completion endpoint)
3. Run the pipeline (uses sample project by default):
   ```bash
   python src/pipeline.py
   ```
4. Outputs:
   - New run folder under `projects/llm_judge_bias/04_runs/` with config, results, and logs.
   - Auto-generated report at `projects/llm_judge_bias/05_writeup/auto_report.md`.
   - Cost trace appended to `projects/llm_judge_bias/meta/costs.json`.

Behavior:
- If hypotheses/plan files are missing or empty, the pipeline auto-generates them via DeepSeek using `00_brief/research_directions.md` / `brief.md` context.
- Experiment step uses DeepSeek API to grade a tiny GSM8K subset in `projects/llm_judge_bias/data/gsm8k_tiny.jsonl`; falls back to simulation when API env vars are absent.

## Adapting to a New Project
1. Copy `projects/llm_judge_bias` to a new directory name.
2. Update `00_brief/brief.md`, `02_hypotheses/hypotheses.json`, and `03_plan/plan.json` per the schemas.
3. Run `python src/pipeline.py --project projects/<your_project>`.

## Notes
- Validation is lightweight (schema key checks, budget sanity, API-only enforcement) to stay dependency-free.
- Experiment execution supports two modes: DeepSeek API calls when env vars are set (recommended) or simulation when offline. No training/fine-tuning is used.
