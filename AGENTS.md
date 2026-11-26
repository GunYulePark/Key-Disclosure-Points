# 개발 작업 규칙

## 세션 시작

1. `PROJECT_REQUIREMENTS.md` 전체와 `ROADMAP.md`, `DEVELOPMENT_STATUS.md`, `NEXT_TASK.md`를 읽는다.
2. `git status --short`, 현재 브랜치와 최근 커밋을 확인한다. 이 저장소가 Git 기준 루트다. 상위 작업 폴더의 미추적 자료를 자동 추가하지 않는다.
3. 중앙 개발 DB의 승인된 환경 식별자를 확인한다. 2026-11-26 추가 연결 계정의 사용자 지정 Free 조직에 서울 `key-disclosure-points-dev`를 생성하고 core/RLS를 검증했다. 실제 ref/workspace는 ignored `.local/task01/approved-target.json`, `cloud-state.json`에만 있다. private bucket·Auth·실자료 이관은 아직 미완료다. 기존 구축/조직 승인을 다시 묻지 않는다. 다른 업무 프로젝트를 재사용·중지·삭제하거나 유료 전환하지 않는다.
4. `NEXT_TASK.md`의 미완료 단계부터 시작하고 실제 테스트와 미검증 상태를 구분한다.

## 승인 경계 — 사용자 최신 지시 우선

- 기존 기능/데이터 삭제, 유료 서비스 전환, 운영 환경 변경, 운영 DB 변경, 배포는 사전 승인 없이는 하지 않는다.
- 최초 TASK 00에서는 분석·설계·로컬 검증·문서만 수행한다. 신규 프로젝트/버킷 생성, 자료 업로드, 원격 migration, 개발/운영 연결 변경은 TASK 01 승인 이후다.
- `main` push는 기존 GitHub Actions가 자동 배포한다. 승인 없이 main push/merge, `workflow_dispatch`, Pages 설정 변경을 하지 않는다. 개발 브랜치 push만 가능하며 먼저 workflow trigger를 확인한다.
- 중앙 DB 계획은 독립 개발 프로젝트 + private Storage다. 운영 정적 사이트와 비공개 Sites/D1을 유지한다.
- 사내자료·개인 업로드·메일 기록·평가 정답·키를 공개 GitHub/외부 API에 전송하지 않는다. 공식 공개 출처 확인도 저장/재배포 권리 승인은 아니다.
- `.local/`, `.env*`(예시 제외), 원본 바이너리, 임시 로그는 커밋하지 않는다. 선택적으로 stage하고 `git add .`는 사용하지 않는다.
- `#operations` 공개 숨김과 슬로건/검토일 장식 제거는 기존 사용자 결정이다. 요구사항 14장의 운영 화면은 TASK 09에서 인증된 관리자 화면으로 검토하며 공개 복구하지 않는다.
- 기존 모니터링 3개 회사는 유지한다. 종근당바이오 추가는 지식 사례 수집 범위로 설계하며 운영 모니터링 확대는 별도 검토한다. 종근당건강을 자동 추가하지 않는다.

## 검증·기록

- 코드/스키마/원본 ID의 호환성을 보존한다. 날짜·좌표·규정·성능을 만들지 않는다.
- 변경 영향에 맞는 테스트를 수행한다. 가짜 응답/fixture 통과를 실제 Supabase 이관/인증/SQL 성공으로 보고하지 않는다.
- 작업 단위마다 `DEVELOPMENT_STATUS.md`에 완료/미완료/검증, `NEXT_TASK.md`에 명령·다음 단계·승인 경계를 기록한다. 결정·변경은 `CHANGELOG.md`에 남긴다.
- DB schema를 작성할 때 Supabase 최신 문서/CLI help 확인 후 migration을 생성한다. 현재 SQL 초안/ERD는 실제 migration이 아니다.
- 업무 종료: 변경 diff·비밀정보 점검 → 해당 테스트 → 선택 stage → 개발 브랜치 commit/push → 인수인계 문서 확인. 문서는 `public/`, `docs/`로 복사하지 않는다.
