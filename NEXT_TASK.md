# 다음 작업 — TASK 01

## 최우선 기능 — 공시 수정 탐지와 일반 GPT 비교

업로드·검색 기능의 완료와 판단 품질을 별도로 본다. 다음 기능은 규정 판본(시행일·적용대상·예외)과 최신 유효 공시·정관을 직접 대조하여 `이미 반영`, `다음 제출본 수정 검토`, `기제출 정정 검토`, `확인 필요`를 구분하는 검토 결과다. 결과에는 수정할 문서의 판본과 절, 확인된 불일치, 적용 조항, 중요도, 추가 확인 자료를 기록한다. 정정 의무 확정은 담당자 판단으로 남긴다.

| 공개 비교 후보 | 확인할 동작 |
|---|---|
| 종근당·종근당홀딩스 자기주식보고서 | 규정 개정으로 과거 첨부 누락이 발생한 시점과 이후 정정본에 이미 첨부한 상태를 구분. 반기와 분기의 요구를 별도 판단 |
| 종근당 배당기준일 | 3분기 정관 인용과 현행 정관, 기업지배구조보고서 지표 X, 실제 배당 절차를 분리 |
| 종근당 자산 2조원 | 분기 연결 수치를 확정 판정에 사용하지 않음. 별도 결산 재무제표·규정별 적용 시점·근거 부족을 확인 |
| 제약·바이오 연구개발 | 코드 미관찰·예정일 경과와 실제 중단·지연을 구분. 변경 판단 근거를 원문의 표 행 또는 문장에 연결 |

공개 사례를 시범용으로 재현하고, 담당자 승인 문항과 홀드아웃으로 성능을 확인한다. 같은 자료 묶음과 기준일로 일반 GPT(자료 직접 제공)와 시스템 결과를 나란히 검토한다. 필수 수정 누락률, 불필요한 정정 제안율, 정확한 원문 위치 연결률, 사람 검토 시간을 각각 기록한다. 승인된 정답은 비공개에 저장한다. 현재 비교 실행·개선폭은 미측정이다. 상세 조건은 [요구사항 13장](PROJECT_REQUIREMENTS.md#13-evaluation-lab--자동-비교-및-평가) 참조.

## 회사별 중앙 자료 접수 계정

회사별 개발 Auth 계정 3개와 소속 회사 범위의 `editor` 멤버십을 등록했다. 회사 PC의 실제 로그인·목록 권한·타사 등록 거부·로그아웃을 확인했다. 다음 확인은 승인된 PDF·텍스트·링크의 공통/회사 전용 등록과 집 PC에서의 교차 열람·PDF 해시 대조다. 집 PC 설정은 [인수인계](HOME_PC_HANDOFF.md#회사-아이디-로그인)를 따른다. 운영 배포는 별도 승인 대상이다.

## 예약 자동화와 규정 변경을 회사별 검토로 연결

1. 현재 운영 공개 수집은 한국시간 평일 오전 8시 예약이고, Gemini는 `needs_key` 상태다. 운영 권한자의 승인 뒤 공개 출처만 다루는 `GEMINI_API_KEY` 연결과 지정 모델 무료 호출을 확인한다. 운영과 분리된 테스트에서 실제 공개 변경 한 건으로 결과 ID·근거 링크·회사별 후속 항목을 확인한다. 승인 전에는 `main` 변경·배포·운영 수동 실행을 하지 않는다.
2. 중앙 자료 접수에서 승인된 링크·작은 PDF와 메모를 실제 로그인으로 저장한다. 다른 브라우저 또는 집 PC에서 메모, 사례 후보 및 PDF SHA-256을 다시 확인한다. 개발판에서 `#prepare`와 `#cases`, 비공개 뷰어에서 `#intake`를 연다. 후보는 접수 시 제목·메모·공식 URL·제한된 텍스트로 연결된다.
3. 후속 개발은 규정의 신·구 조문과 적용일을 비교하고 관련 회사별 점검을 다시 여는 작업이다. 종근당의 다음 결산에서 자산 산정 범위와 적용 주총을 대조한다. 지배구조보고서는 정관 반영, 실제 배당액 확정·기준일 및 2027년 제출분의 6주 전 공시 여부를 각각 근거에 연결한다.
4. 사내 PDF·메모의 의미 분석과 반복 갱신 작업은 아직 구성되지 않았다. 공개 수집기와 분리하고, 사내 자료 처리가 허용되는 실행 환경과 전송 승인 범위가 확인되면 OCR·판본 비교·검토 대기열을 추가한다.

## 규정 전문과 사례 발췌의 중앙 적재

[자료별 저장 범위](PROJECT_REQUIREMENTS.md#63-자료별-저장-범위) 및 [실측과 재현 명령](DATA_SOURCES.md#2026-11-27--사례-발췌와-규정-전문-저장-기준)을 따른다. 우선 보관 근거가 확인된 상법·시행령 2개부터 전문 텍스트를 판본·조문과 원문 위치별로 중앙에서 적재할 수 있도록 구현한다. 기존 원본과 인용 ID는 재사용하고 본문·오프셋 해시, 검색 크기, 실제 물리 DB 증가량을 검증한다. 사례는 기존 검토에서 선정한 발췌와 공식 URL·접수 판본을 연결한다. 이전 74개의 보관 근거 확인 절차는 규정 또는 파일별 예외가 승인된 원본에 적용한다.

## 중앙 접수 확인 및 표준정관 후속

승인된 개발 작업공간의 중앙 자료 접수는 [집 PC 인수인계](HOME_PC_HANDOFF.md#중앙-자료-접수)를 따른다. 사이트 9개는 개발 DB에 있다. 2026-11-27 사용자 승인에 따라 기존 회사 PC Auth 계정의 역할을 `editor`로 변경했고, 실제 개발 DB에서 해당 계정의 권한으로 쓰기·읽기를 검증했다. 다음은 로그인한 화면에서 승인된 작은 PDF와 텍스트 저장 → 별도 브라우저 프로필 또는 집 PC에서 재로그인·본문 조회·PDF의 SHA-256 일치 확인이다. 기존 브라우저 자료는 원본별 보관 근거와 승인 범위를 확인해 필요한 것만 접수한다.

상장협 공개 발간목록은 `python scripts/collector.py --check-klca`로 상태 파일 수정 없이 확인한다. 회원 첨부는 보관 근거와 권한을 확인한 뒤 별도 접수한다. 다음 개발은 중앙 접수의 새 원문과 직전 판본 간 변경 위치를 추출해 기존 증거 뷰어와 회사별 판단·검토 이력에 연결하는 것이다. 회사 정관 변경표에는 2026.3.26 가결된 종근당 사업목적·이사 임기, 종근당홀딩스 이사 임기를 반영한 최종 서명본을 기준으로 삼는다.

운영 예약 실행에 반영하려면 main 배포를 승인받는다. 신규 변경 후보는 작성자 확인을 거쳐 승인된 공개 사례로 이동한다.

## 공개 화면 개발 — 공시 반영 사례

기존 GitHub Pages 개발판의 `#cases`에서 자기주식보고서, 배당기준일, 집중투표, 제약·바이오 사례를 확인한다. 같은 형식으로 새 사례를 추가할 때는 규정 및 시행·적용 조건 → 실제 공시 전후(정관 변경안과 가결, 정기보고서와 정정본 등) → 3사 점검 항목의 근거를 확인한 뒤 `src/disclosure-cases.json`을 갱신한다. 자료 모델과 화면의 표시 데이터는 현재 수동 검증본이다. 집 PC에서는 개발 브랜치를 갱신하고 아래 명령을 실행한다.

```powershell
npm.cmd ci
npm.cmd run check
npm.cmd run build -- --dev-preview
npm.cmd run preview -- --dev-preview
# http://127.0.0.1:4175/Key-Disclosure-Points/#cases
```

우선 점검의 자기주식·연구개발 항목에서 관련 사례로 이동할 수 있다. 후속 개발은 신규 규정 탐지 결과에 비교 공시와 승인 상태를 연결하는 것이다. 배당 인용을 제출본에 반영하려면 사내 최종 정관·실제 배당 절차의 승인 근거를 확인한다. 운영 사이트 반영은 별도 승인 후 진행한다.

## 현재 우선 작업 — 집 PC 복원과 후속 원본 이관

2026-11-27 실제 회사 PC 뷰어에서 사용자가 프로젝트 Auth 로그인·법령 원본 열기 성공을 확인했다. [원문 뷰어 Supabase 모드](EVIDENCE_VIEWER.md#supabase-원본-직접-열기)는 승인된 법령 2개·인용 위치 4개의 DB 기록과 원본을 대조한다. 집 PC에서는 별도로 재현한다.

**인증 원문 뷰어의 다음 개발은 문서 버전 비교**다. 개정일·공표일·접수번호 등으로 실제 관계가 확인된 서로 다른 버전을 연결하고 두 원본과 변경 위치를 나란히 보여 준다. 현재 승인 원본 2개는 서로 다른 법령 자료이므로 비교 전후로 묶지 않는다. 초기 개발은 합성 버전으로 검증하고, 실제 비교에는 출처·보관 근거가 확인된 별도 버전 쌍을 사용한다. 담당자 검토 메모는 비교 화면 후속이다.

2026-11-27 회사 PC의 실제 Auth 복원 성공. 승인 workspace에 `viewer`로 접근해 빈 폴더로 법령 2개(679,729바이트)를 복원하고 SHA-256·인용 4개·공개 접근 거부 2개를 확인했다. 이 PC의 결과는 ignored `.local/task01/viewer-restore-check.json`에 있다. 성공 후 동일한 임시 URL이 연결 거부로 표시되는 것은 로컬 검사 서버 종료 때문이다. [집 PC 인수인계](HOME_PC_HANDOFF.md)에 따라 독립된 집 PC에서 같은 복원을 확인한다.

브라우저 검사 서버를 재시작한 뒤에는 `/verify`를 새로고침하지 말고 `http://127.0.0.1:8767/`에서 새 양식을 연다. 기존 Chromium 403은 로컬 양식의 Origin 검사에서 발생했고 수정했다. 실제 Auth/원본 단계의 오류는 화면에 표시된 단계명으로 구분한다.

이 주소는 같은 PC에서 검사 스크립트가 실행되는 동안 활성화된다. `verify_original_restore.py`의 기본 대기 시간은 20분이며 `--wait-minutes 120`으로 늘릴 수 있다. 검사 페이지가 닫혀 있으면 스크립트를 다시 실행하거나 [집 PC 인수인계](HOME_PC_HANDOFF.md)의 PowerShell 직접 복원을 사용한다.

[74개 권리 검토 기록](research/original-retention-review.json)의 각 SHA는 보류 상태다. 새 근거(해당 파일의 이용표시, 실제 권리자의 허락 또는 범위가 명확한 별도 API 응답)가 확인된 항목만 이관 순서에 올린다.

2026-11-26: 추가 연결 계정에서 사용자 지정 조직의 Free/프로젝트 0개·월 $0을 확인하고 서울 `key-disclosure-points-dev`를 생성했다. 전용 DB `ACTIVE_HEALTHY`, core 9개 테이블/RLS·Storage 정책, workspace 1개와 FK 보완 인덱스까지 적용했다. 기존 구축/조직 승인을 다시 묻거나 다른 프로젝트를 중지·재사용·삭제하지 않는다. 실제 account/ref/workspace는 공개 MD에 쓰지 않으며 이 PC의 `.local/task01/approved-target.json`, `cloud-state.json`을 확인한다. 다른 PC에 이 ignored 파일과 credential은 자동 복제되지 않는다.

Supabase 대시보드에서 `kdp-dev-originals`를 생성했다. 원격 SQL로 `public=false`, 10MiB, 허용 MIME `application/pdf`, `text/html`, `application/x-hwp`, `image/jpeg`와 인증 사용자용 정책 2개를 확인했다. 익명 Storage HTTP 요청은 버킷 메타데이터를 받지 못했다. 프로젝트 Auth 계정 1개의 `viewer` membership을 등록하고 원격 SQL에서 승인 workspace 조회와 쓰기 제한을 확인했다.

비공개 버킷과 프로젝트 Auth viewer membership을 구성했다. **법령 HTML 원본 2개, 679,729바이트 이관과 재다운로드 검증 완료.** ready 문서 버전 2개, 근거 4개, 기존 ID 연결 2개를 원격에서 확인했다. Python 69개 통과. 집 PC에서는 `HOME_PC_HANDOFF.md`의 두 원본 부분 복원을 실행한다. 나머지 자료는 `DATA_SOURCES.md`의 보관 근거 확인 후 같은 순서로 이관한다. 백업 및 다른 PC 복원 검증이 남아 있다.

TASK 02의 CLI 조회(`scripts/case_pack.py --anchor`)와 로컬 UI는 같은 원본 해시·버전·정규화 인용 위치를 검증한다.

11월 24일 기존 계정 Free 2개 한도로 실패했던 기록은 과거 이력이다. 76원본 약 27MB의 offline 검증은 원격 이전이 아니다. 출처별 보관 권리·승인 샘플 범위 확인을 건너뛰지 않는다. 집 PC는 먼저 `HOME_PC_HANDOFF.md`를 읽고 코드 clone과 원본/credential 공유를 구분한다.

## 병행 준비 — 사용자 요청 사례 목록

최신 기준은 `CASE_REVIEW_02.md`, `research/priority-case-pack-v2.json`, `research/case-followup-facts.json`이다. 3월 개정 정관 전문·3사 자산 5개·39개 연구개발 절과 종근당 반기 후속 0500 접수를 확보했다. 1차의 정관 전문 미확보·0303만 확인한 상태를 최신 상태로 반복하지 않는다.

```powershell
python scripts/case_pack.py --pack research/priority-case-pack-v2.json
python scripts/case_followup.py
# 이 PC의 hash-named 원본이 있을 때만:
python scripts/case_followup.py --cache .local/case-research/originals
python -m unittest discover -s tests -v
```

다음은 (1) C09 인용문 보완 후보의 원문 대조·담당자 검토 자료 마련, (2) C08 품목명/적응증/별칭별 3년 의미 대사와 직전 계획·수시공시 연결, (3) C03 공식 자산 산정 범위/새 사업연도 수치·소집 사건의 갱신 검토다. 39개 절 확보를 전체 연구개발 누락 검증 완료로 표시하지 않는다. 이미 바뀐 코드·판매 시점·장기 예정일만으로 중단/지연을 확정하지 않는다. 중앙 환경·이관·배포는 아래 승인 경계를 유지한다.

1차 근거 대조는 `CASE_REVIEW_01.md`를 우선 읽는다. `research/priority-case-pack.json`에 22개 공개 자료 메타데이터와 질문 16개가 있고, `python scripts/case_pack.py`로 clone 직후 구조를 검사할 수 있다. 같은 원본이 이 PC의 `.local/case-research/originals/`에 있으면 `--cache .local/case-research/originals`로 원본·텍스트 위치도 검사한다. 캐시는 Git에 없고 중앙 공유도 아직 미구현이다. 원본 없음을 성공으로 간주하지 않는다.

1차 조사에서 남겼던 수집 항목은 위 2차 기록으로 보강되었다. C01의 과거 미첨부 지적은 현재 미해결로 반복하지 않는다. 실제 승인 QA는 비공개 환경에서 담당자 검토 뒤 만든다. LLM 점수/법률 규칙을 자동 승인하지 않는다.

`CASE_CANDIDATES.md`의 공개 후보 10개는 전체 수집 후보 목록으로 유지한다. 4종의 최신 완료/미완료는 위 후속 기록을 따른다. 검토 질문은 공개 후보이고 승인 정답은 아니며 비공개 평가 데이터나 운영 규칙으로 자동 등록하지 않는다. 원격 구축·업로드·배포 승인 경계와 TASK 순서는 유지한다.

기록일 2026-11-26. TASK 00 기준 `67fc2bc`; 이후 커밋은 git log 확인. TASK 01 전용 DB와 비공개 버킷 구축·설정 검증 완료. Auth·실자료 이관 검증은 진행 중.

## 시작 전

```powershell
git status --short
git branch --show-current
git pull --ff-only
Get-Content PROJECT_REQUIREMENTS.md
Get-Content AGENTS.md
Get-Content DEVELOPMENT_STATUS.md
```

개발 브랜치: `codex/task-00-cloud-foundation`. main으로 변경하거나 merge/push/배포하지 않는다. 실행 대상 project ref가 문서/환경변수/사용자 승인과 같지 않으면 연결하지 않는다.

## 남은 환경·자료 확인 범위

1. 전용 Free 개발 DB는 추가 연결 계정에서 생성·고정했다. 실제 ref/용도/월 $0 확인일은 ignored 승인 기록을 따른다. 기존 업무 프로젝트와 혼동하지 않는다.
2. core schema/RLS/private bucket 구축은 이번 요청의 승인 범위다. 확정된 독립 개발 대상에서 수행하고 운영 Pages/Actions/Sites/D1의 기준 저장소·Secret은 변경하지 않는다.
3. 공개 출처별 보관 권리·샘플 이관 범위를 확인한다. `DATA_SOURCES.md`의 PDF 1개+DART HTML 1개 약 3.06MB와 연구 묶음 76개 약 27MB는 다른 묶음이다. 내부자료·개인 PDF·메일 이력·실제 평가 정답은 제외한다. 출처 확인을 이용 권리 확인으로 대신하지 않는다.

승인 기록에는 대상 ref·용도·Free 비용 확인일·자료 범위·권한·rollback을 명시한다. 계정 키는 채팅/MD에 전달하지 말고 각 PC의 승인된 환경변수/Secret에 설정한다. `.env.example` 변수명 사용. 인증 토큰/DB 비밀번호는 공개 Git이나 browser에 넣지 않는다.

## 승인 뒤 TASK 01 체크리스트

- [x] CLI 3.3.0 help/version·local 기본 target 확인, CLI로 migration 생성. PGlite 0.6.0 격리 설치로 로컬 PostgreSQL/WASM SQL/RLS 검사. Docker Supabase stack 검증은 별도 미완료.
- [x] 사용자 지정 추가 연결 조직의 Free·월 $0·빈 전용 개발 ref·health와 사용량 확인. 실제 식별자는 ignored 승인 기록.
- [x] 실제 개발 Supabase에 core와 인덱스 migration 적용, hosted SQL 15개/익명 REST 거부·advisors 검증.
- [x] 비공개 버킷 생성, 파일 제한·정책과 익명 버킷 메타데이터 미노출 확인.
- [x] 개발 브랜치를 별도 폴더에 GitHub에서 새로 clone하고 집 PC용 Auth/workspace 연결 확인 명령을 준비했다.
- [x] 프로젝트 Auth 계정과 승인 workspace의 viewer membership을 등록하고 원격 SQL에서 읽기 허용·쓰기 제한 확인.
- [x] 회사 PC에서 실제 프로젝트 Auth 로그인·viewer workspace 조회·비공개 원본 2개 복원 및 공개 접근 거부 확인.
- [ ] 집 PC에서 프로젝트 Auth로 같은 workspace와 원본을 조회.
- [ ] 다른 workspace의 비회원 Auth 세션으로 원본 HTTP 접근 거부 확인. 원격 SQL의 비회원 권한 검사는 기존에 완료.
- [x] trusted membership, workspace 복합 FK, revision 조건 갱신/증가, sources/documents/versions/files/legacy map/jobs와 Storage INSERT/SELECT SQL 구현·로컬 검사.
- [x] 법령 2개에서 승인 배치 staging → 비공개 업로드 → 독립 다운로드 SHA/길이 → 기존 ID/FK → ready 순서 검증.
- [x] `central_ingest.py`의 멱등 staging/finish와 `central_sync.py` 부분 복원 구현. 대시보드 업로드 경로 검증.
- [ ] 권리 확인 후 나머지 74개 연구 원본 및 별도 PDF/DART 후보 이관. 승인 계정의 API 전송 및 전체 backup/restore 검증.
- [ ] 재실행 중복 방지, 다중 PC 동시 편집 충돌, 실패 후 재개, anon/다른 workspace 접근 거부 및 QA/holdout 격리 테스트.
- [ ] 두 번째 깨끗한 개발 환경에서 같은 데이터/원본 조회. 실제 집 PC 검증이 없으면 시뮬레이션과 구분.
- [ ] DB와 Storage를 각각 백업·복원해 검증. 이전 로컬 데이터는 보존.
- [ ] TASK 01 완료 증거·미완료·다음 TASK 02를 MD에 기록. 운영 연결/배포는 별도 승인.

## 승인 전 가능한 로컬 작업

실제 자료 전송 없이 fixture 기반 parser·ID/근거 mapping·권한 테스트 설계를 확장할 수 있다. 로컬 테스트를 원격 DB/Storage 구축 완료로 표시하지 않는다. 상세 inventory를 다른 PC로 복사하려면 별도 승인된 비공개 저장소가 필요하며 공개 repo에는 집계만 남긴다.

현재 문의할 필요가 없는 항목: 신규 프론트엔드 재구축, 유료 모델 전환, 공개 운영 메뉴 복구, 수집 주기 변경. 모두 현재 우선 작업이 아니다.

## 알려진 의존성 점검

기존 esbuild 0.28.0: npm audit low 1건(GHSA-g7r4-m6w7-qqqr). Windows dev server 사용 여부와 0.28.2 패치 적용을 검토한다. baseline 버전은 이번 단계에서 변경하지 않았고 audit fix --force를 실행하지 않았다. 실제 DB 구축 승인과 별개로 로컬 패치·회귀 검증 계획을 기록한다.
