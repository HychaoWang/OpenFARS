"""
Minimal end-to-end pipeline scaffold for a FARS-like research loop.

Flow: ideate -> review -> plan -> experiment -> write.
Targets the sample project at `projects/llm_judge_bias/` but works for any
project following the same directory convention and JSON schemas in `schemas/`.
"""

from __future__ import annotations

import argparse
import json
import os
import textwrap
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from deepseek_client import DeepSeekClient


# ---------- helpers ----------


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def dump_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def ensure_required(obj: Dict[str, Any], required: List[str], label: str) -> None:
    missing = [k for k in required if k not in obj]
    if missing:
        raise ValueError(f"{label} missing required fields: {', '.join(missing)}")


# ---------- data containers ----------


@dataclass
class ProjectContext:
    root: Path

    def __post_init__(self) -> None:
        self.root = self.root.resolve()
        self.paths = {
            "brief": self.root / "00_brief" / "brief.md",
            "directions": self.root / "00_brief" / "research_directions.md",
            "hypotheses": self.root / "02_hypotheses" / "hypotheses.json",
            "plan": self.root / "03_plan" / "plan.json",
            "runs": self.root / "04_runs",
            "writeup": self.root / "05_writeup",
            "meta": self.root / "meta",
            "data": self.root / "data" / "gsm8k_tiny.jsonl",
        }


# ---------- agents ----------


class IdeationAgent:
    def __init__(self, ctx: ProjectContext, client: Optional[DeepSeekClient] = None):
        self.ctx = ctx
        self.client = client

    def select_hypothesis(self) -> Dict[str, Any]:
        hyp_path = self.ctx.paths["hypotheses"]
        if hyp_path.exists():
            hypotheses = load_json(hyp_path)
            if hypotheses:
                return hypotheses[0]

        if not self.client:
            raise ValueError("No hypotheses found and DeepSeek client unavailable for generation")

        directions = self._load_research_directions()
        prompt = (
            "You are an ideation agent generating falsifiable hypotheses for LLM judge bias calibration. "
            "Return a JSON array of hypotheses following this schema: [ {id, motivation, statement, expected_gain, "
            "metrics:[{name,type,target}], mvp:{dataset,procedure,sample_size}, failure_conditions:[], budget:{token_limit,compute_hours}, notes} ]. "
            f"Use the research directions:\n{directions}\nRespond with JSON only."
        )
        reply = self.client.chat([
            {"role": "system", "content": "Return JSON only"},
            {"role": "user", "content": prompt},
        ])
        hypotheses = json.loads(reply)
        if not isinstance(hypotheses, list) or not hypotheses:
            raise ValueError("DeepSeek returned empty hypotheses")
        dump_json(hyp_path, hypotheses)
        return hypotheses[0]

    def _load_research_directions(self) -> str:
        if self.ctx.paths["directions"].exists():
            return self.ctx.paths["directions"].read_text(encoding="utf-8")
        return self.ctx.paths["brief"].read_text(encoding="utf-8")


class Reviewer:
    def __init__(self, schemas_root: Path):
        self.schemas_root = schemas_root

    def review_hypothesis(self, hyp: Dict[str, Any]) -> None:
        ensure_required(
            hyp,
            ["id", "motivation", "statement", "metrics", "mvp", "budget", "failure_conditions", "expected_gain"],
            "hypothesis",
        )
        if hyp.get("budget", {}).get("token_limit", 0) <= 0:
            raise ValueError("Hypothesis budget must specify positive token_limit")

    def review_plan(self, plan: Dict[str, Any], hypothesis: Dict[str, Any]) -> None:
        ensure_required(
            plan,
            ["id", "hypothesis_id", "datasets", "models", "variables", "controls", "metrics", "budget", "retry_policy"],
            "plan",
        )
        if plan["hypothesis_id"] != hypothesis["id"]:
            raise ValueError("Plan does not target selected hypothesis")
        if plan["budget"].get("max_runs", 0) < 1:
            raise ValueError("Plan budget must allow at least one run")
        execution = plan.get("execution", {})
        if execution and execution.get("allow_training", True):
            raise ValueError("Plan must disable training; use API inference only")
        if execution and execution.get("llm_mode") not in (None, "api_inference"):
            raise ValueError("Unsupported LLM mode; only api_inference is allowed")


class PlanningAgent:
    def __init__(self, ctx: ProjectContext, client: Optional[DeepSeekClient] = None):
        self.ctx = ctx
        self.client = client

    def load_or_generate_plan(self, hypothesis: Dict[str, Any]) -> Dict[str, Any]:
        plan_path = self.ctx.paths["plan"]
        if plan_path.exists():
            return load_json(plan_path)
        if not self.client:
            raise ValueError("Plan missing and DeepSeek client unavailable for generation")

        prompt = (
            "You are a planning agent. Draft an experiment plan as JSON matching keys: id, hypothesis_id, datasets, "
            "models, variables[{name,values}], controls, metrics[{name,aggregation,stat_test}], ablations, budget{max_runs,max_compute_hours,max_token_usage}, retry_policy{max_retries,on_oom,on_nan}, execution{llm_mode,allow_training,api_url?,api_key?}, notes. "
            f"Target hypothesis: {json.dumps(hypothesis, ensure_ascii=False)}. Keep llm_mode='api_inference' and allow_training=false."
        )
        reply = self.client.chat([
            {"role": "system", "content": "Return JSON only"},
            {"role": "user", "content": prompt},
        ])
        plan = json.loads(reply)
        dump_json(plan_path, plan)
        return plan


class ExperimentAgent:
    def __init__(self, ctx: ProjectContext, client: Optional[DeepSeekClient] = None):
        self.ctx = ctx
        self.client = client

    def run(self, plan: Dict[str, Any], hypothesis: Dict[str, Any]) -> Dict[str, Any]:
        run_id = f"run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        run_dir = self.ctx.paths["runs"] / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        exec_cfg = plan.get("execution", {})
        api_key = exec_cfg.get("api_key") or os.getenv("DEEPSEEK_API_KEY")
        api_url = exec_cfg.get("api_url") or os.getenv("DEEPSEEK_API_URL")
        use_api = bool(api_key and api_url)

        if use_api:
            try:
                client = self.client or DeepSeekClient(api_key=api_key, api_url=api_url)
                results = self._run_with_api(client, plan, hypothesis, run_id)
            except Exception as exc:  # noqa: B902
                results = {
                    "run_id": run_id,
                    "hypothesis_id": hypothesis["id"],
                    "plan_id": plan["id"],
                    "metrics": {},
                    "decision_trace": ["Attempted API run but failed", str(exc)],
                    "cost": {},
                    "status": "failed",
                }
        else:
            results = self._run_simulated(plan, hypothesis, run_id)

        dump_json(run_dir / "config.json", plan)
        dump_json(run_dir / "results.json", results)
        (run_dir / "log.txt").write_text(
            "\n".join([
                f"Run {run_id}",
                "Simulated execution for MVP experiment.",
                f"Metrics: {json.dumps(results['metrics'], indent=2)}",
            ]),
            encoding="utf-8",
        )
        return results

    def _run_simulated(self, plan: Dict[str, Any], hypothesis: Dict[str, Any], run_id: str) -> Dict[str, Any]:
        simulated_baseline = 0.73
        simulated_improved = simulated_baseline + 0.025
        improved_bias_gap = 0.05

        return {
            "run_id": run_id,
            "hypothesis_id": hypothesis["id"],
            "plan_id": plan["id"],
            "metrics": {
                "baseline_accuracy": simulated_baseline,
                "normalized_accuracy": simulated_improved,
                "bias_gap_verbose_vs_concise": improved_bias_gap,
            },
            "decision_trace": [
                "baseline judge evaluated first 200 GSM8K samples (simulated)",
                "applied normalization prompt step_extractor_v1 (simulated)",
                "evaluated normalized answers with rubric gsm8k_math_rubric_v1 (simulated)",
            ],
            "cost": {
                "token_usage": 120000,
                "compute_hours": 1.2,
            },
            "status": "success",
            "mode": "simulation",
        }

    def _run_with_api(self, client: DeepSeekClient, plan: Dict[str, Any], hypothesis: Dict[str, Any], run_id: str) -> Dict[str, Any]:
        samples = self._load_dataset()

        def judge(student_answer: str, problem: str, gold: str) -> bool:
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a strict math grader. Only return JSON with fields pass (true/false) and reasoning."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Problem: {problem}\nGold answer: {gold}\nStudent answer: {student_answer}\n"
                        "Judge correctness of the student answer."
                    ),
                },
            ]
            reply = client.chat(messages)
            try:
                parsed = json.loads(reply)
                return bool(parsed.get("pass"))
            except Exception:
                return "pass" in reply.lower() and "fail" not in reply.lower()

        verbose_passes = []
        concise_passes = []
        for item in samples:
            concise_passes.append(judge(item["concise_answer"], item["problem"], item["gold"]))
            verbose_passes.append(judge(item["verbose_answer"], item["problem"], item["gold"]))

        baseline_accuracy = sum(verbose_passes) / len(verbose_passes)
        normalized_accuracy = sum(concise_passes) / len(concise_passes)
        bias_gap = baseline_accuracy - normalized_accuracy

        return {
            "run_id": run_id,
            "hypothesis_id": hypothesis["id"],
            "plan_id": plan["id"],
            "metrics": {
                "baseline_accuracy": baseline_accuracy,
                "normalized_accuracy": normalized_accuracy,
                "bias_gap_verbose_vs_concise": bias_gap,
            },
            "decision_trace": [
                "Executed DeepSeek API judge for verbose and concise answers",
                f"Samples graded: {len(samples) * 2}",
            ],
            "cost": {},
            "status": "success",
            "mode": "deepseek_api",
        }

    def _load_dataset(self) -> List[Dict[str, str]]:
        if self.ctx.paths["data"].exists():
            with self.ctx.paths["data"].open("r", encoding="utf-8") as f:
                return [json.loads(line) for line in f if line.strip()]
        return []


class WritingAgent:
    def __init__(self, ctx: ProjectContext):
        self.ctx = ctx

    def write_report(self, hypothesis: Dict[str, Any], plan: Dict[str, Any], results: Dict[str, Any]) -> Path:
        report_path = self.ctx.paths["writeup"] / "auto_report.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)

        content = textwrap.dedent(
            f"""
            # Auto-generated Report

            ## Question
            {hypothesis['statement']}

            ## Method
            - Dataset(s): {', '.join(plan['datasets'])}
            - Models: {', '.join(plan['models'])}
            - Variables: {[v['name'] for v in plan.get('variables', [])]}
            - Controls: {', '.join(plan.get('controls', []))}

            ## Results
            - Baseline accuracy: {results['metrics']['baseline_accuracy']:.3f}
            - Normalized accuracy: {results['metrics']['normalized_accuracy']:.3f}
            - Bias gap verbose vs concise: {results['metrics']['bias_gap_verbose_vs_concise']:.3f}
            - Token usage: {results['cost']['token_usage']}
            - Compute hours: {results['cost']['compute_hours']}

            ## Discussion
            - Gain vs. baseline: {results['metrics']['normalized_accuracy'] - results['metrics']['baseline_accuracy']:.3f}
            - Budget within limits: {results['cost']['token_usage'] <= plan['budget']['max_token_usage']}
            - Status: {results['status']}

            ## Next Steps
            - Expand sample size and test alternate normalization prompts.
            - Add statistical significance testing over multiple seeds.
            - Capture human spot-checks for judge reliability.
            """
        ).strip() + "\n"

        report_path.write_text(content, encoding="utf-8")
        return report_path


# ---------- pipeline orchestration ----------


def run_pipeline(project_root: Path, schemas_root: Path) -> Dict[str, Any]:
    ctx = ProjectContext(project_root)

    shared_client = None
    try:
        api_key = os.getenv("DEEPSEEK_API_KEY")
        api_url = os.getenv("DEEPSEEK_API_URL")
        if api_key and api_url:
            shared_client = DeepSeekClient(api_key=api_key, api_url=api_url)
    except Exception:
        shared_client = None

    ideation = IdeationAgent(ctx, client=shared_client)
    reviewer = Reviewer(schemas_root)
    planner = PlanningAgent(ctx, client=shared_client)
    experimenter = ExperimentAgent(ctx, client=shared_client)
    writer = WritingAgent(ctx)

    hypothesis = ideation.select_hypothesis()
    reviewer.review_hypothesis(hypothesis)

    plan = planner.load_or_generate_plan(hypothesis)
    reviewer.review_plan(plan, hypothesis)

    results = experimenter.run(plan, hypothesis)
    report = writer.write_report(hypothesis, plan, results)

    meta_costs_path = ctx.paths["meta"] / "costs.json"
    existing_costs = meta_costs_path.exists() and load_json(meta_costs_path) or []
    existing_costs.append({
        "run_id": results["run_id"],
        "token_usage": results["cost"]["token_usage"],
        "compute_hours": results["cost"]["compute_hours"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    dump_json(meta_costs_path, existing_costs)

    return {
        "hypothesis": hypothesis,
        "plan": plan,
        "results": results,
        "report_path": str(report),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run minimal FARS-like pipeline")
    parser.add_argument(
        "--project",
        type=Path,
        default=Path("projects/llm_judge_bias"),
        help="Path to project root",
    )
    parser.add_argument(
        "--schemas",
        type=Path,
        default=Path("schemas"),
        help="Path to schema directory",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = run_pipeline(args.project, args.schemas)
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
