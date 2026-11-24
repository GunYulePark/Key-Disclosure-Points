# 개발·운영 및 데이터 접근 경계

TASK 00: 원격 프로젝트 목록·plan·public schema 메타데이터만 읽었다. 행 데이터/키 조회, SQL 실행, bucket 생성/업로드, 권한 변경, 운영 설정 변경은 수행하지 않았다. 실제 Supabase RLS/Storage/auth 테스트는 아직 수행하지 않았다.

## 환경과 공개 범위

- 독립 개발 프로젝트가 선정되기 전까지 `CENTRAL_STORE_MODE=disabled`. 기존 업무용 프로젝트 2개는 재사용하지 않는다. schema 이름만 나누는 방식으로 운영 DB에 실험하지 않는다.
- `.env.example`은 빈 값 템플릿이며 승인 또는 작동하는 연결이 아니다. publishable key조차 이 단계에서는 프론트엔드에 연결하지 않는다. DB URL/password·server secret/service role·DART/Gemini 키는 로컬 환경/승인된 Secret에서만 관리한다.
- 공개 코드에 상세 로컬 inventory, 개인 메일/검토 이벤트, 내부 자료, 실제 평가 정답, 프로젝트 관리자 키를 넣지 않는다. 기존 공식 공개 snapshot만 그대로 유지한다.
- 공식 URL+hash 일치는 외부 저장/재배포 권리 또는 회사 보안 승인을 대체하지 않는다. 샘플 후보도 권리·이전 대상 승인 후 업로드한다.

## TASK 01 정책 설계/검증

- 모든 API 요청에 인증과 trusted workspace membership을 확인한다. user_metadata 또는 CORS만으로 권한을 부여하지 않는다.
- public schema RLS 및 명시 GRANT. anon은 기본 거부, 일반 authenticated 사용자는 자기 승인 workspace만 조회. 작성/수정은 역할과 revision 검사 모두 필요하다.
- 멤버·role 관리는 별도 관리자만 허용한다. 권한 함수가 필요한 경우 별도 private schema·최소 EXECUTE·명시 user 검사/고정 search_path를 검증한다. 편의를 위한 SECURITY DEFINER 도입 금지.
- private Storage의 workspace prefix/등록된 파일과 정책을 연결한다. 원본 UPDATE/DELETE는 기본 불허, 서버도 overwrite하지 않는다. signed URL은 권한 확인 후 짧게 발급하고 로그에 저장하지 않는다.
- QA/holdout 및 내부 규칙은 별도 비공개 권한 경계. ingestion/chat/evaluation에 공통 관리자 key를 배포하지 않는다. generic RAG 호출에 holdout 정답을 제공하지 않는다.
- URL allowlist/redirect 검사, ZIP 경로/압축 제한·XXE 차단·HTML sanitize·파일 크기/MIME/hash 검증은 원본 입력마다 적용한다. 문서 내부 지시문을 도구 실행 명령으로 사용하지 않는다.

## 승인 경계

새 클라우드 생성, 실제 이관/원격 migration, 유료 연결/한도 확장, 운영 DB/배포·기존 기능/데이터 삭제는 사전 승인 대상이다. 승인 기록에 환경 ref·범위·용량·예상 비용·되돌리기 방법을 포함한다. TASK 00 문서를 읽었다는 이유만으로 승인된 것으로 간주하지 않는다.

## 무료 플랜과 복구

2026-11-24 확인한 [공식 요금표](https://supabase.com/pricing): Free DB 500MB, Storage 1GB, egress 5GB, active project 제한 2개, 비활성 기간에 따른 pause 안내가 있다. 이는 조사 시점 정책이며 코드 상수·계약 보장으로 사용하지 않는다. 조사한 조직은 Free이고 기존 프로젝트 2개가 active다. 추가 독립 Free 프로젝트를 만들 수 있는지 계정 정책/현재 사용량을 다시 확인해야 한다. 기존 프로젝트 중지·삭제·유료 전환으로 자리를 만들지 않는다.

[DB 백업 문서](https://supabase.com/docs/guides/platform/backups)에 따라 DB 백업과 Storage 객체 백업은 별도로 설계한다. Free의 관리형 복구를 이미 확보한 것으로 가정하지 않는다. 승인된 별도 보관처에 manifest/hash/DB dump/객체를 보관하고 실제 복원 테스트를 한다.

## 참고 문서 (확인일 2026-11-24)

- [RLS](https://supabase.com/docs/guides/database/postgres/row-level-security)
- [Storage access control](https://supabase.com/docs/guides/storage/security/access-control)
- [Private buckets](https://supabase.com/docs/guides/storage/buckets/fundamentals)
- [CLI v3 변경](https://supabase.com/changelog/supabase-cli-v3): local 기본값/remote 대상/확인 절차 변경. 기존 CLI v2 예시를 그대로 실행하지 않는다.

## 기존 의존성 audit

2026-11-24 clean clone에서 npm audit: low 1건(esbuild 0.28.0, [GHSA-g7r4-m6w7-qqqr](https://github.com/advisories/GHSA-g7r4-m6w7-qqqr)). Windows 개발 서버 관련 advisory이며 자동 강제 수정 없이 기록했다. 현재 build API 사용과 advisory 적용 범위를 확인하고 후속 패치에서 회귀 검증한다. audit 결과만으로 전체 애플리케이션 보안 통과를 주장하지 않는다.
