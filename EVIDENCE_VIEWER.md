# 원문 검토 로컬 미리보기

TASK 02의 개발 화면은 같은 PC의 원본 캐시를 읽는다. 공개 Pages 빌드와 별도의 진입점이며 개발 결과물은 ignored `.local/task02/site`에 생성한다.

## 실행

저장소 루트에서 기존 Node/Python 의존성을 설치하고 아래 명령을 실행한다. 집 PC의 환경 설정과 이관된 원본 복원 방법은 [HOME_PC_HANDOFF.md](HOME_PC_HANDOFF.md)를 참조한다.

```powershell
npm.cmd ci
.venv/Scripts/python.exe -m pip install -r requirements.txt
node scripts/build-evidence.mjs
.venv/Scripts/python.exe scripts/serve_evidence.py --target .local/task01/approved-target.json
```

브라우저에서 `http://127.0.0.1:8766/`을 연다. 원문별 `#viewer/{version_id}/{evidence_id}` 링크를 복사해 해당 원본을 가진 다른 개발 PC에서 열 수 있다. 제목 검색 후 인용을 선택하면 해당 문단 또는 표의 텍스트가 강조된다. PDF에서는 인용 쪽으로 바로 열고 배율·회전·페이지를 바꿀 수 있다. HWP는 검증된 인용 주변 텍스트를 표시하고, 이미지 자료는 기록된 수동 확인 위치와 원본 이미지를 표시한다. 원본이 빠지거나 바뀐 경우 화면에서 확인할 수 있다.

## 검증과 저장

- 원본 파일의 길이와 SHA-256, 문서 버전, 인용 위치를 함께 대조한다. 복수 문서에 같은 문구가 나와도 해당 버전의 저장된 위치로만 이동한다.
- HTML은 승인된 태그와 표의 병합 속성만 재구성한다. 링크, 이벤트 처리기, 스크립트, 외부 리소스는 원본 HTML에서 가져와 실행하지 않는다. 공식 출처는 카탈로그 메타데이터의 HTTPS 주소로 열 수 있다.
- PDF 좌표는 PyMuPDF의 미회전 CropBox 좌표에서 PDF.js 표시 좌표로 변환한다. 해시 또는 텍스트가 일치하지 않거나 페이지 기하 정보가 다르면 강조를 표시하지 않는다.
- 로컬 캐시가 없는 다른 PC는 Supabase 인증 복원 후 사용할 수 있다. 서버는 루프백 주소에만 바인딩한다. Auth 세션과 토큰은 이 미리보기 서버에 필요하지 않다.
- 이번 범위는 연구 묶음의 보관된 버전을 검증하며 읽는 화면이다. 인증된 서버에서 직접 읽는 공용 Viewer, DB의 구조화 좌표 저장, 버전 비교, 승인·반려·메모, OCR은 후속 작업이다. 로컬 테스트 통과를 Supabase 로그인 성공이나 운영 배포로 해석하지 않는다.
