---
title: LLM Powered Autonomous Agents
date: 2026-10-15
tags:
  - Agent
categories:
  - 技术
draft: false
---



今天看完了[LLM Powered Autonomous Agents](https://lilianweng.github.io/posts/2023-06-23-agent/)这篇文章，它在2023年6月总结出了AI Agent的结构与概念，对于想了解Agent架构及功能组成的人士来说值得一看。

## 文章概述

在LLM驱动的自主Agent系统中，LLM充当Agent的"大脑"，由以下几个关键组件构成：
- **Planning（规划）**：将大任务分解为子目标，并进行自我反思和修正
- **Memory（记忆）**：短期记忆（上下文学习）和长期记忆（外部向量存储）
- **Tool Use（工具使用）**：调用外部API获取额外信息

以下为文章三个核心部分的总结。

---

## 1. Planning

复杂任务通常包含多个步骤，Agent需要提前规划。

### 1.1 任务分解（Task Decomposition）

将大任务拆解为可管理的子任务：

- **[Chain of Thought (CoT)](https://arxiv.org/abs/2201.11903)**：标准的Prompt技术，让模型"逐步思考"，将困难任务分解为更小更简单的步骤。原论文：[Wei et al. 2022](https://arxiv.org/abs/2201.11903)
- **[Tree of Thoughts (ToT)](https://arxiv.org/abs/2305.10601)**：扩展CoT，在每一步探索多个推理可能性，构建树状结构。搜索过程可用BFS或DFS，每个状态由分类器或多数投票评估。原论文：[Yao et al. 2023](https://arxiv.org/abs/2305.10601)
- **[LLM+P](https://arxiv.org/abs/2304.11477)**：利用外部经典规划器（PDDL）进行长程规划。LLM将问题翻译为PDDL，由外部规划器生成计划，再翻译回自然语言。原论文：[Liu et al. 2023](https://arxiv.org/abs/2304.11477)

任务分解方式：
1. 简单Prompt（如"Steps for XYZ"）
2. 任务特定指令（如"Write a story outline"）
3. 人工输入

### 1.2 自我反思（Self-Reflection）

通过反思过去行为来迭代改进：

- **[ReAct](https://arxiv.org/abs/2210.03629)**：将推理（Reasoning）和行动（Acting）整合到LLM中。扩展动作空间为任务特定动作+语言空间。典型格式：
  ```
  Thought: ...
  Action: ...
  Observation: ...
  ```
  原论文：[Yao et al. 2023](https://arxiv.org/abs/2210.03629)
- **[Reflexion](https://arxiv.org/abs/2303.11366)**：为Agent配备动态记忆和自我反思能力。使用启发式函数判断轨迹是否低效或包含幻觉（hallucination），并决定是否重置环境重新开始。原论文：[Shinn & Labash, 2023](https://arxiv.org/abs/2303.11366)
- **[Chain of Hindsight (CoH)](https://arxiv.org/abs/2302.02676)**：将历史输出序列（附带反馈注释）呈现给模型，训练模型基于反馈序列自我反思以产生更好的输出。数据集来自[WebGPT comparisons](https://huggingface.co/datasets/openai/webgpt_comparisons)、[summarization from human feedback](https://github.com/openai/summarize-from-feedback)和[human preference dataset](https://github.com/anthropics/hh-rlhf)。原论文：[Liu et al. 2023](https://arxiv.org/abs/2302.02676)
- **[Algorithm Distillation (AD)](https://arxiv.org/abs/2210.14215)**：将跨Episode的强化学习历史进行蒸馏，让模型学习RL的学习过程本身。与ED、source policy、[RL²](https://arxiv.org/abs/1611.02779)基准对比，source policies使用[A3C](https://lilianweng.github.io/posts/2018-04-08-policy-gradient/#a3c)和[DQN](http://lilianweng.github.io/posts/2018-02-19-rl-overview/#deep-q-network)训练。原论文：[Laskin et al. 2023](https://arxiv.org/abs/2210.14215)

---

## 2. Memory

### 2.1 记忆的不同类型

人类记忆分类及在AI Agent中的映射：

| 人类记忆类型 | 说明 | Agent对应 |
|---|---|---|
| **感知记忆** | 视觉、听觉、触觉等感官印象，持续数秒 | 原始输入的embedding表示 |
| **短期记忆 / Working Memory** | 当前意识中的信息，约7个项目，持续20-30秒 | In-context Learning（受限于Transformer的有限上下文窗口） |
| **长期记忆 - 声明式** | 可主动回忆的事实和事件 | 外部向量存储（无限容量） |
| &nbsp;&nbsp;&nbsp;&nbsp;├ 情景记忆 | 事件和经历（Episodic） | |
| &nbsp;&nbsp;&nbsp;&nbsp;└ 语义记忆 | 事实和概念（Semantic） | |
| **长期记忆 - 程序性** | 无意识的技能和流程 | 调用skill的自动化流程 |

### 2.2 MIPS（Maximum Inner Product Search）最大内积搜索

外部记忆的标准做法是将信息的embedding表示保存到支持快速[MIPS](https://en.wikipedia.org/wiki/Maximum_inner-product_search)的向量数据库中。为优化检索速度，通常使用**近似最近邻（ANN）算法**：

1. **[LSH](https://en.wikipedia.org/wiki/Locality-sensitive_hashing)**（Locality-Sensitive Hashing）：局部敏感哈希，相似输入以高概率映射到同一桶中
2. **[ANNOY](https://github.com/spotify/annoy)**（Approximate Nearest Neighbors Oh Yeah）：核心数据结构是随机投影树，通过构建多棵随机二叉树来近似哈希函数
3. **[HNSW](https://arxiv.org/abs/1603.09320)**（Hierarchical Navigable Small World）：受[小世界网络](https://en.wikipedia.org/wiki/Small-world_network)启发，构建分层的图结构。从顶层随机节点开始导航，逐步向下层细化搜索质量
4. **[FAISS](https://github.com/facebookresearch/faiss)**（Facebook AI Similarity Search）：基于向量量化的方法，将向量空间划分为簇，先粗量化找候选簇，再细量化搜索
5. **[ScaNN](https://github.com/google-research/google-research/tree/master/scann)**（Scalable Nearest Neighbors）：Google的各向异性向量量化方法，使量化后的内积尽可能接近原始距离。详情参阅[Google Blog: Announcing ScaNN](https://ai.googleblog.com/2020/07/announcing-scann-efficient-vector.html)

更多MIPS算法性能对比可参考 [ann-benchmarks.com](https://ann-benchmarks.com/)。

---

## 3. Tool Use（工具使用）

工具使用是人类区别于其他动物的重要特征。为LLM配备外部工具可显著扩展模型能力。

### 主要框架和方法

- **[MRKL](https://arxiv.org/abs/2205.00445)**（Modular Reasoning, Knowledge and Language）：神经-符号架构，LLM作为路由器将查询路由到最佳专家模块（神经模块如深度学习模型，或符号模块如计算器、天气API）。原论文：[Karpas et al. 2022](https://arxiv.org/abs/2205.00445)
- **[TALM](https://arxiv.org/abs/2205.12255)**（Tool Augmented Language Models; [Parisi et al. 2022](https://arxiv.org/abs/2205.12255)）和 **[Toolformer](https://arxiv.org/abs/2302.04761)**（[Schick et al. 2023](https://arxiv.org/abs/2302.04761)）：微调语言模型学习使用外部工具API，基于新API调用注释是否能提升输出质量来扩展数据集。更多详情参阅[Prompt Engineering 文章的 External APIs 部分](https://lilianweng.github.io/posts/2023-03-15-prompt-engineering/#external-apis)
- **[ChatGPT Plugins](https://openai.com/blog/chatgpt-plugins)** 和 **[OpenAI Function Calling](https://platform.openai.com/docs/guides/gpt/function-calling)**：LLM工具使用能力的实际应用案例
- **[HuggingGPT](https://arxiv.org/abs/2303.17580)**：使用ChatGPT作为任务规划器，根据HuggingFace平台模型描述选择模型，包含4个阶段：
  1. 任务规划（Task Planning）：解析用户请求为多个任务
  2. 模型选择（Model Selection）：将任务分配给专家模型
  3. 任务执行（Task Execution）：专家模型执行具体任务
  4. 响应生成（Response Generation）：汇总结果返回用户
  原论文：[Shen et al. 2023](https://arxiv.org/abs/2303.17580)
- **[API-Bank](https://arxiv.org/abs/2304.08244)**：工具增强LLM的评估基准，包含53个常用API工具，分3个评估层级：
  - Level-1：调用API的能力
  - Level-2：检索API的能力
  - Level-3：规划API调用的能力（处理模糊用户请求）
  原论文：[Li et al. 2023](https://arxiv.org/abs/2304.08244)

---

## 4. 案例研究（Case Studies）

### 4.1 科学发现Agent

- **[ChemCrow](https://arxiv.org/abs/2304.05376)**：LLM配备13个专家设计的工具，完成有机合成、药物发现和材料设计任务，在[LangChain](https://github.com/hwchase17/langchain)中实现。结合CoT推理和任务相关工具。有趣的发现：尽管LLM评估显示GPT-4和ChemCrow表现相当，但专家的人类评估显示ChemCrow远超GPT-4，说明用LLM自我评估深度专业领域可能存在偏差。原论文：[Bran et al. 2023](https://arxiv.org/abs/2304.05376)
- **自主科学实验Agent**（[Boiko et al. 2023](https://arxiv.org/abs/2304.05332)）：使用工具浏览互联网、阅读文档、执行代码、调用机器人实验API，可自主设计、规划和执行复杂科学实验。例如：开发新型抗癌药物时，模型会先调查当前趋势、选择靶点、请求支架、尝试合成。原论文：[Boiko et al. 2023](https://arxiv.org/abs/2304.05332)

### 4.2 生成式Agent模拟（Generative Agents）

25个虚拟角色在沙盒环境中生活和互动（灵感来自《模拟人生》）。原论文：[Park et al. 2023](https://arxiv.org/abs/2304.03442)

架构组成：
- **记忆流（Memory Stream）**：长期记忆模块，以自然语言记录Agent的完整经验
- **检索模型（Retrieval）**：根据**相关性**、**时效性**和**重要性**提取上下文
- **反思机制（Reflection）**：将记忆综合为高层次推断，指导Agent未来行为
- **规划与反应（Planning & Reacting）**：将反思和环境信息转化为行动

涌现行为：信息扩散、关系记忆、社交活动协调（如举办派对）

### 4.3 概念验证示例

- **[AutoGPT](https://github.com/Significant-Gravitas/Auto-GPT)**：以LLM为主控制器的自主Agent概念验证，通过自然语言接口执行搜索、浏览、文件操作、代码执行等任务。大量代码用于解析模型输出。GitHub: https://github.com/Significant-Gravitas/Auto-GPT
- **[GPT-Engineer](https://github.com/AntonOsika/gpt-engineer)**：根据自然语言描述创建完整代码仓库，通过任务澄清对话明确需求后进入代码编写模式。GitHub: https://github.com/AntonOsika/gpt-engineer
- **[BabyAGI](https://github.com/yoheinakajima/babyagi)**：另一个早期的自主Agent概念验证项目。GitHub: https://github.com/yoheinakajima/babyagi

---

## 5. 挑战（Challenges）

1. **有限的上下文长度**：历史信息、详细指令、API调用上下文和响应的容量受限。虽然向量存储和检索可提供更大知识库，但表示能力不如完整注意力机制
2. **长期规划和任务分解困难**：在冗长历史上进行规划并有效探索解空间仍具挑战性。LLM在面临意外错误时难以调整计划
3. **自然语言接口的可靠性**：Agent系统依赖自然语言作为LLM与外部组件（记忆和工具）之间的接口，但模型输出的可靠性存疑（可能出现格式错误、拒绝执行指令等问题），导致大量代码用于解析模型输出

---

## 参考文献

1. [Wei et al. "Chain of thought prompting elicits reasoning in large language models." NeurIPS 2022](https://arxiv.org/abs/2201.11903)
2. [Yao et al. "Tree of Thoughts." arXiv:2305.10601](https://arxiv.org/abs/2305.10601)
3. [Liu et al. "Chain of Hindsight Aligns Language Models with Feedback." arXiv:2302.02676](https://arxiv.org/abs/2302.02676)
4. [Liu et al. "LLM+P: Empowering Large Language Models with Optimal Planning Proficiency." arXiv:2304.11477](https://arxiv.org/abs/2304.11477)
5. [Yao et al. "ReAct: Synergizing reasoning and acting in language models." ICLR 2023](https://arxiv.org/abs/2210.03629)
6. [Shinn & Labash. "Reflexion: an autonomous agent with dynamic memory and self-reflection." arXiv:2303.11366](https://arxiv.org/abs/2303.11366)
7. [Laskin et al. "In-context Reinforcement Learning with Algorithm Distillation." ICLR 2023](https://arxiv.org/abs/2210.14215)
8. [Karpas et al. "MRKL Systems." arXiv:2205.00445](https://arxiv.org/abs/2205.00445)
9. [Parisi et al. "TALM: Tool Augmented Language Models." 2022](https://arxiv.org/abs/2205.12255)
10. [Schick et al. "Toolformer: Language Models Can Teach Themselves to Use Tools." arXiv:2302.04761](https://arxiv.org/abs/2302.04761)
11. [Shen et al. "HuggingGPT." arXiv:2303.17580](https://arxiv.org/abs/2303.17580)
12. [Li et al. "API-Bank: A Benchmark for Tool-Augmented LLMs." arXiv:2304.08244](https://arxiv.org/abs/2304.08244)
13. [Bran et al. "ChemCrow." arXiv:2304.05376](https://arxiv.org/abs/2304.05376)
14. [Boiko et al. "Emergent autonomous scientific research capabilities of large language models." arXiv:2304.05332](https://arxiv.org/abs/2304.05332)
15. [Park et al. "Generative Agents: Interactive Simulacra of Human Behavior." arXiv:2304.03442](https://arxiv.org/abs/2304.03442)
16. [Weng, Lilian. "LLM-powered Autonomous Agents." lilianweng.github.io, Jun 2023](https://lilianweng.github.io/posts/2023-06-23-agent/)
