"""엔진 시트 테마 '화면 설계서'(screen-spec) 만들기 - 실제 화면 설계서(엑셀)의 구조·서식만 옮기고 내용은 일반 예시(고객 정보 없음).

    python3 studio/sheet_themes/screen-spec/build.py      # → 같은 폴더 theme.json

테마를 고칠 때는 이 파일을 고치고 다시 만든다. docs/sheets.md 5절."""
import json
import sys
from pathlib import Path

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent


def cn(i):  # 0 → A
    s = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


class Page:
    def __init__(self, kind, name, cols, landscape=True):
        self.t = {"kind": kind, "name": name, "grid": False, "print": {"landscape": landscape, "fitWidth": 1},
                  "cols": {cn(i): w for i, w in enumerate(cols)}, "rows": {}, "merges": [], "cells": {}}
        self.n = len(cols)
        self.r = 1

    def put(self, c, r, v=None, s=None, **kw):
        cell = {}
        if v is not None:
            cell["v"] = v
        if s:
            cell["s"] = s
        cell.update(kw)
        self.t["cells"][f"{cn(c)}{r}"] = cell

    def band(self, text, s, h, c0=0, c1=None):
        """한 줄 띠(제목·절) - 표 너비만큼 병합, 병합 칸마다 테두리 스타일이 이어지게 같은 스타일."""
        c1 = self.n - 1 if c1 is None else c1
        for c in range(c0, c1 + 1):
            self.put(c, self.r, text if c == c0 else None, s)
        self.t["merges"].append(f"{cn(c0)}{self.r}:{cn(c1)}{self.r}")
        self.t["rows"][str(self.r)] = h
        self.r += 1

    def title(self, text):
        self.band(text, "title", 35)
        self.r += 1

    def section(self, text):
        self.band(text, "section", 29)

    def table(self, head, rows, styles=None, gap=1, spans=None):
        """머리 + 행. styles = 열마다 셀 스타일(없으면 cell). spans = 열마다 [첫 열, 끝 열](넓은 칸은 병합)."""
        styles = styles or ["cell"] * len(head)
        spans = spans or [[c, c] for c in range(len(head))]

        def line(vals, sts):
            for (c0, c1), v, s in zip(spans, vals, sts):
                for c in range(c0, c1 + 1):
                    self.put(c, self.r, v if c == c0 else None, s)
                if c1 > c0:
                    self.t["merges"].append(f"{cn(c0)}{self.r}:{cn(c1)}{self.r}")
            self.r += 1
        line(head, ["header"] * len(head))
        for row in rows:
            line([row[c] if c < len(row) else "" for c in range(len(head))], styles)
        self.r += gap

    def code(self, text, h, c1=None):
        c1 = self.n - 1 if c1 is None else c1
        for c in range(0, c1 + 1):
            self.put(c, self.r, text if c == 0 else None, "code")
        self.t["merges"].append(f"A{self.r}:{cn(c1)}{self.r}")
        self.t["rows"][str(self.r)] = h
        self.r += 2

    def note(self, text, h=None):
        for c in range(self.n):
            self.put(c, self.r, text if c == 0 else None, "memo")
        self.t["merges"].append(f"A{self.r}:{cn(self.n - 1)}{self.r}")
        if h:
            self.t["rows"][str(self.r)] = h
        self.r += 1


pages = []

# 1. 개요
p = Page("overview", "개요", [144, 840], landscape=False)
p.title("화면 설계서 — {{title}}")
info = [("화면명", "{{title}}"), ("화면 ID", "{{screen}}"), ("메뉴 경로", "예) 기준정보 > 우선순위 관리"),
        ("목적", "이 화면으로 무엇을 결정·관리하는지 한두 문장으로 적는다."),
        ("결정 로직", "핵심 규칙 요약 - 예) 기본 규칙(등급 조합) + 예외 규칙(특정 고객·품목)의 2계층."),
        ("대상 테이블", "주 테이블(CRUD)과 참조 테이블 - 상세는 [사용테이블목록]."),
        ("Tab 1", "예) 규칙 설정 : 상단 = 기본 규칙 그리드, 하단 = 예외 규칙 그리드"),
        ("Tab 2", "예) 결과 조회 : 조회 조건으로 대상을 불러와 적용 결과 확인(조회 전용)"),
        ("공통 기준", "예) 고정 상수·권한·조회 기준(사업장·버전 등)"),
        ("프로젝트", "{{project}}"), ("작성자", "{{author}}"), ("작성일 · 버전", "{{date}} · v{{version}}"),
        ("시트 구성", "①개요 ②변경이력 ③사용테이블목록 ④테이블정의 ⑤화면_Tab1 ⑥화면레이아웃 ⑦코드소스 ⑧쿼리 ⑨동작 ⑩유효성검증")]
for k, v in info:
    p.put(0, p.r, k, "label")
    p.put(1, p.r, v, "cell")
    p.t["rows"][str(p.r)] = 40 if k in ("목적", "결정 로직", "시트 구성") else 27
    p.r += 1
pages.append(p.t)

# 2. 변경이력
p = Page("history", "변경이력", [72, 104, 560, 120, 120], landscape=False)
p.title("변경 이력")
p.table(["버전", "일자", "변경 내용", "작성자", "검토자"],
        [["{{version}}", "{{date}}", "최초 작성", "{{author}}", ""], ["", "", "", "", ""], ["", "", "", "", ""], ["", "", "", "", ""]],
        ["center", "center", "cell", "center", "center"])
pages.append(p.t)

# 3. 사용테이블목록
p = Page("tables", "사용테이블목록", [160, 160, 496, 64], landscape=False)
p.title("사용 테이블 목록")
p.table(["테이블", "논리명", "용도", "접근"],
        [["TB_RULE_MST", "우선순위 규칙", "주 테이블(CRUD) — 기본/예외 규칙 저장", "R/W"],
         ["TB_ORDER", "주문 현황", "Tab2 조회 대상", "R"],
         ["TB_CUST_GRP", "고객그룹 마스터", "고객그룹 팝업·콤보 + 고객 등급", "R"],
         ["TB_ITEM", "품목 마스터", "품목 팝업 + 품목 등급", "R"],
         ["TB_CODE_DTL", "공통코드 상세", "등급·우선순위 콤보", "R"]],
        ["key", "cell", "cell", "center"])
pages.append(p.t)

# 4. 테이블정의
p = Page("tabledef", "테이블정의", [128, 128, 88, 160, 176, 120, 104, 72, 88, 144])
p.title("테이블 정의 — TB_RULE_MST  (설계서용 조회 쿼리 결과를 붙여 넣어도 된다)")
H = ["TABLE_NAME", "TABLE_DESC", "COLUMN_ID", "COLUMN_NAME", "COLUMN_DESC", "DATA_TYPE", "PK_POSITION", "DESCEND", "NULLABLE", "DATA_DEFAULT"]
cols = [("PROJECT_CD", "프로젝트 코드", "VARCHAR2(50)", "1", "N", ""), ("CUST_GRP_CD", "고객그룹 코드", "VARCHAR2(30)", "2", "N", "'*'"),
        ("ITEM_CD", "품목 코드", "VARCHAR2(30)", "3", "N", "'*'"), ("APLY_PRORT", "적용 우선순위", "VARCHAR2(10)", "", "Y", ""),
        ("DEL_YN", "삭제 여부", "CHAR(1)", "", "N", "'N'"), ("UPD_USER", "수정자", "VARCHAR2(30)", "", "Y", ""), ("UPD_DTTM", "수정 일시", "DATE", "", "Y", "SYSDATE")]
p.table(H, [["TB_RULE_MST", "우선순위 규칙", str(i + 1), c, d, t, pk, "ASC" if pk else "", nl, df] for i, (c, d, t, pk, nl, df) in enumerate(cols)],
        ["cell", "cell", "center", "key", "cell", "cell", "center", "center", "center", "cell"])
p.section("[코드 값 정의] 규칙 유형 (CUST_GRP_CD / ITEM_CD 조합)")
p.table(["유형", "CUST_GRP_CD", "ITEM_CD", "의미"],
        [["BASE", "*", "*", "기본 규칙 - 등급 조합으로 결정"], ["CUST", "고객그룹", "*", "특정 고객그룹 예외"],
         ["ITEM", "*", "품목", "특정 품목 예외"], ["BOTH", "고객그룹", "품목", "고객그룹 + 품목 예외(가장 우선)"]],
        ["key", "center", "center", "cell"], spans=[[0, 0], [1, 1], [2, 2], [3, 9]])
pages.append(p.t)

# 5. 화면_Tab1
p = Page("screen", "화면_Tab1", [128, 112, 64, 72, 72, 144, 56, 48, 64, 48, 48, 240])
p.title("Tab 1 — 규칙 설정 (상/하 2그리드)")
p.section("[조회조건]")
p.table(["항목", "컨트롤", "소스", "전체옵션", "기본값"],
        [["삭제여부", "콤보", "공통코드 YN_CD (Y=삭제 / N=미삭제)", "예 (전체·N·Y)", "N (미삭제만)"],
         ["고객그룹", "입력+찾기", "TB_CUST_GRP 팝업", "-", "(빈칸 = 전체)"]],
        ["key", "cell", "cell", "cell", "cell"], spans=[[0, 0], [1, 1], [2, 5], [6, 8], [9, 11]])
G = ["컬럼", "논리명", "타입", "가로정렬", "세로정렬", "포맷", "넓이", "표시", "행병합", "필수", "편집", "입력/코드소스"]
GS = ["key", "cell", "center", "center", "center", "center", "center", "center", "center", "center", "center", "cell"]
p.section("[상단 그리드] 기본 규칙 (BASE) — 등급 조합별 적용 우선순위")
p.table(G, [["CUST_PRORT", "고객 등급", "문자", "가운데", "가운데", "", "80", "Y", "Y", "Y", "N", "공통코드 MP_CUST_PRORT"],
            ["ITEM_PRORT", "품목 등급", "문자", "가운데", "가운데", "", "80", "Y", "N", "Y", "N", "공통코드 MP_ITEM_PRORT"],
            ["APLY_PRORT", "적용 우선순위", "콤보", "가운데", "가운데", "", "100", "Y", "N", "Y", "Y", "공통코드 MP_APLY_PRORT"],
            ["UPD_USER", "수정자", "문자", "가운데", "가운데", "", "90", "Y", "N", "N", "N", "자동(로그인 사용자)"]], GS)
p.section("[하단 그리드] 예외 규칙 — 특정 고객/품목")
p.table(G, [["CUST_GRP_CD", "고객그룹", "찾기", "왼쪽", "가운데", "", "120", "Y", "N", "Y", "Y", "고객그룹 팝업"],
            ["ITEM_CD", "품목", "찾기", "왼쪽", "가운데", "", "120", "Y", "N", "Y", "Y", "품목 팝업"],
            ["APLY_PRORT", "적용 우선순위", "콤보", "가운데", "가운데", "", "100", "Y", "N", "Y", "Y", "공통코드 MP_APLY_PRORT"],
            ["DEL_YN", "삭제여부", "콤보", "가운데", "가운데", "", "70", "Y", "N", "Y", "Y", "공통코드 YN_CD"]], GS)
p.section("[버튼]")
p.table(["버튼", "위치", "동작", "권한"],
        [["조회", "상단 오른쪽", "조회조건으로 두 그리드를 다시 읽는다", "전체"], ["저장", "상단 오른쪽", "바뀐 행만 저장 - [동작] 저장 분기 규칙", "편집"],
         ["추가 · 삭제", "하단 그리드 위", "하단 그리드 전용 - 빈 행 추가 · 논리 삭제", "편집"]], ["key", "cell", "cell", "center"], spans=[[0, 0], [1, 1], [2, 10], [11, 11]])
p.section("[팝업]")
p.table(["팝업", "소스", "반환", "표시 컬럼"],
        [["고객그룹 찾기", "TB_CUST_GRP", "CUST_GRP_CD, 고객 등급", "코드 · 이름 · 등급"], ["품목 찾기", "TB_ITEM", "ITEM_CD, 품목 등급", "코드 · 이름 · 등급"]],
        ["key", "cell", "cell", "cell"], spans=[[0, 0], [1, 1], [2, 5], [6, 11]])
p.section("[저장 규칙]")
p.note("· 같은 키(고객그룹 + 품목)가 이미 있으면 저장하지 않고 알린다.\n· 삭제된 행과 같은 키로 다시 추가하면 삭제를 되살린다(DEL_YN = 'N').", 50)
pages.append(p.t)

# 6. 화면레이아웃 - 셀로 그린 와이어프레임(가는 열 24개)
p = Page("layout", "화면레이아웃", [30] * 24)
L = p.t


def box(c0, r0, c1, r1, s, text=None, merge=True):
    for r in range(r0, r1 + 1):
        for c in range(c0, c1 + 1):
            p.put(c, r, text if (r, c) == (r0, c0) and text else None, s)
    if merge and (c0, r0) != (c1, r1):
        L["merges"].append(f"{cn(c0)}{r0}:{cn(c1)}{r1}")


box(0, 1, 18, 2, "wfTitle", "  {{title}} (Tab 1 · 규칙 설정)   〔화면 제목〕")
box(20, 1, 21, 2, "wfBtn", "조회")
box(22, 1, 23, 2, "wfSave", "저장")
box(0, 3, 3, 3, "wfTabOn", "규칙 설정")
box(4, 3, 7, 3, "wfTabOff", "결과 조회")
box(0, 4, 4, 4, "wfSec", "▼ 조회조건")
box(0, 5, 4, 5, "wfLabel", "삭제여부   〔콤보〕")
box(0, 6, 4, 6, "wfInput", "N                     ▼")
box(0, 7, 4, 7, "wfLabel", "고객그룹   〔입력+찾기〕")
box(0, 8, 3, 8, "wfInput", "")
box(4, 8, 4, 8, "wfBtn", "찾기")
box(0, 9, 4, 30, "wfPanel", merge=False)
box(5, 4, 23, 4, "wfGridHead", "  상단 그리드 — 기본 규칙(BASE) · 등급 조합 → 적용 우선순위")
box(5, 5, 23, 15, "wfGridBody", merge=False)
box(5, 9, 23, 10, "wfGrid", "◈  상단 그리드 (Grid 1)  ◈  등급 조합 행 · 콤보 입력")
box(5, 16, 18, 16, "wfHint", "▲ [추가]·[삭제] = 하단 그리드 전용")
box(20, 16, 21, 16, "wfBtn", "추가")
box(22, 16, 23, 16, "wfBtn", "삭제")
box(5, 17, 23, 17, "wfGridHead", "  하단 그리드 — 예외 규칙 · 특정 고객/품목")
box(5, 18, 23, 30, "wfGridBody", merge=False)
box(5, 23, 23, 24, "wfGrid", "◈  하단 그리드 (Grid 2)  ◈  [찾기] 팝업으로 고객/품목 지정")
for r in range(1, 31):
    L["rows"][str(r)] = 22
L["rows"]["32"] = 22
p.put(0, 32, "도형 대신 셀 병합·채우기로 그린 와이어프레임 - 칸을 늘리거나 색을 바꿔 화면 배치를 고친다(엑셀 그림 붙여넣기도 된다).", "memo")
L["merges"].append("A32:X32")
for c in range(1, 24):
    p.put(c, 32, None, "memo")
pages.append(L)

# 7. 코드소스
p = Page("codes", "코드소스", [144, 176, 160, 176], landscape=False)
p.title("코드 / 콤보 / 팝업 소스 요약")
p.section("[공통코드 값] TB_CODE_DTL")
p.table(["화면 항목", "코드 그룹", "코드값(저장)", "이름(표시)"],
        [["적용 우선순위", "MP_APLY_PRORT", "A / B / C / D / Z", "A=최우선 … Z=제외"], ["고객 등급", "MP_CUST_PRORT", "1 / 2 / 3 / 4", "1등급 … 4등급"],
         ["품목 등급", "MP_ITEM_PRORT", "1 / 2 / 3 / 4", "1등급 … 4등급"], ["삭제여부", "YN_CD", "Y / N", "삭제 / 미삭제"]],
        ["key", "cell", "center", "cell"])
p.section("[콤보/팝업 소스 요약] — 각 SELECT 는 [쿼리] 참고")
p.table(["화면 항목", "입력 UI", "소스 테이블", "쿼리"],
        [["적용 우선순위", "콤보", "TB_CODE_DTL", "[쿼리] ①"], ["고객그룹", "팝업", "TB_CUST_GRP", "[쿼리] ②"], ["품목", "팝업", "TB_ITEM", "[쿼리] ③"]],
        ["key", "center", "cell", "center"])
pages.append(p.t)

# 8. 쿼리
p = Page("queries", "쿼리", [144] * 6)
p.title("콤보 / 팝업 / 조회 SELECT 쿼리")
qs = [("① 적용 우선순위 콤보  (MP_APLY_PRORT)", "SELECT CODE_CD AS VALUE, CODE_NM AS LABEL\n  FROM TB_CODE_DTL\n WHERE CODE_GRP = 'MP_APLY_PRORT'\n   AND USE_YN = 'Y'\n ORDER BY SORT_SEQ", 100),
      ("② 고객그룹 팝업  (TB_CUST_GRP)", "SELECT CUST_GRP_CD, CUST_GRP_NM, CUST_PRORT_VAL\n  FROM TB_CUST_GRP\n WHERE (:KEYWORD IS NULL OR CUST_GRP_NM LIKE '%' || :KEYWORD || '%')\n ORDER BY CUST_GRP_CD", 90),
      ("③ 품목 팝업  (TB_ITEM)", "SELECT ITEM_CD, ITEM_NM, ITEM_GRADE\n  FROM TB_ITEM\n WHERE (:KEYWORD IS NULL OR ITEM_NM LIKE '%' || :KEYWORD || '%')", 75),
      ("④ [Tab1] 상단(BASE) 그리드 조회", "SELECT CUST_PRORT, ITEM_PRORT, APLY_PRORT, UPD_USER, UPD_DTTM\n  FROM TB_RULE_MST\n WHERE PROJECT_CD = :PROJECT_CD\n   AND CUST_GRP_CD = '*' AND ITEM_CD = '*'\n ORDER BY CUST_PRORT, ITEM_PRORT", 100)]
for t, q, h in qs:
    p.section(t)
    p.code(q, h)
pages.append(p.t)

# 9. 동작
p = Page("actions", "동작", [112, 128, 736], landscape=False)
p.title("동작 방식 (Tab 1) — 데이터 / 컬럼 / 저장")
p.table(["기능", "구분", "상세"],
        [["공통", "고정상수", "예) PROJECT_CD = :PROJECT_CD, 조회 기준 버전 등 화면 전체에 붙는 조건"],
         ["조회", "데이터설정", "상단(BASE) / 하단(예외) 그리드를 각각 [쿼리] ④·⑤ 로 읽는다"],
         ["조회", "컬럼설정", "[화면_Tab1] 그리드 컬럼 정의대로 - 콤보 소스는 [코드소스]"],
         ["추가", "데이터설정", "하단 빈 행(상태 = INSERT). 기본값: 삭제여부 N"],
         ["저장", "분기규칙", "INSERT(키 없음) → INSERT · 키 있음 → UPDATE · 삭제 행과 같은 키 → 되살리기"],
         ["삭제", "논리삭제", "저장 전 새 행 → 그리드에서 제거. 기존 행 → DEL_YN = 'Y' 로 UPDATE"]],
        ["label", "center", "cell"])
pages.append(p.t)

# 10. 유효성검증
p = Page("validation", "유효성검증", [48, 144, 640], landscape=False)
p.title("유효성 검증 (저장 시)")
p.table(["No", "항목", "규칙"],
        [["1", "필수 입력", "[화면_Tab1] 필수 = Y 컬럼이 비어 있으면 저장하지 않고 그 셀로 이동"],
         ["2", "키 중복", "같은 고객그룹 + 품목 조합이 이미 있으면 알림"],
         ["3", "코드 값", "콤보 값이 공통코드에 없으면 저장하지 않음"]],
        ["center", "key", "cell"])
pages.append(p.t)

theme = {
    "label": "화면 설계서",
    "font": "맑은 고딕", "size": 10, "grid": False,
    "palette": {"primary": "#1F4E78", "secondary": "#2E75B6", "line": "#BFBFBF", "band": "#F2F2F2", "input": "#FFF2CC",
                "warn": "#C00000", "muted": "#808080", "text": "#262626", "code": "#F7F7F7", "light": "#DEEBF7",
                "button": "#D9D9D9", "ok": "#70AD47", "dark": "#404040"},
    "styles": {
        "title": {"size": 13, "b": True, "color": "#FFFFFF", "fill": "primary", "align": "left", "valign": "middle"},
        "section": {"b": True, "color": "#FFFFFF", "fill": "secondary", "align": "left", "valign": "middle", "bd": "line"},
        "header": {"size": 10, "b": True, "color": "#FFFFFF", "fill": "primary", "align": "center", "valign": "middle", "wrap": True, "bd": "line"},
        "label": {"size": 10, "b": True, "fill": "band", "align": "center", "valign": "middle", "wrap": True, "bd": "line"},
        "cell": {"size": 10, "align": "left", "valign": "middle", "wrap": True, "bd": "line"},
        "center": {"size": 10, "align": "center", "valign": "middle", "wrap": True, "bd": "line"},
        "key": {"size": 10, "b": True, "align": "left", "valign": "middle", "wrap": True, "bd": "line"},
        "input": {"fill": "input", "align": "center", "valign": "middle", "bd": "line"},
        "code": {"size": 9, "fill": "code", "align": "left", "valign": "top", "wrap": True, "bd": "line"},
        "memo": {"size": 10, "align": "left", "valign": "top", "wrap": True},
        "warn": {"b": True, "color": "warn"},
        "note": {"size": 9, "color": "muted"},
        "wfTitle": {"b": True, "fill": "band", "align": "left", "valign": "middle", "bd": "line"},
        "wfBtn": {"fill": "button", "align": "center", "valign": "middle", "bd": "line"},
        "wfSave": {"b": True, "color": "#FFFFFF", "fill": "ok", "align": "center", "valign": "middle", "bd": "line"},
        "wfTabOn": {"b": True, "color": "#FFFFFF", "fill": "secondary", "align": "center", "valign": "middle", "bd": "line"},
        "wfTabOff": {"fill": "light", "align": "center", "valign": "middle", "bd": "line"},
        "wfSec": {"b": True, "color": "#FFFFFF", "fill": "secondary", "align": "left", "valign": "middle"},
        "wfLabel": {"b": True, "color": "text", "fill": "band", "align": "left", "valign": "middle"},
        "wfInput": {"fill": "input", "align": "left", "valign": "middle", "bd": "line"},
        "wfPanel": {"fill": "band"},
        "wfGridHead": {"b": True, "color": "#FFFFFF", "fill": "primary", "align": "left", "valign": "middle"},
        "wfGridBody": {"fill": "#FFFFFF"},
        "wfGrid": {"b": True, "color": "primary", "fill": "light", "align": "center", "valign": "middle", "wrap": True},
        "wfHint": {"size": 9, "color": "muted", "align": "left", "valign": "middle"},
    },
    "vars": {"project": "", "screen": "", "author": "", "version": "1.0"},
    "pages": pages,
}
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "theme.json").write_text(json.dumps(theme, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
print("ok", len(pages), "pages")
