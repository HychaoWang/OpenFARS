"""
论文 Idea 评估模块
负责对生成的论文 idea 进行多维度评估
"""
import re
from deepseek_client import DeepSeekClient
from prompts import IDEA_EVALUATION_SYSTEM, IDEA_EVALUATION_USER
from config import TEMPERATURE_EVALUATION, EVAL_WEIGHTS, EVALUATION_THRESHOLD, EVAL_DIMENSION_THRESHOLDS

# 维度名称映射（英文 → 中文）
DIMENSION_NAMES = {
    "novelty": "新颖性",
    "feasibility": "可行性",
    "significance": "重要性",
    "clarity": "清晰度",
    "relevance": "相关性",
}


class EvaluationResult:
    """评估结果数据类"""

    def __init__(self):
        self.novelty: float = 0.0
        self.feasibility: float = 0.0
        self.significance: float = 0.0
        self.clarity: float = 0.0
        self.relevance: float = 0.0
        self.weighted_score: float = 0.0
        self.raw_feedback: str = ""
        self.strengths: list[str] = []
        self.weaknesses: list[str] = []
        self.suggestions: list[str] = []

    @property
    def failed_dimensions(self) -> dict[str, tuple[float, float]]:
        """
        获取未达标的维度及其分数和阈值

        Returns:
            {维度名: (实际分数, 阈值)} 的字典，仅包含未达标维度
        """
        failed = {}
        for dim, threshold in EVAL_DIMENSION_THRESHOLDS.items():
            score = getattr(self, dim, 0.0)
            if score < threshold:
                failed[dim] = (score, threshold)
        return failed

    @property
    def passes_threshold(self) -> bool:
        """
        是否达到通过阈值
        要求：加权综合评分达标 AND 每个维度的小分都达到各自的阈值
        """
        if self.weighted_score < EVALUATION_THRESHOLD:
            return False
        return len(self.failed_dimensions) == 0

    def summary(self) -> str:
        """生成评估摘要，标注每个维度是否达标"""
        failed = self.failed_dimensions

        def _dim_status(dim_key: str) -> str:
            score = getattr(self, dim_key, 0.0)
            threshold = EVAL_DIMENSION_THRESHOLDS.get(dim_key, 0.0)
            if dim_key in failed:
                return f"❌ {score}/10 (阈值: {threshold})"
            return f"✅ {score}/10"

        lines = [
            "📊 评估结果摘要",
            f"  新颖性:   {_dim_status('novelty')}",
            f"  可行性:   {_dim_status('feasibility')}",
            f"  重要性:   {_dim_status('significance')}",
            f"  清晰度:   {_dim_status('clarity')}",
            f"  相关性:   {_dim_status('relevance')}",
            "  ━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"  📌 加权综合评分: {self.weighted_score:.2f}/10 (阈值: {EVALUATION_THRESHOLD})",
        ]

        if self.passes_threshold:
            lines.append("  ✅ 所有维度均达标！")
        else:
            lines.append("  ❌ 未达标（需要优化）")
            if failed:
                failed_names = [f"{DIMENSION_NAMES[d]}({s:.1f}<{t:.1f})" for d, (s, t) in failed.items()]
                lines.append(f"  ⚠️  未达标维度: {', '.join(failed_names)}")
            if self.weighted_score < EVALUATION_THRESHOLD:
                lines.append(f"  ⚠️  综合评分未达标: {self.weighted_score:.2f} < {EVALUATION_THRESHOLD}")

        return "\n".join(lines)


class IdeaEvaluator:
    """论文 Idea 评估器"""

    def __init__(self, client: DeepSeekClient):
        self.client = client

    def evaluate(self, topic: str, idea_content: str, references: str = "") -> EvaluationResult:
        """
        评估单个论文 idea

        Args:
            topic: 研究方向
            idea_content: 待评估的 idea 内容
            references: 相关参考文献（用于查重）

        Returns:
            EvaluationResult 评估结果对象
        """
        if not references:
            references = "未提供具体参考文献，请基于通用学术知识评估。"

        user_prompt = IDEA_EVALUATION_USER.format(
            topic=topic,
            idea_content=idea_content,
            references=references,
        )

        messages = self.client.build_messages(
            system_prompt=IDEA_EVALUATION_SYSTEM,
            user_prompt=user_prompt,
        )

        raw_feedback = self.client.chat(
            messages=messages,
            temperature=TEMPERATURE_EVALUATION,
        )

        result = self._parse_evaluation(raw_feedback)
        return result

    def _parse_evaluation(self, raw_feedback: str) -> EvaluationResult:
        """
        解析评估结果文本，提取各维度分数

        Args:
            raw_feedback: 原始评估反馈文本

        Returns:
            解析后的 EvaluationResult 对象
        """
        result = EvaluationResult()
        result.raw_feedback = raw_feedback

        # 提取各维度分数
        score_patterns = {
            "novelty": r"新颖性.*?(\d+(?:\.\d+)?)\s*/\s*10",
            "feasibility": r"可行性.*?(\d+(?:\.\d+)?)\s*/\s*10",
            "significance": r"重要性.*?(\d+(?:\.\d+)?)\s*/\s*10",
            "clarity": r"清晰度.*?(\d+(?:\.\d+)?)\s*/\s*10",
            "relevance": r"相关性.*?(\d+(?:\.\d+)?)\s*/\s*10",
        }

        for attr, pattern in score_patterns.items():
            match = re.search(pattern, raw_feedback)
            if match:
                setattr(result, attr, float(match.group(1)))

        # 计算加权综合评分
        result.weighted_score = (
            result.novelty * EVAL_WEIGHTS["novelty"]
            + result.feasibility * EVAL_WEIGHTS["feasibility"]
            + result.significance * EVAL_WEIGHTS["significance"]
            + result.clarity * EVAL_WEIGHTS["clarity"]
            + result.relevance * EVAL_WEIGHTS["relevance"]
        )

        # 提取优势
        strengths_section = re.search(
            r"主要优势(.*?)(?=###|主要不足)", raw_feedback, re.DOTALL
        )
        if strengths_section:
            result.strengths = re.findall(r"-\s*(.+)", strengths_section.group(1))

        # 提取不足
        weaknesses_section = re.search(
            r"主要不足(.*?)(?=###|改进建议)", raw_feedback, re.DOTALL
        )
        if weaknesses_section:
            result.weaknesses = re.findall(r"-\s*(.+)", weaknesses_section.group(1))

        # 提取改进建议
        suggestions_section = re.search(
            r"改进建议(.*?)(?=###|综合评语|$)", raw_feedback, re.DOTALL
        )
        if suggestions_section:
            result.suggestions = re.findall(r"-\s*(.+)", suggestions_section.group(1))

        return result
