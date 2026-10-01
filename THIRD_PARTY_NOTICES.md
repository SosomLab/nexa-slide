# 제3자 구성요소 고지

nexa-slide 저장소는 아래 구성요소를 **포함(재배포)하지 않는다**. 사용자가 각자 설치하며, 각 구성요소의 라이선스를 따른다.

| 구성요소 | 쓰는 곳 | 라이선스 | 설치 |
|---|---|---|---|
| [python-pptx](https://github.com/scanny/python-pptx) | `export_pptx.py` PPTX 생성 | MIT | `pip install -r requirements.txt` |
| [lxml](https://lxml.de/) | python-pptx 의존 | BSD-3-Clause | 위와 같이 자동 설치 |
| [Pillow](https://python-pillow.org/) (선택) | 글자 폭 측정·`compare.py` 이미지 비교 | MIT-CMU (HPND) | `pip install -r requirements.txt` |
| [Node.js](https://nodejs.org/) (선택) | `check_parity.py` 가 `render.js` 실행 | MIT | 별도 설치 |
| [@mermaid-js/mermaid-cli](https://github.com/mermaid-js/mermaid-cli) (선택) | `render_mermaid.py` 다이어그램 PNG | MIT | `npx` 로 실행 시 내려받음 |
| [Pretendard](https://github.com/orioncactus/pretendard) (선택) | 본문 글꼴 프리셋 `modern` | SIL OFL 1.1 | `studio/install_fonts.ps1` |
| [JetBrains Mono](https://github.com/JetBrains/JetBrainsMono) (선택) | 코드 글꼴 프리셋 `modern` | SIL OFL 1.1 | `studio/install_fonts.ps1` |
| [D2Coding](https://github.com/naver/d2codingfont) (선택) | 코드 안 한글 | SIL OFL 1.1 | `studio/install_fonts.ps1` |
| Microsoft PowerPoint (선택) | `render_pptx.ps1` 렌더 미리보기(COM) | 상용 — 사용자 보유 라이선스 | — |
| Google Chrome / Microsoft Edge (선택) | `compare.py` 헤드리스 캡처 | 각 제품 라이선스 | — |

- 기본 글꼴 프리셋(`default`)은 운영체제에 있는 글꼴(맑은 고딕·Consolas)을 **이름으로만** 가리킨다. 글꼴 파일은 저장소에 없다.
- `example/assets/brand/` 의 로고·워드마크·파비콘은 이 저장소용으로 만든 자리 표시 이미지이며 MIT 로 함께 배포한다.
- 회사·제품 로고(CI)는 저장소에 넣지 않는다. 각 작업 공간의 `nexa-slide.json` `brand` 항목으로 바깥 파일을 가리킨다.
