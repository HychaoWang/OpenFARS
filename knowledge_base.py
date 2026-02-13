"""
知识库模块：负责连接外部知识源（Arxiv等）
"""
import arxiv
from datetime import datetime
from rich.console import Console

console = Console()


class KnowledgeBase:
    """知识库管理类，负责文献检索"""

    def __init__(self, max_results: int = 5):
        self.max_results = max_results
        self.client = arxiv.Client()

    def search_arxiv(self, query: str) -> list[dict]:
        """
        在 Arxiv 上搜索相关论文

        Args:
            query: 搜索关键词

        Returns:
            论文信息列表
        """
        console.print(f"[dim]🔍 正在 Arxiv 检索: {query}...[/dim]")
        
        try:
            search = arxiv.Search(
                query=query,
                max_results=self.max_results,
                sort_by=arxiv.SortCriterion.SubmittedDate,
                sort_order=arxiv.SortOrder.Descending,
            )

            results = []
            for result in self.client.results(search):
                paper = {
                    "title": result.title,
                    "authors": ", ".join([a.name for a in result.authors]),
                    "summary": result.summary.replace("\n", " "),
                    "published": result.published.strftime("%Y-%m-%d"),
                    "url": result.entry_id,
                }
                results.append(paper)
            
            return results
        except Exception as e:
            console.print(f"[red]⚠️ Arxiv 检索失败: {e}[/red]")
            return []

    def format_papers_for_prompt(self, papers: list[dict]) -> str:
        """
        将论文列表格式化为 Prompt 可用的文本

        Args:
            papers: 论文信息列表

        Returns:
            格式化文本
        """
        if not papers:
            return "未找到相关参考文献。"

        text = ""
        for i, p in enumerate(papers, 1):
            text += (
                f"[{i}] {p['title']}\n"
                f"    作者: {p['authors']}\n"
                f"    发布日期: {p['published']}\n"
                f"    摘要: {p['summary'][:300]}...\n"  # 截断摘要以节省token
                f"    URL: {p['url']}\n\n"
            )
        return text
