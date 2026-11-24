# 개발 진행 상황

## 2026-11-24 — 공개 사례 추천 조사

사용자 요청으로 `CASE_CANDIDATES.md`에 공식 출처 기반 검토 후보 10개와 질문·추가 확보 자료·확인 범위를 기록했다. 상법/정관, 자기주식 공시 범위, 업종 모범사례, 배당절 대조, 실제 정정을 포함한다. 초기 추천은 C01/C03/C08/C09이며, 정답·승인 QA·Rule Engine 활성화는 하지 않았다. TASK 03 구현 완료를 뜻하지 않는다.

주요 후속 확인: 금융위 2026.6.23 발표와 최종 공포/서식 버전을 대조하여 기존 자기주식 예외 답변의 유효성을 재검토한다. 종근당 배당절의 개선 가능 표시/인용 정관은 최신 정관과 대조할 후보이며 정정 의무 미확정이다. 소집공고 안건의 실제 가결은 별도 확인 대상이다. DART 지침 게시·종근당 배당절·정정 요약 HTTP 200 재확인, 공식 상법 개정문/부칙과 기업 IR/KIND 자료 확인. 원문 바이너리 재배포/외부 API 전송·클라우드 쓰기·운영 변경 없음. 변경은 개발 문서 4개뿐이므로 소스 회귀 테스트는 반복하지 않고 diff·문서 참조·변경 범위를 확인한다.

기록일: 2026-11-24 / 요구사항 v2.0 / 현재 단계: **TASK 00 완료, TASK 01 승인·환경 확보 대기**.

## 바로 알아야 할 사항

- 실제 저장소는 이 문서가 있는 폴더. 개발 브랜치 `codex/task-00-cloud-foundation`, 시작 기준 `9e50cd1`(조사 시 origin/main과 같음).
- Supabase 중앙 개발 DB/원본 저장소는 **미생성·미연결**이다. 연결 성공·원격 SQL·샘플 업로드·RLS·두 PC 공유 성공을 주장하지 않는다.
- 무료 조직의 기존 active 프로젝트 2개는 다른 업무 테이블이 있고 이번 개발 대상으로 승인되지 않았다. 이름만 비슷해도 재사용하지 않는다. 추가 독립 Free 프로젝트 확보 가능 여부가 다음 결정이다.
- main push는 실제 배포를 유발한다. 이번 작업은 main merge/push/dispatch/운영 환경 변경을 하지 않는다. 공개 운영 화면 숨김·간결한 문구·현재 데이터 유지.
- 상위 작업 폴더의 legacy 원본/검증기와 별도 private Sites 소스는 이 공개 저장소 clone에 포함되지 않는다. 상세 inventory는 로컬 `.local/task00/`에만 있다.

## TASK 00에서 한 일

1. `PROJECT_REQUIREMENTS.md` 515줄 전체 검토. 상위 원본을 byte 동일하게 저장소 루트에 복사. SHA-256 `297c0b617d1ca7710ae07234b30ea93e5e5df7772abac70122b943acfa3b6e2f`.
2. 공개 React/TS·수집기·Gemini·PDF.js/IndexedDB·정정/근거·GitHub Actions, private Sites/D1의 소스 schema·메일 모듈을 조사했다.
3. Supabase 조직/프로젝트/public table 메타데이터를 읽기 전용으로 확인. 원격 쓰기·키 조회·row 조회 없음. 무료 정책과 CLI v3 변경도 확인했다.
4. 로컬 조사 745파일/45,347,804 bytes, hash 기준 중복 사본 58개. 공식 URL/hash 일치 자료 54파일 약 20.25MB지만 저장/이전 승인은 미확인이다. 상세 범위는 `DATA_SOURCES.md`.
5. 공식 PDF 1개+DART HTML 1개, 합계 3,060,820 bytes를 샘플 dry-run 후보로 선택. 전송 0건. 과거 버전 샘플이며 현행성을 부여하지 않는다.
6. 중앙 DB/Storage ERD·접근정책·legacy alias/불변 원본·staging/ready·동시성·이관/복원 테스트 계획 작성. TASK 01용 순수 로컬 ID/hash/revision 계약과 inventory 도구를 추가했다.
7. `AGENTS.md`, `ARCHITECTURE.md`, `DATA_SCHEMA.md`, `DATA_SOURCES.md`, `SECURITY.md`, `OPERATIONS.md`, `ROADMAP.md`, 이 문서, `NEXT_TASK.md`, `CHANGELOG.md`, `.env.example` 마련. 개발 문서/비밀/원본을 Pages 산출물에 추가하지 않는다.

## 검증 결과

| 검사 | 실제 결과 | 범위/제약 |
|---|---|---|
| 기존 공개 Python 테스트 | 26/26 통과 | 변경 전 baseline |
| 새 inventory/ID/hash/revision 테스트 포함 | 30/30 통과 | 클라우드 테스트 아님 |
| `npm run check` | 통과 | 기존 TS 클라이언트 |
| `npm run build` | 통과 | 로컬 정적 빌드, 배포 안 함 |
| 상위 legacy Python 테스트 | 23/23 통과 | 원본이 있는 이 작업 PC에서만. `fitz` deprecated 경고 1종 |
| private Sites `tsc --noEmit --incremental false` | 통과 | 소스 형 검사만. Worker/메일 API/D1 재검증 아님 |
| DB migration/RLS/advisors/Storage E2E | 미실행 | 개발 ref 미선정, CLI/Docker/psql 미확인 |
| IndexedDB·remote D1 데이터 용량/내용 | 미조사 | 위치/schema만 확인, 실제 0건으로 보고하지 않음 |
| 깨끗한 Git clone + 새 venv/npm ci | 통과 | 로컬 clone 67fc2bc에서 30개 테스트·TS·build 재현. 실제 집 PC/중앙 DB 공유 검증은 아님 |

TASK 00 이후 구현이 필요한 항목: 중앙 연결·API/Auth/RLS·원본 Storage·실 DB 동시성/복원·좌표/표셀 Viewer·Advanced RAG·평가 정답/실행·승인 Rule Engine. 기존 Gemini는 조사 시 키 미등록이며 실응답 결과 0건이다.

## 파일/진행 기록 방법

작업 종료마다 다음 문서와 마지막 개발 커밋을 갱신한다. 첫 TASK 00 코드/설계 커밋은 `67fc2bc`다. 실제 DB migration ID는 아직 없다. 현재 세션 기록 커밋은 `git log --oneline --grep='TASK 00'`로 찾는다. root 문서는 Pages build에 복사되지 않으며 민감한 inventory/실제 private 프로젝트 식별자는 쓰지 않는다.

다음 세션은 `NEXT_TASK.md`의 승인 경계부터 확인한다. 사용자 승인 없이 TASK 01 원격 작업을 진행하지 않는다.

## 확인된 후속 점검

깨끗한 clone의 `npm ci`/`npm audit --json`에서 기존 `esbuild 0.28.0`에 low 1건을 보고했다. advisory `GHSA-g7r4-m6w7-qqqr`, Windows development server 관련, audit가 제시한 수정 버전은 0.28.2다. 현재 코드의 esbuild 사용은 build API이며 배포 사이트가 즉시 영향받는다고 단정하지 않는다. 자동 `audit fix --force`는 하지 않았다. 승인 범위 내 후속 개발에서 패치 적용·회귀 테스트를 검토한다. 높은/중간 등급은 이번 audit 결과 0건이지만 전체 보안 검증 완료를 뜻하지 않는다.

재현 도구: 현재 PC의 지원 런타임을 사용해 로컬 clone + 별도 Python venv + lockfile 설치로 확인했다. 임시 clone은 `.local/task00/clean-clone`에 남아 있고 커밋/이관 대상이 아니다. 다른 PC는 GitHub 개발 브랜치를 clone하고 `OPERATIONS.md`를 따라 설치한다.
