# TASK 01 중앙 개발 기반

2026-11-26 추가 연결 계정의 사용자 지정 Free 조직에 서울 `key-disclosure-points-dev`를 월 $0으로 생성했다. 전용 개발 DB/core 9개 테이블·RLS·Storage SELECT/INSERT 정책·workspace 1개와 FK 인덱스 적용/검증 완료. 실제 ref/UUID는 공개 문서에 기록하지 않고 ignored `.local/task01/approved-target.json`, `cloud-state.json`에만 보관한다. 기존 계정의 11월 24일 생성 한도 실패는 과거 기록이다.

Supabase 대시보드에서 비공개 `kdp-dev-originals`를 만들었다. 원격 SQL로 `public=false`, 10MiB 제한, 허용 MIME `application/pdf`, `text/html`, `application/x-hwp`, `image/jpeg`와 인증 사용자용 SELECT/INSERT 정책을 확인했다. 익명 Storage 버킷 메타데이터 요청은 HTTP 400 `Bucket not found`를 반환했다. 원본과 프로젝트 Auth 사용자·membership은 각각 0개다.

## 원격 적용 및 검증 이력

| 로컬 CLI 생성 파일 | Hosted version / 이름 | SQL SHA-256 |
|---|---|---|
| `20261124080839_kdp_central_core.sql` | `20261126042013 kdp_central_core` | `589472a414ba912c788fb80ea1ef9b19337cbcd7b6dea313b5400cc06260b388` |
| `20261126042319_kdp_file_identity_index.sql` | `20261126042450 kdp_file_identity_index` | `8151942f15c6e8bbb8e21101ea9c2efc965ba885baf4a763956c12ad3c6473e3` |

MCP `apply_migration`은 적용 시각으로 이력을 생성하므로 로컬 파일명과 다르다. 같은 SQL을 `db push`로 중복 적용하지 않는다. CLI 연결 전 migration history 대응을 확인하고 필요 시 `migration repair --help`와 실제 history를 검토한다. 현재 적용 SQL은 로컬 SHA와 같다. core 파일의 NOT applied 주석은 생성 당시 기록이며 hash 보존을 위해 바꾸지 않았다.

`scripts/check_hosted_central.sql`은 **승인된 전용 개발 project에서만** MCP `execute_sql`로 실행한다. 실제 PostgreSQL의 15개 권한/FK/불변/revision/ready 검사를 수행하며 가상 Auth 사용자·metadata는 전부 transaction rollback한다. Storage 테이블/객체를 쓰지 않으며 실제 로그인/Storage HTTP/hash 성공을 주장하지 않는다. 실행 뒤 Auth 사용자 0·workspace 1·문서/객체 0 확인. 익명 publishable key REST 조회는 실제 HTTP 401/42501로 거부됐다.

advisors: security/health 0, performance FK 누락 1건은 전체 복합 인덱스로 보완. 남은 unused_index INFO 4건은 신규 DB 사용 실적이 없어 삭제하지 않았다. [미사용 인덱스 안내](https://supabase.com/docs/guides/database/database-linter?lint=0005_unused_index). DB 약 12MB, 업로드 0건. 초기 empty project 확인이 이관 전 baseline이며 DB/Storage backup·restore 실증은 별도 미완료다. 되돌릴 때는 개발 쓰기를 중단하고 로컬 원본을 보존한다. 프로젝트/테이블 삭제는 별도 승인 없이 하지 않는다.

## 구현 범위

- CLI 3.3.0의 `migration new kdp_central_core`로 생성한 core migration: workspaces/members, sources, documents/versions/files, evidence, legacy map, ingestion jobs의 9개 테이블.
- workspace 복합 FK·인덱스, RLS/명시 GRANT, 관리자만 membership/승인 변경, 원본 identity 불변, revision 증가·조건 갱신, 미검증 원본·근거의 ready 전환 차단.
- 비공개 Storage SELECT/INSERT 정책. 검증된 파일만 읽고, 승인된 사전 등록 경로만 editor가 업로드할 수 있다. 사용자 UPDATE/DELETE/upsert는 허용하지 않는다. 버킷은 SQL insert 대신 Storage API로 생성한다.
- `central_sync.py`: 기본 offline plan, 승인된 전용 개발 target 검사, 비공개 bucket 확인/명시 생성, 인증된 reader로 DB manifest와 원본 hash/길이·인용 위치를 대조한 복원. 개발 workspace bootstrap만 수행했다. 업로드·자료 DB seed/import·Auth membership bootstrap은 아직 구현/실행하지 않았다.
- metadata는 authenticated workspace member의 읽기만 허용한다. 초기 수집/승인 쓰기는 서버 전용이다. 화면 편집·API·회원 가입/로그인 흐름은 이번 core에 포함되지 않는다.

## 재현 가능한 로컬 검증

기존 `requirements.txt` 설치 후 저장소 루트에서 실행한다. PGlite는 별도 ignored 디렉터리에만 설치하며 기존 앱의 dependency/lockfile을 변경하지 않는다.

이번 PC는 Python 3.13의 격리 `.venv`에 기존 pinned requirements를 설치해 Python 63개 통과했다. `check_central_schema.mjs`는 migration 전체와 hosted 검사 SQL의 rollback 동작을 포함해 26개 통과했다. 아래 PGlite Auth/Storage는 fixture이며 실제 hosted SQL/REST 결과는 위 별도 기록을 따른다.

```powershell
npm.cmd install --prefix .local/task01/sql-check --no-audit --no-fund --save-exact @electric-sql/pglite@0.6.0
node scripts/check_central_schema.mjs
.venv/Scripts/python.exe -m unittest discover -s tests -v

# offline 계획용 fixture UUID. 실제 개발 workspace ID가 아니다.
.venv/Scripts/python.exe scripts/central_sync.py plan --workspace 00000000-0000-4000-8000-000000000000
# 회사 PC에 76개 원본이 있을 때만 실제 byte/인용 위치도 확인:
.venv/Scripts/python.exe scripts/central_sync.py plan --workspace 00000000-0000-4000-8000-000000000000 --cache .local/case-research/originals
```

PGlite는 WASM PostgreSQL 엔진이며 Auth UID/Storage 테이블은 합성 fixture다. SQL/RLS 검사는 실제 PostgreSQL에서 실행하지만 hosted Supabase Auth·Storage HTTP/advisors·두 PC 검증을 대신하지 않는다. 과거 CLI local `migration list`는 stack 미기동으로 실패했다. 현재 hosted migration history는 별도 MCP 조회로 위 두 항목을 확인했다. Docker stack 검증은 미완료다. 추가 migration도 적용 전 개발 대상과 SQL을 검증한다.

## 다음 연결 및 Storage·이관 검증

1. 전용 project 생성과 core 검증은 완료했다. 이 PC의 ignored 승인 기록과 현재 ref/health를 대조해 재개한다. 이미 적용한 migration을 다시 실행하지 않는다. 다른 PC에서는 승인 경로로 대상 정보와 credential을 별도 구성한다.
2. 기존 개발 workspace를 재사용하고 실제 Auth 사용자·membership을 bootstrap한다. 가짜 Auth 사용자를 운영 계정으로 추가하지 않는다. workspace_members는 trusted administrator만 등록한다.
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
