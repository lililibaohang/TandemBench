<div align="center">

# TandemBench

[**TandemBench: Benchmarking Decision Models for Multi-Agent Collaboration**](https://arxiv.org/pdf/2611.05827)

**30 tasks** · **200 scenarios** · **1,200 questions**

**English** · [简体中文](README_zh-CN.md)

[Dataset format](#dataset-format) · [Results](#results) · [Data and answer key](#data-and-answer-key)

</div>

TandemBench evaluates whether decision models can use global information to understand coordination among agents and make decisions about team plans. The included test inputs are the English v1.0.0 edition.

- **DA · Team-plan decision**: select the optimal plan from the candidates.
- **VA · Optimality verification**: determine whether an optimal plan is missing from the candidates.

## Dataset format

This release is a multiple-choice test set with a separate answer key. It does not include a model-serving adapter or evaluation code.

- `data/decision/inputs.jsonl`: 1,600 English decision presentations.
- `data/verification/inputs.jsonl`: 3,200 English optimality-verification presentations.
- `evaluation/decision/answers.jsonl` and `evaluation/verification/answers.jsonl`: the released answer and condition metadata; keep these files out of model inputs.
- Each model-facing row contains only `id` and `prompt`; submit one explicit choice, `A`, `B`, `C`, or `D`, for each ID.

See the [dataset format](docs/dataset.md) for record examples and the distinction between input and answer-key fields.

## Results

The leaderboard below reports the English v1.0.0 edition. It contains complete, reviewed results for 50 models (40 decision and 10 general); seven planned general models are omitted until their English results are complete and reviewed.

<!-- RESULTS_START -->
**Results as of: 2026-11-03**

### Decision Models

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

### General Models

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

## Data and answer key

[`data/`](data/) Test inputs · [`evaluation/`](evaluation/) Answer key · [`docs/dataset.md`](docs/dataset.md) Dataset format

The scenarios are derived from [Collab-Overcooked](https://github.com/YusaeMeow/Collab-Overcooked); its [MIT license](third_party/Collab-Overcooked-LICENSE) is included. Licenses for TandemBench code and data are still pending. This repository publishes the English inputs, answer metadata, manifests, and result tables.
