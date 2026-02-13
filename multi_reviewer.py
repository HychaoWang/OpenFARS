"""
多智能体评审模块
实现 Reviewer A (保守派) + Reviewer B (激进派) + Meta Reviewer (领域主席) 的多视角评估架构
"""
from deepseek_client import DeepSeekClient
from idea_evaluator import IdeaEvaluator, EvaluationResult
from prompts import (
    REVIEWER_CRITIC_SYSTEM,
    REVIEWER_INNOVATOR_SYSTEM,
    META_REVIEWER_SYSTEM,
    META_REVIEWER_USER,
    IDEA_EVALUATION_USER,  # 复用基础的用户 prompt 结构
)
from config import TEMPERATURE_EVALUATION


class MultiReviewer(IdeaEvaluator):
    """多智能体评审器"""

    def __init__(self, client: DeepSeekClient):
        super().__init__(client)

    def evaluate(self, topic: str, idea_content: str, references: str = "") -> EvaluationResult:
        """
        执行多智能体评审流程

        Args:
            topic: 研究方向
            idea_content: 待评估的 idea 内容
            references: 相关参考文献

        Returns:
            最终的 EvaluationResult 对象
        """
        if not references:
            references = "未提供具体参考文献，请基于通用学术知识评估。"

        # 1. Reviewer A (Critic) 评审
        review_a = self._get_review(
            topic, idea_content, references, 
            system_prompt=REVIEWER_CRITIC_SYSTEM
        )

        # 2. Reviewer B (Innovator) 评审
        review_b = self._get_review(
            topic, idea_content, references, 
            system_prompt=REVIEWER_INNOVATOR_SYSTEM
        )

        # 3. Meta Reviewer (Chair) 汇总决议
        final_decision = self._get_meta_review(
            topic, idea_content, references, review_a, review_b
        )

        # 4. 解析结果
        result = self._parse_evaluation(final_decision)
        
        # 将中间过程保存到 raw_feedback 中，方便后续查看
        result.raw_feedback = (
            f"### Reviewer A (保守派) 意见\n{review_a}\n\n"
            f"### Reviewer B (激进派) 意见\n{review_b}\n\n"
            f"### 领域主席 (Meta Reviewer) 决议\n{final_decision}"
        )
        
        return result

    def _get_review(
        self, topic: str, idea_content: str, references: str, system_prompt: str
    ) -> str:
        """获取单个 Reviewer 的意见"""
        user_prompt = IDEA_EVALUATION_USER.format(
            topic=topic,
            idea_content=idea_content,
            references=references,
        )
        messages = self.client.build_messages(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
        return self.client.chat(
            messages=messages,
            temperature=TEMPERATURE_EVALUATION,
        )

    def _get_meta_review(
        self, 
        topic: str, 
        idea_content: str, 
        references: str, 
        review_a: str, 
        review_b: str
    ) -> str:
        """获取 Meta Reviewer 的最终决议"""
        user_prompt = META_REVIEWER_USER.format(
            topic=topic,
            idea_content=idea_content,
            references=references,
            review_a=review_a,
            review_b=review_b,
        )
        messages = self.client.build_messages(
            system_prompt=META_REVIEWER_SYSTEM,
            user_prompt=user_prompt,
        )
        return self.client.chat(
            messages=messages,
            temperature=TEMPERATURE_EVALUATION,
        )
