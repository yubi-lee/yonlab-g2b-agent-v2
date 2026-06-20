# 02_AGENT_WORKFLOW ??Agent-first Development

## Required task format

Every Codex task should include:

1. Goal
2. Context
3. Constraints
4. Done when
5. Validation commands

## Development flow

```text
Create small task
??Add/adjust tests
??Implement minimum code
??Run pytest
??Review diff
??Commit
```

## Baseline validation

```powershell
python -m pytest -q
```

## Key principle

Do not ask Codex to build the whole product at once.
