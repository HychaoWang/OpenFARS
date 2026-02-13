下面是基于页面内容提炼的 **FARS 项目完整工作流（research pipeline）**。我按系统实际执行顺序 + 数据流来概括，便于你理解与复刻。

---

# FARS 工作流（端到端自动科研流水线）

## 0️⃣ 输入：研究方向文档

系统起点是一个“研究方向集合文档”：

* 若干 research directions
* 可访问文献库（open papers）
* GitHub 代码库

👉 作为 Ideation agent 的上下文

---

# 1️⃣ Ideation（选题与假设生成）

**目标：从方向 → 具体可研究假设**

流程：

1. 文献检索（papers + repos）
2. 总结现有方法与空白
3. 生成 research hypotheses
4. 自动可行性/新颖性筛选
5. 通过的假设写入项目目录

输出：

* hypothesis（结构化）
* 相关文献
* 动机说明

👉 通过后进入 Planning

---

# 2️⃣ Planning（实验设计）

**目标：把假设转为可执行实验**

Planning agent 会：

* 定义变量与对照
* 选择模型/数据/指标
* 设计实验矩阵
* 预算算力
* 制定执行步骤

输出：

* experiment plan
* config
* evaluation protocol

👉 写入项目 workspace → Experiment 读取

---

# 3️⃣ Experiment（自动实验执行）

**目标：运行实验并产生结果**

Experiment agent：

* 调度 GPU 资源
* 调用模型接口
* 训练/推理/数据生成
* 计算指标
* 记录日志

基础设施：

* 160 GPU 集群
* 模型 API
* LLM judge
* 数据合成工具

输出：

* metrics
* 表格/图
* 失败/成功记录

👉 写入 workspace → Writing 读取

---

# 4️⃣ Writing（论文生成）

**目标：从结果 → 短论文**

Writing agent：

* 读取 hypothesis + plan + results
* 生成 short paper
* 包含负结果
* 单贡献聚焦

输出：

* 完整 research paper

---

# 5️⃣ 审核与发布（部署流程）

FARS 公开部署时：

1. 人类研究员审稿
2. 标注 AI 生成
3. 提交 arXiv/GitHub

---

# 核心系统机制（贯穿全流程）

## 📁 共享文件系统（blackboard）

所有 agent 通过：

> structured project directory

协作，而不是直接通信。

特点：

* 持久记忆
* 可并行项目
* 可追溯
* 可扩展

👉 本质：黑板架构科研系统

---

# FARS 工作流一句话总结

**方向 → 假设 → 实验设计 → 自动实验 → 自动论文 → 发布**

---

# 如果抽象成状态机

```
Research Directions
        ↓
Ideation
        ↓
Hypothesis Approved
        ↓
Planning
        ↓
Experiment Plan
        ↓
Experiment
        ↓
Results
        ↓
Writing
        ↓
Paper
        ↓
Human Review
        ↓
Publication
```

---

# 本质科研单位（FARS 的核心思想）

每个循环只产出：

> 一个假设 + 一个验证

而不是长论文。

---

如果你愿意，我可以把这个 workflow 转成：

* 系统架构图
* agent 接口定义
* project 目录模板

用于你复刻实现。

