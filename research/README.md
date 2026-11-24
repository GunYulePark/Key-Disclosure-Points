# 우선 사례 근거 묶음

최신 추가 조사: `priority-case-pack-v2.json`과 `case-followup-facts.json`, 루트 `CASE_REVIEW_02.md`. v2는 원래 묶음을 보존한 채 자료 76단위/텍스트 위치 97개로 확장했다. 자산 5개 사실(연차·분기 10개 셀), 연구개발 39개 선정 절과 문맥 검토 항목을 연결한다. 이전 묶음은 1차 조사 재현용으로 유지한다.

`priority-case-pack.json`은 C01/C03/C08/C09의 공개 자료 22개, 텍스트 위치 40개, 시각 확인 이미지 위치 3개와 검토 질문 16개를 담는다. 평가 정답·담당자 승인·활성 법률 규칙은 포함하지 않는다. 상세 조사 결과는 루트 `CASE_REVIEW_01.md`를 읽는다.

공식 원본을 읽어 SHA-256·길이·문서 버전·짧은 인용 위치를 고정했다. PDF 위치는 **파일의 1부터 시작하는 페이지 번호**다. 텍스트 start는 기존 collector/plain 또는 PyMuPDF/HWP 추출 결과에서 공백만 제거한 문자열의 0부터 시작하는 위치다. HTML DOM 경로·PDF 하이라이트 좌표는 아직 제공하지 않는다. 스캔 정관/날인 보고서의 visual 위치는 수동 시각 확인이며 OCR 성공을 뜻하지 않는다.

## 검증

프로젝트 requirements 설치 후 저장소 루트에서:

```powershell
python scripts/case_pack.py
python scripts/case_pack.py --cache .local/case-research/originals
python scripts/case_pack.py --pack research/priority-case-pack-v2.json
python scripts/case_followup.py
python scripts/case_followup.py --cache .local/case-research/originals
python -m unittest discover -s tests -v
```

첫 명령은 공개 메타데이터·참조·승인 상태만 확인한다. 두 번째는 해당 PC에 원본 캐시가 있을 때만 22개 원본의 hash/길이와 자동 텍스트 위치를 재검증한다. 이미지 내용의 판독을 자동 검증하지 않는다. 원본이 없으면 실패하며 메타데이터 성공으로 대신하지 않는다. 이 도구는 네트워크·AI·DB·메일·배포 호출을 하지 않는다.

원본은 이 PC의 `.local/case-research/originals/<sha256>.<format>`에만 보관했다. Git clone은 원본을 가져오지 않는다. 다른 PC에서 동일한 원본을 검증하려면 승인된 중앙 저장소가 준비되거나 공개 URL에서 개별 자료를 다시 확보해야 한다. 재확보 결과의 해시가 다르면 과거 버전을 덮어쓰지 말고 자료 변경 여부를 확인해 새 source version/근거를 생성한다. 중앙 DB의 샘플 이관 승인 범위에 이 묶음 22개를 자동 추가하지 않는다.

현재 샘플 확인은 법적 판단 정확도·LLM 성능 평가가 아니다. 지침 권고/법적 의무, 제안/가결, 작성기준일/제출일, 과거 누락/후속 보완을 구분한 답변은 담당자 검토 후 비공개 QA로 별도 관리한다. 같은 개정과 회사의 변형 질문을 서로 다른 train/holdout에 섞지 않는다.

v2와 후속 사실 파일의 연결 지문은 정렬된 키·고정 구분자의 canonical JSON을 SHA-256으로 계산한다. Windows Git의 CRLF 변환이나 들여쓰기는 내용 변경으로 보지 않는다. PDF/HTML/HWP/이미지 **원본 파일 해시에는 정규화를 적용하지 않는다.** 사실 검증기의 셀 좌표는 0부터 시작하는 table/row/cell 순서이며, 지원하지 않는 중첩 재무 표는 판정을 중단한다. 법적 재무 기준을 자동 승인하거나 문자열 미관찰을 임상 중단으로 분류하지 않는다.
