# -*- coding: utf-8 -*-
"""import_docx.py 시험 - 내보낸 .docx 를 다시 가져오면 같은 구조가 나오는지(왕복).  python studio/tests/page_import_test.py
Word 가 만든 문서의 가져오기는 따로(협업 세션의 Word 시험) - 여기는 우리 내보내기와의 왕복만 본다."""
import io
import struct
import sys
import zipfile
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import export_docx as X  # noqa: E402
import import_docx as I  # noqa: E402
import page_doc as P  # noqa: E402
import page_templates as PT  # noqa: E402

fails, n = [], 0


def check(name, ok, got=None):
    global n
    n += 1
    if not ok:
        fails.append(name)
        print(f"FAIL {name}" + (f" - {got!r}" if got is not None else ""))


def png(w, h):
    raw = b"".join(b"\x00" + b"\xcc\x55\x3d" * w for _ in range(h))
    chunk = lambda t, d: struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)  # noqa: E731
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")


def shape(blocks):
    """비교용 꼴 - id 와 기본값을 뺀 구조."""
    out = []
    for b in blocks:
        if b["type"] == "p":
            x = {"p": [{k: v for k, v in r.items()} for r in b["runs"]]}
            for k in ("style", "align", "list", "indent", "line"):
                if b.get(k) is not None:
                    x[k] = b[k]
            out.append(x)
        elif b["type"] == "table":
            out.append({"table": [[{"span": (c.get("colspan", 1), c.get("rowspan", 1)), "fill": c.get("fill"), "blocks": shape(c["blocks"])} for c in r["cells"]] for r in b["rows"]],
                        "head": [bool(r.get("head")) for r in b["rows"]], "cols": [round(c) for c in b["cols"]]})
        elif b["type"] == "image":
            out.append({"image": round(b.get("w", 0)), "align": b.get("align")})
        else:
            out.append({"break": b.get("kind", "page")})
    return out


sys.stdout.reconfigure(encoding="utf-8", errors="replace")
L = lambda i, kind, lv=0, **kw: {"id": i, "type": "p", "list": {"kind": kind, "level": lv, **kw}, "runs": [{"t": i}]}  # noqa: E731
src = P.normalize({"id": "d1", "title": "왕복 시험", "kind": "page",
                   "page": {"size": "B5", "orient": "landscape", "margin": {"t": 20, "r": 15, "b": 22, "l": 18},
                            "header": {"blocks": [{"id": "hd1", "type": "p", "align": "right", "runs": [{"t": "머리말 글"}]}]}, "number": {"show": True, "pos": "footer-center"}},
                   "blocks": [
                       {"id": "b0", "type": "p", "style": "title", "runs": [{"t": "문서 제목"}]},
                       {"id": "b1", "type": "p", "style": "h1", "runs": [{"t": "제목 & <꺾쇠>"}]},
                       {"id": "b2", "type": "p", "align": "justify", "indent": 10, "line": 2, "runs": [
                           {"t": "보통 "}, {"t": "굵게", "b": True}, {"t": "기울임", "i": True}, {"t": "밑줄", "u": "double"}, {"t": "취소", "s": True},
                           {"t": "색", "c": "#c8553d"}, {"t": "형광", "hl": "#ffff00"}, {"t": "2", "sup": True}, {"t": "크게", "size": 14},
                           {"t": "링크", "link": "https://example.com/?a=1&b=2"}, {"t": "漢字", "ruby": "한자"}, {"t": "줄\n바꿈\t탭"}]},
                       {"id": "b3", "type": "p", "style": "h2", "align": "center", "runs": [{"t": "작은 제목"}]},
                       L("n1", "number"), L("n2", "number", 1), L("u1", "bullet"), L("u2", "bullet", 2), L("c1", "check"), L("c2", "check", done=True),
                       {"id": "q1", "type": "p", "style": "quote", "runs": [{"t": "인용 글"}]},
                       {"id": "t1", "type": "table", "cols": [30, 30, 40], "rows": [
                           {"id": "r1", "head": True, "cells": [{"id": "c11", "blocks": [{"id": "p11", "type": "p", "runs": [{"t": "머리 1"}]}]}, {"id": "c12", "colspan": 2, "blocks": [{"id": "p12", "type": "p", "runs": [{"t": "머리 2-3"}]}]}]},
                           {"id": "r2", "cells": [{"id": "c21", "rowspan": 2, "fill": "#eeeeee", "blocks": [{"id": "p21", "type": "p", "runs": [{"t": "세로 병합"}]}]}, {"id": "c22", "blocks": [{"id": "p22", "type": "p", "runs": []}]}, {"id": "c23", "blocks": [{"id": "p23", "type": "p", "runs": [{"t": "가", "b": True}]}]}]},
                           {"id": "r3", "cells": [{"id": "c32", "blocks": [{"id": "p32", "type": "p", "runs": [{"t": "나"}]}]}, {"id": "c33", "blocks": [{"id": "p33", "type": "p", "runs": [{"t": "다"}]}]}]}]},
                       {"id": "im1", "type": "image", "src": "assets/a.png", "w": 60},
                       {"id": "br1", "type": "break"},
                       {"id": "b9", "type": "p", "runs": [{"t": "둘째 쪽"}]},
                   ]})
data = X.build(src, images={"assets/a.png": (png(4, 2), 400, 200)})
doc, images, warn = I.read(data, doc_id="back")
check("가져온 문서 - 형식 통과·kind page", P.validate(doc) is None and doc["kind"] == "page", P.validate(doc))
check("제목 - 문서 정보의 제목", doc["title"] == "왕복 시험", doc["title"])
check("쪽 설정 - 용지·방향·여백", doc["page"]["size"] == "B5" and doc["page"]["orient"] == "landscape" and doc["page"]["margin"] == {"t": 20, "r": 15, "b": 22, "l": 18}, doc["page"])
check("머리말 글·정렬 · 쪽 번호 위치", [P.runs_text(b["runs"]) for b in doc["page"]["header"]["blocks"]] == ["머리말 글"] and doc["page"]["header"]["blocks"][0].get("align") == "right"
      and doc["page"]["number"] == {"show": True, "pos": "footer-center"} and doc["page"]["footer"]["blocks"] == [], doc["page"])
a, b = shape(src["blocks"]), shape(doc["blocks"])
check("블록 수·종류가 같다", [list(x)[0] for x in a] == [list(x)[0] for x in b], [list(x)[0] for x in b])
for k, (x, y) in enumerate(zip(a, b)):
    check(f"블록 {k}({list(x)[0]}) 왕복", x == y, {"보냄": x, "받음": y})
check("그림 바이트를 꺼낸다", len(images) == 1 and list(images.values())[0][:4] == b"\x89PNG")
check("옮기지 못한 것 없음(경고 0)", warn == [], warn)
# 다시 내보내도 같은 구조(가져오기 → 내보내기 → 가져오기)
doc2, _, _ = I.read(X.build(doc, images={next(iter(images)): (png(4, 2), 400, 200)}), doc_id="back2")
check("두 번 왕복해도 같다", shape(doc2["blocks"]) == shape(doc["blocks"]))
# 템플릿 11종 왕복 - 글이 빠지지 않는다
for name in PT.names():
    t = P.new_page("t-" + name, "제목", PT.load(name, "제목", "2026-11-26"))
    back, _, w = I.read(X.build(t), doc_id="b-" + name)
    text = lambda d: "|".join(P.runs_text(x["runs"]) for _, x in P.text_blocks({"blocks": d["blocks"], "page": {}}))  # noqa: E731
    check(f"템플릿 {name} - 본문 글이 그대로", text(t) == text(back), None)
    check(f"템플릿 {name} - 표·목록 수가 그대로", [sum(1 for x in d["blocks"] if x["type"] == "table") for d in (t, back)][0] == sum(1 for x in back["blocks"] if x["type"] == "table")
          and sum(1 for x in t["blocks"] if x.get("list")) == sum(1 for x in back["blocks"] if x.get("list")), w)
# 떠 있는 글 상자·도형 - Word 가 쓰는 꼴(AlternateContent 안에 새 형식과 옛 형식이 같이 있다)
NSX = ('xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" '
       'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape" xmlns:v="urn:schemas-microsoft-com:vml"')
TX = '<w:txbxContent><w:p><w:r><w:t>글</w:t></w:r><w:r><w:t xml:space="preserve"> 상자 글</w:t></w:r></w:p><w:p><w:r><w:rPr><w:b/></w:rPr><w:t>둘째 줄</w:t></w:r></w:p></w:txbxContent>'
body = (f'<w:p><w:r><w:t>앞 문단</w:t></w:r><w:r><mc:AlternateContent><mc:Choice Requires="wps"><w:drawing><wp:anchor><wps:wsp><wps:txbx>{TX}</wps:txbx></wps:wsp></wp:anchor></w:drawing></mc:Choice>'
        f'<mc:Fallback><w:pict><v:shape><v:textbox>{TX}</v:textbox></v:shape></w:pict></mc:Fallback></mc:AlternateContent></w:r></w:p>'
        '<w:p><w:r><w:drawing><wp:anchor><wps:wsp/></wp:anchor></w:drawing></w:r></w:p><w:p><w:r><w:t>뒤 문단</w:t></w:r></w:p>')
bio = io.BytesIO()
with zipfile.ZipFile(bio, "w") as zz:
    zz.writestr("word/document.xml", f'<?xml version="1.0" encoding="UTF-8"?><w:document {NSX}><w:body>{body}</w:body></w:document>')
tb, _, tw = I.read(bio.getvalue(), doc_id="tb")
texts = [P.runs_text(x["runs"]) for x in tb["blocks"] if x["type"] == "p"]
check("글 상자 - 글을 문단으로 꺼낸다(한 번만 · 순서)", texts == ["앞 문단", "글 상자 글", "둘째 줄", "뒤 문단"], texts)
check("글 상자 - 안의 서식 유지", tb["blocks"][2]["runs"] == [{"t": "둘째 줄", "b": True}], tb["blocks"][2])
check("글 상자·떠 있는 도형 - 경고", any("글 상자" in w for w in tw) and any("떠 있는" in w for w in tw), tw)

# 배치용 표(테두리 없음 · 칸 사이 세로선만) 왕복
for kind in ("none", "inner-v"):
    lay = P.normalize({"id": "l", "title": "t", "kind": "page", "blocks": [{"id": "t", "type": "table", "cols": [67, 33], "border": kind, "rows": [{"id": "r", "cells": [
        {"id": "a", "blocks": [{"id": "pa", "type": "p", "runs": [{"t": "왼쪽", "ruby": "S"}]}]}, {"id": "b", "blocks": [{"id": "pb", "type": "p", "list": {"kind": "number", "level": 0}, "runs": [{"t": "오른쪽"}]}]}]}]}]})
    xml = zipfile.ZipFile(io.BytesIO(X.build(lay))).read("word/document.xml").decode("utf-8")
    back, _, _ = I.read(X.build(lay), doc_id="lb")
    tb2 = back["blocks"][0]
    check(f"배치용 표 {kind} - DOCX 테두리·왕복", ('<w:top w:val="none"' in xml) and (('<w:insideV w:val="single"' in xml) == (kind == "inner-v")) and tb2.get("border") == kind
          and tb2["rows"][0]["cells"][0]["blocks"][0]["runs"] == [{"t": "왼쪽", "ruby": "S"}] and tb2["rows"][0]["cells"][1]["blocks"][0].get("list", {}).get("kind") == "number" and [round(c) for c in tb2["cols"]] == [67, 33], tb2)
check("표 border 값 검사", "border" in (P.validate({**P.normalize({"kind": "page", "blocks": []}), "blocks": [{"id": "t", "type": "table", "cols": [1], "border": "dotted", "rows": [{"id": "r", "cells": [{"id": "c", "blocks": []}]}]}]}) or ""))

# 문단 음영(회색 상자) 왕복 - 줄 간격·정렬과 같이 있을 때 pPr 순서
sh = P.normalize({"id": "s", "title": "t", "kind": "page", "blocks": [{"id": "a", "type": "p", "style": "h2", "fill": "#e6e6e6", "line": 2, "align": "center", "indent": 5, "runs": [{"t": "상자"}]},
                                                                  {"id": "b", "type": "p", "list": {"kind": "bullet", "level": 0}, "fill": "#ffeecc", "runs": [{"t": "목록 음영"}]}]})
sx = zipfile.ZipFile(io.BytesIO(X.build(sh))).read("word/document.xml").decode("utf-8")
order = [sx.index(k) for k in ("<w:pStyle", '<w:shd w:val="clear" w:color="auto" w:fill="E6E6E6"', "<w:spacing", "<w:ind", "<w:jc")]
sb, _, _ = I.read(X.build(sh), doc_id="sb")
check("문단 음영 - pPr 순서(pStyle·shd·spacing·ind·jc)", order == sorted(order), order)
check("문단 음영 - 왕복", sb["blocks"][0].get("fill") == "#e6e6e6" and sb["blocks"][0].get("line") == 2 and sb["blocks"][1].get("fill") == "#ffeecc" and sb["blocks"][1]["list"]["kind"] == "bullet", sb["blocks"])

# 거절
for bad_name, payload in (("zip 이 아님", b"not a zip"), ("docx 가 아닌 zip", (lambda: (lambda bio: (zipfile.ZipFile(bio, "w").writestr("a.txt", "x"), bio.getvalue())[1])(io.BytesIO()))())):
    try:
        I.read(payload)
        check(f"거절: {bad_name}", False)
    except ValueError:
        check(f"거절: {bad_name}", True)

# CLI --blocks - 문서를 만들지 않고 블록(JSON)만 꺼낸다(요청 첨부를 있는 문서에 넣을 때). 임시 작업 공간에서
import json as _json  # noqa: E402
import subprocess as _sp  # noqa: E402
import tmpfiles as _tmp  # noqa: E402
import export_docx as _X  # noqa: E402
import page_doc as _P  # noqa: E402
with _tmp.temp_dir("nx-impblk-") as _d:
    _ws = Path(_d) / "slides"
    (_ws / "decks").mkdir(parents=True)
    (_ws / "nexa-slide.json").write_text('{"title": "t"}', encoding="utf-8")
    _src = _P.new_page("s", "첨부 문서")
    _src["blocks"] = [{"id": "a", "type": "p", "style": "h1", "runs": [{"t": "첨부 제목"}]}, {"id": "b", "type": "p", "runs": [{"t": "굵은 ", "b": True}, {"t": "글"}]}]
    (_ws / "첨부 파일.docx").write_bytes(_X.build(_src))
    _r = _sp.run([sys.executable, str(Path(__file__).resolve().parents[1] / "import_docx.py"), "-W", str(_ws), str(_ws / "첨부 파일.docx"), "--blocks"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    _out = _ws / "out" / "import" / "첨부_파일" / "page.json"
    _j = _json.loads(_out.read_text(encoding="utf-8")) if _out.is_file() else {}
    _bs = _j.get("blocks") or []
    check("CLI --blocks - out/import/<이름>/page.json 에 블록(서식 유지) · 덱은 만들지 않는다",
          _r.returncode == 0 and len(_bs) == 2 and _bs[0].get("style") == "h1" and _bs[1]["runs"][0] == {"t": "굵은 ", "b": True} and not list((_ws / "decks").glob("*.json")) and "styles" in _j,
          (_r.returncode, _r.stdout[-300:], _r.stderr[-300:], _bs))

print(f"\n실패 {len(fails)}" if fails else f"\n전부 통과 ({n}사례)")
sys.exit(1 if fails else 0)
