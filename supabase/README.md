# TASK 01 중앙 개발 기반

2026-11-24 현재 **원격 프로젝트/DB/bucket 미생성**. 사용자가 중앙 DB·비공개 저장소 구축과 연결된 TEST 조직의 전용 Free 개발 프로젝트 생성을 승인했다. 신규 생성 비용 조회는 월 $0이었으나 `create_project`가 active Free 프로젝트 2개 한도로 거절됐다. 기존 다른 업무 프로젝트는 변경하지 않았다. 대상 개발 환경 확보 방식에 대한 사용자 답변이 다음 작업이다. 추가 조직만 만들면 계정 한도가 초기화된다고 가정하지 않는다.

## 구현 범위

- CLI 3.3.0의 `migration new kdp_central_core`로 생성한 core migration: workspaces/members, sources, documents/versions/files, evidence, legacy map, ingestion jobs의 9개 테이블.
- workspace 복합 FK·인덱스, RLS/명시 GRANT, 관리자만 membership/승인 변경, 원본 identity 불변, revision 증가·조건 갱신, 미검증 원본·근거의 ready 전환 차단.
- 비공개 Storage SELECT/INSERT 정책. 검증된 파일만 읽고, 승인된 사전 등록 경로만 editor가 업로드할 수 있다. 사용자 UPDATE/DELETE/upsert는 허용하지 않는다. 버킷은 SQL insert 대신 Storage API로 생성한다.
- `central_sync.py`: 기본 offline plan, 승인된 전용 개발 target 검사, 비공개 bucket 확인/명시 생성, 인증된 reader로 DB manifest와 원본 hash/길이·인용 위치를 대조한 복원. 업로드·DB seed/import·Auth membership bootstrap은 아직 구현/실행하지 않았다.
- metadata는 authenticated workspace member의 읽기만 허용한다. 초기 수집/승인 쓰기는 서버 전용이다. 화면 편집·API·회원 가입/로그인 흐름은 이번 core에 포함되지 않는다.

## 재현 가능한 로컬 검증

기존 `requirements.txt` 설치 후 저장소 루트에서 실행한다. PGlite는 별도 ignored 디렉터리에만 설치하며 기존 앱의 dependency/lockfile을 변경하지 않는다.

```powershell
npm.cmd install --prefix .local/task01/sql-check --no-audit --no-fund --save-exact @electric-sql/pglite@0.6.0
node scripts/check_central_schema.mjs
.venv/Scripts/python.exe -m unittest discover -s tests -v

# offline 계획용 fixture UUID. 실제 개발 workspace ID가 아니다.
.venv/Scripts/python.exe scripts/central_sync.py plan --workspace 00000000-0000-4000-8000-000000000000
# 회사 PC에 76개 원본이 있을 때만 실제 byte/인용 위치도 확인:
.venv/Scripts/python.exe scripts/central_sync.py plan --workspace 00000000-0000-4000-8000-000000000000 --cache .local/case-research/originals
```

PGlite는 WASM PostgreSQL 엔진이며 Auth UID/Storage 테이블은 합성 fixture다. SQL/RLS 검사는 실제 PostgreSQL에서 실행하지만 hosted Supabase Auth·Storage HTTP/advisors·두 PC 검증을 대신하지 않는다. CLI `migration list`는 기본 local target `127.0.0.1:54322` 연결을 시도했으나 로컬 stack 미기동으로 실패했다. Docker stack이나 원격 migration history 조회 성공으로 표시하지 않는다. CLI로 생성한 migration 파일은 후보이며 hosted 적용 전 실제 빈 개발 프로젝트에서 다시 검증한다.

## 개발 환경이 확보된 뒤

1. 실제 project ref·용도·Free 비용·health를 확인하고 기존 테이블/권한을 읽기 전용 검사한다. 다른 업무/운영 프로젝트에 적용하지 않는다. 원격 migration은 MCP `apply_migration`으로 기록하고 로컬 파일과 SQL을 일치시킨다.
2. 실제 개발 Auth 사용자와 workspace를 bootstrap한다. 가짜 Auth 사용자를 운영 계정으로 추가하지 않는다. workspace_members는 trusted administrator만 등록한다.
3. `.local/task01/approved-target.json`에 다음 구조로 **실제 승인된 개발 ref와 workspace UUID**를 기록한다. 비밀 키는 넣지 않는다. 아래 표시는 복사해 실행 가능한 target이 아니다.

```json
{
  "purpose": "kdp-development",
  "project_ref": "<approved-development-ref>",
  "workspace_id": "<actual-workspace-uuid>",
  "approved": true
}
```

4. 각 PC의 환경변수에 `.env.example`의 APP_ENV, CENTRAL_STORE_MODE, 개발 URL/ref/workspace를 설정한다. 실제 연결 시에만 `CENTRAL_STORE_MODE=supabase`로 변경한다. `central_sync.py`는 `.env`를 자동 로드하지 않는다. reader는 publishable key와 Auth access JWT, bucket 관리는 server secret을 사용한다. 키/토큰은 Git/채팅/Pages에 넣지 않는다. 만료된 JWT는 다시 인증해 갱신한다.

```powershell
# 기본값은 기존 비공개 bucket 검사만 한다.
.venv/Scripts/python.exe scripts/central_sync.py bucket --target .local/task01/approved-target.json
# 승인된 개발 환경에서만 신규 private bucket 생성:
.venv/Scripts/python.exe scripts/central_sync.py bucket --target .local/task01/approved-target.json --apply
# 서버 이관·검증 DB 기록이 만들어진 뒤 집 PC 복원:
.venv/Scripts/python.exe scripts/central_sync.py restore --target .local/task01/approved-target.json --cache .local/case-research/originals
```

5. 출처별 보관 권리와 승인 범위를 확인한 샘플로 staging → upload(upsert=false) → 별도 실행에서 다운로드/hash → evidence → ready를 검증한다. HTTP에서 누락 버킷의 상태 코드가 fixture와 다르면 실제 응답/공식 API를 확인하고 수정한다. 400 오류를 일괄 '없음'으로 취급하지 않는다.
6. ingestion adapter/멱등 seed, 실패 재개, 원본·metadata의 독립 백업/복원, 실제 Auth·다른 workspace·anon 접근 거부, advisors를 확인한다. 회사와 두 번째 깨끗한 환경의 byte hash·버전을 대조하고 실제 집 PC 검증을 별도로 기록한다.

정적 Pages, 운영 Actions, 기존 D1/브라우저 업로드는 아직 중앙 저장소로 전환하지 않는다. 원격 프로젝트 확보만으로 TASK 01 완료가 아니다.
