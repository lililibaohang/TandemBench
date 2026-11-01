# TandemBench

TandemBench 评估模型能否根据全局信息，理解多智能体之间的协作，并对团队方案作出决策。

基准包含 **30 个任务、200 个场景和 1,200 道题**，从两个方面评估：

- **团队方案决策（DA）**：从候选方案中选出最优方案。
- **最优性验证（VA）**：判断给定方案中是否缺少最优方案。

每道题提供四种选项排列，共 **4,800 条测试输入**。测试场景基于 [Collab-Overcooked](https://github.com/YusaeMeow/Collab-Overcooked)。

## 快速开始

需要 Python 3.10+，无需安装第三方依赖。当前支持 **Chat Completions 兼容 API**。

先用少量题目检查接口：

```bash
python run.py --limit 4
```

按提示输入 API 地址、模型名称和密钥。确认接口正常后运行完整测试：

```bash
python run.py --output runs/my-model
```

默认每个选项排列测试一次，共 **4,800 次请求**；结果保存在 `runs/my-model/REPORT.md` 和 `metrics.json`。`--limit 4` 仅用于接口检查，得到的是子集成绩。

可通过 `--part decision` 或 `--part verification` 单独测试一个维度；使用 `--samples 4` 可对每条输入采样四次。更多参数、断点续跑和评分细节见[使用说明](docs/usage.md)。

## 数据与代码

- `data/`：测试输入；`evaluation/`：独立评分信息，测试时不会发送给模型。
- `tandembench/`：API 调用、答案解析和评分代码；`tests/`：本地模拟测试。
- 原生决策模型的概率接口尚待适配；Chat API 结果应结合具体模型配置解读。

## 来源与许可

TandemBench 基于 Collab-Overcooked 构建，保留其 [MIT 许可证](third_party/Collab-Overcooked-LICENSE)。TandemBench 自身代码和数据的许可证待确定；当前仓库为私有预发布版本。
