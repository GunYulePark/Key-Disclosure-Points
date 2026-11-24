# 회사·집 개발 재현 및 승인 후 중앙 저장소 운영

## 새 PC / 새 Codex 세션

아래는 저장소 루트에서 실행한다. Node 24.x(기존 Actions 기준), Python 3.12.x 권장. 런타임 버전을 설치한 뒤 먼저 `node --version`, `python --version`, `git --version`을 확인한다. `package-lock.json`과 `requirements.txt`를 유지한다.

```powershell
git clone --branch codex/task-00-cloud-foundation https://github.com/GunYulePark/Key-Disclosure-Points.git
cd Key-Disclosure-Points
git status --short
git branch --show-current
git pull --ff-only
Get-Content AGENTS.md
Get-Content DEVELOPMENT_STATUS.md
Get-Content NEXT_TASK.md
npm ci
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe -m unittest discover -s tests -v
npm run check
npm run build
npm run preview
```

PowerShell 실행 정책 때문에 activate가 막혀도 위처럼 venv Python 경로를 직접 쓰면 된다. Linux/macOS에서는 `.venv/bin/python`으로 바꾼다. `npm run build`는 로컬 `docs/`를 재생성하며 배포하지 않는다. 프리뷰는 기존 `scripts/serve.mjs`의 출력 URL을 사용한다.

`.env.example`을 `.env`로 복사하되 TASK 00에서는 값을 비워 두고 중앙 저장소를 disabled로 유지한다. 원격 개발 프로젝트 승인 후 각 PC에서 개별적으로 Secret을 설정한다. 키를 MD/채팅에 붙이지 않는다. 브라우저 개인 PDF는 Git clone으로 옮겨지지 않는다.

이 저장소 밖의 legacy Python 테스트·원본과 private Sites 소스는 clone에 포함되지 않는다. 필요 시 회사 보안/저장소 권한을 확인해 별도 승인된 위치에서 복구한다. private 앱은 현재 clone으로 전체 재현된다고 주장하지 않는다.

## 로컬 조사 도구

```powershell
# --workspace는 조사할 승인된 작업 폴더. 경로는 실행한 PC에서 지정한다.
python scripts/workspace_inventory.py --workspace <작업폴더> --output .local/task00
```

stdout은 집계만, 상세 파일/샘플 경로는 `.local/task00/`에 저장한다. symlink/junction·비밀파일·dependencies·빌드·tmp·DB cache·외부 폴더·IndexedDB는 조사하지 않는다. 이 도구는 네트워크/SQL/업로드를 수행하지 않으며 `transfer_approved=false`로만 만든다. 원본이 없는 새 clone에서 원본 수가 0이라고 기존 자료가 삭제됐다고 해석하지 않는다.

## 예상 용량·호출량 (계획값과 실측 분리)

- 실측 샘플: PDF+HTML 3,060,820 bytes, 신규 객체 2개 후보. 재시도 제외 최초 upload 2회 + 다운로드 검증 2회, 두 번째 환경 다운로드 2회가 최소 가정이다. DB API/권한 테스트 호출은 추가된다.
- 공식 출처/hash 매칭 파일 합계 약 20.25MB는 중복 사본 포함·권리 미승인이다. 이 값을 전체 이관 승인량으로 쓰지 않는다.
- 초기 샘플 metadata/근거 DB 예산은 5MB 이내를 목표로 설정하되 실제 `pg_total_relation_size`와 인덱스로 측정한다. 아직 실 DB 사용량은 미측정이다.
- 향후 2,000 chunks × 768 float32라는 **가정**이면 벡터 원시 배열은 6,144,000 bytes다. 모델 dimension 확정 전 설계 예시이며 text/row/index/백업 비용은 별도다. 50,000 × 1,536 float32만으로 약 307.2MB가 되므로 처음부터 대규모 embedding/index를 만들지 않는다.
- Free 용량/paused 상태/프로젝트 여유·요금은 TASK 01 직전에 공식 정책과 대상 계정에서 다시 확인한다. 비용 get_cost/명시 Free 상태 확인 없이 생성하지 않는다.

## 승인 후 순서와 rollback

1. 전용 개발 프로젝트 확보 → 읽기 전용 연결 검사 → local schema/RLS 검증 → migration/정책 승인 적용.
2. private originals bucket → 승인 샘플만 staging 업로드 → 독립 다운로드 SHA 검증 → 근거/legacy mapping → ready 전환.
3. 두 환경 조회/권한 거부/동시성/재실행/복원 테스트 결과를 상태 문서에 기록.
4. 실패하면 snapshot/ready 전환을 중단하고 이전 상태로 조회한다. staging 레코드·객체는 오류 표시 후 보존한다. cleanup/삭제는 승인 후 수행한다.

현재 중앙 연결은 없고 운영 수집 워크플로도 변경하지 않았다. TASK 01에서 Secret/수집기 연결을 추가하는 것은 별도 승인 단계다. 기존 main push 자동 배포가 있으므로 main push/merge/dispatch 금지. 개발 브랜치에서만 작업한다.

## 다음 세션 시작 문구

> PROJECT_REQUIREMENTS.md, AGENTS.md, ROADMAP.md, DEVELOPMENT_STATUS.md, NEXT_TASK.md를 읽고 현재 브랜치와 승인된 개발 환경을 확인해라. TASK 01 승인이 없거나 개발 프로젝트가 미선정이면 로컬 설계/fixture 작업까지만 진행해라. 원본·기존 ID·현재 운영을 보존하고 비공개 자료·holdout·Secret을 노출하지 마라. 작업 결과와 다음 단계를 MD에 기록해라.
