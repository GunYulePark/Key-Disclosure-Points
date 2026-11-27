# TASK 01 중앙 개발 기반

2026-11-26 추가 연결 계정의 사용자 지정 Free 조직에 서울 `key-disclosure-points-dev`를 월 $0으로 생성했다. 전용 개발 DB/core 9개 테이블·RLS·Storage SELECT/INSERT 정책·workspace 1개와 FK 인덱스 적용/검증 완료. 실제 ref/UUID는 공개 문서에 기록하지 않고 ignored `.local/task01/approved-target.json`, `cloud-state.json`에만 보관한다. 기존 계정의 11월 24일 생성 한도 실패는 과거 기록이다.

Supabase 대시보드에서 비공개 `kdp-dev-originals`를 만들고 법령 HTML 2개를 이관했다. 원격 SQL로 `public=false`, 10MiB 제한과 인증 사용자용 SELECT/INSERT 정책을 확인했다. 프로젝트 Auth 사용자 1개를 승인 workspace에 `viewer`로 등록했다. 2026-11-27 회사 PC에서 실제 viewer 로그인으로 두 원본을 빈 폴더에 복원하고 SHA-256·679,729바이트·인용 4개와 공개 접근 거부 2개를 확인했다. 원격 SQL에서 viewer의 접근과 비회원 차단을 확인했다. 집 PC 복원은 별도로 검증한다.

## 원격 적용 및 검증 이력

| 로컬 CLI 생성 파일 | Hosted version / 이름 | SQL SHA-256 |
|---|---|---|
| `20261124080839_kdp_central_core.sql` | `20261126042013 kdp_central_core` | `589472a414ba912c788fb80ea1ef9b19337cbcd7b6dea313b5400cc06260b388` |
| `20261126042319_kdp_file_identity_index.sql` | `20261126042450 kdp_file_identity_index` | `8151942f15c6e8bbb8e21101ea9c2efc965ba885baf4a763956c12ad3c6473e3` |
| `20261126235013_kdp_evidence_locations.sql` | `20261126235336 kdp_evidence_locations` | `fdb4615a25c9d9eb3005195328260af66377110b28ebbe3ab90dea59d259bf9a` |
| `20261127004007_kdp_central_intake.sql` | `20261127004806 kdp_central_intake` | `07aacf7f1dcb0c111b605cc9eaf673676d8a12d7fff4fc11cfb782628a7343c6` |
| `20261127020921_kdp_intake_context.sql` | `20261127021710 kdp_intake_context` | `05cced07e936c33f04ce1ec1bb2b8ce4211aac8bd9f54257e5807747cdb7235c` |
| `20261127022626_kdp_company_intake_scope.sql` | `20261127025727 kdp_company_intake_scope` | `f64d36240e576df6797297a2c6fe7af12984b838b86d71fad7d1219c4c103bba` |

MCP `apply_migration`은 적용 시각으로 이력을 생성하므로 로컬 파일명과 다르다. 같은 SQL을 `db push`로 중복 적용하지 않는다. CLI 연결 전 migration history 대응을 확인하고 필요 시 `migration repair --help`와 실제 history를 검토한다. 현재 적용 SQL은 로컬 SHA와 같다. core 파일의 NOT applied 주석은 생성 당시 기록이며 hash 보존을 위해 바꾸지 않았다.

위치 migration은 전용 개발 DB에만 적용했다. `scripts/evidence_locations.py`는 승인 목록과 별도 다운로드한 원본을 대조해 ignored 경로에 backfill SQL만 생성한다. 승인/원본/근거/버전 일치가 확인되면 같은 추출기 버전을 중복 없이 저장한다. 기존 값과 다르면 트랜잭션 오류로 중단한다. 첫 배치 실제 SQL 권한 및 중복 검증은 `DEVELOPMENT_STATUS.md` 참조.

위치 테이블 적용 뒤 Supabase 권고에서 해당 테이블 관련 지적은 없었다. 프로젝트 Auth의 유출 비밀번호 검사 비활성화 경고는 별개로 남아 있다. [Supabase 비밀번호 보호 안내](https://supabase.com/docs/guides/auth/password-security#password-strength-and-leaked-password-protection)

`scripts/check_hosted_central.sql`은 **승인된 전용 개발 project에서만** MCP `execute_sql`로 실행한다. 실제 PostgreSQL의 15개 권한/FK/불변/revision/ready 검사를 수행하며 가상 Auth 사용자·metadata는 전부 transaction rollback한다. Storage 테이블/객체를 쓰지 않으며 실제 로그인/Storage HTTP/hash 성공을 주장하지 않는다. 실행 뒤 Auth 사용자 0·workspace 1·문서/객체 0 확인. 익명 publishable key REST 조회는 실제 HTTP 401/42501로 거부됐다.

advisors: security/health 0, performance FK 누락 1건은 전체 복합 인덱스로 보완. 남은 unused_index INFO 4건은 신규 DB 사용 실적이 없어 삭제하지 않았다. [미사용 인덱스 안내](https://supabase.com/docs/guides/database/database-linter?lint=0005_unused_index). DB 약 12MB, 업로드 0건. 초기 empty project 확인이 이관 전 baseline이며 DB/Storage backup·restore 실증은 별도 미완료다. 되돌릴 때는 개발 쓰기를 중단하고 로컬 원본을 보존한다. 프로젝트/테이블 삭제는 별도 승인 없이 하지 않는다.

## 구현 범위

- CLI 3.3.0의 `migration new kdp_central_core`로 생성한 core migration: workspaces/members, sources, documents/versions/files, evidence, legacy map, ingestion jobs의 9개 테이블.
- workspace 복합 FK·인덱스, RLS/명시 GRANT, 관리자만 membership/승인 변경, 원본 identity 불변, revision 증가·조건 갱신, 미검증 원본·근거의 ready 전환 차단.
- 비공개 Storage SELECT/INSERT 정책. 검증된 파일만 읽고, 승인된 사전 등록 경로만 editor가 업로드할 수 있다. 사용자 UPDATE/DELETE/upsert는 허용하지 않는다. 버킷은 SQL insert 대신 Storage API로 생성한다.
- `central_sync.py`: 기본 offline plan, 승인된 전용 개발 target 검사, 비공개 bucket 확인/명시 생성, 인증된 reader로 DB manifest와 원본 hash/길이·인용 위치를 대조한 복원. `--source`를 반복해 이관된 파일만 선택할 수 있다.
- `central_ingest.py`: 명시적인 승인 배치의 원본·locator 검증, 멱등 staging·finish SQL 생성. 파일 전송은 개발 Storage 관리자 세션에서 수행했고, 다시 받은 바이트로 확인한 뒤 ready를 기록했다.
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
2. 기존 개발 workspace를 재사용한다. 개발 프로젝트 대시보드의 Authentication → Users에서 실제 개발자가 자신의 프로젝트 Auth 계정을 설정한다. 관리자가 해당 Auth 사용자의 UUID를 확인해 기존 workspace에 필요한 역할로 등록한다. 파일·DB 읽기 검증은 `viewer` 권한으로 가능하다.
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
# 승인된 개발 workspace를 프로젝트 Auth 자격증명으로 읽기:
.venv/Scripts/python.exe scripts/central_sync.py check --target .local/task01/approved-target.json --password-login
# 기본값은 기존 비공개 bucket 검사만 한다.
.venv/Scripts/python.exe scripts/central_sync.py bucket --target .local/task01/approved-target.json
# 승인된 개발 환경에서만 신규 private bucket 생성:
.venv/Scripts/python.exe scripts/central_sync.py bucket --target .local/task01/approved-target.json --apply
# 이관한 연구 원본 두 개를 Auth 계정으로 집 PC 복원:
.venv/Scripts/python.exe scripts/central_sync.py restore --target .local/task01/approved-target.json --cache .local/case-research/originals --password-login --source commercial-amendments --source commercial-decree-33
```

`check`는 프로젝트 Auth 사용자와 해당 workspace의 membership 및 읽기 여부를 확인한다. 명령에서 `--password-login`을 생략하면 현재 프로세스의 `SUPABASE_DEV_ACCESS_TOKEN`을 사용한다. 권한이 확인되면 `workspace_visible: true`와 역할을 출력한다. 파일 복원에는 이관 완료된 원본과 manifest가 필요하다.

5. 출처별 보관 권리와 승인 범위를 확인한 샘플로 staging → upload(upsert=false) → 별도 실행에서 다운로드/hash → evidence → ready를 검증한다. HTTP에서 누락 버킷의 상태 코드가 fixture와 다르면 실제 응답/공식 API를 확인하고 수정한다. 400 오류를 일괄 '없음'으로 취급하지 않는다.
6. ingestion adapter/멱등 seed, 실패 재개, 원본·metadata의 독립 백업/복원, 실제 Auth·다른 workspace·anon 접근 거부, advisors를 확인한다. 회사와 두 번째 깨끗한 환경의 byte hash·버전을 대조하고 실제 집 PC 검증을 별도로 기록한다.

### 다음 승인 배치 이관 절차

1. 무시 경로의 승인 JSON에 `project_ref`, `workspace_id`, `pack_fingerprint`, `transfer_approved: true`, `approved_by`, `sources`를 기록한다. `sources`는 source ID별 SHA-256, 권리 근거 `rights_url`, `publisher`, `document_type`을 담는다.
2. `central_ingest.py stage --pack <pack> --target <target> --approval <approval> --files <original-cache> --out <new-.local-folder>`로 사본과 SQL을 생성한다. 승인된 개발 DB에서 `stage.sql`을 실행한 후 `batch.json`에 기록된 경로에 각 파일을 덮어쓰기 없이 업로드한다. Windows 대시보드 파일 선택은 긴 로컬 경로에서 0바이트로 실패할 수 있으므로 원본 캐시의 짧은 파일 경로를 사용한다.
3. 별도 폴더에 버킷 객체를 다시 다운로드한다. 같은 옵션으로 `finish`를 실행하되 `--files`에 다운로드 폴더를, `--out`에 새 폴더를 지정한다. `finish.sql`을 실행하고 버전·작업 상태, 원본 해시·길이, 근거 수를 확인한다. 시각 근거는 담당자 검증 전 `unverified`다.

## 중앙 접수

`kdp_intake_entries`에는 회사·제목·출처·보관 근거·SHA-256·텍스트와 파일 상태가 들어간다. PDF는 비공개 `kdp-dev-originals`의 작업공간 접수 경로에 저장한다. 확인된 PDF를 회원에게 열기 전 파일을 다시 내려받아 SHA-256과 길이를 확인한다. 접수 준비와 파일 업로드를 두 단계로 저장해, 파일 저장 후 응답이 끊겨도 같은 자료로 재시도할 수 있다. 직접 변경·덮어쓰기는 허용하지 않는다. 원문 검증이 완료된 연구 자료의 기존 테이블과 원본 경로는 계속 사용한다. 접수 자료를 검토 후 그 원문·근거 체계에 연결하는 단계는 후속이다.

`kdp_reference_sites`는 [기본 참고 경로](../monitoring/reference-sites.json)를 기존 승인된 개발 작업공간에 URL 중복 없이 등록했다. 조회는 작업공간 회원, 등록은 편집자 이상이다. 이 목록은 크롤러 대상 설정을 자동 변경하지 않는다. [중앙 자료 접수 시작 명령](../HOME_PC_HANDOFF.md#중앙-자료-접수)이 있다. 운영 Pages·Actions·D1의 실제 배포와 기존 브라우저 원본 이관은 각각 승인 범위를 따른다.
