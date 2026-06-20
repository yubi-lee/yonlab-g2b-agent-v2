# YOnLab G2B Agent v2 — 현재 상태 복구/초기화 명령

## 1) 현재 폴더로 이동

```powershell
Set-Location D:\Views\yonlab-g2b-agent-v2
.\.venv\Scripts\Activate.ps1
```

## 2) setup script 실행

다운로드한 `setup_yonlab_g2b_agent_v2.ps1`을 프로젝트 루트로 복사한 뒤 실행합니다.

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\setup_yonlab_g2b_agent_v2.ps1
```

## 3) 생성 확인

```powershell
.\scripts\check_initial_setup.ps1
```

## 4) 테스트 실행

```powershell
python -m pytest -q
```

정상 결과:

```text
1 passed
```

## 5) 서버 실행

```powershell
.\scripts\dev_start.ps1
```

브라우저에서 확인:

```text
http://127.0.0.1:8000/health
```
