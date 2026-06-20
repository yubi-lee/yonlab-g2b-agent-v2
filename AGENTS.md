# AGENTS.md ??YOnLab G2B Agent v2

## Repository identity

This repository is the second-generation YOnLab G2B/Narajangteo AI Bid Recommendation Agent.

It is independent from the previous repository:

- Previous repository: `D:\Views\yonlab-bid-agent`
- Current repository: `D:\Views\yonlab-g2b-agent-v2`

Do not import, copy, or assume previous repository code unless explicitly instructed.

## Product goal

The application should:

1. Retrieve or load Korean procurement notices.
2. Normalize G2B/public procurement data.
3. Evaluate YOnLab eligibility.
4. Score opportunity fit on a 100-point basis.
5. Detect risks such as region restriction, performance requirements, license mismatch, and deadline urgency.
6. Generate a YOnLab-specific recommendation report.

## YOnLab baseline

Use this profile as fixed domain context:

- Company: 二쇱떇?뚯궗 ??댁삩??- Location: ?쒖슱?밸퀎??媛뺣궓援?- Size: ?뚭린??/ ?뚯긽怨듭씤
- Status: 珥덇린李쎌뾽湲곗뾽
- Core qualification: ?뚰봽?몄썾?댁궗?낆옄
- Key procurement categories:
  - ?멸났吏?μ냼?꾪듃?⑥뼱
  - ?뺣낫?쒖뒪?쒓컻諛쒖꽌鍮꾩뒪
  - ?⑦궎吏?뚰봽?몄썾?닿컻諛쒕컦?꾩엯?쒕퉬??  - ?대씪?곕뱶?뚰봽?몄썾??  - ?쒖뒪?쒓?由ъ냼?꾪듃?⑥뼱
- Core technical strengths:
  - ?⑤뵒諛붿씠??AI
  - Device Farm
  - AI/SW ?먭꺽 寃利?  - 濡쒕큸/?곗뾽??AI
  - AI Agent
  - ?대씪?곕뱶 ?쒖뒪??
## Architecture rules

- Use FastAPI for the API layer.
- Keep domain logic independent from FastAPI.
- Keep G2B integration logic separate from scoring logic.
- Use fixtures first. Real API calls must be opt-in.
- Use Pydantic models for normalized data.
- Do not hardcode API keys.
- Do not commit `.env`.
- Keep changes small and testable.

## Testing rules

Baseline validation for every coding task:

```powershell
python -m pytest -q
```

Task-specific tests should be run only after those test files exist.

Examples:

```powershell
python -m pytest -q tests/test_app_health.py
```

For future scoring changes, after scoring tests are created:

```powershell
python -m pytest -q tests/test_yonlab_eligibility.py tests/test_score_engine.py
```

For future G2B integration changes, after G2B tests are created:

```powershell
python -m pytest -q tests/test_g2b_normalizer.py
```

Do not treat missing future test files as an application failure during Phase 1 initialization.

## Completion report

Every Codex task must end with:

1. Files changed
2. Behavior changed
3. Tests run
4. Test result
5. Known risks
6. Suggested next task

## Security rules

- Never print or expose API keys.
- Never commit `.env`.
- Use `.env.example` only.
- Real API tests require explicit confirmation.
