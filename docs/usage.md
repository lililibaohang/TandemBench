# 评测使用说明

以下命令均在仓库根目录执行。

独立的测试集与 API 评测工具。**Python 3.10+，仅使用标准库，无需安装模型或第三方依赖。**

当前公开入口是 TandemBench 的 **SystemOne 原生决策接口**：提供 API 地址、模型名和 API key，即可提交结构化状态、候选选项和决策问题并自动评分。地址需包含服务要求的 `/v1` 等前缀；调用适配集中在 `tandembench/native_runner.py`。本包不训练模型、不重新求解最优答案。

## 快速开始

解压后进入本目录。最简单的方式：

```bash
python run_native.py --base-url https://YOUR-ENDPOINT/v1 --model YOUR-MODEL \
  --output runs/my-model-smoke --limit 4
```

按提示或参数提供原生 API 地址、模型名和 API key。密钥隐藏输入，不写入配置或结果文件。这会对两个维度各取 4 条展示，共调用 8 次，用于检查接口；子集结果明确标为 smoke test。

确认接口正常后，执行全量评测：

```bash
export TANDEMBENCH_API_KEY=YOUR_KEY
python run_native.py --base-url https://YOUR-ENDPOINT/v1 --model YOUR-MODEL \
  --output runs/my-model-full
```

原生服务需要提供 `POST /v1/systemone`，请求中的 `state` 和 `questions.decision.criteria` 分别对应全局状态与 A--D 候选选项。响应至少需要返回 `answers.decision.choice`；如果同时返回 `answers.decision.probabilities`，程序会保存在 `predictions.jsonl` 中供后续分析使用。

如果模型服务使用 vLLM 作为后端，仍需模型专用适配器把后端包装成上述原生接口。`run_native.py` 不能直接请求 vLLM 的 `/v1/chat/completions`，因为那是文本生成协议。

默认是 4,800 次请求，每条展示一次，默认并发数 1。可以通过 `--workers` 调整并发，通过 `--timeout` 和 `--retries` 控制网络等待与重试。

先检查数据和请求数量，不连接 API：

```bash
python run_native.py --dry-run
```

## 接口参数

```bash
# 只评测一个维度，或改变并发、超时和重试次数。
python run_native.py --part decision --workers 2 --timeout 300 --retries 2 \
  --base-url https://YOUR-ENDPOINT/v1 --model YOUR-MODEL \
  --output runs/my-model-decision
```

`--part` 可选 `all`、`decision`、`verification`。`--limit N` 是每个维度的展示条数上限，仅用于冒烟测试，不能把子集分数当作完整榜单成绩。

## 中断与续跑

使用完全相同的模型、参数和输出目录，并增加 `--resume`：

```bash
python run_native.py --base-url https://YOUR-ENDPOINT/v1 --model YOUR-MODEL \
  --output runs/my-model-full --resume
```

已完整返回的响应不会重复调用，包括无效和截断回答；仅缺失或传输失败的项目继续执行。更改数据、代码或配置会拒绝续跑，避免混合协议。可重试的 HTTP 408/429/5xx 和连接错误默认最多重试 2 次，全部 attempt 都保留；400/401/403/404/405/413/422 会停止后续批次。

按一次 Ctrl+C 时，会等待当前在途批次返回或超时并保存响应，再标记为 interrupted；请避免在保存期间再次强制终止。日志损坏或配置不符时，续跑拒绝执行，并保留已有指标与报告。

进程被强制终止可能留下 `.running.lock`，确认原进程已退出后再移除该锁文件。若最后一条 JSONL 因断电损坏，程序会拒绝读取而不丢弃记录，应先备份并恢复完整日志。请求已在服务器完成但本地未记录时，续跑可能再次请求该项，API 调用不能保证网络层面的 exactly-once。

## 数据与评分

- 30 个任务，200 个场景；400 道团队方案决策题＋800 道配对最优性验证题。
- 每题包含四种循环选项排列，共 **1,600＋3,200＝4,800 条展示**。
- 当前测试输入为英文 v1.0.0，每次请求只发送题目 prompt。该版本还修正了一处位置名称，涉及 8 条展示。内部条件 ID 已转换为不透露答案的 ID。
- README 榜单使用英文版 v1.0.0 输入，当前发布 50 个模型的完整复核结果；7 个计划中的通用模型尚未加入榜单。
- `data/` 是模型输入；`evaluation/` 是本地评分答案与分组信息，不发送给模型。
- **DA**：团队方案决策的平均正确率。
- **VA**：删除最优方案组的正确检出率与保留最优方案组的正确拒报率的等权平均。保留组选择任一有效具体方案都算拒报，不要求选中具体最优方案。
- 无效/歧义回答和截断回答计错；网络/API 失败单独记录。一个维度缺少响应时，不输出该维度的完整得分。
- 原生接口只解析 `answers.decision.choice`，不从文本推理中猜测答案；如果服务返回 A--D 概率向量，也会原样保存在预测记录中。
- 同场景变体和旋转不是独立样本；没有虚构 train/test split。独立人工复核尚未完成。

## 输出文件

```text
runs/<run>/
  config.json             模型、接口、采样参数、代码和数据哈希；不含密钥
  EXPERIMENT_CARD.md       本次评测协议说明
  run_manifest.json        执行状态与输出哈希
  attempts.jsonl          逐请求原始响应、失败类型、usage、耗时及重试记录
  predictions.jsonl       归一化选择和解析状态，可从原始响应重建
  metrics.json            机器可读 DA/VA；数值为 0–1
  REPORT.md               可阅读的百分比成绩
```

默认不会把新结果并入论文榜单。先审核完整性和模型配置，再按项目的结果快照流程采用。

## 验证本包

```bash
python verify.py
python -B -m unittest discover -s tests -v
```

测试仅启动本机模拟 HTTP 服务，验证调用、网络重试、断点续跑、截断/歧义处理和评分；不使用真实模型、不消耗外部 API 额度。分发前另校验 `PACKAGE_MANIFEST.json` 中的 SHA-256。

## 发布身份

版本 1.0.0，TandemBench 私有仓库预发布版。代码和数据许可证待作者确定，当前目录不冒充已授予开源许可证。数据版本与来源见 `data/manifest.json`、`PROVENANCE.json`。不包含模型权重、私有服务器配置或整个研究工作区。


## 0.1.1 审查修复

- 损坏或不一致的续跑日志不会覆盖已有成绩和预测文件。
- Ctrl+C 保存当前已发出批次的响应，更新 interrupted 状态，再允许续跑。
- 评分拒绝空答案集和非法答案标签；无效回答不能被误计为正确拒报。
- 服务响应中的回显密钥在 JSON 解码后递归脱敏，覆盖转义字符串；HTTP 重定向不携带认证信息跟随。
- 数据清单限定预期文件，核对输入数、唯一 ID、哈希；超时及附加参数进行类型和范围检查。

测试只验证本机模拟服务和数据/代码的一致性；没有使用真实外部服务进行兼容性认证。原生服务本身需要由模型提供者或模型专用适配器部署；本包负责请求、记录、解析和评分。

## 上游来源

本测试集基于 Collab-Overcooked 的协作烹饪环境构建，保留上游 [MIT 许可证及版权声明](../third_party/Collab-Overcooked-LICENSE)。TandemBench 自身代码和数据的许可证仍待作者确定。
