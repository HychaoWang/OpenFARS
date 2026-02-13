"""
配置文件：DeepSeek API 和系统参数配置
"""
import os
from dotenv import load_dotenv

load_dotenv()


def _load_api_key() -> str:
    """从环境变量或 key 文件中加载 API Key"""
    key = os.getenv("DEEPSEEK_API_KEY", "")
    if key:
        return key
    # 尝试从项目目录下的 key 文件读取
    key_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "deepseek_key1.txt")
    if os.path.exists(key_file):
        with open(key_file, "r", encoding="utf-8") as f:
            return f.read().strip()
    return "your-api-key-here"


# ======================== DeepSeek API 配置 ========================
DEEPSEEK_API_KEY = _load_api_key()
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# ======================== Agent 参数配置 ========================
# 每次生成的 idea 数量
NUM_IDEAS_PER_ROUND = 3

# idea 评估的最低分数阈值 (1-10)，低于此分数的 idea 会被优化
EVALUATION_THRESHOLD = 8.0

# 最大迭代优化轮次
MAX_REFINEMENT_ROUNDS = 3

# API 调用参数
TEMPERATURE_GENERATION = 0.9    # idea 生成温度（较高以获取更多创意）
TEMPERATURE_EVALUATION = 0.3    # idea 评估温度（较低以获取更稳定的评估）
TEMPERATURE_REFINEMENT = 0.7    # idea 优化温度
MAX_TOKENS = 4096               # 最大 token 数

# ======================== 评估维度权重 ========================
EVAL_WEIGHTS = {
    "novelty": 0.25,        # 新颖性
    "feasibility": 0.20,    # 可行性
    "significance": 0.25,   # 重要性
    "clarity": 0.15,        # 清晰度
    "relevance": 0.15,      # 相关性
}

# ======================== 各维度独立达标阈值 ========================
# 每个维度都必须 >= 对应阈值才算该维度达标，所有维度达标才算整体通过
EVAL_DIMENSION_THRESHOLDS = {
    "novelty": 9.0,         # 新颖性最低分
    "feasibility": 9.0,     # 可行性最低分
    "significance": 8.0,    # 重要性最低分
    "clarity": 8.0,         # 清晰度最低分
    "relevance": 8.0,       # 相关性最低分
}
