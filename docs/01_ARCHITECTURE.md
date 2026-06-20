# 01_ARCHITECTURE ??Initial Architecture

## Layering

```text
API layer       FastAPI routes
Core layer      configuration, logging
Domain layer    procurement notice and recommendation models
Integration     G2B client, fixture loader, normalizer
Scoring layer   eligibility, risk, and score engine
Report layer    deterministic Korean markdown report
```

## Current implementation

Only the API and core configuration baseline are implemented.

```text
GET /health
```

## Rule

Domain and scoring logic must not depend on FastAPI.
