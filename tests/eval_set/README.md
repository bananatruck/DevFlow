# Evaluation Dataset (Stub)

Place your 100 labeled workflow items here, e.g. as JSONL:

- `workflows.jsonl`: each row = {issue, pr_diff, labels...}

The evaluation harness will:
- run the agent on each issue
- score outputs vs. ground truth
- write metrics to CI artifacts
