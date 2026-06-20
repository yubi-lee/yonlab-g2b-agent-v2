# 04. Agent-first 개발 방법론

## 1. 문서 목적

이 문서는 `YOnLab G2B Agent v2`를 개발할 때 사용할 **Agent-first 개발 규칙**을 정의한다.

목표는 단순히 AI에게 코드를 많이 맡기는 것이 아니다.  
목표는 AI Agent가 다음을 반복적으로 수행할 수 있는 개발 시스템을 만드는 것이다.

```text
이해
→ 계획
→ 구현
→ 테스트
→ 자체 수정
→ 결과 보고
→ 사람의 승인
```

---

## 2. Agent-first 개발의 핵심 정의

Agent-first 개발은 다음 조건을 만족해야 한다.

| 조건 | 설명 |
|---|---|
| repo 기반 기억 | 중요한 규칙은 대화가 아니라 repo 문서에 둔다 |
| 작은 작업 단위 | 한 번에 하나의 기능 또는 하나의 vertical slice만 구현한다 |
| 테스트 우선 | 기능 구현과 테스트를 항상 함께 요구한다 |
| fixture-first | 실제 외부 API보다 샘플 데이터로 먼저 검증한다 |
| 완료 조건 명확화 | “잘 됨”이 아니라 검증 명령 통과로 판단한다 |
| 보안 분리 | `.env`, API key, secret은 절대 commit하지 않는다 |
| 결과 보고 표준화 | 변경 파일, 테스트 결과, 리스크를 항상 보고한다 |

---

## 3. 역할 분담

| 역할 | 담당 |
|---|---|
| 사용자 / 대표 | 제품 방향, 와이온랩 전략 기준, 최종 승인 |
| ChatGPT | 개발 PM, 아키텍처 설계, Codex 요청문 작성, 리뷰 |
| Codex | 코드 구현, 테스트 작성, 실패 수정, 변경 보고 |
| pytest | 품질 게이트 |
| Git | 변경 이력 관리 |
| 문서 | Agent의 장기 기억 |
| Fixture | 외부 API 없이 개발 가능한 테스트 데이터 |

---

## 4. 기본 개발 루프

모든 작업은 다음 루프를 따른다.

```text
1. 작업 목표 정의
2. 관련 문서 확인
3. Codex 요청문 작성
4. Codex가 파일 확인 후 최소 수정
5. 테스트 실행
6. 실패 시 Codex가 자체 수정
7. Completion Report 작성
8. 사용자가 git diff와 테스트 결과 확인
9. commit
```

---

## 5. 작업 요청문 표준 구조

모든 Codex 요청은 아래 구조를 따른다.

```markdown
## Task: [작업명]

### Goal
[이번 작업의 최종 목표]

### Context
[관련 파일, 현재 상태, 참고 문서, 기존 제약]

### Required work
[생성 또는 수정할 파일과 기능]

### Constraints
- Do not modify `D:\Views\yonlab-bid-agent`.
- Work only in `D:\Views\yonlab-g2b-agent-v2`.
- Do not call real G2B APIs unless explicitly required.
- Do not create or commit `.env`.
- Do not print or expose API keys.
- Keep the diff small and reviewable.
- Add or update tests.
- Preserve existing passing tests.

### Done when
- [ ] Required files are created or updated.
- [ ] The intended behavior works.
- [ ] Tests are added or updated.
- [ ] `python -m pytest -q` passes.
- [ ] Completion Report is provided.

### Validation commands
```powershell
python -m pytest -q
git status
git diff --stat
```
```

---

## 6. 작업 단위 설계 원칙

### 좋은 작업 단위

- `/health` API와 테스트 생성
- `BidNotice` 모델 생성
- YOnLab eligibility 판정 함수 생성
- score engine 1차 구현
- markdown report generator 구현
- fixture 3개 추가와 normalizer 테스트 작성

### 나쁜 작업 단위

- “전체 나라장터 Agent 완성”
- “API, DB, UI, scoring 모두 구현”
- “실제 API 붙이고 추천까지 완성”
- “기존 프로젝트 참고해서 알아서 개선”

---

## 7. 수직 슬라이스 우선 원칙

v2는 수직 슬라이스 방식으로 개발한다.

```text
샘플 공고 입력
→ 정규화
→ 적격성 판단
→ 점수화
→ 리스크 분석
→ 리포트 생성
→ API 응답
→ 테스트 통과
```

초기에는 DB, UI, 스케줄러, 로그인, 운영 관리 기능을 만들지 않는다.  
먼저 하나의 공고가 끝까지 처리되는 흐름을 완성한다.

---

## 8. Fixture-first 원칙

실제 나라장터 API는 다음 문제가 있다.

- API key 필요
- 호출 제한 가능성
- 응답 필드 변경 가능성
- 네트워크 오류 가능성
- 개발 중 불필요한 실 API 호출 위험

따라서 개발 순서는 다음으로 고정한다.

```text
1. 수동 작성 fixture
2. normalizer 테스트
3. scoring 테스트
4. report 테스트
5. API wrapper
6. controlled smoke test
7. real API 연동
```

---

## 9. Real API 사용 규칙

기본값은 항상 다음이어야 한다.

```env
G2B_ENABLE_REAL_API=false
```

실제 API 호출은 별도 명령과 명시적 확인 플래그가 있을 때만 허용한다.

예:

```powershell
python scripts\smoke_real_api.py --confirm-real-api-call
```

금지 사항:

- 테스트 중 자동으로 실제 API 호출
- API key를 로그에 출력
- `.env` 파일 commit
- 실패한 실제 API 응답을 무분별하게 repo에 저장
- 개인정보 또는 민감정보 포함 응답 저장

---

## 10. Git 운영 규칙

### 작업 전

```powershell
Set-Location D:\Views\yonlab-g2b-agent-v2
.\.venv\Scripts\Activate.ps1
git status
python -m pytest -q
```

### 작업 후

```powershell
python -m pytest -q
git diff --stat
git diff
git status
```

### commit 기준

다음 조건을 모두 만족해야 commit한다.

- 전체 테스트 통과
- 의도한 파일만 변경
- `.env` 미포함
- 불필요한 임시 파일 미포함
- 문서 또는 테스트 갱신 완료

예:

```powershell
git add .
git commit -m "Add YOnLab eligibility baseline"
```

---

## 11. 브랜치 전략

초기에는 단순하게 운영한다.

| 작업 유형 | 브랜치 예시 |
|---|---|
| 초기화 | `task/init-project` |
| 도메인 모델 | `task/domain-models` |
| scoring | `task/scoring-engine` |
| report | `task/report-generator` |
| G2B fixture | `task/g2b-fixtures` |
| real API smoke | `task/real-api-smoke` |

브랜치 사용이 부담되면 `main`에서 진행하되, 작업 전후 `git status`와 `git diff`를 반드시 확인한다.

---

## 12. 테스트 전략

### 테스트 종류

| 테스트 | 목적 |
|---|---|
| `test_app_health.py` | 앱 기본 구동 |
| `test_g2b_normalizer.py` | 외부 API 응답 정규화 |
| `test_yonlab_eligibility.py` | 와이온랩 적격성 판단 |
| `test_score_engine.py` | 추천 점수 계산 |
| `test_risk_analyzer.py` | 리스크 감지 |
| `test_markdown_report.py` | 최종 리포트 출력 |
| `test_api_contract.py` | API 응답 형식 고정 |

### 최소 기준

```powershell
python -m pytest -q
```

이 명령은 항상 실행 가능해야 한다.

---

## 13. 완료 보고 표준

Codex는 모든 작업 완료 후 아래 형식으로 보고해야 한다.

```markdown
## Completion Report

### Files changed
- `app/...`
- `tests/...`
- `docs/...`

### Behavior changed
- ...

### Tests run
```powershell
python -m pytest -q
```

### Test result
- Passed

### Known risks
- ...

### Suggested next task
- ...
```

---

## 14. 개발 단계별 우선순위

### Phase 0 — 초기화

- `AGENTS.md`
- README
- `.gitignore`
- `.env.example`
- FastAPI `/health`
- pytest baseline

### Phase 1 — 도메인 모델

- `BidNotice`
- `YOnLabProfile`
- `EligibilityResult`
- `RiskItem`
- `RecommendationScore`

### Phase 2 — 와이온랩 판정

- SW사업자 조건
- 소기업/소상공인 조건
- 창업기업 조건
- 지역 제한
- 실적 제한
- 직접생산확인 필요 여부

### Phase 3 — 점수 엔진

- 100점 기준 scoring
- 리스크 감점
- 추천 등급
- 사유와 리스크 목록 반환

### Phase 4 — 리포트 생성

- Markdown report
- 제출 서류 체크리스트
- 입찰 준비 전략
- 권장 대응

### Phase 5 — G2B 연동

- fixture loader
- normalizer
- controlled real API smoke
- API 응답 보정

### Phase 6 — 운영 기능

- 저장소
- 검색 이력
- 스케줄러
- 알림
- UI

---

## 15. v2 첫 번째 Codex 요청문

```markdown
## Task: Initialize YOnLab G2B Agent v2 repository

### Goal
Create the initial project skeleton for a new independent Agent-first YOnLab G2B bid recommendation application.

### Context
This project is independent from the existing v1 repository.

- Existing repository: `D:\Views\yonlab-bid-agent`
- New repository: `D:\Views\yonlab-g2b-agent-v2`

Do not modify or depend on the existing repository.

### Required work
Create:

- `AGENTS.md`
- `README.md`
- `.gitignore`
- `.env.example`
- `app/main.py`
- `app/core/config.py`
- `app/api/routes.py`
- `tests/test_app_health.py`
- `docs/00_PROJECT_CHARTER.md`
- `docs/01_ARCHITECTURE.md`
- `docs/02_AGENT_WORKFLOW.md`
- `docs/03_YONLAB_MATCHING_RULES.md`
- `scripts/dev_start.ps1`
- `scripts/run_tests.ps1`

Create a minimal FastAPI app with:

- `GET /health`

Expected response:

```json
{
  "status": "ok",
  "app": "YOnLab G2B Agent v2"
}
```

### Constraints
- Work only in `D:\Views\yonlab-g2b-agent-v2`.
- Do not modify `D:\Views\yonlab-bid-agent`.
- Do not call real APIs.
- Do not create `.env`.
- Do not include secrets.
- Keep the implementation minimal.
- Add tests.

### Done when
- `python -m pytest -q` passes.
- `/health` returns the expected response.
- Completion Report is provided.

### Validation commands
```powershell
python -m pytest -q
git status
git diff --stat
```
```

---

## 16. 판단 기준

Agent-first 개발이 제대로 되고 있는지는 다음으로 판단한다.

| 질문 | 합격 기준 |
|---|---|
| Codex가 매번 같은 규칙을 따르는가 | `AGENTS.md`와 docs 기준으로 작업 |
| 사람이 로그를 덜 해석하는가 | Completion Report 제공 |
| 변경 범위가 작은가 | task별 diff가 명확 |
| 테스트가 자동으로 증명하는가 | pytest 통과 |
| 실제 API 없이 개발 가능한가 | fixture 기반 테스트 |
| 와이온랩 기준이 코드에 반영되는가 | eligibility/scoring 테스트 존재 |
| 기존 v1과 충돌하지 않는가 | 경로 분리와 git 확인 |

---

## 17. 결론

v2 개발의 핵심은 “더 많은 기능을 더 빨리”가 아니라, **AI Agent가 안정적으로 반복 작업을 수행할 수 있는 개발 운영체계**를 만드는 것이다.

따라서 첫 1~2일은 기능보다 다음에 집중한다.

- 프로젝트 구조
- `AGENTS.md`
- 테스트 기준
- 문서 기준
- 작업 요청문 표준
- fixture-first 개발 흐름

이 기반이 완성되면 이후 기능 개발 속도가 빨라진다.
