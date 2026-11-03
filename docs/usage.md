# 评测使用说明

以下命令均在仓库根目录执行。

独立的测试集与 API 评测工具。**Python 3.10+，仅使用标准库，无需安装模型或第三方依赖。**

支持 OpenAI 兼容的 **Chat Completions** 接口：提供 API 地址、模型名和 API key，即可运行并自动评分。地址需包含服务要求的 `/v1` 等前缀；也可以直接提供以 `/chat/completions` 结尾的完整地址。本包不要求使用 OpenAI 服务。

原生 typed-decision/probability API、Responses API 和其他私有请求格式不属于当前适配范围，不能直接换一个 URL 就保证兼容。调用适配集中在 `tandembench/api.py`。本包不训练模型、不重新求解最优答案。

## 快速开始

解压后进入本目录。最简单的方式：

```bash
python run.py --limit 4
```

按提示输入 API base URL、模型名和 API key。密钥隐藏输入，不写入配置或结果文件。这会对两个维度各取 4 条展示，共调用 8 次，用于检查接口；子集结果明确标为 smoke test。

也可以通过参数和环境变量配置：

```bash
# 通过终端安全输入或平台密钥管理工具设置 TANDEMBENCH_API_KEY。
# 不要把真实密钥写入脚本、README 或提交到仓库。
python run.py \
  --base-url https://YOUR-ENDPOINT/v1 \
  --model YOUR-MODEL \
  --output runs/my-model-smoke \
  --limit 4
```

未设置环境变量时，程序会提示隐藏输入密钥；本地无认证服务可输入任意占位值。

确认接口正常后，执行全量评测：

```bash
python run.py --base-url https://YOUR-ENDPOINT/v1 --model YOUR-MODEL \
  --output runs/my-model-full
```

默认是 4,800 次请求，每条展示采样一次，temperature=0、max_tokens=16,384、并发数 4。请求数不含可能发生的网络重试。API 使用量由你选择的服务计费，本包不会估算具体金额。

先检查数据和请求数量，不连接 API：

```bash
python run.py --dry-run
```

## 采样与接口参数

```bash
# 每条展示四次采样，共 19,200 次请求；按均值计分，不投票、不择优。
python run.py --base-url https://YOUR-ENDPOINT/v1 --model YOUR-MODEL \
  --samples 4 --temperature 0.6 --output runs/my-model-n4

# 只评测其中一个维度，或改变并发、超时和输出预算。
python run.py --part decision --workers 2 --timeout 180 --max-tokens 8192
```

`--part` 可选 `all`、`decision`、`verification`。`--limit N` 是每个维度的展示条数上限，仅用于冒烟测试，不能把子集分数当作完整榜单成绩。

服务专用参数可以通过 JSON 文件传入：

```bash
python run.py --request-options request-options.example.json
```

允许字段为 `top_p`、`seed`、`reasoning_effort`、`chat_template_kwargs`、`enable_thinking`、`max_completion_tokens`。仅传服务明确支持的字段。示例文件 `{}` 表示不额外指定；使用 `max_completion_tokens` 时不会同时发送 `max_tokens`。模型名、消息、stream、n 和密钥不能通过该文件覆盖。

论文中的不同模型使用原生接口、精度、模板和推理配置；通用模型每位置四次采样、原生决策模型通常一次。这里的通用 Chat API 结果**不自动等同于论文中的原生模型配置结果**。比较前应记录并核对模型版本、服务端推理设置和预算。不要仅把 `--samples` 改成 4 就宣称完整复现论文配置。

## 中断与续跑

使用完全相同的模型、参数和输出目录，并增加 `--resume`：

```bash
python run.py --base-url https://YOUR-ENDPOINT/v1 --model YOUR-MODEL \
  --output runs/my-model-full --resume
```

已完整返回的响应不会重复调用，包括无效和截断回答；仅缺失或传输失败的项目继续执行。更改数据、代码或配置会拒绝续跑，避免混合协议。可重试的 HTTP 408/429/5xx 和连接错误默认最多重试 2 次，全部 attempt 都保留；400/401/403/404/405/413/422 会停止后续批次。

按一次 Ctrl+C 时，会等待当前在途批次返回或超时并保存响应，再标记为 interrupted；请避免在保存期间再次强制终止。日志损坏或配置不符时，续跑拒绝执行，并保留已有指标与报告。

进程被强制终止可能留下 `.running.lock`，确认原进程已退出后再移除该锁文件。若最后一条 JSONL 因断电损坏，程序会拒绝读取而不丢弃记录，应先备份并恢复完整日志。请求已在服务器完成但本地未记录时，续跑可能再次请求该项，API 调用不能保证网络层面的 exactly-once。

## 数据与评分

- 30 个任务，200 个场景；400 道团队方案决策题＋800 道配对最优性验证题。
- 每题包含四种循环选项排列，共 **1,600＋3,200＝4,800 条展示**。
- 当前测试输入为英文 v1.0.0，每次请求只发送题目 prompt。该版本还修正了一处位置名称，涉及 8 条展示。内部条件 ID 已转换为不透露答案的 ID。
- README 榜单使用中文输入评测，不能直接视为英文版成绩；不同语言版本的结果不等同。
- `data/` 是模型输入；`evaluation/` 是本地评分答案与分组信息，不发送给模型。
- **DA**：团队方案决策的平均正确率。
- **VA**：删除最优方案组的正确检出率与保留最优方案组的正确拒报率的等权平均。保留组选择任一有效具体方案都算拒报，不要求选中具体最优方案。
- 无效/歧义回答和截断回答计错；网络/API 失败单独记录。一个维度缺少响应时，不输出该维度的完整得分。
- 只解析显式最终答案，不从前面的推理文字中猜测答案。解析器沿用项目 v5 规则，并为 Chat API 包装适配；例如 `A`、`答案：A`、`Final answer: A` 和 `\boxed{A}`。
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

测试只验证本机模拟服务和数据/代码的一致性；没有使用真实外部服务进行兼容性认证。当前仅支持 Chat Completions，原生决策概率接口仍需要相应适配器。

## 上游来源

本测试集基于 Collab-Overcooked 的协作烹饪环境构建，保留上游 [MIT 许可证及版权声明](../third_party/Collab-Overcooked-LICENSE)。TandemBench 自身代码和数据的许可证仍待作者确定。
