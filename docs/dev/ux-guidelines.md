# UX 지침 — 기능은 늘려도 화면은 단순하게

기능이 많아질수록 편집기가 복잡해지지 않도록 지키는 원칙과, 최근 제작 도구(Canva · Figma Slides · Gamma · Pitch · Google Slides · Keynote · Notion)에서 검증된 패턴 가운데 nexa-slide 에 들여온 것.

## 원칙

1. **한 번에 보이는 것은 지금 필요한 것만**(점진적 공개). 자주 쓰는 속성은 바로, 드물게 쓰는 속성은 접힌 절(`details.fold`, 상태 기억)이나 "요소 JSON (고급)" 뒤에.
2. **깊은 메뉴 대신 검색**. 넣을 것·동작은 글자를 쳐서 찾는다 — ＋ 추가 패널의 검색, 명령 팔레트(`Ctrl+K` · `/`). 하위 메뉴는 두지 않는다(도형·다이어그램·차트도 한 패널의 타일).
3. **문맥 도구 모음**. 요소를 고르면 그 요소에 맞는 단추만 떠 있는 도구 모음에(글꼴·크기·색·정렬·위치). 패널은 보조.
4. **직접 조작 + 안내선**. 끌면 다른 요소의 가장자리·가운데와 슬라이드 가운데에 붙고(스마트 가이드), 두 번 클릭이면 글자 편집, 실행 취소는 언제나.
5. **같은 일은 같은 모양**: 칩(`chip`)·세그먼트(`seg`)·행(`row`)·절(`sec`)만 쓰고, 새 위젯을 만들지 않는다. 켬/끔은 세그먼트, 선택지는 select, 색은 토큰 팔레트.
6. **단축키는 발견 가능하게**: `?` 도움말, 메뉴·팔레트 항목 옆에 키 표시, 툴팁에 키.
7. **빈 상태·실패에는 다음 할 일**을 적는다("…이 없습니다 - 이렇게 하세요"), 토스트는 한 줄.
8. **부모를 벗어나지 않는다**: 패널 안 어떤 자식도 밖으로 밀어내지 않고, 길면 그 안에서 스크롤.

## 들여온 패턴 (2026-10)

| 패턴 | 어디서 익숙한가 | nexa-slide |
|---|---|---|
| 검색 가능한 삽입 패널(타일) | Canva 요소 패널, Figma 자산 | ＋ 추가: 기본·데이터·미디어·도형·다이어그램 타일 + 검색, Enter = 첫 항목 |
| 명령 팔레트 | Figma(Ctrl+/), Pitch(Cmd+K), Notion(/), VS Code | `Ctrl+K` · `/`: 넣기와 동작을 한 곳에서, 최근 쓴 것이 위 |
| 문맥 떠 있는 도구 모음 | Google Slides, Figma | 선택한 요소 위의 글꼴·크기·색·정렬·위치 메뉴(이미 있음) |
| 스마트 가이드 | Keynote, Figma, PowerPoint | 끌 때 가장자리·가운데 맞춤 + 빨간 점선, Shift = 자유 |
| 점진적 공개 | Figma 속성 패널 | 글머리 종류 등 드문 절은 접힘, 요소 JSON 은 고급 |
| 발표자 보기 | Keynote, Google Slides | `P`: 지금·다음·노트·시간, 두 창 동기화 |
| 묶음 | 모든 도구 | Ctrl+G / Ctrl+Shift+G |

시장 흐름(참고): Canva 는 부서를 넘어 하나의 편집기로 쓰이는 방향, Gamma 는 프롬프트에서 초안을 만들고 편집기에 머무르게 하는 AI 우선, Figma Slides 는 디자인 시스템(글꼴·색·컴포넌트)과 AI 글 다듬기를 강조한다 — nexa-slide 는 "AI 세션이 초안·수정을, 사람은 편집기에서 다듬기"라는 같은 흐름 위에 있다(출처: [Sacra — Slides absorbed into AI workflows](https://sacra.com/chat/h/158b80cd-01d9-4407-8388-2dba6a0f3c48/), [Gamma guide](https://gamma.app/th/explore/content/guides/best-ai-text-to-slide-solutions-business-professionals-2026), [Figma Slides 가이드](https://mockuuups.studio/blog/post/best-figma-slides/), [Canva alternatives 2026](https://ponder.ing/blog/canva-alternatives)).

## 새 기능을 넣을 때 확인

- 메뉴 항목을 더하지 말고 **삽입 패널 타일 또는 팔레트 항목**으로(검색어 `kw` 에 한·영 동의어).
- 속성은 **문맥 도구 모음에 1개 이하**, 패널에는 행 2~3개 이내 — 넘치면 접는 절.
- 단축키를 주면 `HELP` 와 팔레트 `key` 에 적는다.
- 헤드리스 시험(`studio/tests/`)에 한 단계 넣는다.
