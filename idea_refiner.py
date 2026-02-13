"""
论文 Idea 优化模块
负责根据评估反馈对论文 idea 进行优化和改进
"""
from deepseek_client import DeepSeekClient
from prompts import IDEA_REFINEMENT_SYSTEM, IDEA_REFINEMENT_USER
from config import TEMPERATURE_REFINEMENT


class IdeaRefiner:
    """论文 Idea 优化器"""

    def __init__(self, client: DeepSeekClient):
        self.client = client

    def refine(
        self,
        topic: str,
        original_idea: str,
        evaluation_feedback: str,
    ) -> str:
        """
        根据评估反馈优化 idea

        Args:
            topic: 研究方向
            original_idea: 原始 idea 内容
            evaluation_feedback: 评估反馈内容

        Returns:
            优化后的 idea 文本
        """
        user_prompt = IDEA_REFINEMENT_USER.format(
            topic=topic,
            original_idea=original_idea,
            evaluation_feedback=evaluation_feedback,
        )

        messages = self.client.build_messages(
            system_prompt=IDEA_REFINEMENT_SYSTEM,
            user_prompt=user_prompt,
        )

        refined_idea = self.client.chat(
            messages=messages,
            temperature=TEMPERATURE_REFINEMENT,
        )

        return refined_idea
