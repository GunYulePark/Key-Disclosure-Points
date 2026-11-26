# 다음 작업 — TASK 01

## 현재 우선 작업 — 승인된 구축의 환경 확보

2026-11-26 재확인. 같은 계정의 새 조직도 무료 프로젝트 한도를 공유한다. 무료 여유가 있는 별도 Supabase 계정에서 전용 환경을 확보할 수 있다. 새 계정이 연결되면 조직·프로젝트 목록과 비용을 확인해 승인 대상 ref를 고정한다. 기존 두 프로젝트는 용도가 있고 최근 로그도 있어 현 상태에서 임의 중지·재사용 대상이 아니다. 조사 범위는 `DEVELOPMENT_STATUS.md`를 참고한다.

2026-11-24 중앙 DB/private 원본 저장소 구축과 TEST 조직 전용 Free 프로젝트 생성은 사용자 승인됐다. get_cost 월 $0 → 서울 `key-disclosure-points-dev` create 시도 → 계정 active Free 2개 한도 거절. 신규 프로젝트/원격 migration/bucket/업로드는 없다. 환경 확보 방식 질문의 답변부터 확인한다. 기존 구축/조직 승인을 다시 묻지 않는다. 다른 업무 프로젝트 중지·재사용·삭제나 유료 전환은 승인되지 않았다.

`supabase/README.md`와 `20261124080839_kdp_central_core.sql`이 최신 로컬 구현 기준이다. core 9개 테이블·RLS/FK·private Storage 정책, offline plan/bucket 검사·명시 생성/인증 reader 복원 도구까지 준비했다. Python 63개와 PostgreSQL/WASM SQL 24개 통과. 실제 76원본 offline 검증. 원격 bootstrap·server ingestion adapter·샘플 이관·advisors·Auth/Storage HTTP·백업 복원·두 PC 동일 조회는 남아 있다. CLI `migration list`는 local stack 미기동으로 실패했다.

집 PC에서 시작한다면 먼저 `HOME_PC_HANDOFF.md`를 읽는다. 개발 브랜치 clone만으로 원본 76개가 복구되지 않는다. 우선순위는 독립 개발 환경 확보·TASK 01 승인 범위 확인과 중앙 DB/private Storage 구축이며, 사례 추가로 중앙 공유 구축을 완료한 것으로 대신하지 않는다.

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

기록일 2026-11-24. TASK 00 코드/설계 기준 커밋 `67fc2bc`; 이후 검증 기록 커밋은 git log 확인. TASK 00 진단·로컬 검증·설계 완료. 원격 구축은 아직 시작하지 않았다.

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

1. 전용 Free 생성은 시도 후 한도로 거절됐다. 사용자가 선택한 환경 확보 방식을 확인하고 실제 개발 ref/용도/비용을 고정한다. 새 조직만으로 계정의 Free 한도가 초기화된다고 가정하지 않는다. 기존 프로젝트는 임의 변경하지 않는다.
2. core schema/RLS/private bucket 구축은 이번 요청의 승인 범위다. 확정된 독립 개발 대상에서 수행하고 운영 Pages/Actions/Sites/D1의 기준 저장소·Secret은 변경하지 않는다.
3. 공개 출처별 보관 권리·샘플 이관 범위를 확인한다. `DATA_SOURCES.md`의 PDF 1개+DART HTML 1개 약 3.06MB와 연구 묶음 76개 약 27MB는 다른 묶음이다. 내부자료·개인 PDF·메일 이력·실제 평가 정답은 제외한다. 출처 확인을 이용 권리 확인으로 대신하지 않는다.

승인 기록에는 대상 ref·용도·Free 비용 확인일·자료 범위·권한·rollback을 명시한다. 계정 키는 채팅/MD에 전달하지 말고 각 PC의 승인된 환경변수/Secret에 설정한다. `.env.example` 변수명 사용. 인증 토큰/DB 비밀번호는 공개 Git이나 browser에 넣지 않는다.

## 승인 뒤 TASK 01 체크리스트

- [x] CLI 3.3.0 help/version·local 기본 target 확인, CLI로 migration 생성. PGlite 0.6.0 격리 설치로 로컬 PostgreSQL/WASM SQL/RLS 검사. Docker Supabase stack 검증은 별도 미완료.
- [ ] 승인된 개발 project ref의 읽기 전용 연결/계정·용도 확인. 실제 사용량과 Free 상태/비용 확인.
- [ ] 로컬 core migration을 실제 개발 Supabase에서 검증·적용하고 advisors/실 Auth/Storage API를 확인한다. local fixture 통과를 원격 성공으로 대체하지 않는다.
- [x] trusted membership, workspace 복합 FK, revision 조건 갱신/증가, sources/documents/versions/files/legacy map/jobs와 Storage INSERT/SELECT SQL 구현·로컬 검사.
- [ ] `central_sync.py`의 기본 offline plan/target 제한/bucket/reader 복원에 더해 멱등 DB seed·승인 자료 server ingestion/upload adapter를 구현·실 검증한다. 기존 `central_contract.py`는 순수 함수로 유지한다.
- [ ] 이전 후보의 원본/URL/기존 ID/해시 재확인 → 백업 → staging → upload → 독립 download SHA/길이 검증 → 기존 근거 alias/FK → ready 순서 검증.
- [ ] 재실행 중복 방지, 다중 PC 동시 편집 충돌, 실패 후 재개, anon/다른 workspace 접근 거부 및 QA/holdout 격리 테스트.
- [ ] 두 번째 깨끗한 개발 환경에서 같은 데이터/원본 조회. 실제 집 PC 검증이 없으면 시뮬레이션과 구분.
- [ ] DB와 Storage를 각각 백업·복원해 검증. 이전 로컬 데이터는 보존.
- [ ] TASK 01 완료 증거·미완료·다음 TASK 02를 MD에 기록. 운영 연결/배포는 별도 승인.

## 승인 전 가능한 로컬 작업

실제 자료 전송 없이 fixture 기반 parser·ID/근거 mapping·권한 테스트 설계를 확장할 수 있다. 로컬 테스트를 원격 DB/Storage 구축 완료로 표시하지 않는다. 상세 inventory를 다른 PC로 복사하려면 별도 승인된 비공개 저장소가 필요하며 공개 repo에는 집계만 남긴다.

현재 문의할 필요가 없는 항목: 신규 프론트엔드 재구축, 유료 모델 전환, 공개 운영 메뉴 복구, 수집 주기 변경. 모두 현재 우선 작업이 아니다.

## 알려진 의존성 점검

기존 esbuild 0.28.0: npm audit low 1건(GHSA-g7r4-m6w7-qqqr). Windows dev server 사용 여부와 0.28.2 패치 적용을 검토한다. baseline 버전은 이번 단계에서 변경하지 않았고 audit fix --force를 실행하지 않았다. 실제 DB 구축 승인과 별개로 로컬 패치·회귀 검증 계획을 기록한다.
