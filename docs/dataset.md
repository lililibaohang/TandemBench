# Dataset format

TandemBench is distributed here as a multiple-choice dataset with a separate answer key. The package does not include a model-serving adapter, prompt parser, or scorer.

## Files

- `data/decision/inputs.jsonl`: 1,600 decision presentations (400 logical questions × four option rotations).
- `data/verification/inputs.jsonl`: 3,200 optimality-verification presentations (800 logical questions × four rotations).
- `evaluation/decision/answers.jsonl`: the correct option for each decision presentation.
- `evaluation/verification/answers.jsonl`: the condition (`removed` or `retained`) and reference option for each verification presentation.

The two `data/` files are the model-facing inputs. Keep the corresponding `evaluation/` file out of the model prompt. Each input row has exactly two fields:

```json
{"id":"00026591b7e63a7afacf41c1","prompt":"[Task and Recipe]\n...\n[Question]\n...\n[Options]\nA.\n...\nB.\n...\nC.\n...\nD.\n..."}
```

A submission is one explicit choice (`A`, `B`, `C`, or `D`) for every input ID. The answer key is released so users can implement their own evaluation, sampling, or analysis workflow.

## Answer-key records

Decision records contain the correct option and rotation metadata:

```json
{"id":"00026591b7e63a7afacf41c1","correct_letter":"A","rotation":1,"base_group":"30c8dc1e23016acecc35ce98"}
```

Verification records distinguish the retained-optimum and removed-optimum conditions:

```json
{"id":"0009178b8ce98db9249cb437","condition":"retained","meta_letter":"D","rotation":0,"scenario_group":"f023bbaf71d310cd1189d253","base_group":"71e4523985efb7e3de358d21"}
```

`meta_letter` identifies the option whose removal or retention defines the pair; it is answer metadata and must not be appended to the model input.

## Scope

The English edition is `tandembench-en-v1.0.0`: 30 tasks, 200 scenarios, 1,200 logical questions, and 4,800 recorded presentations. There is no formal train/validation/test split. The dataset manifest records SHA-256 hashes for the four data and answer files.
