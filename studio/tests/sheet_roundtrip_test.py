# -*- coding: utf-8 -*-
"""시트 엑셀 왕복 시험 - 시트 문서를 xlsx 로 내보내고(export_xlsx) 다시 가져와(sheet_import) 같은지 본다.
값·수식·계산값·서식·병합·틀 고정·열 너비·숨김·유효성·조건부 서식·메모·다른 탭 참조·동적 배열(넘침·H2#)·새 함수(LET·XMATCH)·엑셀 표(구조적 참조).
엑셀 파일은 시험 안에서 만든다(저장소에 바이너리를 두지 않는다). Excel 로 연 결과는 사람이 확인했다(CHANGELOG 0.24.0)."""
import copy
import json
import os
import sys
import tempfile
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
TMP = Path(tempfile.mkdtemp(prefix="nexa-sheet-rt-"))
(TMP / "nexa-slide.json").write_text("{}", encoding="utf-8")
os.environ["NEXA_SLIDE_WORKSPACE"] = str(TMP)  # export_xlsx 가 common 을 읽는다 - 빈 작업 공간이면 된다
sys.path.insert(0, str(HERE.parent))
import export_xlsx  # noqa: E402
import sheet_calc  # noqa: E402
import sheet_import  # noqa: E402

FAILS = []


def check(name, ok, got=None):
    print(("OK   " if ok else "FAIL ") + name + ("" if ok else f" → {got}"))
    if not ok:
        FAILS.append(name)


DOC = {"kind": "sheet", "title": "왕복", "slides": [], "sheets": [
    {"id": "t01", "name": "데이터", "freeze": "A2", "cols": {"A": 120, "B": 90},
     "merges": ["F1:G1"], "hiddenRows": ["9"], "hiddenCols": ["H"],
     "validations": [{"range": "D2:D5", "list": ["완료", "진행", "대기"]}],
     "conds": [{"range": "B2:B5", "type": "gt", "value": 700, "style": {"fill": "#FFC7CE", "color": "#9C0006"}}],
     "tables": [{"name": "매출표", "ref": "A1:E5", "cols": ["지역", "1분기", "2분기", "상태", "합계"]}],
     "cells": {
         "A1": {"v": "지역", "b": True, "fill": "#1F4E79", "color": "#FFFFFF"}, "B1": "1분기", "C1": "2분기", "D1": "상태", "E1": "합계",
         "A2": "서울", "B2": {"v": 1200, "fmt": "#,##0"}, "C2": 1500, "D2": "완료", "E2": {"f": "=[@1분기]+[@[2분기]]"},
         "A3": "부산", "B3": 800, "C3": 700, "D3": "진행", "E3": {"f": "=매출표[@1분기]+매출표[@2분기]"},
         "A4": "대구", "B4": 500, "C4": 900, "D4": "완료", "E4": {"f": "=B4+C4"},
         "A5": "광주", "B5": 300, "C5": {"v": 0.15, "fmt": "0.0%"}, "D5": "대기", "E5": {"f": "=B5+C5"},
         "F1": {"v": "병합 제목", "align": "center"}, "F2": {"f": "=SUM(매출표[1분기])"}, "F3": {"f": "=COUNTIF(매출표[상태],\"완료\")"},
         "F4": {"v": True}, "F5": {"v": 46323, "fmt": "yyyy-mm-dd", "note": "기준일"},
         "J1": {"f": "=SORT(B2:B5)"}, "K1": {"f": "=SUM(J1#)"}, "L1": {"f": "=J1#*10"},
         "M1": {"f": "=LET(x,SUM(B2:B5),y,4,x/y)"}, "M2": {"f": "=XMATCH(\"대구\",A2:A5)"}, "M3": {"f": "=TEXTJOIN(\",\",TRUE,UNIQUE(D2:D5))"},
         "M4": {"f": "=요약!A1*2"},
         "N1": {"f": "=SUM(분기1)"}, "N2": {"f": "=목표*2"}, "N3": {"f": "=COUNTA(지역들)"},
         "O1": {"f": "=GROUPBY(D2:D5,B2:B5,SUM)"}},
     "names": {"지역들": "데이터!$A$2:$A$5"}},
    {"id": "t02", "name": "요약", "hidden": True, "cells": {"A1": {"f": "=데이터!F2"}, "A2": "숨긴 탭"}},
], "names": {"분기1": "데이터!$B$2:$B$5", "목표": "1000"}}


def val(c):
    return c.get("v") if isinstance(c, dict) else c


def main():
    for st in (sys.stdout, sys.stderr):
        try:
            st.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass
    src = copy.deepcopy(DOC)
    sheet_calc.recalc(src)  # 기대 계산값 - 내보내기·가져오기를 거쳐도 같아야 한다
    out = TMP / "rt.xlsx"
    export_xlsx.export(copy.deepcopy(DOC), out)
    check("내보내기 - 파일이 생김", out.is_file())
    z = zipfile.ZipFile(out)
    xml = z.read("xl/worksheets/sheet1.xml").decode("utf-8")
    check("파일 형식 - 새 함수 접두사·이 행·넘친 범위", all(s in xml for s in ("_xlfn._xlws.SORT(", "_xlfn.ANCHORARRAY(J1)", "_xlfn.LET(_xlpm.x", "매출표[[#This Row],[1분기]]")), xml[:0])
    check("파일 형식 - 표 파트", any(n.startswith("xl/tables/") for n in z.namelist()), z.namelist())
    tabs, warnings, _ = sheet_import.import_xlsx(out)
    check("가져오기 - 탭 2개·이름·숨김", [t["name"] for t in tabs] == ["데이터", "요약"] and tabs[1].get("hidden") is True, [(t["name"], t.get("hidden")) for t in tabs])
    a, e = tabs[0], src["sheets"][0]
    check("값·계산값이 같다(수식 칸 포함)", all(sheet_calc.fix(val(a["cells"].get(k))) == sheet_calc.fix(val(c)) if isinstance(val(c), float) else val(a["cells"].get(k)) == val(c)
                                     for k, c in e["cells"].items() if not (isinstance(c, dict) and c.get("sp"))),
          {k: (val(a["cells"].get(k)), val(c)) for k, c in e["cells"].items() if val(a["cells"].get(k)) != val(c)})
    f = {k: c.get("f") for k, c in a["cells"].items() if isinstance(c, dict) and c.get("f")}
    check("수식 글이 화면 형식으로 돌아온다", f.get("E2") == "=매출표[@[1분기]]+매출표[@[2분기]]" and f.get("K1") == "=SUM(J1#)" and f.get("M1") == "=LET(x,SUM(B2:B5),y,4,x/y)"
          and f.get("J1") == "=SORT(B2:B5)" and f.get("M4") == "=요약!A1*2", f)
    check("동적 배열 - 기준 칸 da, 넘친 칸 sp", a["cells"]["J1"].get("da") is True and a["cells"]["J4"].get("sp") == "J1" and a["cells"]["L4"].get("v") == 12000,
          {k: a["cells"].get(k) for k in ("J1", "J4", "L4")})
    check("서식 - 굵게·채우기·글자색·표시 형식·정렬", a["cells"]["A1"].get("b") is True and str(a["cells"]["A1"].get("fill", "")).upper() == "#1F4E79"
          and a["cells"]["B2"].get("fmt") == "#,##0" and a["cells"]["C5"].get("fmt") == "0.0%" and a["cells"]["F1"].get("align") == "center",
          {k: a["cells"].get(k) for k in ("A1", "B2", "C5", "F1")})
    check("병합·틀 고정·열 너비", a.get("merges") == ["F1:G1"] and a.get("freeze") == "A2" and a.get("cols", {}).get("A") == 120, (a.get("merges"), a.get("freeze"), a.get("cols")))
    check("숨긴 행·열", [str(x) for x in a.get("hiddenRows") or []] == ["9"] and a.get("hiddenCols") == ["H"], (a.get("hiddenRows"), a.get("hiddenCols")))
    dv = a.get("validations") or []
    check("드롭다운 목록", len(dv) == 1 and dv[0].get("range") == "D2:D5" and dv[0].get("list") == ["완료", "진행", "대기"], dv)
    cf = a.get("conds") or []
    check("조건부 서식", len(cf) == 1 and cf[0].get("type") == "gt" and cf[0].get("value") == 700 and cf[0].get("range") == "B2:B5", cf)
    check("메모", a["cells"]["F5"].get("note") == "기준일", a["cells"].get("F5"))
    tb = a.get("tables") or []
    check("엑셀 표 - 이름·범위·열", len(tb) == 1 and tb[0]["name"] == "매출표" and tb[0]["ref"] == "A1:E5" and tb[0]["cols"][4] == "합계", tb)
    check("파일 형식 - GROUPBY 는 _xlfn.·_xleta.", "_xlfn.GROUPBY(D2:D5,B2:B5,_xleta.SUM)" in xml, "")
    check("GROUPBY - 수식 글·넘친 값(합계 줄)", f.get("O1") == "=GROUPBY(D2:D5,B2:B5,SUM)" and val(a["cells"].get("O4")) == "Total" and val(a["cells"].get("P4")) == 2800, {k: a["cells"].get(k) for k in ("O1", "O4", "P4")})
    check("이름 정의 칸 계산값", [val(a["cells"].get(k)) for k in ("N1", "N2", "N3")] == [2800, 2000, 4], [val(a["cells"].get(k)) for k in ("N1", "N2", "N3")])
    doc2, _ = sheet_import.to_doc("rt", "왕복", out)
    nb, nt = doc2.get("names") or {}, doc2["sheets"][0].get("names") or {}
    check("이름 정의 - 문서 범위·탭 범위로 돌아온다", nb.get("목표") == "1000" and "$B$2:$B$5" in nb.get("분기1", "") and "$A$2:$A$5" in nt.get("지역들", ""), (nb, nt))
    doc2["sheets"][0]["cells"]["B2"] = 2200
    sheet_calc.recalc(doc2)
    check("이름 정의 - 원본 칸을 고치면 다시 계산(=SUM(분기1))", val(doc2["sheets"][0]["cells"]["N1"]) == 3800, doc2["sheets"][0]["cells"].get("N1"))
    again = {"sheets": copy.deepcopy(tabs)}  # 이름 정의 없이 - 이름 칸은 엑셀 값을 그대로 둬야 같다
    sheet_calc.recalc(again)
    check("다시 계산해도 같다(가져온 문서)", json.dumps(again["sheets"], ensure_ascii=False, sort_keys=True) == json.dumps(tabs, ensure_ascii=False, sort_keys=True), "")
    print("경고:", warnings or "없음")
    print("\n실패:", FAILS or "없음")
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
