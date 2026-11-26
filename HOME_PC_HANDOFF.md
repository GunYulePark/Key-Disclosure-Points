# 집 PC에서 개발 이어가기

확인일 2026-11-26. 집 PC는 GitHub의 개발 브랜치와 서울의 같은 Supabase 개발 프로젝트를 사용한다. 회사 PC를 켜 둘 필요는 없다. 변경한 코드는 개발 브랜치에 commit/push한다. 각 PC의 로컬 설정과 원본 캐시는 별도로 관리한다.

## 현재 공유되는 범위

| 항목 | 집 PC에서의 상태 |
|---|---|
| 코드·요구사항·진행 기록·검토 결과·테스트·연구 메타데이터 | Git clone으로 확보 가능 |
| 최신 사례 결과 | `CASE_REVIEW_02.md`, `research/priority-case-pack-v2.json`, `research/case-followup-facts.json` |
| 조사 원본 76개, 27,024,097 bytes | 회사 PC 캐시에 76개 보관. 집 PC에서 Supabase로부터 법령 HTML 2개 복원 가능. 나머지 74개는 보관 근거 확인 중 |
| Supabase 중앙 DB·private 원본 Storage | 전용 Free DB와 비공개 버킷 생성 완료. 회사 PC에서 실제 viewer 로그인으로 법령 원본 2개 복원 확인. 집 PC의 실제 로그인·복원 검증 예정 |
| 환경변수·인증·API 키·브라우저 개인 업로드 | Git으로 공유하지 않음. 집 PC에서 필요한 연결을 별도 설정 |
| 저장소 밖 legacy/private Sites 소스·로컬 데이터 | 이 저장소의 clone에 포함되지 않음 |

집에서도 코드 수정·메타데이터 검증·로컬 테스트는 가능하다. 원본 byte/본문/페이지를 다시 대조하려면 승인된 경로로 동일 원본을 확보해야 한다. 원본이 없을 때 `--cache` 검증 성공이나 전체 환경 재현 완료로 보고하지 않는다.

## 집 PC 시작 순서

1. Git, Node 24.x, Python 3.12.x와 Codex를 준비한다. 실제 설치·연결 여부는 집 PC에서 확인한다.
2. 새 작업 폴더에서 아래 명령으로 개발 브랜치를 받는다. 이미 clone한 폴더라면 새로 덮어쓰지 말고 `git status --short`로 미커밋 작업을 확인한 뒤 해당 브랜치에서 `git pull --ff-only`한다.

```powershell
git clone --branch codex/task-00-cloud-foundation https://github.com/GunYulePark/Key-Disclosure-Points.git
cd Key-Disclosure-Points
git branch --show-current
git log -1 --oneline
```

3. 이 폴더를 Codex 작업 폴더로 열고 다음 문구로 시작한다. 의존성 설치·검증 명령은 `OPERATIONS.md`에 있다. 기존 개발 기준 커밋은 `1993b69`이며, 인수인계 문서 후속 커밋은 `git log`로 확인한다.

> HOME_PC_HANDOFF.md와 AGENTS.md를 읽고 PROJECT_REQUIREMENTS.md 전체, ROADMAP.md, DEVELOPMENT_STATUS.md, NEXT_TASK.md, CASE_REVIEW_02.md를 확인해서 이어서 진행해줘. 현재 개발 브랜치는 codex/task-00-cloud-foundation이다. 이 PC에 원본이 있는지 먼저 확인하고, 없으면 원본 검증을 완료한 것으로 표시하지 마. 중앙 개발 DB와 비공개 버킷을 구축했다. Auth·원본 이전 검증이 남아 있다. NEXT_TASK.md와 승인 경로의 개발 대상 정보를 확인하고 Storage/Auth 검증을 이어가라. 기존 데이터와 기능을 유지하고, 운영 변경·배포·유료 전환·승인되지 않은 클라우드 쓰기는 하지 마. 작업 결과와 다음 작업을 MD에 기록하고 개발 브랜치에만 저장해줘.

## 회사와 집 사이를 오갈 때

- 시작: `git status --short` → 현재 브랜치 확인 → 작업 폴더가 깨끗할 때 `git pull --ff-only` → 상태·다음 작업 문서 읽기.
- 종료: 필요한 검증 → 진행/다음 작업 MD 갱신 → 비밀정보·원본 제외 확인 → 선택 stage → 개발 브랜치 commit/push → push 성공 확인. main push/merge는 배포하므로 하지 않는다.
- 한 PC의 미커밋·미push 변경은 다른 PC에 없으며, 두 PC에서 동시에 같은 부분을 수정하면 충돌을 정리해야 한다. 클라우드 동기화 폴더에 저장소 전체를 복제하는 방식 대신 Git으로 코드를 교환한다.

## 중앙 공유 구축의 다음 단계

최신 상태(2026-11-26): 추가 연결 계정에서 사용자 지정 Free 조직의 서울 전용 개발 DB/core를 생성·검증했다. 비공개 버킷을 생성하고 크기 및 MIME 제한을 확인했다. `supabase/README.md`에 실제 migration 이력·검증·다음 절차가 있다. ignored 승인 ref/workspace와 credential은 clone으로 공유되지 않으므로 승인 경로로 집 PC에 별도 구성한다. 같은 이름의 프로젝트를 새로 생성하거나 다른 업무 프로젝트를 변경하지 않는다.

### 집 PC에서 개발 DB 연결 확인

1. Supabase 대시보드에서 기존 `key-disclosure-points-dev`를 열어 Project URL과 publishable key를 확인한다. 대시보드에서 같은 DB의 테이블을 조회할 수 있다. 앱 수준 조회에는 개발 프로젝트에서 만든 Auth 계정을 사용한다. 해당 계정의 workspace 역할은 `viewer`다.
2. 회사 PC의 `.local/task01/approved-target.json`을 승인된 경로로 집 PC의 같은 위치에 복사한다. 이 파일에는 대상 식별자만 들어 있다. 파일을 복사할 수 없으면 프로젝트 관리자에게 승인된 ref와 workspace UUID를 받아 `supabase/README.md`의 형식으로 작성한다.
3. 집 PC의 PowerShell에서 아래 명령을 실행한다. 표시된 placeholder에는 개발 프로젝트의 publishable key를 넣고, 로그인 프롬프트에는 프로젝트 Auth 사용자가 직접 입력한다.

```powershell
$kdpTarget = Get-Content -Raw .local/task01/approved-target.json | ConvertFrom-Json
$env:APP_ENV = 'development'
$env:CENTRAL_STORE_MODE = 'supabase'
$env:SUPABASE_DEV_PROJECT_REF = $kdpTarget.project_ref
$env:SUPABASE_DEV_URL = 'https://' + $kdpTarget.project_ref + '.supabase.co'
$env:SUPABASE_DEV_WORKSPACE_ID = $kdpTarget.workspace_id
$env:SUPABASE_DEV_PUBLISHABLE_KEY = '<development-publishable-key>'
.\.venv\Scripts\python.exe scripts/central_sync.py check --target .local/task01/approved-target.json --password-login
```

`workspace_visible: true`와 자신의 `member_role`이 출력되면 집 PC의 프로젝트 Auth 세션으로 승인된 workspace를 읽은 것이다. 아래 명령을 같은 PowerShell에서 실행하면 이미 이관한 두 원본을 내려받으며, 해시·길이·인용 위치를 대조한다.

```powershell
.\.venv\Scripts\python.exe scripts/central_sync.py restore --target .local/task01/approved-target.json --cache .local/case-research/originals --password-login --source commercial-amendments --source commercial-decree-33
.\.venv\Scripts\python.exe scripts/case_pack.py --pack research/priority-case-pack-v2.json --cache .local/case-research/originals --anchor commercial-decree-33:1
```

처음 복원하면 `restored: 2`, 이미 같은 파일이 캐시에 있으면 `cached_verified`로 기록된다. 좌표 조회는 이관된 원문 버전·SHA-256·정규화한 문자 범위를 출력한다.

복원한 원본은 [원문 검토 로컬 미리보기](EVIDENCE_VIEWER.md)에서 바로 열 수 있다. 로컬 미리보기 서버는 캐시를 읽으므로 두 파일을 Supabase에서 받은 뒤 시작한다. 원격 복원 여부를 별도로 증명하려면 새로운 빈 캐시 폴더로 두 파일을 받거나, `verify_original_restore.py`에서 임시 빈 폴더를 사용하는 인증 검사를 실행한다.

화면에서 원본을 읽기만 할 때는 위와 같은 개발 환경변수로 [Supabase 원본 모드](EVIDENCE_VIEWER.md#supabase-원본-직접-열기)를 실행하면 된다. Auth 로그인 후 필요한 원본을 서버에서 직접 읽는다. 집 PC의 직접 읽기와 빈 폴더 복원은 각각 확인한다.

2026-11-27 회사 PC에서는 임시 검사로 원본 2개·679,729바이트, 인용 4개, 공개 접근 거부 2개를 확인했다. 임시 검사 서버는 성공 결과를 저장하면 종료한다. 주소가 이후 열리지 않아도 `.local/task01/viewer-restore-check.json`에서 검증 결과를 확인할 수 있다. 이 결과는 집 PC에서의 검증과 별개다.

목표는 GitHub에 코드·개발 기록, 승인된 독립 Supabase 개발 DB에 구조화 데이터, private Storage에 승인된 원본을 두는 것이다. 기존 계정의 active 프로젝트 2개는 다른 업무용이므로 임의로 재사용·중지·삭제하거나 유료 전환하지 않는다. TASK 01의 승인된 개발 ref를 확인하고 private bucket/Auth·샘플 이관 범위와 권리를 검증한다. 약 27MB 연구 원본 전체 업로드는 기존 3.06MB 샘플 이관과 다른 범위다.

## 회사 PC를 끄는 것과 자동 실행

공개 GitHub Pages는 회사 PC와 별도로 서비스된다. 저장소에는 GitHub Actions의 평일 오전 8시(한국시간) 일정이 설정돼 있다. 실제 실행/성공 여부는 Actions 기록과 Secret 상태로 확인하며, 스케줄 정의만으로 AI 분석 성공을 보장하지 않는다. 로컬 Codex 작업·미push 파일은 회사 PC를 끄면 집 PC로 자동 이어지지 않는다. 원격 접속을 위해 회사 PC를 켜 두는 방식을 전제로 하지 않는다.
