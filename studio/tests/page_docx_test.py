# -*- coding: utf-8 -*-
"""export_docx.py 시험 - 만든 .docx 의 구조(zip 안의 XML)를 본다.  python studio/tests/page_docx_test.py
Word 로 실제로 여는 검증은 따로(tests/docx_open_check.ps1 - Word 가 있을 때)."""
import io
import struct
import sys
import zipfile
import zlib
from pathlib import Path
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import export_docx as X  # noqa: E402
import page_doc as P  # noqa: E402

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
fails, n = [], 0


def check(name, ok, got=None):
    global n
    n += 1
    if not ok:
        fails.append(name)
        print(f"FAIL {name}" + (f" - {got!r}" if got is not None else ""))


def png(w, h):
    """아주 작은 PNG(단색) - 그림 넣기 시험용."""
    raw = b"".join(b"\x00" + b"\xcc\x55\x3d" * w for _ in range(h))
    chunk = lambda t, d: struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)  # noqa: E731
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")


sys.stdout.reconfigure(encoding="utf-8", errors="replace")
L = lambda i, kind, lv=0, **kw: {"id": i, "type": "p", "list": {"kind": kind, "level": lv, **kw}, "runs": [{"t": i}]}  # noqa: E731
doc = P.normalize({"id": "d1", "title": "시험 <문서> & 제목", "kind": "page",
                   "page": {"size": "A4", "orient": "landscape", "margin": {"t": 20, "r": 15, "b": 20, "l": 15},
                            "header": {"blocks": [{"id": "hd1", "type": "p", "align": "right", "runs": [{"t": "머리말 글"}]}]}, "number": {"show": True, "pos": "footer-center"}},
                   "blocks": [
                       {"id": "b1", "type": "p", "style": "h1", "runs": [{"t": "제목 & <꺾쇠>"}]},
                       {"id": "b2", "type": "p", "align": "justify", "indent": 10, "runs": [
                           {"t": "보통 "}, {"t": "굵게", "b": True}, {"t": "기울임", "i": True}, {"t": "밑줄", "u": "double"}, {"t": "취소", "s": True},
                           {"t": "색", "c": "accent"}, {"t": "형광", "hl": "#ffff00"}, {"t": "2", "sup": True}, {"t": "크게", "size": 14, "font": "mono"},
                           {"t": "링크", "link": "https://example.com/?a=1&b=2"}, {"t": "漢字", "ruby": "한자"}, {"t": "줄\n바꿈\t탭"}]},
                       L("n1", "number"), L("n2", "number"), L("n3", "number", 1),
                       {"id": "mid", "type": "p", "runs": [{"t": "사이 문단"}]},
                       L("n4", "number"), L("u1", "bullet"), L("u2", "bullet", 1), L("c1", "check"), L("c2", "check", done=True),
                       {"id": "t1", "type": "table", "cols": [30, 30, 40], "rows": [
                           {"id": "r1", "head": True, "cells": [{"id": "c11", "blocks": [{"id": "p11", "type": "p", "runs": [{"t": "머리 1"}]}]}, {"id": "c12", "colspan": 2, "blocks": [{"id": "p12", "type": "p", "runs": [{"t": "머리 2-3"}]}]}]},
                           {"id": "r2", "cells": [{"id": "c21", "rowspan": 2, "fill": "#eeeeee", "blocks": [{"id": "p21", "type": "p", "runs": [{"t": "세로 병합"}]}]}, {"id": "c22", "blocks": []}, {"id": "c23", "valign": "middle", "blocks": [{"id": "p23", "type": "p", "runs": [{"t": "가"}]}]}]},
                           {"id": "r3", "cells": [{"id": "c32", "blocks": [{"id": "p32", "type": "p", "runs": [{"t": "나"}]}]}]}]},
                       {"id": "im1", "type": "image", "src": "assets/a.png", "w": 60, "caption": "그림 설명"},
                       {"id": "im2", "type": "image", "src": "assets/none.png"},
                       {"id": "br1", "type": "break"},
                       {"id": "b9", "type": "p", "runs": [{"t": "둘째 쪽"}]},
                   ]})
check("시험 문서 형식", P.validate(doc) is None, P.validate(doc))
data = X.build(doc, images={"assets/a.png": (png(4, 2), 400, 200)})
z = zipfile.ZipFile(io.BytesIO(data))
names = set(z.namelist())
check("zip 안의 부분", {"[Content_Types].xml", "_rels/.rels", "word/document.xml", "word/styles.xml", "word/numbering.xml", "word/settings.xml", "word/_rels/document.xml.rels",
                    "word/header1.xml", "word/footer1.xml", "word/media/image1.png", "docProps/core.xml"} <= names, sorted(names))
trees = {}
for nm in names:
    if nm.endswith(".xml") or nm.endswith(".rels"):
        try:
            trees[nm] = ET.fromstring(z.read(nm))
        except ET.ParseError as e:
            check(f"XML 형식 {nm}", False, str(e))
check("XML 모두 읽힘", len(trees) == len([x for x in names if x.endswith(('.xml', '.rels'))]))
d = trees["word/document.xml"]
body = d.find(f"{W}body")
kids = list(body)
check("본문의 마지막은 구역 속성", kids[-1].tag == f"{W}sectPr")
sect = kids[-1]
pg, mar = sect.find(f"{W}pgSz"), sect.find(f"{W}pgMar")
check("용지 - A4 가로(twip)", (pg.get(f"{W}w"), pg.get(f"{W}h"), pg.get(f"{W}orient")) == ("16838", "11906", "landscape"), dict(pg.attrib))
check("여백(twip)", (mar.get(f"{W}top"), mar.get(f"{W}left")) == ("1134", "850"), dict(mar.attrib))
check("머리말·꼬리말 참조", len(sect.findall(f"{W}headerReference")) == 1 and len(sect.findall(f"{W}footerReference")) == 1)
paras = [k for k in kids if k.tag == f"{W}p"]
p1 = paras[0]
check("제목 문단 - 스타일·글 이스케이프", p1.find(f"{W}pPr/{W}pStyle").get(f"{W}val") == "h1" and "".join(t.text for t in p1.iter(f"{W}t")) == "제목 & <꺾쇠>")
p2 = paras[1]
ppr = p2.find(f"{W}pPr")
check("문단 - 양쪽 정렬·들여쓰기", ppr.find(f"{W}jc").get(f"{W}val") == "both" and ppr.find(f"{W}ind").get(f"{W}left") == "567", ET.tostring(ppr, encoding="unicode"))
x2 = ET.tostring(p2, encoding="unicode")
for label, frag in (("굵게", "<ns0:b />"), ("기울임", "<ns0:i />"), ("이중 밑줄", 'ns0:val="double"'), ("취소선", "<ns0:strike />"), ("색 토큰", 'ns0:val="C8553D"'),
                    ("형광(음영)", 'ns0:fill="FFFF00"'), ("위 첨자", 'ns0:val="superscript"'), ("크기 14pt", '<ns0:sz ns0:val="28" />'), ("글꼴", "Consolas"),
                    ("윗주", "<ns0:ruby>"), ("줄바꿈", "<ns0:br />"), ("탭", "<ns0:tab />")):
    check(f"글 조각 - {label}", frag in x2, x2[:0])
link = p2.find(f"{W}hyperlink")
rels = {r.get("Id"): r for r in trees["word/_rels/document.xml.rels"]}
check("링크 - 바깥 관계", link is not None and rels[link.get(f"{R}id")].get("Target") == "https://example.com/?a=1&b=2" and rels[link.get(f"{R}id")].get("TargetMode") == "External")
check("윗주 - 위 글·바탕 글", [t.text for t in p2.find(f".//{W}ruby/{W}rt").iter(f"{W}t")] == ["한자"] and [t.text for t in p2.find(f".//{W}ruby/{W}rubyBase").iter(f"{W}t")] == ["漢字"])
num = lambda p: (p.find(f"{W}pPr/{W}numPr/{W}numId").get(f"{W}val"), p.find(f"{W}pPr/{W}numPr/{W}ilvl").get(f"{W}val")) if p.find(f"{W}pPr/{W}numPr") is not None else None  # noqa: E731
by = {"".join(t.text or "" for t in p.iter(f"{W}t")): p for p in paras}
ids = {k: num(by[k]) for k in ("n1", "n2", "n3", "n4", "u1", "u2", "c1", "c2", "사이 문단")}
check("목록 - 이어진 번호는 같은 인스턴스, 끊기면 새 인스턴스", ids["n1"][0] == ids["n2"][0] == ids["n3"][0] != ids["n4"][0] and ids["n3"][1] == "1" and ids["사이 문단"] is None, ids)
check("목록 - 글머리·확인란·끝낸 확인란", (ids["u1"], ids["u2"], ids["c1"], ids["c2"]) == (("1", "0"), ("1", "1"), ("3", "0"), ("4", "0")), ids)
nb = trees["word/numbering.xml"]
nums = {x.get(f"{W}numId"): x for x in nb.findall(f"{W}num")}
check("번호 정의 - 쓰인 인스턴스가 모두 있다·다시 시작", all(v[0] in nums for v in ids.values() if v) and len(nums[ids["n4"][0]].findall(f"{W}lvlOverride")) == 9, sorted(nums))
abs2 = [x for x in nb.findall(f"{W}abstractNum") if x.get(f"{W}abstractNumId") == "2"][0]
check("번호 꼴 - 1. a. i. 돌려 쓰기", [lv.find(f"{W}numFmt").get(f"{W}val") for lv in abs2.findall(f"{W}lvl")][:4] == ["decimal", "lowerLetter", "lowerRoman", "decimal"])
tbl = body.find(f"{W}tbl")
rows = tbl.findall(f"{W}tr")
grid = [int(g.get(f"{W}w")) for g in tbl.find(f"{W}tblGrid")]
check("표 - 열 3개·너비 비율 3:3:4", len(grid) == 3 and abs(grid[2] / grid[0] - 4 / 3) < 0.01, grid)
check("표 - 머리글 행 반복", rows[0].find(f"{W}trPr/{W}tblHeader") is not None and rows[1].find(f"{W}trPr") is None)
c = lambda r, k: rows[r].findall(f"{W}tc")[k].find(f"{W}tcPr")  # noqa: E731
check("표 - 가로 병합", c(0, 1).find(f"{W}gridSpan").get(f"{W}val") == "2" and len(rows[0].findall(f"{W}tc")) == 2)
check("표 - 세로 병합(시작·이어짐)", c(1, 0).find(f"{W}vMerge").get(f"{W}val") == "restart" and c(2, 0).find(f"{W}vMerge") is not None and c(2, 0).find(f"{W}vMerge").get(f"{W}val") is None and len(rows[2].findall(f"{W}tc")) == 3, [len(r.findall(f"{W}tc")) for r in rows])
check("표 - 칸 채움·세로 정렬·머리 음영", c(1, 0).find(f"{W}shd").get(f"{W}fill") == "EEEEEE" and c(1, 2).find(f"{W}vAlign").get(f"{W}val") == "center" and c(0, 0).find(f"{W}shd").get(f"{W}fill") == "F0F0F0")
check("표 - 모든 칸이 문단으로 끝난다", all(list(tc)[-1].tag == f"{W}p" for tc in tbl.iter(f"{W}tc")))
xml = z.read("word/document.xml").decode("utf-8")
check("그림 - 글자처럼 넣기·크기(60mm, 2:1)", 'r:embed="' in xml and '<wp:extent cx="2160000" cy="1080000"/>' in xml, xml[xml.find("<wp:extent"):][:60])
check("그림 - 캡션·없는 그림 표시", "그림 설명" in xml and "[그림 없음: assets/none.png]" in xml)
check("쪽 나누기", '<w:br w:type="page"/>' in xml)
check("머리말 글·꼬리말 쪽 번호", "머리말 글" in z.read("word/header1.xml").decode("utf-8") and " PAGE " in z.read("word/footer1.xml").decode("utf-8"))
st = trees["word/styles.xml"]
styles = {s.get(f"{W}styleId"): s for s in st.findall(f"{W}style")}
check("스타일 - 본문이 기본, 제목은 상속·개요 수준", styles["Normal"].get(f"{W}default") == "1" and styles["h1"].find(f"{W}basedOn").get(f"{W}val") == "Normal"
      and styles["h2"].find(f"{W}basedOn").get(f"{W}val") == "h1" and styles["h2"].find(f"{W}pPr/{W}outlineLvl").get(f"{W}val") == "1", sorted(styles))
sp = styles["Normal"].find(f"{W}pPr/{W}spacing")
check("스타일 - 줄 간격 1.6·문단 뒤 6pt·크기 10.5pt", (sp.get(f"{W}line"), sp.get(f"{W}after")) == ("384", "120") and styles["Normal"].find(f"{W}rPr/{W}sz").get(f"{W}val") == "21", dict(sp.attrib))
check("스타일 - 제목 다음은 본문", styles["h1"].find(f"{W}next").get(f"{W}val") == "Normal")
ct = z.read("[Content_Types].xml").decode("utf-8")
check("콘텐츠 종류 - png·머리말·꼬리말", 'Extension="png"' in ct and "header1.xml" in ct and "footer1.xml" in ct)
check("문서 정보 - 제목 이스케이프", "시험 &lt;문서&gt; &amp; 제목" in z.read("docProps/core.xml").decode("utf-8"))
used = set(__import__("re").findall(r'r:(?:id|embed)="(rId\d+)"', xml + z.read("word/header1.xml").decode("utf-8")))
check("관계 - 쓰인 id 가 모두 정의돼 있다", used <= set(rels), sorted(used - set(rels)))
try:
    X.build({"kind": "page", "blocks": [{"id": "a", "type": "nope"}]})
    check("형식이 틀린 문서는 거절", False)
except ValueError as e:
    check("형식이 틀린 문서는 거절", "페이지 형식 아님" in str(e), str(e))
empty = zipfile.ZipFile(io.BytesIO(X.build(P.new_page("e", ""))))
check("빈 문서 - 머리말·꼬리말 없이도 만들어진다", "word/header1.xml" not in empty.namelist() and ET.fromstring(empty.read("word/document.xml")) is not None)

# 템플릿 토큰 - 영문·한글 글꼴을 따로, 색 별칭(accent·muted·ink)·글꼴 별칭(title = heading)
fonts, colors = X.token_maps({"fonts": {"body": {"css": "x", "latin": "Pretendard", "ea": "맑은 고딕"}, "heading": {"latin": "Inter", "ea": "Pretendard"}, "mono": "Consolas, monospace"},
                              "colors": {"primary": "#A91F24", "on-surface": "#1F1B1B", "on-surface-variant": "#534343", "bad": "red"}})
check("토큰 - 글꼴 {latin, ea}·별칭", fonts["body"] == {"latin": "Pretendard", "ea": "맑은 고딕"} and fonts["title"] == fonts["heading"] and fonts["mono"] == "Consolas", fonts)
check("토큰 - 색 별칭·형식이 아닌 색은 뺌", colors["accent"] == "#A91F24" and colors["muted"] == "#534343" and colors["ink"] == "#1F1B1B" and "bad" not in colors, colors)
zt = zipfile.ZipFile(io.BytesIO(X.build(doc, fonts=fonts, colors=colors, images={"assets/a.png": (png(4, 2), 400, 200)})))
st2, dx2 = zt.read("word/styles.xml").decode("utf-8"), zt.read("word/document.xml").decode("utf-8")
check("토큰 - 본문 글꼴이 영문·한글 따로 나간다", 'w:ascii="Pretendard" w:hAnsi="Pretendard" w:eastAsia="맑은 고딕"' in st2, st2[st2.find("<w:rFonts"):][:120])
check("토큰 - 제목 글꼴(title → heading)·강조 색", 'w:ascii="Inter" w:hAnsi="Inter" w:eastAsia="Pretendard"' in st2 and 'w:val="A91F24"' in dx2)

# 개체(도형·글 상자) - 매인 문단 맨 앞의 떠 있는 도형(wp:anchor + wps:wsp)
od = P.new_page("o", "개체")
od["blocks"] = [{"id": "p1", "type": "p", "runs": [{"t": "첫 문단"}]}, {"id": "p2", "type": "p", "runs": [{"t": "둘째 문단"}]}]
od["objects"] = [
    {"id": "o1", "type": "shape", "shape": "ellipse", "anchor": "p2", "rel": "page", "x": 30, "y": 40, "w": 50, "h": 20, "line": {"c": "#C8553D", "w": 1.5, "dash": "dash"}},
    {"id": "o2", "type": "shape", "shape": "rect", "anchor": "p2", "rel": "para", "x": 5, "y": -3, "w": 60, "h": 25, "fill": "#EEEEEE", "line": None, "z": "behind", "valign": "middle",
     "blocks": [{"id": "ot", "type": "p", "runs": [{"t": "상자 글", "b": True}]}]},
    {"id": "o3", "type": "shape", "shape": "arrow", "anchor": "p1", "x": 20, "y": 60, "w": 40, "h": 10, "flip": True},
    {"id": "o4", "type": "shape", "shape": "brace-l", "anchor": "p1", "x": 10, "y": 80, "w": 4, "h": 30},
]
check("개체 - 형식 검사 통과", P.validate(P.normalize(od)) is None, P.validate(P.normalize(od)))
ox = zipfile.ZipFile(io.BytesIO(X.build(od))).read("word/document.xml").decode("utf-8")
ot = ET.fromstring(ox)
WP = "{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
WPS = "{http://schemas.microsoft.com/office/word/2010/wordprocessingShape}"
paras = ot.find(f"{W}body").findall(f"{W}p")
per = [len(p.findall(f".//{WP}anchor")) for p in paras]
check("개체 - 매인 문단 안에 들어간다(p1 에 2개 · p2 에 2개)", per[:2] == [2, 2], per)
an = {a.find(f"{WP}docPr").get("name"): a for a in ot.iter(f"{WP}anchor")}
first = paras[1].findall(f".//{WP}anchor")
e1, e2 = first[0], first[1]
check("개체 - 쪽 기준 자리(mm → EMU)", e1.find(f"{WP}positionH").get("relativeFrom") == "page" and e1.find(f"{WP}positionH/{WP}posOffset").text == str(30 * 36000)
      and e1.find(f"{WP}positionV").get("relativeFrom") == "page" and e1.find(f"{WP}positionV/{WP}posOffset").text == str(40 * 36000) and e1.find(f"{WP}extent").get("cx") == str(50 * 36000))
check("개체 - 문단 기준 자리(음수 가능) · 글 뒤로", e2.find(f"{WP}positionH").get("relativeFrom") == "column" and e2.find(f"{WP}positionV").get("relativeFrom") == "paragraph"
      and e2.find(f"{WP}positionV/{WP}posOffset").text == str(-3 * 36000) and e2.get("behindDoc") == "1" and e1.get("behindDoc") == "0")
g1 = e1.find(f".//{WPS}spPr")
check("개체 - 타원 · 채움 없음 · 선 색·굵기·점선", g1.find(f"{A}prstGeom").get("prst") == "ellipse" and g1.find(f"{A}noFill") is not None and g1.find(f"{A}ln").get("w") == str(int(1.5 * 12700))
      and g1.find(f"{A}ln/{A}solidFill/{A}srgbClr").get("val") == "C8553D" and g1.find(f"{A}ln/{A}prstDash").get("val") == "dash")
g2 = e2.find(f".//{WPS}spPr")
check("개체 - 글 상자: 채움 · 선 없음 · 안의 문단 · 세로 가운데", g2.find(f"{A}solidFill/{A}srgbClr").get("val") == "EEEEEE" and g2.find(f"{A}ln/{A}noFill") is not None
      and "".join(t.text for t in e2.iter(f"{W}t")) == "상자 글" and e2.find(f".//{WPS}bodyPr").get("anchor") == "ctr" and e2.find(f".//{WPS}txbx/{W}txbxContent/{W}p") is not None)
ar = paras[0].findall(f".//{WP}anchor")
check("개체 - 화살표: 선 도형 · 끝 화살촉 · 위로 뒤집기 · 글 없음", ar[0].find(f".//{A}prstGeom").get("prst") == "line" and ar[0].find(f".//{A}ln/{A}tailEnd").get("type") == "triangle"
      and ar[0].find(f".//{A}xfrm").get("flipV") == "1" and ar[0].find(f".//{WPS}cNvCnPr") is not None and ar[0].find(f".//{WPS}txbx") is None)
check("개체 - 중괄호 모양", ar[1].find(f".//{A}prstGeom").get("prst") == "leftBrace")
ids_ = [a.find(f"{WP}docPr").get("id") for a in ot.iter(f"{WP}anchor")]
check("개체 - docPr id 가 겹치지 않는다", len(set(ids_)) == 4, ids_)
order = [c.tag.split("}")[1] for c in e2.find(f".//{WPS}wsp")]
check("개체 - wsp 자식 순서(cNvSpPr → spPr → txbx → bodyPr)", order == ["cNvSpPr", "spPr", "txbx", "bodyPr"], order)

# 각주 - 글 조각의 fn → 본문의 w:footnoteReference + word/footnotes.xml
fd = P.new_page("f", "각주")
fd["blocks"] = [{"id": "p1", "type": "p", "runs": [{"t": "첫 문장"}, {"t": "끝", "fn": "첫째 각주 <글>"}, {"t": " 그리고 둘째", "fn": "둘째 각주"}]},
                {"id": "t1", "type": "table", "cols": [100], "rows": [{"id": "r1", "cells": [{"id": "c1", "blocks": [{"id": "cp", "type": "p", "runs": [{"t": "칸", "fn": "칸 안 각주"}]}]}]}]}]
fd["page"]["header"] = {"blocks": [{"id": "h1", "type": "p", "runs": [{"t": "머리", "fn": "머리말 각주"}]}]}
fd["objects"] = [{"id": "o1", "type": "shape", "shape": "rect", "anchor": "p1", "x": 10, "y": 10, "w": 40, "h": 20, "blocks": [{"id": "ot", "type": "p", "runs": [{"t": "상자", "fn": "상자 각주"}]}]}]
check("각주 - 형식 검사 통과 · 문서 순서 번호(본문·칸만)", P.validate(P.normalize(fd)) is None and P.footnotes(fd) == [(1, "첫째 각주 <글>"), (2, "둘째 각주"), (3, "칸 안 각주")], (P.validate(P.normalize(fd)), P.footnotes(fd)))
fz = zipfile.ZipFile(io.BytesIO(X.build(fd)))
fx, fn_xml = fz.read("word/document.xml").decode("utf-8"), fz.read("word/footnotes.xml").decode("utf-8")
ft = ET.fromstring(fn_xml)
refs = [e.get(W + "id") for e in ET.fromstring(fx).iter(W + "footnoteReference")]
check("각주 - 본문 참조 id 2·3·4(0·1 은 구분선) · 글 상자 안에는 참조 없음", refs == ["2", "3", "4"], refs)
notes = {f.get(W + "id"): "".join(t.text or "" for t in f.iter(W + "t")).strip() for f in ft.findall(W + "footnote")}
check("각주 - footnotes.xml 에 구분선 둘 + 각주 글(특수 문자 그대로)", set(notes) == {"0", "1", "2", "3", "4"} and notes["2"] == "첫째 각주 <글>" and notes["4"] == "칸 안 각주"
      and ft.find(f"{W}footnote[@{W}id='0']").get(W + "type") == "separator", notes)
check("각주 - 관계·콘텐츠 형식 등록", "relationships/footnotes" in fz.read("word/_rels/document.xml.rels").decode("utf-8") and "wordprocessingml.footnotes+xml" in fz.read("[Content_Types].xml").decode("utf-8"))
check("각주 - 머리말·글 상자 안은 글로 푼다([주: …])", "[주: 머리말 각주]" in fz.read("word/header1.xml").decode("utf-8") and "[주: 상자 각주]" in fx and "footnoteReference" not in fz.read("word/header1.xml").decode("utf-8"))
check("각주 없는 문서 - footnotes.xml 을 만들지 않는다", "word/footnotes.xml" not in zipfile.ZipFile(io.BytesIO(X.build(P.new_page("e2", "")))).namelist())
check("각주 거절 - 빈 글·글이 아닌 값", all(isinstance(P.validate({**P.normalize(fd), "blocks": [{"id": "x", "type": "p", "runs": [{"t": "가", "fn": v}]}], "objects": []}), str) for v in ("", "  ", 3)))

print(f"\n실패 {len(fails)}" if fails else f"\n전부 통과 ({n}사례)")
sys.exit(1 if fails else 0)
