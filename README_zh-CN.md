<div align="center">

# TandemBench

[**TandemBench: Benchmarking Decision Models for Multi-Agent Collaboration**](https://arxiv.org/pdf/2611.05827)

**30 个任务** · **200 个场景** · **1,200 道题**

[English](README.md) · **简体中文**

[数据格式](#数据格式) · [测试结果](#测试结果) · [数据与答案](#数据与答案)

</div>

TandemBench 评估决策模型能否根据全局信息理解成员间的协作，并对团队方案作出选择与判断。本仓库提供英文版 v1.0.0 测试输入。

- **DA · 团队方案决策**：从候选方案中选出最优方案。
- **VA · 最优性验证**：判断给定方案中是否缺少最优方案。

## 数据格式

本版本是带独立答案信息的选择题测试集，不包含模型服务适配器或测评代码。

- `data/decision/inputs.jsonl`：1,600 条英文团队方案决策展示。
- `data/verification/inputs.jsonl`：3,200 条英文最优性验证展示。
- `evaluation/decision/answers.jsonl` 和 `evaluation/verification/answers.jsonl`：已提供的答案与条件元数据；这些文件不能放入模型输入。
- 模型输入每行只有 `id` 和 `prompt`；模型对每个 ID 输出一个明确选项：`A`、`B`、`C` 或 `D`。

记录示例和输入/答案字段区别见[数据格式说明](docs/dataset.md)。

## 测试结果

以下榜单使用英文版 v1.0.0，包含 50 个模型（40 个决策模型、10 个通用模型）的完整复核结果；另外 7 个计划中的通用模型待英文结果完成并复核后再加入。

<!-- RESULTS_START -->
**评测结果截至：2026-11-03**

### 决策模型

| Rank | Model | Params. (B) | DA ↑ | VA ↑ |
|---:|---|---:|---:|---:|
| 3 | **KnowLine-31B-Gen1** | 31 | **62.50** | 51.44 |
| 4 | **Basal-Omni-1.0-Ultra** | 31 | 60.75 | 51.97 |
| 5 | **Quyet-1.0-Large** | 31 | 60.75 | 52.06 |
| 7 | DOPEST-1.0-31B | 31 | 60.38 | 52.16 |
| 8 | PPLX-Decider-v1.2 | 27 | 60.38 | 55.31 |
| 10 | PPLX-Decider-v1.1-27B | 27 | 59.44 | 54.28 |
| 11 | Torchcast-4B-v1.2 | 4 | 58.94 | 50.66 |
| 12 | H2O-Lightning-31B (BF16) | 31 | 58.69 | 50.19 |
| 13 | D3 | 27 | 58.69 | 52.19 |
| 14 | GLiDE-1.2-Open | 27 | 58.13 | 54.72 |
| 15 | StartLux-v1.1-27B-Instant | 27 | 57.44 | 54.00 |
| 16 | René-31B (dequant. BF16) | 31 | 55.56 | 53.41 |
| 17 | PPLX-Decider-Flash-v1.2 | 4 | 52.94 | 53.19 |
| 18 | D3-Turbo | 27 | 52.94 | 49.97 |
| 19 | Torchcast-4B-v1.3 | 4 | 52.75 | 51.28 |
| 20 | deck31b (BF16) | 31 | 52.19 | 49.72 |
| 21 | Wald-26B-A4B | 26/4 | 50.63 | 51.09 |
| 22 | Jeff-1.1-Medium | 12 | 50.50 | 50.69 |
| 23 | Vega-27B | 27 | 50.25 | 52.28 |
| 24 | Tacit-9B | 9 | 48.63 | 49.94 |
| 25 | D3-Ultra | 27 | 47.50 | **56.28** |
| 26 | MeTask-Rain-31B | 31 | 47.44 | 50.56 |
| 27 | MeTask-Rain-12B | 12 | 47.38 | 50.66 |
| 28 | Liquid AI d1-3B | 3.12 | 47.19 | 53.47 |
| 29 | Torchcast-12B | 12 | 46.75 | 52.69 |
| 31 | Tacit-4B | 4 | 46.31 | 50.00 |
| 33 | Mapika-Decider-12B | 12 | 44.25 | 50.78 |
| 34 | Mammoth-1 | 27 | 43.88 | 52.34 |
| 35 | Torchcast-4B-v1.1 | 4 | 43.50 | 52.34 |
| 37 | Clef | 27 | 40.94 | 52.91 |
| 38 | Joey-1 | 2 | 40.69 | 50.53 |
| 41 | Tacit-2B | 2 | 39.44 | 50.25 |
| 42 | H2O-Lightning-4B | 4 | 39.06 | 51.19 |
| 43 | Nox-4B | 4 | 39.00 | 50.00 |
| 44 | Clef-Flash | 9 | 35.81 | 49.91 |
| 45 | Lux-9B | 9 | 34.56 | 51.97 |
| 46 | Tacit-1.7B | 1.7 | 29.44 | 49.59 |
| 47 | Laya-421M | 0.421 | 25.88 | 49.69 |
| 48 | Kai-0.6B | 0.6 | 21.81 | 50.00 |
| 50 | CLM-8B | 8 | 15.44 | 45.94 |

### 通用模型

| Rank | Model | Params. (B) | DA ↑ | VA ↑ |
|---:|---|---:|---:|---:|
| 1 | **Qwen3.8-27B** | 27 | **82.80** | **71.88** |
| 2 | **Gemma4-31B** | 31 | 73.11 | 57.03 |
| 6 | **Gemma4-26B-A4B** | 26/4 | 60.58 | 53.66 |
| 9 | Muse-Glimmer-30B | 30 | 59.64 | 60.35 |
| 30 | Qwen3-32B | 32 | 46.33 | 49.45 |
| 32 | Gemma4-E4B | 8 | 45.03 | 51.16 |
| 36 | Qwen3-8B | 8 | 41.03 | 49.85 |
| 39 | Ministral 3 14B Instruct | 14 | 39.89 | 51.45 |
| 40 | Llama3.3-70B | 70 | 39.50 | 48.92 |
| 49 | Qwen3-0.6B | 0.6 | 17.19 | 40.61 |
<!-- RESULTS_END -->

## 数据与答案

[`data/`](data/) 测试输入 · [`evaluation/`](evaluation/) 答案信息 · [`docs/dataset.md`](docs/dataset.md) 数据格式

测试场景基于 [Collab-Overcooked](https://github.com/YusaeMeow/Collab-Overcooked)，保留上游 [MIT 许可证](third_party/Collab-Overcooked-LICENSE)。TandemBench 自身代码与数据的许可证仍待确定。本仓库发布英文输入、答案元数据、清单和结果表。
