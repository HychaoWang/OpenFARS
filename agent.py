"""
主 Agent 模块
编排 idea 生成 → 评估 → 优化 的完整工作流
"""
import re
import os
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, TextColumn

from deepseek_client import DeepSeekClient
from idea_generator import IdeaGenerator
from idea_evaluator import IdeaEvaluator, EvaluationResult
from idea_refiner import IdeaRefiner
from knowledge_base import KnowledgeBase
from multi_reviewer import MultiReviewer  # 导入多智能体评审
from prompts import FINAL_REPORT_SYSTEM, FINAL_REPORT_USER
from config import (
    MAX_REFINEMENT_ROUNDS,
    EVALUATION_THRESHOLD,
    NUM_IDEAS_PER_ROUND,
    TEMPERATURE_GENERATION,
)

console = Console()


class ResearchIdeaAgent:
    """
    AI 科研论文 Idea 生成 Agent

    工作流程：
    1. 检索相关文献 (RAG)
    2. 根据研究方向生成多个论文 idea
    3. 对每个 idea 进行多维度评估 (多智能体评审)
    4. 对未达标的 idea 进行优化
    5. 重复评估-优化循环直到达标或达到最大轮次
    6. 生成最终研究提案报告
    """

    def __init__(self):
        self.client = DeepSeekClient()
        self.generator = IdeaGenerator(self.client)
        # 使用 MultiReviewer 替换原来的 IdeaEvaluator
        self.evaluator = MultiReviewer(self.client)
        self.refiner = IdeaRefiner(self.client)
        self.knowledge_base = KnowledgeBase(client=self.client)

        # 存储运行历史
        self.ideas_history: list[dict] = []

    def run(
        self,
        topic: str,
        background: str = "",
        num_ideas: int = NUM_IDEAS_PER_ROUND,
        max_rounds: int = MAX_REFINEMENT_ROUNDS,
        constraints: list[str] | None = None,
        auto_report: bool = True,
    ) -> dict:
        """
        运行完整的 idea 生成-评估-优化流程
        """
        console.print(
            Panel(
                f"[bold cyan]🔬 AI 科研论文 Idea 生成 Agent 2.5 (多智能体版)[/bold cyan]\n\n"
                f"📌 研究方向: {topic}\n"
                f"📚 检索增强: 开启\n"
                f"⚔️  多智能体评审: 开启 (保守派 vs 激进派)\n"
                f"🔄 最大优化轮次: {max_rounds}\n"
                f"📊 评估阈值: {EVALUATION_THRESHOLD}/10\n"
                f"💡 生成 idea 数量: {num_ideas}",
                title="系统启动",
                border_style="bright_blue",
            )
        )

        results = {
            "topic": topic,
            "background": background,
            "references": [],
            "ideas": [],
            "final_report": None,
        }

        # ========== 第一步：知识检索 (RAG) ==========
        console.print("\n[bold green]📚 第一步：检索相关文献 (RAG)...[/bold green]")
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(f"正在 Arxiv 上搜索: {topic}...", total=None)
            papers = self.knowledge_base.search_arxiv(topic)
            formatted_references = self.knowledge_base.format_papers_for_prompt(papers)
            results["references"] = papers
            progress.update(task, completed=True)
        
        console.print(f"[cyan]✅ 已检索到 {len(papers)} 篇相关文献[/cyan]")
        if papers:
            console.print(Panel(formatted_references, title="参考文献摘要", border_style="dim", height=10))

        # ========== 第二步：生成 Ideas ==========
        console.print("\n[bold green]📝 第二步：生成论文 Ideas...[/bold green]")
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("正在调用 DeepSeek 生成 ideas...", total=None)
            if constraints:
                raw_ideas = self.generator.generate_with_constraints(
                    topic=topic,
                    background=background,
                    constraints=constraints,
                    references=formatted_references,
                    num_ideas=num_ideas,
                )
            else:
                raw_ideas = self.generator.generate(
                    topic=topic,
                    background=background,
                    references=formatted_references,
                    num_ideas=num_ideas,
                )
            progress.update(task, completed=True)

        console.print(Panel(Markdown(raw_ideas), title="生成的 Ideas", border_style="green"))

        # 分割出单独的 ideas
        individual_ideas = self._split_ideas(raw_ideas)
        console.print(f"\n[cyan]✅ 成功解析出 {len(individual_ideas)} 个 ideas[/cyan]")

        # ========== 第三步 & 第四步：评估与优化循环 ==========
        for idx, idea in enumerate(individual_ideas):
            idea_result = self._process_single_idea(
                topic=topic,
                idea_content=idea,
                references=formatted_references,
                idea_index=idx + 1,
                max_rounds=max_rounds,
            )
            results["ideas"].append(idea_result)

        # ========== 第五步：生成最终报告 ==========
        if auto_report:
            console.print("\n[bold green]📋 第五步：生成最终研究提案报告...[/bold green]")
            best_idea = self._select_best_idea(results["ideas"])
            if best_idea:
                report = self._generate_final_report(topic, best_idea)
                results["final_report"] = report
                console.print(
                    Panel(Markdown(report), title="📋 最终研究提案报告", border_style="bright_magenta")
                )

        # ========== 保存结果 ==========
        self._save_results(results)

        # ========== 输出总结 ==========
        self._print_summary(results)

        return results

    def _process_single_idea(
        self,
        topic: str,
        idea_content: str,
        references: str,
        idea_index: int,
        max_rounds: int,
    ) -> dict:
        """
        处理单个 idea 的评估-优化循环

        Args:
            topic: 研究方向
            idea_content: idea 内容
            references: 参考文献文本
            idea_index: idea 编号
            max_rounds: 最大优化轮次

        Returns:
            包含该 idea 完整处理记录的字典
        """
        idea_record = {
            "original": idea_content,
            "current": idea_content,
            "evaluations": [],
            "refinements": [],
            "final_score": 0.0,
            "rounds_used": 0,
        }

        console.print(f"\n[bold yellow]{'='*60}[/bold yellow]")
        console.print(f"[bold yellow]🔍 处理 Idea #{idea_index}[/bold yellow]")
        console.print(f"[bold yellow]{'='*60}[/bold yellow]")

        current_idea = idea_content

        for round_num in range(1, max_rounds + 1):
            # --- 评估 ---
            console.print(
                f"\n[bold blue]📊 第 {round_num} 轮评估 (Idea #{idea_index})...[/bold blue]"
            )
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("正在评估...", total=None)
                eval_result = self.evaluator.evaluate(topic, current_idea, references)
                progress.update(task, completed=True)

            # 显示评估结果
            console.print(Panel(eval_result.summary(), title=f"评估结果 (第 {round_num} 轮)", border_style="blue"))
            console.print(Panel(Markdown(eval_result.raw_feedback), title="详细评估反馈", border_style="dim"))

            idea_record["evaluations"].append({
                "round": round_num,
                "score": eval_result.weighted_score,
                "dimension_scores": {
                    "novelty": eval_result.novelty,
                    "feasibility": eval_result.feasibility,
                    "significance": eval_result.significance,
                    "clarity": eval_result.clarity,
                    "relevance": eval_result.relevance,
                },
                "failed_dimensions": list(eval_result.failed_dimensions.keys()),
                "feedback": eval_result.raw_feedback,
            })
            idea_record["final_score"] = eval_result.weighted_score
            idea_record["rounds_used"] = round_num

            # --- 检查是否达标（综合分 + 每个维度小分都达标）---
            if eval_result.passes_threshold:
                console.print(
                    f"\n[bold green]✅ Idea #{idea_index} 在第 {round_num} 轮评估达标！"
                    f"(综合: {eval_result.weighted_score:.2f}/{EVALUATION_THRESHOLD}，"
                    f"所有维度均达标)[/bold green]"
                )
                break

            # --- 未达标，显示未通过的维度并进行优化 ---
            failed = eval_result.failed_dimensions
            failed_info = ""
            if failed:
                from idea_evaluator import DIMENSION_NAMES
                failed_parts = [f"{DIMENSION_NAMES[d]}({s:.1f}<{t:.1f})" for d, (s, t) in failed.items()]
                failed_info = f"未达标维度: {', '.join(failed_parts)}"

            if round_num < max_rounds:
                console.print(
                    f"\n[bold red]❌ Idea #{idea_index} 未达标 "
                    f"(综合: {eval_result.weighted_score:.2f}/{EVALUATION_THRESHOLD})"
                    f"{' | ' + failed_info if failed_info else ''}，"
                    f"开始第 {round_num} 轮优化...[/bold red]"
                )
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console,
                ) as progress:
                    task = progress.add_task("正在优化 idea...", total=None)
                    refined_idea = self.refiner.refine(
                        topic=topic,
                        original_idea=current_idea,
                        evaluation_feedback=eval_result.raw_feedback,
                    )
                    progress.update(task, completed=True)

                console.print(
                    Panel(Markdown(refined_idea), title=f"优化后的 Idea (第 {round_num} 轮)", border_style="yellow")
                )

                idea_record["refinements"].append({
                    "round": round_num,
                    "content": refined_idea,
                })

                current_idea = refined_idea
            else:
                console.print(
                    f"\n[bold red]⚠️ Idea #{idea_index} 已达到最大优化轮次 ({max_rounds})，"
                    f"最终综合评分: {eval_result.weighted_score:.2f}"
                    f"{' | ' + failed_info if failed_info else ''}[/bold red]"
                )

        idea_record["current"] = current_idea
        return idea_record

    def _split_ideas(self, raw_ideas: str) -> list[str]:
        """
        将生成的多个 ideas 文本分割为单独的 idea

        Args:
            raw_ideas: 包含多个 idea 的原始文本

        Returns:
            分割后的 idea 列表
        """
        # 使用 "### Idea" 或 "---" 作为分隔符
        parts = re.split(r"(?=### Idea\s*\d+)", raw_ideas)
        ideas = [part.strip() for part in parts if part.strip() and "Idea" in part]

        # 如果分割失败，将整段作为一个 idea
        if not ideas:
            ideas = [raw_ideas.strip()]

        return ideas

    def _select_best_idea(self, ideas: list[dict]) -> dict | None:
        """
        选择评分最高的 idea

        Args:
            ideas: idea 记录列表

        Returns:
            最佳 idea 记录
        """
        if not ideas:
            return None
        return max(ideas, key=lambda x: x["final_score"])

    def _generate_final_report(self, topic: str, best_idea: dict) -> str:
        """
        生成最终研究提案报告

        Args:
            topic: 研究方向
            best_idea: 最佳 idea 记录

        Returns:
            最终报告文本
        """
        # 整理评估历史
        eval_history = ""
        for eval_record in best_idea["evaluations"]:
            eval_history += f"\n### 第 {eval_record['round']} 轮评估 (得分: {eval_record['score']:.2f})\n"
            eval_history += eval_record["feedback"] + "\n"

        user_prompt = FINAL_REPORT_USER.format(
            topic=topic,
            final_idea=best_idea["current"],
            evaluation_history=eval_history,
        )

        messages = self.client.build_messages(
            system_prompt=FINAL_REPORT_SYSTEM,
            user_prompt=user_prompt,
        )

        report = self.client.chat(
            messages=messages,
            temperature=TEMPERATURE_GENERATION,
        )

        return report

    def _save_results(self, results: dict) -> None:
        """
        保存运行结果到文件

        Args:
            results: 完整结果字典
        """
        output_dir = "outputs"
        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        topic_slug = results["topic"][:20].replace(" ", "_").replace("/", "_")

        # 保存所有 ideas 和评估记录
        ideas_file = os.path.join(output_dir, f"{timestamp}_{topic_slug}_ideas.md")
        with open(ideas_file, "w", encoding="utf-8") as f:
            f.write(f"# AI 科研论文 Idea 生成报告 (RAG 版)\n\n")
            f.write(f"**研究方向**: {results['topic']}\n\n")
            f.write(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            if results["references"]:
                f.write(f"## 📚 参考文献 (基于 Arxiv)\n\n")
                for i, ref in enumerate(results["references"], 1):
                    f.write(f"{i}. **{ref['title']}**\n")
                    f.write(f"   - 作者: {ref['authors']}\n")
                    f.write(f"   - 日期: {ref['published']}\n")
                    f.write(f"   - URL: {ref['url']}\n\n")

            f.write(f"---\n\n")

            for idx, idea in enumerate(results["ideas"], 1):
                f.write(f"## Idea #{idx}\n\n")
                f.write(f"**最终评分**: {idea['final_score']:.2f}/10\n\n")
                f.write(f"**优化轮次**: {idea['rounds_used']}\n\n")
                f.write(f"### 最终版本\n\n{idea['current']}\n\n")

                if idea["evaluations"]:
                    f.write(f"### 评估历史\n\n")
                    for eval_record in idea["evaluations"]:
                        f.write(f"#### 第 {eval_record['round']} 轮 (得分: {eval_record['score']:.2f})\n\n")
                        f.write(f"{eval_record['feedback']}\n\n")

                f.write(f"---\n\n")

        # 保存最终报告
        if results["final_report"]:
            report_file = os.path.join(output_dir, f"{timestamp}_{topic_slug}_report.md")
            with open(report_file, "w", encoding="utf-8") as f:
                f.write(results["final_report"])

        console.print(f"\n[green]💾 结果已保存到 {output_dir}/ 目录[/green]")

    def _print_summary(self, results: dict) -> None:
        """
        打印运行总结

        Args:
            results: 完整结果字典
        """
        console.print("\n")
        console.print(Panel(
            "[bold cyan]🎉 运行完成！总结如下：[/bold cyan]",
            border_style="bright_cyan",
        ))

        summary_lines = []
        for idx, idea in enumerate(results["ideas"], 1):
            status = "✅ 达标" if idea["final_score"] >= EVALUATION_THRESHOLD else "⚠️ 未达标"
            summary_lines.append(
                f"  Idea #{idx}: 最终评分 {idea['final_score']:.2f}/10 | "
                f"优化 {idea['rounds_used']} 轮 | {status}"
            )

        best = self._select_best_idea(results["ideas"])
        if best:
            summary_lines.append(f"\n  🏆 最佳 Idea 评分: {best['final_score']:.2f}/10")

        console.print("\n".join(summary_lines))
        console.print()
