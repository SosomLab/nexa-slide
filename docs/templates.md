# 템플릿

**디자인은 엔진 템플릿에, 작업 공간에는 선택만.**
색·글꼴·글자 크기·검사 기준·디자인 기준 문서처럼 "어떻게 보이는가"를 정하는 것은 모두 `studio/templates/<이름>/` 에 있다.
작업 공간(교재·발표 저장소)은 `nexa-slide.json` 에서 **이름을 고르기만** 하고, 디자인 값을 직접 쓰거나 파일로 두지 않는다.

```json
{ "template": "lecture", "fontPreset": "modern" }
```

## 제공 템플릿

| 이름 | 내용 | 글자 크기 | 검사 기준(최소 pt) |
|---|---|---|---|
| `lecture` (기본) | 강의·교재 16:9, Material v2, 레이아웃 21종 — **기존 디자인 그대로** | 레이아웃에 정한 값 그대로(0.3 까지와 결과 동일) | 본문 11 · 각주 8 · 경로 9 · 쪽번호 9 — 알리기만, 조정은 장 단위 검토에서 |
| `report` · `brief` · `story` · `notice` · `schedule` · `proposal` | 목적별(보고·결정·회고·공지·일정·RFP) - `lecture` 바탕에 색·글꼴·모서리만 바꿈([starters.md](starters.md)) | 역할별 최소 15px 로 올림 | lecture 와 같음 |
| `lecture-large` | `lecture` 를 바탕으로 글자만 일괄 확대 | 빌드할 때 역할별 최소 px 로 올림 — 본문 15px · 각주 11px · 경로·쪽번호 12px. 상자 크기는 그대로라 촘촘한 도식은 넘칠 수 있음 | lecture 와 같음 |

디자인 템플릿과 별도로, 내용 뼈대를 주는 **시작용 교안**이 있다 - `starters/lecture-course`(강의 교안 3일 과정, 템플릿 `lecture` 사용). [lecture-starter.md](lecture-starter.md)

## 템플릿 폴더

```
studio/templates/<이름>/
├─ template.json      정의(아래)
├─ tokens.json        색 역할 · 반경 · 글꼴 프리셋(fontPresets) · 코드 색 · PPT 줄 배치 보정
└─ design/            디자인 기준 문서(concept.html · tokens.css — gen_tokens_css.py 가 tokens.json 과 값 대조)
```

`template.json`:

| 키 | 설명 |
|---|---|
| `extends` | 다른 템플릿을 바탕으로 — 사전은 깊게 합치고 나머지는 덮어쓴다 |
| `label` · `description` | 편집기·목록에 보이는 이름과 설명 |
| `tokens` | 토큰 파일(이 폴더 기준) |
| `design.concept` · `design.css` | 디자인 기준 문서 |
| `sizes.minPx` | 빌드할 때 글자 크기의 역할별 하한(px, 0 = 쓰지 않음). 역할 = 요소의 `role`(`footnotes`·`crumb`·`page`·`title`·`subtitle` …), 없으면 `default`. 이미 크면 그대로 |
| `tokenOverrides` | 토큰 파일 위에 덮을 값(`colors`·`radius`·`fonts` - 예: `story` 의 `heading` 명조). 바탕 템플릿의 토큰 파일을 그대로 두고 값만 바꾼다 |
| `check.minFontPt` | 레이아웃 검사(`check_layout.py`)의 역할별 최소 pt |

## 작업 공간이 고를 수 있는 것 (선택만)

| 키 | 고르는 것 |
|---|---|
| `template` | 템플릿 이름 |
| `fontPreset` | 템플릿 `tokens.json` 의 `fontPresets` 중 하나(편집기 글꼴 선택·`set_fonts.py` 가 이 값을 바꾼다) |
| `brand` | 자기 로고·워드마크·파비콘 파일 경로(작업 공간의 자산을 가리킴) |
| `partLabels` · `coverBadge` · `endNextNote` | 슬라이드에 들어가는 문구(내용) |
| `check.ignore` · `check.ignoreSlides` | 검사에서 뺄 규칙·슬라이드 |

작업 공간에 `tokens.json`·`design/`·검사 기준값을 두지 않는다. 다른 크기·글꼴·색이 필요하면 **새 템플릿을 엔진에 추가**하고 이름으로 고른다.

## 템플릿 바꾸기

1. `nexa-slide.json` 의 `template` 을 바꾼다(미리보기만 하려면 환경변수 `NEXA_SLIDE_TEMPLATE=<이름>` — 설정 파일은 그대로).
2. 서버를 다시 시작한다(`nexa.py restart`) — 토큰·검사 기준이 바뀐다.
3. 글자 크기(`sizes`)는 **빌드할 때** 적용된다 → 장마다 `build_deck.py <id> --force` 로 다시 만들고 "검사" 탭으로 확인한다.
   편집기에서 고친 슬라이드가 있으면 build 가 멈춘다(내용 원본에 옮긴 뒤 다시, 또는 `--discard-edits`).

## 새 템플릿 만들기

```
studio/templates/my-template/template.json
{ "extends": "lecture", "label": "…", "sizes": {"minPx": {"default": 16}}, "check": {"minFontPt": {"default": 12}} }
```

색·글꼴까지 바꾸려면 `tokens.json` 을 복사해 고치고 `"tokens": "tokens.json"` 을 넣는다. 확인:
`check_parity.py`(화면·PPT 규칙 동일) · `check_layout.py`(크기를 올린 뒤 넘침·겹침) · `compare.py`(PowerPoint 렌더 대조).
