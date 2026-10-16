# -*- coding: utf-8 -*-
"""차트 확장(0.22.13) 시험 - 누적 가로·100% 누적(세로·가로)·콤보(막대 + 선, 보조 축)·축 제목·숫자 형식.
PPTX 로 내보내 차트 XML(barDir·grouping·c:lineChart·둘째 c:valAx·축 제목·formatCode)을 보고, render.js 가 같은 종류를 SVG 로 그리는지(node) 본다."""
import json
import os
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
for _s in (sys.stdout, sys.stderr): _s.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).resolve().parent
STUDIO = HERE.parent
WORK = Path(os.environ.get("NEXA_TEST_DIR") or Path(tempfile.gettempdir()) / "nexa-slide-tests")
USER, PROJ, PORT = WORK / "user", WORK / "projects", 5667
WS = PROJ / "chart시험" / "slides"
ENV = {**os.environ, "NEXA_SLIDE_USER_DIR": str(USER), "NEXA_SLIDE_PROJECTS": str(PROJ), "PYTHONIOENCODING": "utf-8", "NEXA_SLIDE_WORKSPACE": str(WS)}
FAILS = []


def check(name, cond, extra=""):
    print(("OK  " if cond else "FAIL"), name, "" if cond else extra)
    if not cond:
        FAILS.append(name)


BASE = {"type": "chart", "x": 40, "y": 40, "w": 600, "h": 300, "labels": True, "categories": ["1분기", "2분기", "3분기"],
        "series": [{"name": "매출", "values": [100, 120, 90]}, {"name": "비용", "values": [60, 70, 50]}, {"name": "성장률", "values": [0.1, 0.2, -0.05]}]}


def main():
    for d in (USER, PROJ):
        d.mkdir(parents=True, exist_ok=True)
    if not (WS / "nexa-slide.json").is_file():
        subprocess.run([sys.executable, str(STUDIO / "init_workspace.py"), str(WS.parent), "--title", "chart시험", "--port", str(PORT)], env=ENV, capture_output=True, text=True, encoding="utf-8")
    els = []
    for i, k in enumerate(["stackedBar", "stackedColumn100", "stackedBar100", "combo", "combo", "column"]):
        e = dict(BASE, id=f"c{i}", chart=k, x=40 + (i % 2) * 620, y=40 + (i // 2) * 220)
        if k == "combo":
            e.update(lineSeries=["성장률"], numFmt="#,##0", axisTitle="억 원", catTitle="분기")
            if i == 4:
                e.update(secondaryAxis=True, numFmt2="0%", axisTitle2="성장률", axisMax2=0.5)
        if k == "column":
            e.update(numFmt='#,##0"억"', axisTitle="매출")
        els.append(e)
    (WS / "decks").mkdir(exist_ok=True)
    (WS / "decks" / "ct.json").write_text(json.dumps({"title": "차트", "slides": [{"id": "s1", "elements": els}]}, ensure_ascii=False), encoding="utf-8")
    r = subprocess.run([sys.executable, str(STUDIO / "export_pptx.py"), "ct", "--out", "out/ct.pptx"], env=ENV, cwd=str(WS), capture_output=True, text=True, encoding="utf-8", errors="replace")
    check("export_pptx 성공", r.returncode == 0 and (WS / "out" / "ct.pptx").is_file(), (r.stderr or r.stdout)[-400:])
    if not (WS / "out" / "ct.pptx").is_file():
        print("실패:", FAILS); sys.exit(1)
    with zipfile.ZipFile(WS / "out" / "ct.pptx") as z:
        names = sorted(n for n in z.namelist() if re.match(r"ppt/charts/chart\d+\.xml", n))
        xs = [z.read(n).decode("utf-8") for n in names]
    check("차트 6개 모두 네이티브 c:chart", len(xs) == 6, str(len(xs)))
    if len(xs) == 6:
        sb, sc100, sb100, cb, cb2, col = xs
        check("누적 가로: barDir=bar grouping=stacked overlap 100", 'barDir val="bar"' in sb and 'grouping val="stacked"' in sb and 'overlap val="100"' in sb)
        check("100% 누적 세로: grouping=percentStacked, 축 max 안 씀", 'barDir val="col"' in sc100 and 'grouping val="percentStacked"' in sc100 and "<c:max " not in sc100)
        check("100% 누적 가로: barDir=bar percentStacked", 'barDir val="bar"' in sb100 and 'grouping val="percentStacked"' in sb100)
        lc = re.findall(r"<c:lineChart>.*?</c:lineChart>", cb, re.S)
        check("콤보: barChart(계열 2) + lineChart(계열 1 - 성장률, 표식·smooth 0)", len(lc) == 1 and lc[0].count("<c:ser>") == 1 and "성장률" in lc[0] and '<c:symbol val="circle"' in lc[0] and '<c:smooth val="0"' in lc[0] and re.search(r"<c:barChart>.*?</c:barChart>", cb, re.S).group(0).count("<c:ser>") == 2)
        check("콤보: 축 하나 공유(valAx 1) · 축 제목 억 원·분기 · formatCode #,##0", cb.count("<c:valAx>") == 1 and "<a:t>억 원</a:t>" in cb and "<a:t>분기</a:t>" in cb and 'formatCode="#,##0"' in cb)
        axes = re.findall(r"<c:valAx>.*?</c:valAx>", cb2, re.S)
        check("콤보 보조 축: valAx 2 - 둘째는 axPos r · crosses max · 0% · 제목 성장률 · max 0.5", len(axes) == 2 and 'axPos val="r"' in axes[1] and 'crosses val="max"' in axes[1] and 'formatCode="0%"' in axes[1] and "성장률" in axes[1] and '<c:max val="0.5"' in axes[1], str([re.findall(r'<c:axPos val="(\w)"', a) for a in axes]))
        check("콤보 보조 축: 주 축은 왼쪽·#,##0·제목 억 원·숨긴 catAx 하나", len(axes) == 2 and 'axPos val="l"' in axes[0] and 'formatCode="#,##0"' in axes[0] and "억 원" in axes[0] and cb2.count('<c:delete val="1"/>') == 1)
        lc2 = re.search(r"<c:lineChart>.*?</c:lineChart>", cb2, re.S).group(0)
        check("콤보 보조 축: lineChart 가 보조 축 id 를 참조", re.findall(r'<c:axId val="(\d+)"', lc2) == ["500100", "500200"], str(re.findall(r'<c:axId val="(\d+)"', lc2)))
        check("세로 막대: 숫자 형식 #,##0\"억\" 눈금·값 표시, 축 제목", 'formatCode="#,##0&quot;억&quot;"' in col and col.count('formatCode="#,##0&quot;억&quot;"') >= 2 and "<a:t>매출</a:t>" in col)
    # render.js
    js = f'''
const fs=require("fs"); const src=fs.readFileSync({json.dumps(str(STUDIO / "render.js"))},"utf8");
const w={{document:{{createElement:()=>({{style:{{}}}}),querySelector:()=>null}},location:{{}},navigator:{{}}}}; w.window=w; w.self=w;
const vm=require("vm"); vm.createContext(w); vm.runInContext(src,w);
const R=w.Render; R.setTokens({{colors:{{primary:"#A91F24","on-surface":"#1F1B1B","on-surface-variant":"#555555","outline-variant":"#DDDDDD"}},fonts:{{body:{{css:"x"}},heading:{{css:"x"}},mono:{{css:"x"}}}}}});
const els={json.dumps(els, ensure_ascii=False)};
const out={{}}; for (const e of els) out[e.id]=R.renderElement(e,1);
out.fmt=[R.chartFmt(1234.5,"#,##0"),R.chartFmt(0.256,"0%"),R.chartFmt(-12.345,"0.0"),R.chartFmt(3200,'#,##0"만 원"'),R.chartFmt(1500,"")];
out.lines=[[...R.comboLines({{chart:"combo",lineSeries:["성장률",7]}},[{{name:"매출"}},{{name:"비용"}},{{name:"성장률"}}])],[...R.comboLines({{chart:"combo"}},[{{name:"a"}},{{name:"b"}}])],[...R.comboLines({{chart:"combo",lineSeries:[0,1]}},[{{name:"a"}},{{name:"b"}}])]];
console.log(JSON.stringify(out));
'''
    r = subprocess.run(["node", "-e", js], capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = {}
    try:
        out = json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:  # noqa: BLE001
        check("render.js 실행", False, (r.stderr or r.stdout)[-300:])
    if out:
        check("chartFmt - 천 단위·%·소수·글자", out["fmt"] == ["1,235", "26%", "-12.3", "3,200만 원", "1,500"], str(out["fmt"]))
        check("comboLines - 이름·범위 밖 무시·기본 마지막·전부 선이면 마지막", out["lines"] == [[2], [1], [1]], str(out["lines"]))
        check("render 누적 가로: 막대 9개(3 계열 × 3) · 범례", out["c0"].count("<rect ") >= 9 and "range" not in out["c0"])
        check("render 100% 누적: 축 눈금 0%~100%", ">0%<" in out["c1"] and ">100%<" in out["c1"] and ">100%<" in out["c2"])
        check("render 콤보: 선 1개(polyline)·막대 6개·축 제목 세로(rotate -90)", out["c3"].count("<polyline") == 1 and out["c3"].count("<rect ") >= 6 and "rotate(-90" in out["c3"] and ">분기<" in out["c3"])
        check("render 콤보 보조 축: 오른쪽 눈금 %·제목 rotate(90)", "rotate(90" in out["c4"] and ">50%<" in out["c4"] and ">20%<" in out["c4"])
        check("render 숫자 형식 #,##0\"억\" 눈금", ">150억<" in out["c5"] or ">100억<" in out["c5"], out["c5"][:0])
    print("실패:", FAILS or "없음")
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
