# -*- coding: utf-8 -*-
"""page_doc.py 시험 - 새 문서 · 검사 · 정규화 · 스타일 풀기.  python studio/tests/page_doc_test.py"""
import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import page_doc as P  # noqa: E402

fails = []
n = 0


def check(name, ok, got=None):
    global n
    n += 1
    if not ok:
        fails.append(name)
        print(f"FAIL {name}" + (f" - {got!r}" if got is not None else ""))


def bad(name, mutate, expect):
    d = copy.deepcopy(BASE)
    mutate(d)
    e = P.validate(d)
    check(f"거절: {name}", e is not None and expect in e, e)


sys.stdout.reconfigure(encoding="utf-8", errors="replace")
doc = P.new_page("rep1", "보고서")
check("새 문서 - 형식 통과", P.validate(doc) is None, P.validate(doc))
check("새 문서 - kind·slides·제목 문단", doc["kind"] == "page" and doc["slides"] == [] and doc["blocks"][0]["runs"] == [{"t": "보고서"}] and doc["blocks"][0]["style"] == "title", doc["blocks"])
check("새 문서 - 제목이 없으면 빈 제목 문단", P.new_page("x", "")["blocks"][0]["runs"] == [])
tpl = {"name": "report", "page": {"margin": {"t": 30, "r": 25, "b": 30, "l": 25}}, "styles": {"h1": {"based": "body", "size": 18}},
       "blocks": [{"type": "p", "style": "h1", "runs": [{"t": "가"}, {"t": "나"}]}]}
d2 = P.new_page("t1", "제목", tpl)
check("템플릿 - page·styles 덮어쓰기, id 채움, runs 합침", d2["page"]["margin"]["t"] == 30 and d2["page"]["size"] == "A4" and d2["styles"]["h1"]["size"] == 18
      and "h2" in d2["styles"] and d2["blocks"][0]["id"] and d2["blocks"][0]["runs"] == [{"t": "가나"}] and d2["template"] == "report" and P.validate(d2) is None, d2["blocks"])

BASE = P.normalize({"id": "d", "title": "t", "kind": "page", "blocks": [
    {"id": "b1", "type": "p", "style": "h1", "align": "center", "runs": [{"t": "제목", "b": True}, {"t": "", "i": True}, {"t": " 이어서", "b": 1}]},
    {"id": "b2", "type": "list", "kind": "number", "items": [{"id": "i1", "level": 0, "runs": [{"t": "하나"}]}, {"id": "i2", "level": 1, "runs": []}]},
    {"id": "b3", "type": "table", "cols": [40, 60], "rows": [
        {"id": "r1", "head": True, "cells": [{"id": "c1", "blocks": [{"id": "p1", "type": "p", "runs": [{"t": "머리"}]}]}, {"id": "c2", "blocks": []}]},
        {"id": "r2", "cells": [{"id": "c3", "colspan": 2, "blocks": [{"id": "p2", "type": "p", "runs": [{"t": "합친 칸", "c": "accent", "u": False}]}]}]}]},
    {"id": "b4", "type": "image", "src": "assets/a.png", "w": 80},
    {"id": "b5", "type": "break"},
]})
check("정규화 - 형식 통과", P.validate(BASE) is None, P.validate(BASE))
check("정규화 - runs 합치기·꺼진 서식 제거", BASE["blocks"][0]["runs"] == [{"t": "제목 이어서", "b": True}] and BASE["blocks"][2]["rows"][1]["cells"][0]["blocks"][0]["runs"] == [{"t": "합친 칸", "c": "accent"}], BASE["blocks"][0])
check("정규화 - 입력을 고치지 않는다·기본값", BASE["page"]["size"] == "A4" and "body" in BASE["styles"] and BASE["objects"] == [])
check("정규화 - 빈 본문에는 문단 하나", [b["type"] for b in P.normalize({"kind": "page", "blocks": []})["blocks"]] == ["p"])
ids = [b.get("id") for _, b in P.walk(BASE)]
check("walk - 블록·항목·행·셀·셀 안 문단", ids == ["b1", "b2", "i1", "i2", "b3", "r1", "c1", "p1", "c2", "r2", "c3", "p2", "b4", "b5"], ids)
check("text_blocks - 글이 든 것만", [b["id"] for _, b in P.text_blocks(BASE)] == ["b1", "i1", "i2", "p1", "p2"])
check("id 채움 - 빠진 id 는 겹치지 않게", len({b["id"] for _, b in P.walk(P.normalize({"kind": "page", "blocks": [{"type": "p", "runs": []}, {"id": "b01", "type": "p", "runs": []}, {"type": "p", "runs": []}]}))}) == 3)

bad("kind", lambda d: d.update(kind="sheet"), "페이지 문서 아님")
bad("용지", lambda d: d["page"].update(size="A9"), "용지 크기")
bad("방향", lambda d: d["page"].update(orient="up"), "방향")
bad("여백", lambda d: d["page"]["margin"].update(t=-1), "여백")
bad("body 스타일 없음", lambda d: d["styles"].pop("body"), "body")
bad("없는 기준 스타일", lambda d: d["styles"].update(x={"based": "nope"}), "없는 기준 스타일")
bad("도는 기준 스타일", lambda d: d["styles"].update(a={"based": "b"}, b={"based": "a"}), "돈다")
bad("모르는 블록", lambda d: d["blocks"].append({"id": "z", "type": "video"}), "모르는 블록 종류")
bad("없는 스타일", lambda d: d["blocks"][0].update(style="nope"), "없는 스타일")
bad("정렬", lambda d: d["blocks"][0].update(align="middle"), "align")
bad("runs 형식", lambda d: d["blocks"][0].update(runs=[{"text": "x"}]), "글 조각")
bad("모르는 서식", lambda d: d["blocks"][0]["runs"].append({"t": "x", "blink": True}), "모르는 서식")
bad("목록 종류", lambda d: d["blocks"][1].update(kind="star"), "목록 kind")
bad("목록 단계", lambda d: d["blocks"][1]["items"][0].update(level=9), "level")
bad("표 열", lambda d: d["blocks"][2].update(cols=[]), "cols")
bad("표 칸 수 넘침", lambda d: d["blocks"][2]["rows"][0]["cells"][0].update(colspan=2), "넘는다")
bad("표 안의 표", lambda d: d["blocks"][2]["rows"][0]["cells"][1]["blocks"].append({"id": "t2", "type": "table", "cols": [1], "rows": [{"id": "rr", "cells": []}]}), "표 안의 표")
bad("그림 src", lambda d: d["blocks"][3].pop("src"), "src")
bad("나누기 종류", lambda d: d["blocks"][4].update(kind="line"), "나누기")
bad("id 중복", lambda d: d["blocks"][0].update(id="b2"), "id 중복")
bad("id 형식", lambda d: d["blocks"][0].update(id="a b"), "id 형식")
bad("머리말 블록", lambda d: d["page"].update(header={"blocks": [{"id": "h1x", "type": "nope"}]}), "모르는 블록 종류")

st = P.resolve_style(BASE, "h2")
check("스타일 풀기 - h2 → h1 → body", st["size"] == 15 and st["bold"] is True and st["font"] == "title" and st["line"] == 1.6 and "based" not in st and "name" not in st, st)
check("스타일 풀기 - 없는 이름은 body", P.resolve_style(BASE, "nope") == P.resolve_style(BASE, "body"))
box = P.page_box(BASE)
check("쪽 상자 - A4 세로", (box["w"], box["h"], box["cw"], box["ch"]) == (210, 297, 170, 247), box)
land = copy.deepcopy(BASE); land["page"]["orient"] = "landscape"
check("쪽 상자 - 가로", (P.page_box(land)["w"], P.page_box(land)["cw"]) == (297, 257), P.page_box(land))
check("runs 규칙 - nexa-text 와 같은 결과", P.norm_runs([{"t": "가", "b": False}, {"t": ""}, {"t": "나"}, {"t": "다", "b": 1}, {"t": "라", "b": True, "i": None}]) == [{"t": "가나"}, {"t": "다라", "b": True}])

print(f"\n실패 {len(fails)}" if fails else f"\n전부 통과 ({n}사례)")
sys.exit(1 if fails else 0)
