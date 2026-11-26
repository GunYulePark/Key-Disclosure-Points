# 개발 진행 상황

## 2026-11-26 — 전용 Free 개발 DB 생성·원격 검증 / Storage 로그인 대기

사용자가 지정한 추가 연결 계정의 조직 1개는 Free이며 조회 프로젝트는 0개였다. 해당 조직에 생성을 명시적으로 지정받고 월 $0 비용을 확인해 서울 리전에 `key-disclosure-points-dev`를 생성했다. `ACTIVE_HEALTHY`, 기존 public table/migration 없음 확인 후 core 9개 테이블·RLS/FK·Storage SELECT/INSERT 정책을 적용했다. 개발 workspace 1개를 bootstrap했으며 Auth 사용자·membership, 문서·원본 객체는 0개다. 계정 이메일·실제 ref/UUID는 공개 문서에 쓰지 않고 ignored `.local/task01/approved-target.json`, `cloud-state.json`에만 기록했다. 새로운 계정/조직 승인을 다시 요구하거나 다른 업무 프로젝트를 변경하지 않는다.

원격 migration: `20261126042013 kdp_central_core`와 `20261126042450 kdp_file_identity_index`. 로컬 CLI 생성 파일명과 hosted 적용 시각은 다르므로 `supabase/README.md`의 이름·SHA 대응을 따른다. core 파일의 초기 미적용 주석은 생성 당시 이력이며 SQL 본문/bytes를 바꾸지 않았다. 성능 advisors의 복합 FK 인덱스 누락을 additive migration으로 보완했다. 보안/health 0건, 성능은 미사용 인덱스 INFO 4건만 남겼다. 사용 실적 없는 인덱스를 임의 삭제하지 않는다.

검증: hosted SQL rollback fixture **15개 통과**, 9개 RLS 확인, 익명 REST 실제 HTTP **401 / 42501**로 metadata 접근 거부. rollback 뒤 Auth 사용자 0·workspace 1·문서 0·bucket 0·객체 0 재확인. PGlite **26개 통과**(추가 migration/hosted 검사 SQL의 fixture 실행·rollback 포함). Python 회귀 **63개 통과**. 이 SQL의 가상 사용자/검증표시는 transaction에서만 존재하며 실제 로그인·Storage HTTP·원본 hash 검증 성공이 아니다.

현재 PC의 기존 `.venv` 부재와 기본 `python` alias/전역 PyMuPDF 누락으로 최초 Python 실행은 실패했다. 설치된 Python 3.13으로 ignored `.venv`를 만들고 기존 pinned `requirements.txt`만 설치한 뒤 63개 전체 통과했다. 앱 dependency/lockfile은 바꾸지 않았다. `npx --no-install supabase`는 최신 3.4.0 캐시 부재로 실패해 기존 캐시의 CLI 3.3.0을 명시 실행하고 version/help 확인 후 인덱스 migration을 생성했다. 새 CLI 설치·자동 업그레이드는 하지 않았다.

**미완료:** 대시보드가 로그인 화면이라 private `kdp-dev-originals` 버킷은 아직 생성되지 않았다. 현재 Supabase connector에는 버킷 생성/관리자 credential 조회 도구가 없으며, storage schema에 SQL로 직접 metadata를 쓰는 우회는 사용하지 않는다. 사용자 로그인 후 Storage API/UI로 private bucket·10MiB 제한·허용 MIME을 생성하고 실제 Auth/Storage 접근을 검사한다. 사용자 계정 로그인과 프로젝트 내부 Auth 사용자는 별개다. 실제 자료 권리/샘플 범위·server ingestion adapter·백업/복원·두 PC 조회도 남아 있다. TASK 01 전체 완료나 원본 중앙 공유 성공으로 보고하지 않는다. 운영/Pages/Actions/Sites/D1·유료 전환·실자료 업로드 없음.

## 2026-11-26 — 추가 Supabase 계정 연결 확인

사용자가 제공한 플러그인 화면에 추가 Supabase 계정이 표시됐다. 현재 Codex 채팅에서 조직·프로젝트를 다시 조회하면 기존 연결의 조직과 프로젝트 2개만 반환된다. 새 계정의 조직과 무료 프로젝트 자리는 아직 확인되지 않았다. 새 Codex 채팅에서 Supabase 계정을 명시해 읽기 전용으로 확인한 뒤 전용 환경을 확보한다. 원격 변경은 수행하지 않았다.

## 2026-11-26 — 무료 개발 환경 경로와 기존 프로젝트 사용 확인

연결 계정에는 활성 프로젝트 2개가 있다. 다른 조직을 같은 계정의 Owner/Admin으로 개설해도 무료 2개 한도는 합산된다. 무료 여유가 있는 별도 계정에서 전용 개발 프로젝트를 확보하는 방식은 가능하다. [Supabase 무료 정책](https://supabase.com/docs/guides/platform/billing-on-supabase#free-plan)

기존 두 프로젝트는 읽기 전용으로 용도를 확인했다. 하나는 캘린더 동기화·접근 승인용으로 최근 정상 API 응답을 확인했다. 다른 하나는 손익자료 수집·피벗·다운로드 함수가 있고 최근 DB 서비스 로그가 있으며, 테이블 구조·데이터 최신 갱신은 연결 시간 초과로 재확인하지 못했다. 두 프로젝트 모두 별도 용도로 보고 전용 개발 DB 후보와 분리한다. 프로젝트 설정·데이터·플러그인 연결은 조회 당시 상태다. 실제 개발 DB/원본 저장소 생성은 새 계정 인증과 대상 프로젝트 확보 이후다.

## 2026-11-24 — TASK 01 로컬 구현 / 무료 프로젝트 생성 거절

사용자가 중앙 DB/비공개 원본 저장소 구축 및 TEST 조직의 전용 Free 프로젝트 생성을 승인했다. 신규 비용은 월 $0 조회됐고 `key-disclosure-points-dev` 서울 리전 생성을 시도했으나 계정의 active Free 프로젝트 2개 한도로 Supabase가 거절했다. **원격 DB/bucket 생성·migration·자료 업로드는 0건**이다. 기존 프로젝트는 변경하지 않았다. 환경 확보 방식(다른 사용 가능한 개발 환경/사용자가 지정할 중지 가능한 기존 프로젝트/유료 비용 비교)을 질문했으며 답변을 확인해야 한다. 기존 구축 승인을 다시 요구하지 않는다.

로컬 준비: Supabase CLI 3.3.0 help 확인·`migration new`로 core SQL 후보 생성, 9개 테이블/RLS·명시 권한·복합 FK·원본 identity 불변·revision·ready 차단·private Storage 정책 구현. `central_sync.py`는 기본 offline plan, 승인된 전용 개발 target/URL 제한, bucket 확인/명시 생성, 인증 reader의 manifest/원본/인용 위치 검증 복원을 제공한다. DB seed/ingestion 업로드 adapter·Auth bootstrap·실제 HTTP/권한/advisors·백업 복원·두 PC 검증은 아직 남아 있다.

검증: Python 전체 **63/63 통과**(기존 52+동기화 도구 11). 최종 Python 수정 후 해당 11개 재검증 통과. PGlite PostgreSQL/WASM **24/24 SQL 검사 통과**(Auth/Storage는 fixture). 실제 로컬 76원본 **27,024,097 bytes**의 hash/길이·텍스트 위치를 offline 이관 계획에서 재확인했다. 네트워크 전송·승인 승격 없음. CLI 기본 local `migration list`는 stack 미기동으로 연결 거절됐고 hosted 성공으로 표시하지 않는다. 앱 dependency/운영 UI/Actions/배포는 변경하지 않았다. 재현·다음 명령은 `supabase/README.md`.

## 2026-11-24 — 집 PC 재개 안내

`HOME_PC_HANDOFF.md`에 clone할 개발 브랜치, 새 세션 문구, PC 전환 절차와 실제 공유 범위를 기록했다. 기존 개발 커밋 `1993b69`의 원격 브랜치 일치를 확인했다. 코드·메타데이터는 GitHub로 재개할 수 있으나 76원본 약 27MB는 회사 PC 로컬에만 있다. 중앙 DB/Storage와 실제 집 PC 재현은 미검증이다. 연결된 무료 조직의 active 프로젝트 2개는 다른 업무용임을 재확인했으며 생성/연결/업로드/운영/배포는 하지 않았다. 문서 변경만으로 diff·문서 참조·workflow trigger를 확인하고 소스 테스트는 반복하지 않았다.

## 2026-11-24 — 우선 사례 추가 사실 대조 완료

`CASE_REVIEW_02.md`에 2차 결과 기록. 2026.3.26 개정 종근당 정관 전문(6월 기타공개첨부서류)을 확보하고 PDF 15·17쪽을 시각 대조해 배당절 인용 보완 후보를 구체화했다. 3사 2025년말 표시 자산 5개를 연차·Q3 10개 셀에서 교차 확인했고, 단순 단위 비교를 법률 적용 승인과 분리했다. 482건 공시목록을 페이지 총건수와 대조해 3사×13시점의 연구개발 절 39개를 확보했다. 코드 언급 변화 36개는 중단/지연 판정이 아니다. 종근당 반기 후속 접수 `20261022000500`도 연결했다.

v1 묶음 보존, v2 76자료/97텍스트 위치와 후속 사실 JSON·검증 helper/테스트 추가. 원본 총 27,024,097 bytes는 로컬 ignored 캐시만 사용한다. **전체 52/52 테스트**, 76원본 hash/길이·텍스트 위치, 자산 10셀 및 39개 절 문자 추출 재검증 통과. canonical JSON 지문으로 LF/CRLF·키 순서 차이를 허용하고 원본 byte hash는 유지한다. 줄바꿈 모의 검사이며 실제 다른 PC/중앙 DB 성공은 아니다.

남은 범위: 모든 품목·적응증·별칭의 3년 의미 대사, 수시공시·내부 계약·일정과의 대사, 법률 적용·정정 필요 담당자 검토. 승인 QA/규칙/AI 성능평가 미실행. 기존 운영 UI/snapshot/배포/클라우드·의존성은 변경하지 않았다. 로드맵 TASK 03은 사전자료 준비이고 자동 파이프라인 구현 완료가 아니다.

## 2026-11-24 — C01/C03/C08/C09 1차 착수 완료

사용자 착수 지시에 따라 `CASE_REVIEW_01.md`, `research/priority-case-pack.json`/README, 오프라인 검증 도구와 테스트를 추가했다. 공개 자료 22단위(문서·절·이미지), 질문 16개, 자동 텍스트 위치 40개 및 수동 시각 확인 이미지 3개. 원본 15,638,525 bytes는 ignored 로컬 캐시에만 있으며 공개 Git에는 메타데이터·짧은 위치 문자열·질문만 기록했다.

새 확인: 최신 11.13 시행 작성기준 확보; 종근당 10.22 반기 정정 요약과 실제 자기주식보고서 추가 첨부 확인; 삼성전자/한세실업 정관 변경 후속 승인 자료 연결; 8월 HWP 및 3사 Q3 선정 절 재확보; 배당절 인용과 첨부 정관 이미지 문구 차이를 P1 보완 검토 후보로 구체화. 전체 정정/규정/정관 전수 검토나 담당자 승인은 아니다.

검증: 전체 Python **39/39 통과**(기존 30+신규 9), 원본 22개 hash/길이·텍스트 위치 40개 재검증 통과. 이미지의 실제 문구 판독은 수동이며 OCR/좌표 Viewer 성공으로 표시하지 않았다. 승인 QA 0, 활성 규칙 0, 실제 AI 성능 측정 미실행. 기존 UI/snapshot/운영/의존성/클라우드 연결/배포는 변경하지 않았다. TASK 03은 조사 입력 준비이며 수집 파이프라인 구축 완료로 변경하지 않는다.

## 2026-11-24 — 공개 사례 추천 조사

사용자 요청으로 `CASE_CANDIDATES.md`에 공식 출처 기반 검토 후보 10개와 질문·추가 확보 자료·확인 범위를 기록했다. 상법/정관, 자기주식 공시 범위, 업종 모범사례, 배당절 대조, 실제 정정을 포함한다. 초기 추천은 C01/C03/C08/C09이며, 정답·승인 QA·Rule Engine 활성화는 하지 않았다. TASK 03 구현 완료를 뜻하지 않는다.

주요 후속 확인: 금융위 2026.6.23 발표와 최종 공포/서식 버전을 대조하여 기존 자기주식 예외 답변의 유효성을 재검토한다. 종근당 배당절의 개선 가능 표시/인용 정관은 최신 정관과 대조할 후보이며 정정 의무 미확정이다. 소집공고 안건의 실제 가결은 별도 확인 대상이다. DART 지침 게시·종근당 배당절·정정 요약 HTTP 200 재확인, 공식 상법 개정문/부칙과 기업 IR/KIND 자료 확인. 원문 바이너리 재배포/외부 API 전송·클라우드 쓰기·운영 변경 없음. 변경은 개발 문서 4개뿐이므로 소스 회귀 테스트는 반복하지 않고 diff·문서 참조·변경 범위를 확인한다.

기록일: 2026-11-24 / 요구사항 v2.0 / 현재 단계: **TASK 00 완료, TASK 01 전용 DB·원격 SQL 검증 완료 / Storage·Auth·샘플 검증 진행 중**. 아래 TASK 00 및 11월 24일 기록은 당시 이력이며 최신 상태는 맨 위 11월 26일 기록을 따른다.

## 바로 알아야 할 사항

- 실제 저장소는 이 문서가 있는 폴더. 개발 브랜치 `codex/task-00-cloud-foundation`, 시작 기준 `9e50cd1`(조사 시 origin/main과 같음).
- 전용 Free 개발 DB/core RLS는 생성·원격 검증했다. private bucket/Auth·샘플 업로드·두 PC 공유는 미완료다. 실제 대상은 ignored 승인 기록을 따르며 공개 문서에 ref를 쓰지 않는다.
- 기존 계정의 다른 업무 프로젝트 2개는 보존한다. 추가 연결 계정에서 확보한 독립 개발 프로젝트만 이번 대상으로 승인됐다.
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
