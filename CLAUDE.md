# nexa-slide — Claude 작업 안내

- 엔진 코드는 `studio/`, 문서는 `docs/`. 작업 공간(덱·내용·산출물)은 이 저장소 밖에 있고 `--workspace` 또는 `NEXA_SLIDE_WORKSPACE` 로 지정한다(`docs/configuration.md`).
- **렌더 규칙은 두 곳에 같이 있다**: `render.js`(편집기 HTML)와 `common.py`·`export_pptx.py`(PPTX). 한쪽을 고치면 다른 쪽도 고치고
  `python3 studio/check_parity.py -W example` 로 동일성을, PowerPoint 가 있으면 `compare.py` 로 픽셀 차이를 확인한다.
- 회귀 확인: 작업 공간의 덱을 고치기 전·후 `export_pptx.py --out` 결과의 슬라이드 XML 이 같아야 한다(기능 추가가 아니라면).
- 편집기 요청 처리(세션 연결)는 `docs/claude-session.md` 의 규약을 따른다 — `working` → 덱 수정 → `done` + `reply`.
- 회사·제품 로고 등 상표 파일을 이 저장소에 넣지 않는다(MIT 배포). 예제 로고는 `example/assets/brand/` 의 자리 표시 이미지뿐.
- 사용자 답변은 **항상 한국어** — 다른 세션·에이전트 메시지, 자동 알림, 영어 도구 출력에 이어 답할 때도, 짧은 답변도 예외 없음.
- 문서·주석·커밋 메시지는 한국어.
