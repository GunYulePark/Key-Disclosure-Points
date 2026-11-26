# 원문 검토 개발 미리보기

TASK 02의 개발 화면은 로컬 캐시 또는 개발 프로젝트의 비공개 원본을 읽는다. 공개 Pages 빌드와 별도의 진입점이며 개발 결과물은 ignored `.local/task02/site`에 생성한다.

## 실행

저장소 루트에서 기존 Node/Python 의존성을 설치하고 아래 명령을 실행한다. 집 PC의 환경 설정과 이관된 원본 복원 방법은 [HOME_PC_HANDOFF.md](HOME_PC_HANDOFF.md)를 참조한다.

```powershell
npm.cmd ci
.venv/Scripts/python.exe -m pip install -r requirements.txt
node scripts/build-evidence.mjs
.venv/Scripts/python.exe scripts/serve_evidence.py --target .local/task01/approved-target.json
```

브라우저에서 `http://127.0.0.1:8766/`을 연다. 원문별 `#viewer/{version_id}/{evidence_id}` 링크를 복사해 해당 원본을 가진 다른 개발 PC에서 열 수 있다. 제목 검색 후 인용을 선택하면 해당 문단 또는 표의 텍스트가 강조된다. PDF에서는 인용 쪽으로 바로 열고 배율·회전·페이지를 바꿀 수 있다. HWP는 검증된 인용 주변 텍스트를 표시하고, 이미지 자료는 기록된 수동 확인 위치와 원본 이미지를 표시한다. 원본이 빠지거나 바뀐 경우 화면에서 확인할 수 있다.

## Supabase 원본 직접 열기

[집 PC 인수인계](HOME_PC_HANDOFF.md)의 승인 대상 파일과 환경변수를 먼저 설정한다. 이 모드에는 개발 프로젝트의 publishable key와 프로젝트 Auth 계정이 필요하다.

```powershell
node scripts/build-evidence.mjs
.venv/Scripts/python.exe scripts/serve_evidence.py --target .local/task01/approved-target.json --cloud --port 8768
```

같은 PC의 브라우저에서 `http://127.0.0.1:8768/`을 열고 프로젝트 Auth 계정으로 로그인한다. 승인된 작업공간과 DB에서 검증된 버전의 원본이 목록에 표시된다. 현재 대상은 이미 이관한 법령 2개다. 이 모드에서는 사본을 먼저 복원해둘 필요 없이 선택할 때마다 Supabase에서 읽는다. 종료할 때 화면의 **로그아웃**을 사용한다. 로그인 세션은 최대 30분이며 만료되면 다시 로그인한다.

운영 환경의 배포와는 별개인 루프백 전용 개발 기능이다. 뷰어는 서명 URL이나 관리 키를 사용하지 않는다. 원본은 사용자의 실제 Storage RLS를 거쳐 받으며, 사용자 토큰과 세션은 브라우저 저장소나 디스크에 기록하지 않는다.

## 검증과 저장

- 원본 파일의 길이와 SHA-256, 문서 버전, 인용 위치를 함께 대조한다. 복수 문서에 같은 문구가 나와도 해당 버전의 저장된 위치로만 이동한다.
- HTML은 승인된 태그와 표의 병합 속성만 재구성한다. 링크, 이벤트 처리기, 스크립트, 외부 리소스는 원본 HTML에서 가져와 실행하지 않는다. 공식 출처는 카탈로그 메타데이터의 HTTPS 주소로 열 수 있다.
- PDF 좌표는 PyMuPDF의 미회전 CropBox 좌표에서 PDF.js 표시 좌표로 변환한다. 해시 또는 텍스트가 일치하지 않거나 페이지 기하 정보가 다르면 강조를 표시하지 않는다.
- 로컬 캐시 모드는 원본 캐시를 읽고 Auth 입력을 받지 않는다. Supabase 모드는 로그인, 작업공간 권한, 승인 출처·ready 버전·verified 파일·일치하는 인용과 원본 bytes를 확인한다. 두 모드는 데이터 경로를 섞지 않는다.
- 이번 범위는 연구 묶음의 보관된 버전을 검증하며 읽는 화면이다. DB의 구조화 좌표 저장, 버전 비교, 승인·반려·메모, OCR은 후속 작업이다. 로컬 테스트 통과를 실제 계정 로그인이나 운영 배포로 해석하지 않는다.
