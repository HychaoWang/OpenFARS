"""
论文 Idea 生成模块
负责根据研究方向生成创新性的论文 idea
"""
from deepseek_client import DeepSeekClient
from prompts import IDEA_GENERATION_SYSTEM, IDEA_GENERATION_USER
from config import TEMPERATURE_GENERATION, NUM_IDEAS_PER_ROUND


class IdeaGenerator:
    """论文 Idea 生成器"""

    def __init__(self, client: DeepSeekClient):
        self.client = client

    def generate(
        self,
        topic: str,
        background: str = "",
        references: str = "",
        num_ideas: int = NUM_IDEAS_PER_ROUND,
    ) -> str:
        """
        生成论文 idea

        Args:
            topic: 研究方向/主题
            background: 背景信息（可选）
            references: 参考文献文本（可选）
            num_ideas: 生成的 idea 数量

        Returns:
            生成的 idea 文本内容
        """
        if not background:
            background = "无额外背景信息，请根据研究方向自行分析当前领域的研究现状和挑战。"
        
        if not references:
            references = "未提供具体参考文献，请基于通用学术知识生成。"

        # 构建 idea 编号占位
        # 为每个 idea 生成对应的编号提示
        user_prompt = IDEA_GENERATION_USER.format(
            topic=topic,
            background=background,
            references=references,
            num_ideas=num_ideas,
            idea_number="1/2/3/...",
        )

        messages = self.client.build_messages(
            system_prompt=IDEA_GENERATION_SYSTEM,
            user_prompt=user_prompt,
        )

        result = self.client.chat(
            messages=messages,
            temperature=TEMPERATURE_GENERATION,
        )

        return result

    def generate_with_constraints(
        self,
        topic: str,
        background: str = "",
        constraints: list[str] | None = None,
        references: str = "",
        num_ideas: int = NUM_IDEAS_PER_ROUND,
    ) -> str:
        """
        带约束条件的 idea 生成

        Args:
            topic: 研究方向/主题
            background: 背景信息
            constraints: 约束条件列表（如："必须涉及多模态"、"需要可在单GPU上运行"等）
            references: 参考文献文本
            num_ideas: 生成的 idea 数量

        Returns:
            生成的 idea 文本内容
        """
        constraint_text = ""
        if constraints:
            constraint_text = "\n\n## 额外约束条件\n"
            for i, c in enumerate(constraints, 1):
                constraint_text += f"{i}. {c}\n"

        enhanced_background = background + constraint_text if background else constraint_text

        return self.generate(
            topic=topic,
            background=enhanced_background,
            references=references,
            num_ideas=num_ideas,
        )
