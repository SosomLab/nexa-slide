# -*- coding: utf-8 -*-
"""0.22.11 문서 구조·마무리 시험 - PPTX 로 내보내 XML 을 본다:
숨김 슬라이드(show=0) · 구분(섹션, p14:sectionLst - section 필드·chapter 레이아웃) · 문서 속성(core.xml 제목·작성자) ·
도형 테두리 점선(prstDash) · 액자 색·두께(frameColor·frameWidth) · SVG 그림(svgBlip + 대체 PNG) · 글자 단위 표기(취소선·첨자·형광펜·링크).
편집기 render.js 가 점선 테두리 SVG·액자 색·새 표기를 내는지도(node)."""
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
WS = PROJ / "docstruct시험" / "slides"
ENV = {**os.environ, "NEXA_SLIDE_USER_DIR": str(USER), "NEXA_SLIDE_PROJECTS": str(PROJ), "PYTHONIOENCODING": "utf-8", "NEXA_SLIDE_WORKSPACE": str(WS)}
FAILS = []
PNG = bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d4944415478da63f8cfc0f01f0005000201e4ae07ea0000000049454e44ae426082")
SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><rect width="100" height="100" fill="#A91F24"/></svg>'


def check(name, cond, extra=""):
    print(("OK  " if cond else "FAIL"), name, "" if cond else extra)
    if not cond:
        FAILS.append(name)


def main():
    for d in (USER, PROJ):
        d.mkdir(parents=True, exist_ok=True)
    if not (WS / "nexa-slide.json").is_file():
        subprocess.run([sys.executable, str(STUDIO / "init_workspace.py"), str(WS.parent), "--title", "docstruct시험", "--port", str(PORT)], env=ENV, capture_output=True, text=True, encoding="utf-8")
    cfg = json.loads((WS / "nexa-slide.json").read_text(encoding="utf-8"))
    cfg["author"] = "시험 작성자"
    (WS / "nexa-slide.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    (WS / "assets" / "images").mkdir(parents=True, exist_ok=True)
    (WS / "assets" / "images" / "t.png").write_bytes(PNG)
    (WS / "assets" / "images" / "v.svg").write_text(SVG, encoding="utf-8")
    deck = {"title": "구조 시험 덱", "slides": [
        {"id": "s01", "layout": "cover", "elements": [
            {"id": "e1", "type": "text", "x": 80, "y": 80, "w": 800, "h": 100, "size": 24, "text": "~~취소~~ m^{2} CO_{2} [[link:https://example.com|문서]] [[link:#3|셋]] [[bg:primary|형광]]"},
            {"id": "e2", "type": "rect", "x": 80, "y": 200, "w": 300, "h": 100, "fill": "surface-container", "stroke": "primary", "strokeWidth": 2, "strokeDash": "dash"},
            {"id": "e3", "type": "shape", "shape": "hexagon", "x": 400, "y": 200, "w": 200, "h": 120, "fill": "primary-container", "stroke": "primary", "strokeDash": "dot"},
            {"id": "e4", "type": "image", "x": 80, "y": 340, "w": 200, "h": 150, "src": "assets/images/t.png", "effect": "frame", "frameColor": "primary", "frameWidth": 8},
            {"id": "e5", "type": "image", "x": 320, "y": 340, "w": 150, "h": 150, "src": "assets/images/v.svg"},
            {"id": "e6", "type": "table", "x": 600, "y": 340, "w": 600, "h": 160, "rows": [["항목", "1분기", "2분기"], ["매출", "10", "20"], ["비용", "5", "7"], ["합계", "15", "27"]],
             "cellFill": [[3, None, "primary-container"], [1, 2, "s1"]], "borders": [[3, "*", "T", "primary", 2], [None, 1, "LR"]]},
            {"id": "e7", "type": "table", "x": 600, "y": 520, "w": 400, "h": 100, "rows": [["a", "b"], ["1", "2"]], "gridLines": True, "header": False}]},
        {"id": "s02", "layout": "chapter", "elements": [{"id": "t", "type": "text", "x": 80, "y": 300, "w": 900, "h": 100, "size": 46, "text": "**1장** 시작"}]},
        {"id": "s03", "hidden": True, "elements": [{"id": "t", "type": "text", "x": 80, "y": 80, "w": 600, "h": 60, "text": "숨김"}]},
        {"id": "s04", "section": "부록", "elements": [{"id": "t", "type": "text", "x": 80, "y": 80, "w": 600, "h": 60, "text": "부록"}]},
    ]}
    (WS / "decks").mkdir(exist_ok=True)
    (WS / "decks" / "ds.json").write_text(json.dumps(deck, ensure_ascii=False), encoding="utf-8")
    r = subprocess.run([sys.executable, str(STUDIO / "export_pptx.py"), "ds", "--out", "out/ds.pptx"], env=ENV, cwd=str(WS), capture_output=True, text=True, encoding="utf-8", errors="replace")
    check("export_pptx 성공", r.returncode == 0 and (WS / "out" / "ds.pptx").is_file(), (r.stderr or r.stdout)[-400:])
    if not (WS / "out" / "ds.pptx").is_file():
        print("실패:", FAILS); sys.exit(1)
    with zipfile.ZipFile(WS / "out" / "ds.pptx") as z:
        names = z.namelist()
        s1 = z.read("ppt/slides/slide1.xml").decode("utf-8")
        s3 = z.read("ppt/slides/slide3.xml").decode("utf-8")
        pres = z.read("ppt/presentation.xml").decode("utf-8")
        core = z.read("docProps/core.xml").decode("utf-8")
        rels1 = z.read("ppt/slides/_rels/slide1.xml.rels").decode("utf-8")
    # 글 표기
    check("취소선 strike=sngStrike", 'strike="sngStrike"' in s1)
    check("위·아래 첨자 baseline", 'baseline="30000"' in s1 and 'baseline="-25000"' in s1)
    check("형광펜 a:highlight", re.search(r"<a:highlight>\s*<a:srgbClr val=\"[0-9A-F]{6}\"", s1) is not None)
    check("글자 링크 URL(hlinkClick + 외부 관계)", 'hlinkClick r:id="' in s1 and 'TargetMode="External"' in rels1 and "https://example.com" in rels1)
    check("글자 링크 슬라이드(ppaction://hlinksldjump → slide3)", 'action="ppaction://hlinksldjump"' in s1 and "slide3.xml" in rels1)
    check("링크 글자색 유지 hlinkClr tx", 'hlinkClr' in s1 and 'val="tx"' in s1)
    # 도형 테두리 점선 · 액자
    check("rect 테두리 파선 prstDash dash", 'prstDash val="dash"' in s1)
    check("shape 테두리 점선 prstDash sysDot", 'prstDash val="sysDot"' in s1)
    check("액자 색·두께(8px = 6pt = 76200 EMU, primary)", re.search(r'<a:ln w="76200"[^>]*>\s*<a:solidFill>\s*<a:srgbClr val="A91F24"', s1) is not None, s1[:0])
    # SVG
    check("SVG 그림 - svgBlip 확장 + media .svg", "svgBlip" in s1 and any(n.endswith(".svg") for n in names), str([n for n in names if "media" in n]))
    check("SVG 대체 blip(PNG) 있음", re.search(r'<a:blip r:embed="rId\d+">', s1) is not None)
    # 표 셀별 채움·테두리·격자(0.22.12)
    tbls = re.findall(r"<a:tbl>.*?</a:tbl>", s1, re.S)
    check("표 2개", len(tbls) == 2, str(len(tbls)))
    if len(tbls) == 2:
        t1, t2 = tbls
        rows1 = re.findall(r"<a:tr .*?</a:tr>", t1, re.S)
        check("합계 행(3) 세 칸 모두 채움 primary-container + 위 선 2px(primary)", len(rows1) == 4 and rows1[3].count("<a:solidFill>") >= 3 and re.search(r'<a:lnT w="19050"[^>]*>\s*<a:solidFill>\s*<a:srgbClr val="A91F24"', rows1[3]) is not None, rows1[3][:0] if len(rows1) == 4 else "")
        check("1행 3열 한 칸 채움(s1) · 1열 전체 L/R 선", 'val="3B5BA9"' in rows1[1] and all(re.search(r'<a:lnL w="\d+"[^>]*>\s*<a:solidFill>', r) is not None for r in rows1) )
        check("머리 행 아래 선 없음(기존 규칙 유지)", re.search(r'<a:lnB w="0">\s*<a:noFill/>', rows1[0]) is not None)
        rows2 = re.findall(r"<a:tr .*?</a:tr>", t2, re.S)
        check("격자(gridLines) - 모든 칸 B·R 선, 첫 행 T, 첫 열 L", all(re.search(r'<a:lnB w="\d+"[^>]*>\s*<a:solidFill>', r) is not None and re.search(r'<a:lnR w="\d+"[^>]*>\s*<a:solidFill>', r) is not None for r in rows2)
              and re.search(r'<a:lnT w="\d+"[^>]*>\s*<a:solidFill>', rows2[0]) is not None and re.search(r'<a:lnT w="0">', rows2[1]) is not None)
    # 숨김 · 섹션 · 문서 속성
    check("숨김 슬라이드 show=0", 'show="0"' in s3)
    secs = re.findall(r'<p14:section name="([^"]*)"', pres)
    check("섹션 3개 - 덱 제목·장 표지 제목·section 필드", secs == ["구조 시험 덱", "1장 시작", "부록"], str(secs))
    check("섹션 슬라이드 배분(1 / 2 / 1)", [len(re.findall(r"<p14:sldId ", blk)) for blk in re.findall(r"<p14:section .*?</p14:section>", pres, re.S)] == [1, 2, 1])
    check("문서 속성 제목·작성자", "<dc:title>구조 시험 덱</dc:title>" in core and "<dc:creator>시험 작성자</dc:creator>" in core, core[:300])
    # render.js
    js = f'''
const fs=require("fs"); const src=fs.readFileSync({json.dumps(str(STUDIO / "render.js"))},"utf8");
const w={{document:{{createElement:()=>({{style:{{}}}}),querySelector:()=>null}},location:{{}},navigator:{{}}}}; w.window=w; w.self=w;
const vm=require("vm"); vm.createContext(w); vm.runInContext(src,w);
const R=w.Render; R.setTokens({{colors:{{primary:"#A91F24","on-surface":"#1F1B1B","surface-container":"#EEE","primary-container":"#FFDDDD",s1:"#3B5BA9","surface-container-high":"#DDDDDD"}},fonts:{{body:{{css:"x"}},heading:{{css:"x"}},mono:{{css:"x"}}}}}});
const out={{}};
out.text=R.renderElement({json.dumps(deck["slides"][0]["elements"][0], ensure_ascii=False)},1);
out.rect=R.renderElement({json.dumps(deck["slides"][0]["elements"][1], ensure_ascii=False)},1);
out.shape=R.renderElement({json.dumps(deck["slides"][0]["elements"][2], ensure_ascii=False)},1);
out.frame=R.renderElement({json.dumps(deck["slides"][0]["elements"][3], ensure_ascii=False)},1);
out.tbl=R.renderElement({json.dumps(deck["slides"][0]["elements"][5], ensure_ascii=False)},1);
out.grid=R.renderElement({json.dumps(deck["slides"][0]["elements"][6], ensure_ascii=False)},1);
console.log(JSON.stringify(out));
'''
    r = subprocess.run(["node", "-e", js], capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = {}
    try:
        out = json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:  # noqa: BLE001
        check("render.js 실행", False, (r.stderr or r.stdout)[-300:])
    if out:
        check("render 취소선·첨자·형광펜·링크", "line-through" in out["text"] and "top:-0.45em" in out["text"] and "top:0.2em" in out["text"] and "background:#A91F24" in out["text"] and 'data-link="https://example.com"' in out["text"] and 'data-link="#3"' in out["text"])
        check("render rect 파선 - box-shadow 없이 SVG stroke-dasharray 8 6", "box-shadow:inset" not in out["rect"] and 'stroke-dasharray="8 6"' in out["rect"])
        check("render shape 점선 stroke-dasharray 1 1", 'stroke-dasharray="1 1"' in out["shape"])
        check("render 액자 색·두께", "border:8px solid #A91F24" in out["frame"])
        cells = re.findall(r'<div class="rs-cell" style="([^"]*)"', out["tbl"])
        check("render 표 셀 채움·테두리(합계 행 위 2px primary · 1열 L/R · 한 칸 s1)", len(cells) == 12 and cells[9].count("background:#FFDDDD") == 1 and "border-top:2px solid #A91F24" in cells[9] and "border-left:1px solid" in cells[4] and "border-right:1px solid" in cells[4] and "background:#3B5BA9" in cells[5], str(cells[9:10]))
        gcells = re.findall(r'<div class="rs-cell" style="([^"]*)"', out["grid"])
        check("render 격자 - 모든 칸 B·R, 첫 행 T, 첫 열 L", len(gcells) == 4 and all("border-bottom:1px" in c and "border-right:1px" in c for c in gcells) and "border-top:1px" in gcells[0] and "border-top" not in gcells[2] and "border-left:1px" in gcells[2] and "border-left" not in gcells[3])
    print("실패:", FAILS or "없음")
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
