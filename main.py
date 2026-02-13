"""
AI 科研论文 Idea 生成 Agent - 主程序入口

使用方式：
    1. 交互式模式：python main.py
    2. 命令行模式：python main.py --topic "研究方向" --background "背景信息"
"""
import argparse
import sys

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

from agent import ResearchIdeaAgent
from config import NUM_IDEAS_PER_ROUND, MAX_REFINEMENT_ROUNDS, EVALUATION_THRESHOLD

console = Console()


def print_banner():
    """打印欢迎横幅"""
    banner = """
[bold bright_cyan]
 ╔══════════════════════════════════════════════════════════════╗
 ║          🔬 AI 科研论文 Idea 生成 Agent 🔬                  ║
 ║                                                              ║
 ║   基于 DeepSeek 大模型的智能科研论文 Idea 生成系统            ║
 ║   功能：自动生成 → 多维评估 → 迭代优化 → 研究提案            ║
 ╚══════════════════════════════════════════════════════════════╝
[/bold bright_cyan]
    """
    console.print(banner)


def interactive_mode():
    """交互式模式"""
    print_banner()

    console.print("[bold green]📌 请输入以下信息来启动 Agent：[/bold green]\n")

    # 获取研究方向
    topic = Prompt.ask("[bold cyan]🔍 研究方向/主题[/bold cyan]")
    if not topic.strip():
        console.print("[red]❌ 研究方向不能为空！[/red]")
        sys.exit(1)

    # 获取背景信息
    console.print("\n[dim]（可选）输入研究背景信息，帮助 Agent 更好地理解你的需求。[/dim]")
    console.print("[dim]直接按回车跳过。[/dim]")
    background = Prompt.ask("[bold cyan]📖 背景信息[/bold cyan]", default="")

    # 获取约束条件
    constraints = []
    if Confirm.ask("\n[cyan]🔒 是否添加额外约束条件？[/cyan]", default=False):
        console.print("[dim]每行输入一个约束条件，输入空行结束。[/dim]")
        while True:
            constraint = Prompt.ask("[cyan]  约束条件[/cyan]", default="")
            if not constraint.strip():
                break
            constraints.append(constraint)

    # 获取参数配置
    console.print(f"\n[dim]默认参数：生成 {NUM_IDEAS_PER_ROUND} 个 idea，"
                  f"最多优化 {MAX_REFINEMENT_ROUNDS} 轮，"
                  f"评估阈值 {EVALUATION_THRESHOLD}/10[/dim]")

    if Confirm.ask("[cyan]⚙️  是否使用自定义参数？[/cyan]", default=False):
        num_ideas = int(Prompt.ask("  生成 idea 数量", default=str(NUM_IDEAS_PER_ROUND)))
        max_rounds = int(Prompt.ask("  最大优化轮次", default=str(MAX_REFINEMENT_ROUNDS)))
    else:
        num_ideas = NUM_IDEAS_PER_ROUND
        max_rounds = MAX_REFINEMENT_ROUNDS

    # 确认启动
    console.print("\n")
    console.print(Panel(
        f"[bold]研究方向[/bold]: {topic}\n"
        f"[bold]背景信息[/bold]: {background or '无'}\n"
        f"[bold]约束条件[/bold]: {', '.join(constraints) if constraints else '无'}\n"
        f"[bold]生成数量[/bold]: {num_ideas}\n"
        f"[bold]最大轮次[/bold]: {max_rounds}",
        title="确认配置",
        border_style="yellow",
    ))

    if not Confirm.ask("\n[bold green]🚀 确认启动 Agent？[/bold green]", default=True):
        console.print("[yellow]已取消。[/yellow]")
        sys.exit(0)

    # 启动 Agent
    console.print("\n")
    agent = ResearchIdeaAgent()
    results = agent.run(
        topic=topic,
        background=background,
        num_ideas=num_ideas,
        max_rounds=max_rounds,
        constraints=constraints if constraints else None,
        auto_report=True,
    )

    return results


def cli_mode(args):
    """命令行模式"""
    print_banner()

    constraints = args.constraints.split(",") if args.constraints else None

    agent = ResearchIdeaAgent()
    results = agent.run(
        topic=args.topic,
        background=args.background or "",
        num_ideas=args.num_ideas,
        max_rounds=args.max_rounds,
        constraints=constraints,
        auto_report=not args.no_report,
    )

    return results


def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="AI 科研论文 Idea 生成 Agent - 基于 DeepSeek 大模型",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 交互式模式
  python main.py

  # 命令行模式
  python main.py --topic "大语言模型在代码生成中的应用"

  # 带背景信息和约束条件
  python main.py --topic "多模态学习" --background "关注视觉-语言对齐" --constraints "需要在单GPU上可运行,使用开源模型"

  # 自定义参数
  python main.py --topic "强化学习" --num-ideas 5 --max-rounds 5
        """,
    )

    parser.add_argument(
        "--topic", "-t",
        type=str,
        help="研究方向/主题",
    )
    parser.add_argument(
        "--background", "-b",
        type=str,
        default="",
        help="背景信息（可选）",
    )
    parser.add_argument(
        "--constraints", "-c",
        type=str,
        default="",
        help="约束条件，用逗号分隔（可选）",
    )
    parser.add_argument(
        "--num-ideas", "-n",
        type=int,
        default=NUM_IDEAS_PER_ROUND,
        help=f"生成的 idea 数量（默认: {NUM_IDEAS_PER_ROUND}）",
    )
    parser.add_argument(
        "--max-rounds", "-r",
        type=int,
        default=MAX_REFINEMENT_ROUNDS,
        help=f"最大优化轮次（默认: {MAX_REFINEMENT_ROUNDS}）",
    )
    parser.add_argument(
        "--no-report",
        action="store_true",
        help="不生成最终报告",
    )

    args = parser.parse_args()

    try:
        if args.topic:
            results = cli_mode(args)
        else:
            results = interactive_mode()
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️ 用户中断，程序退出。[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[bold red]❌ 运行出错: {e}[/bold red]")
        console.print_exception()
        sys.exit(1)


if __name__ == "__main__":
    main()
