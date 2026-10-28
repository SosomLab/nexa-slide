# 웹 스프레드시트 조사 — M365 Excel · Google Sheets 기준 (2026-10-28)

> engine-request #12 의 배경 조사. 시트 기능 설계·로드맵은 [../sheets.md](../sheets.md).
> 공식 도움말(support.microsoft.com·support.google.com·learn.microsoft.com)과 라이브러리 공식 문서·GitHub 를 우선으로 확인했다.
> **(추정)**·**(일반 지식)** 표시는 1차 출처로 확인하지 못한 것이다.

## 0. 결론

- **2026년 변화**
  - Excel `=COPILOT()` 함수는 정식 출시 없이 2026-09-14 에 폐지됐다(MC1454373). 기존 결과는 캐시 값으로 남고, 다시 계산하면 `#NAME?` 가 된다. Microsoft 는 대안으로 **Copilot 사이드 패널**을 권한다.
  - Google Sheets `=AI()`(`=Gemini()`)는 남아 있다. 다만 텍스트만 출력하고, 넘긴 범위만 보며, 다른 함수 안에 넣을 수 없고, 실행 취소 대신 "다시 생성"을 쓴다.
  - AI 의 중심은 셀 함수가 아니라 **사이드 패널 + 미리보기·적용·되돌리기**로 옮겨 갔다.
    - Excel Agent Mode 는 GA 이고 편집 허용·계획·채팅만 세 모드가 있다.
    - Sheets 는 Gemini 패널의 작업 미리보기 카드 → 적용 → 실행 취소 흐름이다.
  - nexa-slide 의 "범위 선택 → 요청 → AI 가 JSON 수정 → reply" 는 이 흐름과 같은 모양이다.
- **라이선스(MIT 배포)**
  - 쓸 수 없는 것
    - HyperFormula 는 GPLv3 또는 상용이라 엔진에 넣을 수 없다.
    - Handsontable 은 6.2.2(2018) 이후 상용이다.
  - 쓸 수 있지만 걸리는 것
    - Univer 는 Apache-2.0 이지만 xlsx 입출력·협업·피벗·차트가 Pro 다.
    - FortuneSheet 는 MIT 지만 React 중심이고 1.0 전이다.
    - Jspreadsheet CE 는 수식 엔진이 Pro 다.
    - AG Grid Community 는 수식 모델이 아니다.
  - Luckysheet 은 2025-10-30 에 보관됐다.
- **권고**
  - 격자와 수식 평가기는 **직접 작게** 만든다.
  - xlsx 쓰기는 XlsxWriter 를 쓰고 수식 캐시 값을 채운다. xlsx 읽기는 서버 openpyxl 로 한다.
  - 함수가 60개를 넘어서면 Univer `engine-formula`(Apache-2.0)를 서버·브라우저 공용 엔진으로 검토한다(추정, 시험 필요).

## 1. UI 구성과 상호작용

| 요소 | Excel | Google Sheets | nexa-slide |
|---|---|---|---|
| 명령 영역 | 탭형 리본(웹은 단순 리본) | 메뉴 + 한 줄 툴바 | **Sheets 식 한 줄 툴바** |
| 이름 상자 | 현재 셀·범위, 주소 입력으로 이동 | 같다 | `B2:D5` 표시·이동 + **요청 대상 표시** |
| 수식 입력줄 | fx, 인수 도움 | fx, 수식 도움말·자동 완성 | 1단계 필수, 자동 완성은 2단계 |
| 시트 탭 | 아래쪽, +, 우클릭(삽입·삭제·이름·색·숨기기·이동) | 같다 + 모든 시트 목록 | `sheets[]` |
| 상태 표시줄 | 선택 범위 평균·개수·합계(+최소·최대) | 오른쪽 아래 합계 칩 (일반 지식) | 값싸고 유용하다 |
| 컨텍스트 메뉴 | 잘라내기·붙여넣기 옵션·삽입·삭제·정렬·필터·메모·서식 | 비슷 + 수정 기록 표시 | 복사·붙여넣기·행열 삽입/삭제·지우기·**"이 범위로 AI 요청"** |

- **선택**
  - 클릭·Shift·드래그·Ctrl(여러 범위)·머리글 클릭으로 고른다.
  - Ctrl/Shift+Space 는 열/행 전체, Ctrl+A 는 현재 영역 → 전체 순서로 넓힌다.
  - Ctrl+화살표는 데이터 경계로 간다.
- **채우기 핸들**
  - 숫자 1개는 복사하고, 2개 이상은 등차로 채운다. 날짜·요일·월 이름은 이어지고, "제품1"은 숫자만 늘어난다.
  - 수식은 상대 참조만 이동하고 `$` 절대 참조는 고정한다. 더블클릭하면 왼쪽 열 끝까지 채운다.
  - 패턴 채우기: Excel Ctrl+E 빠른 채우기, Sheets 자동 완성 제안.
  - Ctrl+D·Ctrl+R 은 아래·오른쪽으로 채우고, Ctrl+Enter 는 선택 범위를 같은 값으로 채운다.
- **붙여넣기 특수**
  - Excel(Ctrl+Alt+V): 값·수식·서식·메모·유효성·열 너비·행열 바꿈·연산·빈 셀 무시.
  - Sheets(Ctrl+Shift+V 는 값만): 값·서식·수식·조건부 서식·유효성·행열 바꿈·열 너비.
  - 외부 붙여넣기는 TSV/HTML 표를 해석한다.
- **실행 취소**: 공동 편집 중에는 자기 작업만 되돌린다 (일반 지식).
- **찾기·바꾸기**: 대소문자·셀 전체 일치·수식 안·정규식(Sheets)·범위 지정을 고를 수 있다.

**자주 쓰는 단축키(Windows)**
- 편집: F2 편집, Enter/Shift+Enter, Tab/Shift+Tab, Esc
- 실행 취소·클립보드: Ctrl+Z/Y, Ctrl+C/X/V, 붙여넣기 특수(Excel Ctrl+Alt+V, Sheets Ctrl+Shift+V)
- 이동·선택: Ctrl+화살표, Ctrl+Shift+화살표, Ctrl+Home/End, Ctrl/Shift+Space, Ctrl+A
- 서식: Ctrl+B/I/U, Ctrl+1(셀 서식, Excel), Ctrl+Shift+1~6(숫자 형식)
- 입력: Alt+=(자동 합계), F4(절대/상대 참조), Ctrl+;(오늘), Ctrl+Enter, Ctrl+D/R, Alt+Enter(셀 안 줄바꿈)
- 찾기: Ctrl+F/H
- 기타: Ctrl+K(링크), Ctrl+Shift+L(필터), Ctrl+T(표, Excel)·Ctrl+Alt+T(표, Sheets)
- 행열·시트: Ctrl+-/+(행열 삭제·삽입), Ctrl+PgUp/PgDn(시트 전환)
- 메모·보기: Shift+F2(메모), Ctrl+Alt+M(댓글), Ctrl+`(수식 보기)

웹에서는 브라우저 단축키와 겹친다. Excel 웹에는 "브라우저 단축키 무시" 설정이 있다. nexa 도 Ctrl+S·Ctrl+F 를 가로챌지 정해야 한다.

## 2. 데이터 기능

- **표시 형식**
  - Excel 형식 코드(`#,##0.00`, `0%`, `yyyy-mm-dd`, `[Red]-#,##0`)를 쓰고, 양수;음수;0;텍스트 4구역 구조다. Excel 과 Sheets 가 거의 같다.
  - 표시만 바꾸고 값은 그대로 둔다.
  - nexa 의 `fmt` 에 그대로 담으면 XlsxWriter `num_format` 에 1:1 로 넘어간다.
- **정렬·필터**
  - 여러 키로 정렬하고, 자동 필터(▼)로 값·조건·색을 거른다.
  - Sheets **필터 보기**와 Excel **시트 보기**는 다른 사람 화면을 바꾸지 않는 *개인용* 필터다.
  - 사람과 AI 가 같은 문서를 볼 때는 필터를 보기 상태(JSON 밖 또는 사용자별)로 두는 편이 충돌이 적다.
- **데이터 유효성**: 목록(드롭다운)·숫자·날짜·길이·사용자 지정 수식. 위반 시 거부 또는 경고. Sheets 에는 체크박스와 칩 드롭다운도 있다.
- **조건부 서식**
  - 규칙 종류: 값 비교·텍스트 포함·날짜·상위 N·평균·중복·사용자 지정 수식·색조.
  - 데이터 막대·아이콘은 Excel 에만 있다.
  - 규칙에 우선순위가 있다.
- **틀 고정**: Excel 은 고른 셀의 위·왼쪽을 고정한다. nexa `freeze:"B2"` 는 XlsxWriter `freeze_panes` 와 1:1 이다.
- **숨기기·그룹(개요)**, **병합**(왼쪽 위 값만 남는다)
  - 병합하면 정렬·필터·붙여넣기를 막는 일이 많다. Excel 은 "선택 영역의 가운데로"를 권한다 (일반 지식).
- **표**
  - Excel Table(Ctrl+T): 머리글·줄무늬·자동 확장·요약 행, 구조적 참조 `표1[금액]`·`[@금액]`.
  - Sheets Tables(2024~): **열 유형**(숫자·날짜·드롭다운·체크박스)과 유형 위반 경고.
- **피벗**: 대화형 피벗 표. Excel 에는 수식형 `GROUPBY`·`PIVOTBY` 도 있다.
- **차트**: 막대·꺾은선·원·영역·분산·콤보·폭포·히스토그램·상자·트리맵·선버스트·깔때기·지도·게이지·스파크라인.
- **이름 정의**: Excel 이름 관리자 + `LAMBDA` 사용자 함수, Sheets 이름이 지정된 범위·함수.

## 3. 수식

- **자주 쓰는 함수**
  - 집계: SUM·AVERAGE·MIN·MAX·COUNT·COUNTA·SUMIF(S)·COUNTIF(S)·AVERAGEIF(S)·SUBTOTAL·PRODUCT·MEDIAN
  - 논리: IF·IFS·AND·OR·NOT·IFERROR·IFNA·SWITCH
  - 조회: VLOOKUP·HLOOKUP·INDEX·MATCH·XLOOKUP·XMATCH·CHOOSE·OFFSET·INDIRECT
  - 수학: ROUND(UP/DOWN)·INT·MOD·ABS·SUMPRODUCT
  - 텍스트: CONCAT/TEXTJOIN/&·LEFT·RIGHT·MID·LEN·TRIM·UPPER·SUBSTITUTE·TEXT·VALUE·FIND·TEXTSPLIT
  - 날짜: TODAY·NOW·DATE·YEAR·EDATE·EOMONTH·DATEDIF·NETWORKDAYS·WEEKDAY
  - 동적 배열: FILTER·SORT·UNIQUE·SEQUENCE·LET·LAMBDA·GROUPBY
  - 1단계 7개 다음 순서로 권하는 것: COUNTA·SUMIF·COUNTIF·IFERROR·AND/OR·ABS·INT·&·LEFT/RIGHT/LEN·TEXT·TODAY·VLOOKUP/XLOOKUP.
- **동적 배열**
  - 결과가 이웃 셀로 흘러 넘친다(spill). 자리가 막히면 `#SPILL!`, 흘러 넘친 범위 전체는 `A2#` 로 가리킨다.
  - xlsx 에서는 `_xlfn.`·`_xlpm.` 접두사가 필요하고, XlsxWriter `write_dynamic_array_formula` 로 쓴다.
- **시트 간 참조**
  - `Sheet2!A1`, `'매출 2026'!B2`, 3D 참조 `Sheet1:Sheet3!A1`.
  - 시트 이름을 바꾸면 참조도 다시 써야 한다. 내부에서는 시트 id 로 해석하는 편이 안전하다.
- **오류 값**
  - 고전: `#DIV/0!`·`#N/A`·`#NAME?`·`#NULL!`·`#NUM!`·`#REF!`·`#VALUE!`
  - 새로 생긴 것: `#SPILL!`·`#CALC!`
  - 순환 참조는 경고로 알린다.
- **재계산(Microsoft Learn)**
  - 의존성 트리 → 계산 체인 → 바뀐 셀의 종속 셀만 dirty 로 표시해 다시 계산한다.
  - 휘발성 함수(NOW·TODAY·RAND·OFFSET·INDIRECT)는 매번 계산한다.
  - 수천 셀 규모면 로드할 때 위상 정렬 + 편집할 때 dirty 전파로 충분하다.

### 라이브러리 비교

| 이름 | 라이선스 | MIT 배포 | 내용 | xlsx | 상태 |
|---|---|---|---|---|---|
| HyperFormula | GPLv3 / 상용 | **불가** | 헤드리스 엔진, 함수 423개 | 없음 | 활발 |
| formula.js | MIT (추정) | 예 | 함수 모음(파서·그래프 없음) | 없음 | 보통 (추정) |
| fast-formula-parser | MIT | 예 | 파서+평가기 | 없음 | 2024-06 이후 정체 |
| Univer | Apache-2.0 + Pro | OSS 부분 예 | 캔버스 격자·수식 엔진·유효성·조건부 서식·댓글, AI SDK·MCP | **Pro** | 매우 활발 |
| Luckysheet | MIT | 예 | 완성도 높은 UI | 플러그인 | **2025-10 보관** |
| FortuneSheet | MIT | 예 | Luckysheet TS 포크, op 협업 | 별도 | 1.0 전, React |
| x-spreadsheet | MIT | 예 | 가벼운 캔버스 | 없음 | wolf-table 로 이전, 옛 판 XSS |
| Handsontable | 6.2.2 까지 MIT | 최신 불가 | 고급 격자 | 일부 | 활발 |
| Jspreadsheet CE | MIT | 예 | 격자(수식은 Pro) | Pro | 활발 |
| AG Grid Community | MIT | 예 | 데이터 그리드(셀 주소·수식 없음) | Enterprise | 활발 |
| SheetJS CE | Apache-2.0 | 예 | xlsx 읽기·쓰기(스타일은 Pro) | 예 | 활발 |
| ExcelJS | MIT (추정) | 예 | 스타일 포함 xlsx | 예 | 느려짐 (추정) |

## 4. 협업·AI

- **존재감(presence)**
  - 다른 사용자의 선택 셀을 사람마다 다른 색 테두리로 보이고, 아바타를 누르면 그 위치로 간다 (일반 지식).
  - nexa 에서는 AI 세션도 참여자로 보고, `working` 동안 **대상 범위에 AI 색 테두리 + "작업 중"** 을 표시한다.
- **댓글과 메모**
  - 두 제품 모두 스레드 댓글(답글·멘션·해결)과 메모를 구분한다.
  - nexa 의 `note` 는 메모에, 요청·reply 는 댓글에 해당한다.
- **기록**
  - Sheets 셀 수정 기록에는 누가·언제·이전 값이 남는다. 행열 삽입·서식·수식이 바꾼 값은 빠진다.
  - nexa 에서 가장 값싼 대응은 **"이 요청이 바꾼 셀" 목록을 reply 에 붙이는 것**이다.
- **Copilot in Excel**
  - 할 수 있는 일: 시트 추가·삭제, 셀 수정, 서식·유효성, 데이터·수식 생성, 차트·피벗, 대시보드, 인사이트, 조건부 서식, 웹 검색, Skills.
  - 모드: 편집 허용·**계획**·채팅만.
  - 사이드 패널에서 진행을 실시간으로 보고 멈출 수 있다.
  - Python in Excel 은 Microsoft 클라우드(Anaconda)에서 실행된다.
- **Gemini in Sheets**
  - 사이드 패널에서 표·수식·분석·차트·조건부 서식·피벗·정렬·필터·형식·고정·채우기를 한다.
  - **작업 미리보기 카드 → 적용 → 실행 취소** 흐름이고, 대상 탭을 제한할 수 있다.
  - 차트는 원본이 바뀌어도 갱신되지 않는다.
  - "Gemini 로 정리"는 새 표만 만든다.
  - `=AI()`: 생성 후 삽입하고, 다시 만들려면 새로 고침 후 삽입한다. 실행 취소가 없고 한 번에 350셀까지다.

## 5. xlsx 호환 주의

1. **공유 문자열·스타일**: 같은 서식 조합은 같은 Format 객체로 캐시한다. 셀마다 `add_format` 을 부르면 스타일이 폭증한다.
2. **수식 캐시 값**
   - XlsxWriter 는 수식을 계산하지 않고 0 을 쓴 뒤 "열 때 재계산" 표시를 한다.
   - Excel 은 열 때 다시 계산하지만, 미리보기·뷰어·PDF 변환·일부 모바일 앱은 **0 만 보인다**.
   - 그래서 **Python 쪽에도 같은 평가기가 필요하다**.
3. **함수 이름**: 영어 이름에 쉼표 구분자를 쓴다. 2010 이후 함수는 `_xlfn.` 접두사가 붙는다.
4. **날짜**
   - 1900 체계에는 1900-02-29 버그가 있어 기준일 1899-12-30 으로 계산한다. 시간은 하루의 소수부다.
   - JSON 에는 ISO 문자열 + 날짜 `fmt` 로 두고, 내보낼 때 `write_datetime` 으로 쓴다.
5. **너비·높이**
   - 열 너비는 기본 글꼴 숫자 폭 기준 문자 수(+5px)라서 `set_column_pixels` 를 쓴다.
   - 행 높이는 pt(px×0.75)다.
   - 글꼴이 바뀌면 같은 너비 값도 픽셀이 달라진다.
6. **병합**: 테두리·채우기는 나머지 셀에도 준다. 겹치는 병합은 예외가 난다.
7. **조건부 서식·유효성**
   - XlsxWriter `conditional_format`·`data_validation` 으로 쓴다.
   - 직접 적은 유효성 목록은 255자 제한이 있다 (일반 지식).
8. **가져오기**
   - openpyxl 로 값·수식·스타일·병합·고정·너비·메모·조건부 서식·유효성을 읽는다.
   - 캐시 값은 `data_only=True` 로 따로 연다.
   - 차트·피벗·이미지는 경고만 하고 버린다.

## 6. 확인하지 못한 것

- formula.js·ExcelJS·openpyxl 의 현재 라이선스와 유지 상태
- 라이브러리 번들 크기
- Univer engine-formula 를 단독으로 쓸 수 있는지
- Excel 웹 공동 편집 커서·변경 표시 UI 세부
- `#FIELD!`·`#BUSY!` 의 정확한 의미
- Agent Mode 의 EU·UK 제공 상태(2차 출처)

## 출처

- HyperFormula 라이선스 https://handsontable.com/docs/hyperformula/guide/licensing.html · 개요 https://handsontable.com/docs/hyperformula/
- Univer https://github.com/dream-num/univer · 가져오기/내보내기 https://docs.univer.ai/guides/sheets/features/import-export · engine-formula https://docs.univer.ai/reference/packages/plugins/univerjs/engine-formula
- Luckysheet https://github.com/dream-num/Luckysheet · FortuneSheet https://github.com/ruilisi/fortune-sheet
- Handsontable 라이선스 https://handsontable.com/docs/software-license/ · Jspreadsheet https://bossanova.uk/jspreadsheet/blog/jspreadsheet-ce-vs-pro
- AG Grid https://www.ag-grid.com/javascript-data-grid/community-vs-enterprise.md · SheetJS https://docs.sheetjs.com/docs/miscellany/license
- COPILOT 함수 https://support.microsoft.com/en-us/Excel/functions/copilot-function · https://mc.merill.net/message/MC1454373
- Copilot in Excel https://support.microsoft.com/en-us/office/get-started-with-copilot-in-excel-d7110502-0334-4b4f-a175-a73abdfc118a · Agent Mode https://techcommunity.microsoft.com/t5/excel/bg-p/ExcelBlog
- Python in Excel https://support.microsoft.com/en-us/office/introduction-to-python-in-excel-55643c2e-ff56-4168-b1ce-9428c8308545
- Gemini in Sheets https://support.google.com/docs/answer/14356410 · Gemini 로 정리 https://support.google.com/docs/answer/13951830 · AI 함수 https://support.google.com/docs/answer/15877199
- Sheets 표 https://support.google.com/docs/answer/14239833 · 단축키 https://support.google.com/docs/answer/181110 · 수정 기록 https://support.google.com/docs/answer/190843
- Excel 단축키 https://support.microsoft.com/en-us/office/keyboard-shortcuts-in-excel-1798d9d5-842a-42b8-9c99-9b7213f0040f
- 동적 배열 https://support.microsoft.com/en-us/office/dynamic-array-formulas-and-spilled-array-behavior-205c6b06-03ba-4151-89a1-87a7eb36e531 · PIVOTBY https://support.microsoft.com/en-us/Excel/functions/pivotby-function
- Excel 재계산 https://learn.microsoft.com/en-us/office/client-developer/excel/excel-recalculation · 오류 값 https://learn.microsoft.com/en-us/javascript/api/excel/excel.errorcellvaluetype
- 댓글과 메모 https://support.microsoft.com/en-us/excel/the-difference-between-threaded-comments-and-notes
- XlsxWriter 수식 https://xlsxwriter.readthedocs.io/working_with_formulas.html · ECMA-376 열 너비 https://webapp.docx4java.org/OnlineDemo/ecma376/SpreadsheetML/col.html
