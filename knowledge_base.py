"""
知识库模块：负责连接外部知识源（Arxiv等）
"""
import arxiv
from rich.console import Console
# 避免循环引用，这里使用类型提示时的字符串前向引用，或者在运行时导入
# from deepseek_client import DeepSeekClient 

console = Console()


class KnowledgeBase:
    """知识库管理类，负责文献检索"""

    def __init__(self, client=None, max_results: int = 5):
        self.max_results = max_results
        self.client = arxiv.Client()
        self.llm_client = client  # DeepSeekClient 实例

    def search_arxiv(self, query: str) -> list[dict]:
        """
        在 Arxiv 上搜索相关论文
        会自动将中文 query 翻译为英文

        Args:
            query: 搜索关键词

        Returns:
            论文信息列表
        """
        # 1. 如果有 LLM 客户端，尝试将 query 翻译为英文关键词
        english_query = query
        if self.llm_client and self._is_contains_chinese(query):
            console.print(f"[dim]🔄 正在将关键词 '{query}' 翻译为英文...[/dim]")
            english_query = self._translate_query(query)
            console.print(f"[dim]🔍 使用英文关键词检索: {english_query}[/dim]")

        console.print(f"[dim]🔍 正在 Arxiv 检索: {english_query}...[/dim]")
        
        try:
            search = arxiv.Search(
                query=english_query,
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

    def _is_contains_chinese(self, string: str) -> bool:
        """检查字符串是否包含中文"""
        for char in string:
            if '\u4e00' <= char <= '\u9fff':
                return True
        return False

    def _translate_query(self, query: str) -> str:
        """调用 LLM 将中文 query 翻译为 Arxiv 搜索关键词"""
        try:
            prompt = (
                f"Please translate the following research topic into effective English keywords for Arxiv search. "
                f"Output ONLY the keywords, separated by spaces. No explanation.\n\nTopic: {query}"
            )
            # 使用简单的非流式调用，temperature=0.1 保证稳定
            messages = [{"role": "user", "content": prompt}]
            english_query = self.llm_client.chat(messages, temperature=0.1)
            return english_query.strip().replace('"', '')
        except Exception as e:
            console.print(f"[yellow]⚠️ 关键词翻译失败，将使用原始 query: {e}[/yellow]")
            return query

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
