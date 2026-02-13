# 🔬 OpenFARS Idea - AI Research Idea Generator Agent

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![DeepSeek](https://img.shields.io/badge/Powered%20by-DeepSeek-blueviolet)](https://www.deepseek.com/)

**OpenFARS Idea** 是一个基于大语言模型（LLM）的自动化科研 Idea 生成系统。它不仅仅是一个简单的生成器，而是一个集成了 **RAG（检索增强生成）** 和 **多智能体对抗评审（Multi-Agent Review）** 的完整科研助手。

系统能够根据指定的研究方向，自动检索最新文献，生成创新性的论文 Idea，并模拟顶会审稿流程进行多轮“评估-优化”迭代，最终输出成熟的研究提案。

---

## ✨ 核心特性

- **📚 检索增强 (RAG)**: 集成 `arxiv` 实时文献检索。在生成 Idea 前自动搜索最新相关工作，确保 Idea 的新颖性，并自动进行查重，避免“造轮子”。
- **⚔️ 多智能体对抗评审**: 引入真实顶会的评审机制，由三个不同的 AI 角色共同把关：
    - **Reviewer A (Critic / 保守派)**: 严苛的审稿人，专注于找漏洞、质疑可行性和实验设计的严谨性。
    - **Reviewer B (Innovator / 激进派)**: 开放的创新者，专注于挖掘亮点，鼓励高风险高回报的颠覆性创新。
    - **Meta Reviewer (Area Chair / 领域主席)**: 综合两者意见，给出最终的权威评分和改进建议。
- **🔄 自动迭代优化**: 如果 Idea 评分未达标（综合分或单项分不足），Agent 会根据评审意见自动修改和完善 Idea，直到达到高标准。
- **📊 多维量化评估**: 基于 **新颖性 (Novelty)**、**可行性 (Feasibility)**、**重要性 (Significance)**、**清晰度 (Clarity)**、**相关性 (Relevance)** 五个维度进行打分。
- **📝 完整提案生成**: 最终输出包含摘要、背景、方法、实验设计等完整章节的研究提案报告。

## 🏗️ 系统架构

```mermaid
graph TD
    User[用户输入: 研究方向] --> Search[Arxiv 检索 (RAG)]
    Search --> Generator[Idea 生成器]
    Generator --> |初步 Ideas| Review{多智能体评审}
    
    subgraph Multi-Agent Review
        Review --> Critic[Reviewer A: 保守派]
        Review --> Innovator[Reviewer B: 激进派]
        Critic --> Meta[Meta Reviewer: 领域主席]
        Innovator --> Meta
    end
    
    Meta --> |评分 & 意见| Decision{是否达标?}
    
    Decision --> |❌ 未达标| Refiner[Idea 优化器]
    Refiner --> |优化后的 Idea| Review
    
    Decision --> |✅ 达标| Report[最终报告生成器]
    Report --> Output[输出: Markdown 报告]
```

## 🚀 快速开始

### 1. 环境准备

克隆项目并安装依赖：

```bash
git clone https://github.com/your-username/OpenFARS_idea.git
cd OpenFARS_idea

# 建议使用 conda 或 venv 创建虚拟环境
conda create -n openfars python=3.10
conda activate openfars

pip install -r requirements.txt
```

### 2. 配置 API Key

本项目使用 **DeepSeek API**。你需要配置 API Key 才能运行。

**方式一：环境变量（推荐）**
在项目根目录创建 `.env` 文件：
```bash
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

**方式二：Key 文件**
在项目根目录创建 `deepseek_key1.txt` 文件，将 API Key 直接粘贴在文件中。

### 3. 运行系统

**交互式模式**（推荐新手使用）：
```bash
python main.py
```
系统会引导你输入研究方向、背景信息等。

**命令行模式**：
```bash
# 基础用法
python main.py --topic "大语言模型在代码生成中的应用"

# 进阶用法：指定背景信息和约束条件
python main.py \
  --topic "多模态大模型" \
  --background "关注视觉-语言对齐问题，特别是细粒度对齐" \
  --constraints "必须使用开源模型, 显存占用不超过24G" \
  --num-ideas 3 \
  --max-rounds 5
```

## ⚙️ 参数配置

你可以在 `config.py` 中调整系统的核心参数：

```python
# 生成参数
NUM_IDEAS_PER_ROUND = 3       # 每次生成的 idea 数量
MAX_REFINEMENT_ROUNDS = 3     # 最大优化轮次

# 评估阈值 (非常严格!)
EVALUATION_THRESHOLD = 8.0    # 综合评分及格线 (1-10)

# 各维度独立阈值 (所有维度必须同时达标)
EVAL_DIMENSION_THRESHOLDS = {
    "novelty": 9.0,           # 新颖性要求极高
    "feasibility": 9.0,       # 可行性要求极高
    "significance": 8.0,
    # ...
}
```

## 📂 输出结果

运行结束后，结果会自动保存到 `outputs/` 目录：

1.  `{timestamp}_{topic}_ideas.md`: 包含所有生成的 Idea、每一轮的详细评审意见（两个 Reviewer + Meta Reviewer）以及优化过程记录。
2.  `{timestamp}_{topic}_report.md`: 最终优胜 Idea 的完整研究提案报告。

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！如果你有更好的 Prompt 策略或新的 Reviewer 角色设定，欢迎分享。

## 📄 许可证

MIT License
