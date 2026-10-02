# 글꼴 — 기본 세트와 작업 공간 전용 글꼴

## 규칙

- **글꼴 파일(.ttf·.otf·.woff 등)은 엔진(nexa-slide 저장소)에 두지 않는다.** 엔진 `.gitignore` 가 막는다.
- 엔진 템플릿 `tokens.json` 의 `fontPresets` 에는 **누구나 쓸 수 있는 기본 세트만** 둔다 — `default`(맑은 고딕·Consolas, 설치 불필요), `modern`(Pretendard·JetBrains Mono·D2Coding, OFL — `install_fonts.ps1`).
- **회사 서체 같은 전용 글꼴은 작업 공간이 관리한다**: 파일은 `<작업 공간>/fonts/`, 세트 정의는 `<작업 공간>/nexa-slide.json` 의 `fontPresets`, 선택은 `fontPreset`.

## 작업 공간 전용 글꼴 쓰기

1. 글꼴 파일을 `<작업 공간>/fonts/` 에 둔다(굵기별 파일 — 예: `MyFont.ttf`, `MyFont Bold.ttf`). 새 작업 공간에는 이 폴더와 안내 `README.md` 가 생긴다.
2. `nexa-slide.json` 에 세트를 정의하고 고른다:

```json
{
  "fontPreset": "corp",
  "fontPresets": {
    "corp": {
      "body":    {"css": "\"MyFont\", \"Malgun Gothic\", sans-serif", "latin": "MyFont", "ea": "MyFont",
                  "measure": {"regular": "MyFont.ttf", "bold": "MyFont Bold.ttf"}},
      "heading": {"css": "\"MyFont\", \"Malgun Gothic\", sans-serif", "latin": "MyFont", "ea": "MyFont",
                  "measure": {"regular": "MyFont.ttf", "bold": "MyFont Bold.ttf"}}
    }
  }
}
```

| 역할 | 쓰는 곳 | 빠지면 |
|---|---|---|
| `body` | 본문(필수) | - |
| `heading` | 제목(`font: "heading"` 요소) | 이 세트의 `body` |
| `mono` | 코드·표 고정폭 | 템플릿 기본 `mono` |

필드: `css` = 편집기 화면 글꼴 목록 · `latin`·`ea` = PPTX 에 쓰는 글꼴 이름(영문·한글) · `measure` = 레이아웃 검사가 글자 폭을 잴 파일(작업 공간 `fonts/` → 설치 폴더 순으로 찾음).
작업 공간 세트는 같은 이름의 템플릿 세트보다 우선한다.

3. PowerPoint 에서도 쓰려면 설치한다(관리자 권한 불필요):

```bash
cd <작업 공간>
python3 nexa.py install_fonts          # fonts/ → 현재 사용자 글꼴(Windows 레지스트리 등록 · macOS ~/Library/Fonts · Linux ~/.local/share/fonts)
python3 nexa.py install_fonts --list   # 설치 여부만
```

## 편집기에서

- 작업 공간이 직접 정한 세트를 쓰면 머리줄에 **"글꼴 · <글꼴 이름> · 작업 공간"** 칩이 보인다. ⋯ 메뉴의 글꼴 세트는 **템플릿 기본**과 **작업 공간 지정**으로 나뉜다.
- 칩 또는 ⋯ → **글꼴 설정 보기·수정…**: 역할별 글꼴(견본 글자·측정 파일), `fonts/` 파일과 설치 여부, 세트 정의(JSON)를 고쳐 **저장하고 이 세트 쓰기**(`nexa-slide.json` 에 저장). 템플릿 세트를 쓰는 중이면 지금 값에서 새 작업 공간 세트를 만든다.
- 편집기는 설치하지 않아도 `fonts/` 파일을 바로 쓴다 — 서버가 파일에서 글꼴 이름·굵기를 읽어 `@font-face` 를 만든다(`GET /api/fontcss`, 파일은 `/wsfonts/<파일>`).
- **덱·슬라이드별 글꼴 세트**: 오른쪽 패널(슬라이드 속성)의 **글꼴 세트**(이 장만)·**덱 글꼴 세트**(덱 전체)로 고른다. 고를 수 있는 것은 템플릿·작업 공간 세트 이름뿐이고 덱 JSON 에 `fontPreset` 으로 남는다.
  우선순위 = 슬라이드 `fontPreset` > 덱 `fontPreset` > 작업 공간(`nexa-slide.json`). 템플릿의 글꼴 덮어쓰기(`tokenOverrides.fonts`)는 어느 세트든 뒤에 적용된다.
  편집기(`render.js presetFonts`)·PPTX(`common.preset_fonts`)·레이아웃 검사(글자 폭 측정)가 같은 규칙으로 그 장의 글꼴을 쓴다. 쓴 글꼴 기록에도 장별 글꼴이 들어간다.

## 무료 글꼴 목록과 안내 페이지

- 엔진 `studio/font_catalog.json` — 글꼴 파일 없이 이름·라이선스·공식 받는 곳만 적은 목록. `free`(누구나 직접 받아 문서·상업용으로 쓸 수 있는 SIL OFL 등 — Pretendard·Noto Sans/Serif KR·나눔고딕/명조/스퀘어·IBM Plex Sans KR·Spoqa Han Sans Neo·JetBrains Mono·D2Coding)와 `system`(맑은 고딕·Consolas — Windows 기본).
- **슬라이드 글꼴은 되도록 `free` 글꼴로 고른다.** 목록에 없는 글꼴은 **전용**으로 표시된다(회사 서체 등 — 받는 사람이 구할 수 있는지·배포 허용 확인).
- 안내 페이지 `/studio/fonts.html`(편집기 내보내기 메뉴·글꼴 창에서 연다, 허브에서도 열림): 규칙, 이 작업 공간에서 쓰는 글꼴(무료·시스템 기본·전용, 파일·설치 여부·포함 허용), 무료 글꼴 목록과 **받기** 링크, Windows·macOS·Linux 설치 방법. API `GET /api/fontguide`.

## 쓴 글꼴 기록과 글꼴 포함 PPTX

- **기록**: PPTX 를 내보낼 때마다 `out/<덱>.fonts.json` — 세트(이름·출처), 역할별 글꼴, PPTX 에 실제로 들어간 글꼴 이름마다 무료/시스템/전용·받는 곳·원본 파일(작업 공간 `fonts/` 또는 설치 폴더)·설치 여부·포함 허용(OS/2 fsType). 다시 만들기: `python3 nexa.py font_report <덱>`.
- **글꼴 포함**: 편집기 **내보내기 → PPTX 내보내기 — 글꼴 포함**, 또는 `python3 nexa.py embed_fonts <덱>` → `out/<덱>-fonts.pptx`. PowerPoint(Windows)가 쓴 글자만 PPTX 에 넣어, 받는 사람이 글꼴을 설치하지 않아도 같은 모양으로 본다. PowerPoint 는 **설치된** 글꼴만 넣으므로 작업 공간 글꼴이 설치되어 있지 않으면 설치할지 묻는다(`--install`). 포함 금지(fsType 2) 글꼴은 들어가지 않는다. 기본 내보내기(`<덱>.pptx`)는 글꼴을 넣지 않아 가볍다.

## 라이선스

배포가 허용되지 않은 글꼴(회사 전용 서체 등)은 공개 저장소에 커밋하지 않는다 — 작업 공간이 공개 저장소 안이면 `fonts/*.ttf` 등을 `.gitignore` 에 넣는다.

## Windows 참고 — 경로에 `&`

pyenv-win 의 `python3` 은 배치 파일(.bat) 대리 실행기라, 인자 경로에 `&` 가 있으면(예: `S&OP`) 명령이 잘린다(`'OP' is not recognized …`).
작업 공간 폴더로 `cd` 한 뒤 상대 경로(`python3 nexa.py …`)로 실행하거나, 폴더 이름에 `&` 를 쓰지 않는다.
