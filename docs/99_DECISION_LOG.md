# 99_DECISION_LOG

## 2026-06-20

Decision: Create a separate v2 project instead of modifying the existing v1 repository.

Reason:

- Prevent v1/v2 code contamination.
- Test Agent-first development from a clean baseline.
- Keep the first milestone small and verifiable.

Initial validation target:

```powershell
python -m pytest -q
```
