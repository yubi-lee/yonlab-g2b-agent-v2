# 04_TESTING_STRATEGY ??Initial

## Phase 1 baseline

```powershell
python -m pytest -q
```

Expected:

```text
1 passed
```

## Future test groups

- `test_app_health.py`
- `test_g2b_normalizer.py`
- `test_yonlab_eligibility.py`
- `test_score_engine.py`
- `test_markdown_report.py`

Future test files should be created by the task that implements the corresponding feature.
