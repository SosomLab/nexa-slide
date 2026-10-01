# 변경 이력

## 0.3.0 — 2026-10-01 · 레이아웃 검사

- `check_layout.py` + `GET /api/check/<id>` + 편집기 "검사" 탭(저장마다 자동 · 항목 클릭 = 요소로 이동·영역 표시 · 썸네일 ⚠ 배지).
- 규칙: `t1.overlap.text-text` · `t1.overlap.text-crosses-border` · `t2.cutoff.spill` · `t2.cutoff.container` · `t3.offslide` · `t4.font.min`(역할별 최소 pt) · `t5.mono.align`(실행계획 열 정렬).
  Genspark `check_slide_layout` 실측(규칙 id·기하 판정)을 본뜨고, Genspark 에 없는 최소 글자·고정폭 정렬·요소 이동을 더했다.
- 기준 설정 `nexa-slide.json` `check`(minFontPt · ignore · ignoreSlides).
- 검사로 찾은 실제 결함 예(교재 덱): 파일 경로 줄바꿈 겹침, 장 표지 설명 넘침, 8.25pt 글자.

## 0.2.0 — 2026-10-01 · 독립 저장소로 분리

sql-tutorial-with-oracle 저장소의 `ppt/studio`(슬라이드 스튜디오 v0)를 엔진으로 분리했다. 렌더·PPTX 규칙은 그대로다
(분리 전후 ch00·ch18 덱 빌드 JSON 과 PPTX 184·259 파트가 완전히 같음).

- **작업 공간 분리**: `--workspace` / `NEXA_SLIDE_WORKSPACE` / 위로 찾기, 설정 `nexa-slide.json`(경로·`assetRoot`·토큰·브랜드·부 이름·표지 배지·EoD 안내·포트).
  - URL `/studio/`(엔진) · `/out/`(산출물) · 그 밖 `assetRoot`.
- **여러 작업 공간 동시 운영**:
  - 작업 공간별 포트
  - 작업 공간당 서버 하나(중복 시작 거부)
  - 배타적 포트 열기(Windows `SO_EXCLUSIVEADDRUSE`)
  - `service.py start|stop|restart|status|url` 백그라운드 서비스, `status.py`
  - 실행 정보 `out/.studio/server.json`
- **Claude 세션 연결**:
  - `watch_requests.py --stream`(요청 묶음마다 JSON 한 줄 — Monitor 알림), 하트비트 `out/.studio/session.json`
  - 작업 공간당 감시 하나(중복 시 `refused`)
  - 편집기 세션 칩(연결됨/처리 중/연결 없음) · "요청 보내기"/"지금 보내기"(flush) · 요청 상태 `working`
- **배포**: MIT `LICENSE`, `THIRD_PARTY_NOTICES.md`(외부 구성요소 재배포 없음, 회사 CI 미포함), 예제 작업 공간 `example/`(자리 표시 로고), 문서 `docs/` 7편.

## 0.1 — 2026-09 · 슬라이드 스튜디오 v0 (sql-tutorial-with-oracle `ppt/studio`)

덱 JSON 단일 원본, 브라우저 편집기, python-pptx 기본 도형 PPTX, PowerPoint 렌더 미리보기·픽셀 비교, 요청 메모 → 세션 전달(1회 감시).
이력은 원 저장소 git 기록에 있다.
