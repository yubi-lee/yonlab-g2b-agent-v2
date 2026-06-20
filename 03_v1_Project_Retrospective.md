# 03. 기존 프로젝트 v1 회고 요약

## 1. 문서 목적

이 문서는 기존 `YOnLab 나라장터 AI Agent 개발` v1 프로젝트에서 확인된 경험과 문제를 정리하여, 신규 `YOnLab G2B Agent v2`에서 같은 문제가 반복되지 않도록 하기 위한 회고 문서다.

v2는 기존 프로젝트를 대체하는 것이 아니라, **Agent-first 개발 방식 실험을 위한 별도 프로젝트**다.

---

## 2. 기존 프로젝트와 신규 프로젝트의 분리 원칙

| 구분 | v1 | v2 |
|---|---|---|
| 기존 경로 | `D:\Views\yonlab-bid-agent` | 사용 금지 |
| 신규 경로 | 해당 없음 | `D:\Views\yonlab-g2b-agent-v2` |
| 개발 방식 | 기존 Task 기반 누적 개발 | Agent-first / test-first / fixture-first |
| 목적 | 기존 방식 유지 및 계속 개발 | 새 방식 검증 |
| 코드 공유 | v1 내부 유지 | v1 코드 복사 금지 |
| 문서 활용 | 필요시 참조 | 요약 문서만 참조 |
| GitHub 저장소 | 기존 저장소 | 신규 저장소 권장: `yonlab-g2b-agent-v2` |

### 핵심 원칙

> v2는 v1의 코드를 복사하지 않고, v1에서 얻은 교훈만 반영한다.

---

## 3. v1에서 확인된 긍정적 성과

v1은 단순 실패 프로젝트가 아니다. 이미 다음과 같은 기반을 확보했다.

| 성과 | 설명 |
|---|---|
| 나라장터/G2B API 연동 방향성 확보 | 공공데이터포털 기반 조달 공고 수집 구조를 검토함 |
| YOnLab 맞춤 매칭 개념 정립 | 와이온랩의 AI/SW/Device Farm 역량을 공고 추천 기준으로 반영하기 시작함 |
| Fixture 기반 테스트 필요성 확인 | 실제 API보다 fixture 기반 개발이 안전하다는 점을 확인함 |
| 다수 테스트 축적 | 이후 기준점에서는 전체 pytest가 대량 통과하는 안정 상태도 확인됨 |
| API route 확장 경험 | `/g2b/*`, `/recommendations`, `/readiness` 등 다양한 API 방향성을 실험함 |
| 운영 문서화 필요성 확인 | 개발 절차, 환경 변수, PowerShell 실행법, GitHub 관리법을 문서화해야 함을 확인함 |

---

## 4. v1에서 확인된 주요 문제

### 4.1 작업 경로 혼선

가장 중요한 문제는 **동일 또는 유사 프로젝트가 여러 경로에 존재하면서 Codex 또는 작업 결과가 다른 경로에 반영된 사례**다.

확인된 예:

```text
기준 작업 경로:
D:\Views\yonlab-bid-agent

혼선 발생 경로:
C:\Users\joyke\OneDrive\문서\YOnLab 나라장터 AI Agent 개발\yonlab-bid-agent
```

이로 인해 다음 문제가 발생했다.

- 사용자가 확인한 로컬 경로에서는 변경 파일이 보이지 않음
- Codex가 수정했다고 보고했지만 실제 검토 경로와 달랐음
- `git status`, `git diff` 결과와 Codex 보고가 불일치
- 같은 문제를 반복 확인해야 했음

### v2 반영 원칙

- 모든 Codex 요청에 새 경로를 명시한다.
- 모든 작업 시작 전 `pwd`, `git status`, `git branch`를 확인한다.
- 기존 경로 `D:\Views\yonlab-bid-agent`는 수정 금지한다.
- OneDrive 하위 경로를 작업 경로로 사용하지 않는다.

---

### 4.2 작업 완료 조건이 자동화되지 않은 시기 발생

초기 작업에서는 다음과 같은 문제가 있었다.

- 테스트 폴더 또는 특정 테스트 파일이 없는데 테스트 실행을 지시함
- route 등록 여부를 수동 스크립트로 확인해야 했음
- 앱 import 구조와 CLI import side effect가 혼동됨
- 완료 판단이 “보고상 완료”에 의존한 경우가 있었음

### v2 반영 원칙

- 모든 기능은 테스트를 먼저 또는 동시에 만든다.
- `python -m pytest -q`가 항상 실행 가능한 상태를 유지한다.
- route 등록은 `tests/test_app_health.py`, `tests/test_api_routes.py` 등으로 검증한다.
- CLI import side effect에 의존하지 않는다.
- FastAPI route는 `app/main.py` 또는 명확한 `include_router` 구조에서 등록한다.

---

### 4.3 Agent 지시문이 대화에 흩어짐

v1에서는 중요한 규칙이 ChatGPT 대화에 축적되었지만, repo 내부 고정 문서로 충분히 정리되지 않은 시기가 있었다.

문제점:

- Codex가 매번 전체 맥락을 알지 못함
- 작업 요청문이 길어짐
- 완료 조건이 일관되지 않음
- 와이온랩 매칭 기준이 코드/문서/대화에 분산됨

### v2 반영 원칙

- repo 루트에 `AGENTS.md`를 가장 먼저 만든다.
- `docs/03_YONLAB_MATCHING_RULES.md`에 매칭 기준을 고정한다.
- `docs/02_AGENT_WORKFLOW.md`에 작업 방식과 완료 조건을 고정한다.
- Codex 요청문은 `Goal / Context / Constraints / Done when / Validation commands` 구조로 통일한다.

---

### 4.4 기능 확장과 품질 게이트의 순서 혼선

v1에서는 API, fixture, scoring, route, db, roadmap 등 여러 기능이 병렬적으로 확장되면서 특정 시점에는 제품 핵심 가치보다 주변 기능 정리에 시간이 쓰였다.

### v2 반영 원칙

v2는 다음 순서의 **수직 슬라이스**로 진행한다.

```text
샘플 공고 1개
→ 정규화
→ 와이온랩 적격성 판단
→ 점수화
→ 리스크 분석
→ 추천 리포트 생성
→ API로 호출
→ 테스트 통과
```

즉, 처음부터 전체 시스템을 만들지 않고, 작은 완성 제품을 먼저 만든다.

---

## 5. v2에서 반복 금지할 작업 방식

| 금지할 방식 | 이유 | 대체 방식 |
|---|---|---|
| “전체 기능을 한 번에 구현” 요청 | diff가 커지고 검증이 어려움 | 작은 vertical slice |
| 테스트 없이 기능 구현 | 완료 여부 불명확 | 테스트 포함 요청 |
| 실제 API부터 연동 | key, quota, 응답 불안정성 | fixture-first |
| 기존 코드 복사 | v1 구조 문제를 반복할 위험 | 새 구조로 재설계 |
| CLI import side effect 의존 | route 등록 혼선 | 명시적 app/router 구조 |
| 작업 경로 미확인 | 다른 폴더 수정 위험 | `pwd`, `git status` 확인 |
| `.env` 생성/공유 | 보안 리스크 | `.env.example`만 commit |
| 긴 대화 맥락에 의존 | Agent 재현성 낮음 | repo 문서 기준 |

---

## 6. v2의 필수 품질 게이트

모든 작업은 다음 조건을 만족해야 한다.

### 공통 완료 조건

```powershell
python -m pytest -q
```

- 전체 테스트 통과
- 변경 파일 명확
- `git diff` 확인 가능
- `.env`, API key, secret 미포함
- 신규 기능은 최소 1개 이상의 테스트 포함
- 문서 변경이 필요한 경우 docs 갱신

### Codex 완료 보고 필수 항목

```markdown
## Completion Report

### Files changed
- ...

### Behavior changed
- ...

### Tests run
```powershell
python -m pytest -q
```

### Test result
- Passed / Failed

### Known risks
- ...

### Suggested next task
- ...
```

---

## 7. v2 권장 프로젝트 구조

```text
D:\Views\yonlab-g2b-agent-v2
├─ AGENTS.md
├─ README.md
├─ .gitignore
├─ .env.example
├─ requirements.txt
├─ app
│  ├─ main.py
│  ├─ core
│  ├─ api
│  ├─ domain
│  ├─ integrations
│  │  └─ g2b
│  ├─ scoring
│  └─ reports
├─ tests
├─ data
│  └─ fixtures
│     └─ g2b
├─ docs
└─ scripts
```

---

## 8. v2에서 우선 구현할 최소 제품

v2의 1차 성공 기준은 다음이다.

> 샘플 공고 JSON 1개를 입력하면, 와이온랩 기준으로 적격성·점수·리스크·추천 리포트가 자동 생성된다.

이를 위해 첫 5개 기능만 구현한다.

| 순서 | 기능 | 산출물 |
|---:|---|---|
| 1 | FastAPI `/health` | 최소 앱 구동 |
| 2 | `BidNotice`, `YOnLabProfile` | 도메인 모델 |
| 3 | Eligibility 판정 | Pass/Fail 및 리스크 |
| 4 | Score Engine | 100점 기준 점수 |
| 5 | Markdown Report | 최종 추천 리포트 |

실제 G2B API는 이 이후에 붙인다.

---

## 9. v2 첫 번째 작업 요청 기준

v2 첫 작업은 반드시 초기 구조 생성이어야 한다.

```text
Task: Initialize YOnLab G2B Agent v2 repository
```

첫 작업의 완료 기준은 다음으로 고정한다.

- `AGENTS.md` 존재
- `.env.example` 존재
- `.gitignore` 존재
- `app/main.py` 존재
- `/health` API 존재
- `tests/test_app_health.py` 존재
- `python -m pytest -q` 통과
- 기존 `D:\Views\yonlab-bid-agent` 수정 없음

---

## 10. 회고 결론

v1은 방향성을 찾는 데 의미가 있었다.  
v2는 같은 기능을 더 빠르게 만들기 위한 프로젝트가 아니라, **AI Agent가 반복적으로 안정적인 결과를 내는 개발 시스템을 검증하는 프로젝트**다.

v2의 성공 여부는 기능 수가 아니라 다음으로 판단한다.

- Codex가 같은 규칙을 반복 적용하는가
- 테스트가 항상 동작하는가
- 작업 경로 혼선이 없는가
- 작은 기능이 빠르게 완성되는가
- 와이온랩 매칭 기준이 코드에 안정적으로 반영되는가
- 실제 API 없이도 핵심 추천 파이프라인을 검증할 수 있는가
