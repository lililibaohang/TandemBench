<div align="center">

# TandemBench

**Benchmarking Decision Models for Multi-Agent Collaboration**

**30 个任务** · **200 个场景** · **1,200 道题**

[English](README.md) · **简体中文**

[快速开始](#快速开始) · [测试结果](#测试结果) · [数据与代码](#数据与代码)

</div>

TandemBench 评估决策模型能否根据全局信息理解成员间的协作，并对团队方案作出选择与判断。本仓库提供英文版 v1.0.1 测试输入。

- **DA · 团队方案决策**：从候选方案中选出最优方案。
- **VA · 最优性验证**：判断给定方案中是否缺少最优方案。

## 快速开始

需要 Python 3.10+，无需安装第三方依赖。当前支持 Chat Completions 兼容 API。

```bash
python run.py --output runs/my-model
```

按提示输入 API 地址、模型名称和密钥。默认每个选项排列测试一次，共 **4,800 次请求**。结果保存在 `runs/my-model/REPORT.md` 和 `metrics.json`。完整参数及续跑方式见[使用说明](docs/usage.md)。

## 测试结果

以下成绩基于中文输入，不能直接视为英文版成绩；不同语言版本的结果不等同。

<!-- RESULTS_START -->
**评测结果截至：2026-11-01**

### 决策模型

| Rank | Model | Params. (B) | DA ↑ | VA ↑ |
|---:|---|---:|---:|---:|
| 3 | **Basal-Omni-1.0-Ultra** | 31 | **64.38** | 51.06 |
| 4 | **KnowLine-31B-Gen1** | 31 | 62.19 | 50.19 |
| 7 | **Quyet-1.0-Large** | 31 | 59.75 | 52.06 |
| 8 | H2O-Lightning-31B (BF16) | 31 | 59.19 | 49.97 |
| 11 | DOPEST-1.0-31B | 31 | 57.56 | 52.69 |
| 12 | PPLX-Decider-v1.1-27B | 27 | 56.06 | **57.03** |
| 13 | René-31B (dequant. BF16) | 31 | 54.56 | 53.41 |
| 14 | Torchcast-4B-v1.2 | 4 | 54.19 | 51.94 |
| 16 | deck31b (BF16) | 31 | 54.00 | 50.72 |
| 17 | D3 | 27 | 54.00 | 52.47 |
| 18 | PPLX-Decider-v1.2 | 27 | 51.25 | 56.50 |
| 19 | Jeff-1.1-Medium | 12 | 51.13 | 50.72 |
| 20 | Torchcast-4B-v1.3 | 4 | 51.06 | 53.03 |
| 21 | MeTask-Rain-31B | 31 | 50.94 | 50.84 |
| 22 | StartLux-v1.1-27B-Instant | 27 | 50.63 | 54.22 |
| 23 | GLiDE-1.2-Open | 27 | 50.56 | 54.94 |
| 24 | Torchcast-12B | 12 | 50.38 | 52.44 |
| 25 | Torchcast-4B-v1.1 | 4 | 47.81 | 52.97 |
| 26 | Wald-26B-A4B | 26/4 | 46.81 | 51.44 |
| 28 | Tacit-9B | 9 | 46.38 | 50.00 |
| 29 | D3-Ultra | 27 | 45.75 | 54.31 |
| 30 | D3-Turbo | 27 | 45.44 | 52.25 |
| 31 | Vega-27B | 27 | 45.25 | 51.28 |
| 32 | Clef | 27 | 44.56 | 52.06 |
| 33 | MeTask-Rain-12B | 12 | 44.50 | 50.56 |
| 34 | Liquid AI d1-3B | 3.12 | 44.13 | 53.38 |
| 35 | Tacit-4B | 4 | 44.13 | 50.16 |
| 36 | PPLX-Decider-Flash-v1.2 | 4 | 44.00 | 51.34 |
| 38 | Nox-4B | 4 | 43.63 | 50.50 |
| 40 | Mapika-Decider-12B | 12 | 43.06 | 51.53 |
| 41 | Mammoth-1 | 27 | 42.50 | 52.31 |
| 42 | Joey-1 | 2 | 39.69 | 50.00 |
| 43 | Clef-Flash | 9 | 39.38 | 50.00 |
| 45 | H2O-Lightning-4B | 4 | 38.75 | 50.47 |
| 46 | Lux-9B | 9 | 38.06 | 51.72 |
| 49 | Tacit-2B | 2 | 30.06 | 50.00 |
| 50 | Tacit-1.7B | 1.7 | 28.31 | 50.59 |
| 53 | Kai-0.6B | 0.6 | 25.50 | 50.00 |
| 54 | Laya-421M | 0.421 | 24.88 | 50.00 |
| 56 | CLM-8B | 8 | 19.50 | 50.00 |

### 通用模型

| Rank | Model | Avg. output tokens | DA ↑ | VA ↑ |
|---:|---|---:|---:|---:|
| 1 | **Qwen3.8-27B** | 8,616 | **83.97** | **72.20** |
| 2 | **Gemma4-31B** | 1,000 | 70.08 | 56.13 |
| 5 | **Gemma4-26B-A4B** | 1,170 | 61.78 | 54.42 |
| 6 | Muse-Glimmer-30B | 1,053 | 60.98 | 58.95 |
| 9 | Qwen3.5-9B | 7,944 | 57.67 | 55.11 |
| 10 | GPT-OSS-120B | 11,165 | 57.63 | 55.59 |
| 15 | Qwen3.5-4B | 7,551 | 54.13 | 51.52 |
| 27 | Qwen3-32B | 581 | 46.70 | 50.65 |
| 37 | Gemma4-E4B | 2,559 | 43.91 | 51.72 |
| 39 | GPT-OSS-20B | 9,946 | 43.59 | 43.15 |
| 44 | Llama3.3-70B | 430 | 38.91 | 50.59 |
| 47 | Qwen3-8B | 899 | 37.80 | 50.05 |
| 48 | Ministral 3 14B Instruct | 899 | 35.16 | 50.47 |
| 51 | Llama3.1-8B | 183 | 27.44 | 49.61 |
| 52 | Qwen3.5-2B | 10,237 | 26.84 | 47.73 |
| 55 | Qwen3.5-0.8B | 5,907 | 20.27 | 45.23 |
| 57 | Qwen3-0.6B | 6 | 11.31 | 40.15 |
<!-- RESULTS_END -->

## 数据与代码

[`data/`](data/) 测试输入 · [`evaluation/`](evaluation/) 评分信息 · [`tandembench/`](tandembench/) 评测代码 · [`docs/`](docs/) 使用说明

测试场景基于 [Collab-Overcooked](https://github.com/YusaeMeow/Collab-Overcooked)，保留上游 [MIT 许可证](third_party/Collab-Overcooked-LICENSE)。TandemBench 自身代码与数据的许可证待确定；当前为私有预发布版本。原生决策模型的概率接口尚待适配。
