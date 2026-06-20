## Task: Verify and complete initial YOnLab G2B Agent v2 baseline

### Goal
Verify the newly generated project baseline and make the smallest necessary corrections so the app has a working FastAPI `/health` endpoint and passing pytest baseline.

### Context
This is a new independent project:

- Existing v1 project path: `D:\Views\yonlab-bid-agent`
- New v2 project path: `D:\Views\yonlab-g2b-agent-v2`

Do not modify or depend on the v1 project.

Current Phase 1 target:

- Minimal FastAPI application
- `GET /health`
- `tests/test_app_health.py`
- `python -m pytest -q` passes

### Required work
1. Inspect the file tree.
2. Confirm the following files exist:
   - `AGENTS.md`
   - `README.md`
   - `.gitignore`
   - `.env.example`
   - `pyproject.toml`
   - `app/main.py`
   - `app/api/routes.py`
   - `app/core/config.py`
   - `tests/test_app_health.py`
   - `scripts/run_tests.ps1`
   - `scripts/dev_start.ps1`
3. Run the baseline tests.
4. If tests fail, fix only the minimum required files.
5. Do not implement scoring, G2B integration, report generation, database, or UI in this task.

### Constraints
- Do not touch `D:\Views\yonlab-bid-agent`.
- Do not call any real G2B/Public Data Portal API.
- Do not create or print `.env`.
- Do not include secrets.
- Keep changes small.
- Do not create future test files such as `test_score_engine.py` unless the feature is implemented in a later task.

### Done when
- `python -m pytest -q` passes.
- `GET /health` returns:

```json
{
  "status": "ok",
  "app": "YOnLab G2B Agent v2"
}
```

### Validation commands
```powershell
Set-Location D:\Views\yonlab-g2b-agent-v2
.\.venv\Scripts\Activate.ps1
python -m pytest -q
python - <<'PY'
from app.main import app
print([route.path for route in app.routes])
PY
```

### Completion report
Report:

1. Files changed
2. Behavior changed
3. Tests run
4. Test result
5. Known risks
6. Suggested next task
