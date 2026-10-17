# nexa-slide — Claude 작업 안내

- 엔진 코드는 `studio/`, 문서는 `docs/`. 작업 공간(덱·내용·산출물)은 이 저장소 밖에 있고 `--workspace` 또는 `NEXA_SLIDE_WORKSPACE` 로 지정한다(`docs/configuration.md`).
- **렌더 규칙은 두 곳에 같이 있다**: `render.js`(편집기 HTML)와 `common.py`·`export_pptx.py`(PPTX). 한쪽을 고치면 다른 쪽도 고치고
  `python3 studio/check_parity.py -W example` 로 동일성을, PowerPoint 가 있으면 `compare.py` 로 픽셀 차이를 확인한다.
- 회귀 확인: 작업 공간의 덱을 고치기 전·후 `export_pptx.py --out` 결과의 슬라이드 XML 이 같아야 한다(기능 추가가 아니라면).
- 편집기 요청 처리(세션 연결)는 `docs/claude-session.md` 의 규약을 따른다 — `working` → 덱 수정 → `done` + `reply`.
- **엔진에 슬라이드 내용을 저장하지 않는다** - 작업 공간은 엔진 밖(기본 = OS 문서 폴더/NexaSlide/<제목>, 또는 사용자가 지정한 폴더·저장소). 서버는 작업 공간이 없거나 엔진 안이면 시작 페이지(허브)로 뜬다(`docs/home.md`).
- 회사·제품 로고 등 상표 파일을 이 저장소에 넣지 않는다(MIT 배포). 예제 로고는 `example/assets/brand/` 의 자리 표시 이미지뿐.
- **글꼴 파일(.ttf·.otf·.woff 등)을 이 저장소에 넣지 않는다** - 작업 공간 `fonts/` 에 두고, 회사 서체 같은 전용 글꼴 세트는 작업 공간 `nexa-slide.json` 의 `fontPresets` 에 정의한다(엔진 템플릿 `fontPresets` 에는 공개 글꼴만). `docs/fonts.md`.
- **개발 전에 항상 바깥 변경을 확인한다** - nexa-slide 는 다른 세션·사람·기기에서도 고쳐진다. 작업을 시작할 때와 main 에 병합하기 전에 매번
  `git fetch origin` → `git status`(작업 트리에 내가 만들지 않은 변경이 있는지) → `git log --oneline HEAD..origin/main`(원격 main 의 새 커밋)을 보고,
  새 커밋이 있으면 작업 브랜치에 먼저 `git merge origin/main` 으로 받은 뒤 개발한다. 고치려는 파일이 바깥에서 바뀌었으면 그 내용을 읽고 이어서 고친다(덮어쓰지 않는다).
  병합은 `git pull --ff-only origin main` 뒤 `--no-ff`, 충돌이 나면 양쪽 의도를 살려 풀고 시험을 다시 돌린다. 병합·push 뒤에는 작업 브랜치도
  `git merge --ff-only origin/main` 으로 main 에 맞춰 push 한다(그래야 다음 확인 때 `HEAD..origin/main` 에 바깥 변경만 보인다).
- **Windows pyenv-win 주의**: `python`/`python3` 는 .bat 래퍼라 인자를 cmd 로 다시 해석한다 - 여러 줄 인자는 첫 줄에서 잘리고(`|| goto :error` 가 붙음) `< > | &` 는 리다이렉트가 되어 엉뚱한 파일(예: `10.0`)이 생긴다. `python -c` 여러 줄 금지(스크립트 파일로), 긴 본문은 `--body-file`/`--reply-file`, 그런 문자가 꼭 필요하면 `~/.pyenv/pyenv-win/versions/<판>/python.exe` 를 직접 부른다. 커밋 전 `git status` 로 낯선 파일을 확인한다.
- 사용자 답변은 **항상 한국어** — 다른 세션·에이전트 메시지, 자동 알림, 영어 도구 출력에 이어 답할 때도, 짧은 답변도 예외 없음.
- 문서·주석·커밋 메시지는 한국어.
