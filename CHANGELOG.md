# 변경 이력

## 0.7.0 - 2026-10-02 · 시작 페이지 · 기본 메뉴 · 제작 도구와 내용 분리

- 엔진에 슬라이드 내용을 두지 않는다: 작업 공간을 못 찾으면 현재 폴더를 쓰지 않고, 서버는 **허브(시작 페이지)** 로 뜬다(포트 5599, 실행 정보는 사용자 설정 폴더). 엔진 폴더 안의 작업 공간(`example/`)은 서버가 열지 않는다. 작업 공간이 필요한 도구는 안내를 내고 끝난다.
- 기준 폴더: 운영체제 기본 문서 폴더(Windows 알려진 폴더 - OneDrive 이동 포함, macOS `~/Documents`, Linux XDG) 아래 `NexaSlide/`, 제작마다 하위 폴더. `NEXA_SLIDE_PROJECTS` · 사용자 설정 `projectsRoot` 로 바꾼다. 사용자가 폴더·저장소를 지정하면 그 아래에 내용과 서버 실행 정보를 넣는다(`studio/paths.py`).
- 시작 페이지 `studio/home.html`(`hub.py`): 새 슬라이드 만들기(템플릿 · 목적·대상·작성 방향·참고 자료 → `BRIEF.md` · 저장 위치 · 첫 초안 요청), 폴더·저장소 열기(폴더 고르기 창, 작업 공간 없으면 그 자리에 만들기), 최근 작업, 튜토리얼, 데모(예제를 기준 폴더로 복사해 열기), 템플릿 목록, 샘플 사이트 등록·둘러보기.
- `/` 이동: 작업할 덱이 있으면 Studio, 없으면 시작 페이지. 만들기·열기는 그 작업 공간 서버를 띄워 Studio 로 넘긴다.
- 기본 메뉴 `studio/menu.js`: Studio·시작 페이지 머리줄 왼쪽 위 메뉴 단추 → 왼쪽 서랍(GitHub 방식) - 홈 · 새로 만들기 · 열기 · Studio · 튜토리얼 · 데모 · 템플릿 · 샘플 · 최근 작업(찾기) · 기준 폴더 설정.
- API: `GET /api/home` · `POST /api/project`(create/open/demo/forget) · `POST /api/settings` · `GET /api/fs`. 문서 `docs/home.md`.
- 0.6.0 시작용 교안(`starters/`)과 함께 병합 - 시작 페이지는 `starters/<이름>/starter.json` 을 인식한다.

## 0.6.0 - 2026-10-02 · 강의 교안 시작용(lecture-course)

- `starters/lecture-course/` - 실제 강의 교재(3일 과정)의 구성을 익명화한 시작용 교안: 공통 표지·전체 목차·EoD(`_common.json`), 과정 안내 장 ch00(본문 24장, 레이아웃 17종 예시)·이론 장 ch01(본문 12장, Mermaid 다이어그램), 일차 이름·표지 배지 선택값. 로고는 자리 표시, 내용은 자리 표시와 일반 예제(주문 관리).
- `init_workspace.py --starter lecture-course` - 시작용 내용·그림 복사, `partLabels`·`coverBadge` 반영, 빌드할 덱 안내.
- `docs/lecture-starter.md` - 구성 순서, 장·절·소분류·실습 번호 체계(장 번호 = 교육 순서), 각주·노트(원문) 규약, 작성 규칙.
- 수정: 작업 공간이 엔진과 다른 드라이브(Windows)에 있으면 실행기 `nexa.py` 안내 문구의 절대 경로 역슬래시가 문법 오류(유니코드 이스케이프)를 내던 문제 - 경로를 `/` 로 쓴다.

## 0.5.3 - 2026-10-02 · 요청 칸 Enter 남기기

- 편집기 요청 탭의 슬라이드 요청 칸: Enter = 메모 남기기(초안), Shift+Enter = 줄바꿈 - 요소 메모 팝오버와 같은 동작. 보내기는 그대로 아래 바 "요청 N개 보내기".

## 0.5.2 - 2026-10-02 · 바닥 각주 가로 배치 · 요청 입력 보관

- 바닥 각주(`role: footnotes`): 위치 표시(crumb)는 각주가 없는 슬라이드와 같은 왼쪽 아래 자리에 고정하고, 각주는 그 바로 위(아래 끝 668, 쪽번호 칩 위)에 9pt(12px)로 1, 2, 3 순서대로 가로로 잇는다. 한 줄 폭을 넘으면 각주 단위로 줄을 바꾼다(`layouts.foot_lines`).
- 바닥 각주 번호는 위첨자 대신 보통 숫자를 굵은 강조색(`==n==`)으로 - 작은 글씨에서도 번호가 잘 보이게. 본문 표식(`[[theory|¹]]`)은 그대로.
- 편집기: 아직 남기지 않은 요청 입력(요청 탭 슬라이드 요청 칸 · 요소 메모)을 덱·슬라이드·요소별로 브라우저에 보관 - 슬라이드를 옮기거나 새로 고쳐도 유지, 메모를 남기면 지움.

## 0.5.1 — 2026-10-01 · 새 프로젝트 시작 도구·설명서

- `studio/init_workspace.py <폴더>` — 작업 공간 뼈대(선택만 담은 nexa-slide.json · 실행기 nexa.py · CLAUDE.md 세션 안내 · 시작용 content · .gitignore · 자리 표시 로고), 빈 포트 자동 선택.
- `studio/layout_samples.py` — 레이아웃 21종과 필드 예시(초안 작성용, 실행기 `nexa.py layout_samples`).
- `docs/new-project.md` — 다른 폴더·저장소에서 VS Code(Claude Code)·Claude Desktop 으로 연결해 초안 작성·검토·내보내기까지, macOS·Windows 명령 병기.

## 0.5.0 — 2026-10-01 · 편집기 UI 개편 (Genspark 작업 화면 방식 차용, 슬라이드 디자인 불변)

- 모드 3분할 **편집(E) · 선택(M) · 그리기(D)** — 선택은 요소를, 그리기는 박스·펜·핀 영역을 눌러 그 자리 **메모 팝오버**(개체 종류별 빠른 칩, Enter = 추가) → 번호 배지·레일 ✎ 배지 → 아래 바 **"요청 N개 보내기"**(초안 → 대기, 즉시 전달). 취소 범위 = 이 슬라이드(없으면 전체).
- 모드 바 아래 **붙박이 서식 줄**: 글꼴 · 크기 px(프리셋)·pt · 글자색 · 굵게 · 정렬 · 줄 간격·세로 정렬 · 채우기 · 테두리 · 선 속성 · 복제 · 삭제 · 잠금 · **위치 조정 ▾**(정렬 6 · 순서 4 · 너비/높이/X/Y). 색은 템플릿 토큰 팔레트.
- 오른쪽 클릭 메뉴, 순서 단축키(Ctrl+] [ · Alt+Ctrl+] [), Ctrl+X/B, 모드 키 E/M/D, 도움말 ?.
- ✨ 레이아웃 고치기(검사 결과를 담아 바로 요청) · ✨ 다듬기.
- 바닥줄: 노트 · 개요 · 검사 탭, ◀ n/N ▶, **확대 10~300%**(Ctrl+휠 포인터 기준 · Ctrl+= - 0 1) · Space+끌기 화면 이동.
- 머리줄: 덱 탭 · ▶ 발표(F5 · Shift+F5 · N 노트·시간) · 기록(자동 백업 되돌리기) · 내보내기 ▾ · 더보기(글꼴 세트·템플릿·단축키).
- **바뀐 것이 없으면 저장하지 않음**. 레일 폭 조절·오른쪽 패널 접기·배치 기억.
- 서버: 요청 `draft`·`region`·`send`·`discard`, `GET /api/history/<id>`. 감시 이벤트에 `region` 포함.

## 0.4.1 — 2026-10-01 · 요청 감시 "가짜 연결" 방지

- Monitor 만료 시 셸만 끝나고 python 감시가 남아 하트비트만 쓰던 문제(편집기는 "연결됨", 요청은 전달 안 됨)를 막음:
  - `--ttl`(`--stream` 기본 1780초) 뒤 `{"event":"ttl"}` 을 내고 스스로 종료
  - `--takeover` 로 남은 이전 감시를 끝내고 넘겨받기

## 0.4.0 — 2026-10-01 · 디자인 템플릿

- `studio/templates/<이름>/`(template.json · tokens.json · design/) — 색·글꼴·글자 크기·검사 기준·디자인 기준 문서를 템플릿으로 묶음.
  - `lecture`(기본): 기존 디자인·크기 그대로(0.3 까지와 결과 동일 확인), 검사 기준 11·8·9pt — 크기 조정은 장 단위 검토에서
  - `lecture-large`: 글자만 일괄 확대(본문 15px · 각주 11px · 경로·쪽번호 12px) — 선택 사항
  - 원칙: 기능(검사·세션 연결·템플릿)은 Genspark 등에서 차용하되 구성·디자인은 기존 형태 유지
- 작업 공간은 선택만: `template`·`fontPreset`. 작업 공간 `tokens.json`·`designCss`·`check.minFontPt` 는 더 쓰지 않는다(`check` 는 ignore·ignoreSlides 만).
  - 글꼴 선택(`set_fonts.py`·편집기)은 `nexa-slide.json` 의 `fontPreset` 을 바꾼다
  - `/studio/tokens.json` 은 템플릿 + 선택을 매번 계산해 준다. `GET /api/templates`
  - `NEXA_SLIDE_TEMPLATE` 로 설정을 바꾸지 않고 미리보기
- 디자인 기준 문서(concept.html·tokens.css)를 템플릿으로 옮기고 회사 로고·문구를 자리 표시로 바꿈.

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
