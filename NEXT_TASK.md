# 다음 작업 — TASK 01

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

## 사용자가 결정·승인해야 할 구체적 범위

1. **독립 Free 개발 프로젝트**를 사용할 계정/조직 및 프로젝트. 현재 연결된 무료 조직의 2개 active 프로젝트는 다른 업무용이며 자동 재사용하지 않는다. 추가 Free 생성 가능 여부/현재 제한을 확인한다. 기존 프로젝트 pause/delete 또는 Pro 전환은 요청하지 않고 대안으로 자동 실행하지도 않는다.
2. 확보한 개발 프로젝트에서 core DB schema·RLS·private bucket 생성 및 최소권한 연결을 허용할지 확인한다. 운영 Pages/Actions/Sites/D1의 기준 저장소·Secret은 변경하지 않는 범위다.
3. `DATA_SOURCES.md`의 PDF 1개+DART HTML 1개 약 3.06MB를 private 개발 Storage에 보관할 권리와 샘플 이관을 승인한다. 회사 내부자료·개인 PDF·메일 이력·실제 평가 정답은 제외한다.

승인 기록에는 대상 ref·용도·Free 비용 확인일·자료 범위·권한·rollback을 명시한다. 계정 키는 채팅/MD에 전달하지 말고 각 PC의 승인된 환경변수/Secret에 설정한다. `.env.example` 변수명 사용. 인증 토큰/DB 비밀번호는 공개 Git이나 browser에 넣지 않는다.

## 승인 뒤 TASK 01 체크리스트

- [ ] 최신 CLI help/version/remote 동작을 확인하고 재현 가능한 버전을 pin한다. local PostgreSQL 환경 확보; 현재 이 PC에서는 CLI/Docker/psql이 PATH에서 확인되지 않았다.
- [ ] 승인된 개발 project ref의 읽기 전용 연결/계정·용도 확인. 실제 사용량과 Free 상태/비용 확인.
- [ ] `DATA_SCHEMA.md` 최소 schema를 로컬에서 구현·권한/advisors 테스트. migration 파일은 CLI로 생성한다. 임의 파일명/운영 schema 변경 금지.
- [ ] trusted membership, workspace 복합 FK, revision CAS, sources/documents/versions/files/legacy map/ingestion 상태, private Storage INSERT/SELECT 정책 구현.
- [ ] `--dry-run` 기본값·별도 apply 승인·대상 ref allowlist·no-overwrite를 갖는 server-only adapter 작성. 현재 `central_contract.py`는 순수 함수이며 DB adapter가 아니다.
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
