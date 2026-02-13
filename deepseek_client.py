"""
DeepSeek API 客户端封装
基于 OpenAI SDK，兼容 DeepSeek API 接口
"""
from openai import OpenAI
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL, MAX_TOKENS


class DeepSeekClient:
    """DeepSeek API 客户端"""

    def __init__(self):
        self.client = OpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL,
        )
        self.model = DEEPSEEK_MODEL

    def chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = MAX_TOKENS,
        response_format: dict | None = None,
    ) -> str:
        """
        发送聊天请求到 DeepSeek API

        Args:
            messages: 消息列表，每条消息包含 role 和 content
            temperature: 温度参数，控制输出随机性
            max_tokens: 最大生成 token 数
            response_format: 响应格式（可选，用于 JSON 模式）

        Returns:
            模型生成的回复文本
        """
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            kwargs["response_format"] = response_format

        try:
            response = self.client.chat.completions.create(**kwargs)
            return response.choices[0].message.content
        except Exception as e:
            raise RuntimeError(f"DeepSeek API 调用失败: {e}") from e

    def build_messages(
        self, system_prompt: str, user_prompt: str, history: list[dict] | None = None
    ) -> list[dict]:
        """
        构建消息列表

        Args:
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            history: 历史对话（可选）

        Returns:
            格式化的消息列表
        """
        messages = [{"role": "system", "content": system_prompt}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user_prompt})
        return messages
