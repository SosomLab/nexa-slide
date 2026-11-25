# -*- coding: utf-8 -*-
"""페이지 문서 병합(deckmerge.py 의 blocks) 시험.  python studio/tests/pagemerge_test.py
    --dump  사례와 서버 병합 결과를 JSON 으로 찍는다(tests/pagemerge_check.js 가 화면 병합 nexa-merge.js 와 맞춰 본다)."""
import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import deckmerge  # noqa: E402

P = lambda i, t, **kw: {"id": i, "type": "p", "runs": [{"t": t}] if t else [], **kw}  # noqa: E731
CELL = lambda i, *bs: {"id": i, "blocks": list(bs)}  # noqa: E731
TABLE = {"id": "t1", "type": "table", "cols": [50, 50], "rows": [{"id": "r1", "head": True, "cells": [CELL("c11", P("p11", "머리1")), CELL("c12", P("p12", "머리2"))]},
                                                               {"id": "r2", "cells": [CELL("c21", P("p21", "가")), CELL("c22", P("p22", "나"))]}]}
BASE = {"id": "d", "title": "문서", "kind": "page", "slides": [], "updated": "2026-01-01T00:00:00",
        "page": {"size": "A4", "orient": "portrait", "margin": {"t": 25, "r": 20, "b": 25, "l": 20}, "header": {"blocks": [P("h1", "머리말")]}, "footer": {"blocks": []}},
        "styles": {"body": {"size": 10.5}, "h1": {"based": "body", "size": 20}},
        "blocks": [P("b1", "첫 문단"), P("b2", "둘째 문단"), P("b3", "셋째 문단"), copy.deepcopy(TABLE), P("b5", "끝 문단")], "objects": []}


def mk(fn):
    d = copy.deepcopy(BASE)
    fn(d)
    return d


def blk(d, i):
    return next(b for b in d["blocks"] if b["id"] == i)


def text(b):
    return "".join(r["t"] for r in b.get("runs", []))


def cell(d, rid, cid):
    t = blk(d, "t1")
    return next(c for r in t["rows"] if r["id"] == rid for c in r["cells"] if c["id"] == cid)


ids = lambda d: [b["id"] for b in d["blocks"]]  # noqa: E731
CASES = [
    ("다른 문단을 고침 - 둘 다 남는다", lambda d: blk(d, "b1")["runs"].__setitem__(0, {"t": "첫 문단(나)"}), lambda d: blk(d, "b3")["runs"].__setitem__(0, {"t": "셋째(남)"}), "ours", 0,
     lambda m: text(blk(m, "b1")) == "첫 문단(나)" and text(blk(m, "b3")) == "셋째(남)"),
    ("같은 문단의 글을 둘 다 고침 - 충돌, 내 것", lambda d: blk(d, "b2").update(runs=[{"t": "나"}]), lambda d: blk(d, "b2").update(runs=[{"t": "남"}]), "ours", 1,
     lambda m: text(blk(m, "b2")) == "나"),
    ("같은 문단의 글을 둘 다 고침 - AI 저장이면 사람(남)이 이긴다", lambda d: blk(d, "b2").update(runs=[{"t": "나"}]), lambda d: blk(d, "b2").update(runs=[{"t": "남"}]), "theirs", 1,
     lambda m: text(blk(m, "b2")) == "남"),
    ("같은 문단 - 한쪽은 글, 한쪽은 정렬·스타일", lambda d: blk(d, "b2").update(runs=[{"t": "글 바꿈", "b": True}]), lambda d: blk(d, "b2").update(align="center", style="h1"), "ours", 0,
     lambda m: blk(m, "b2")["runs"] == [{"t": "글 바꿈", "b": True}] and blk(m, "b2")["align"] == "center" and blk(m, "b2")["style"] == "h1"),
    ("문단 넣기 - 양쪽이 다른 자리에", lambda d: d["blocks"].insert(1, P("n1", "내가 넣음")), lambda d: d["blocks"].insert(3, P("n2", "남이 넣음")), "ours", 0,
     lambda m: ids(m) == ["b1", "n1", "b2", "b3", "n2", "t1", "b5"]),
    ("문단 지우기 대 다른 문단 고치기", lambda d: d["blocks"].pop(1), lambda d: blk(d, "b5").update(runs=[{"t": "끝(남)"}]), "ours", 0,
     lambda m: ids(m) == ["b1", "b3", "t1", "b5"] and text(blk(m, "b5")) == "끝(남)"),
    ("지운 문단을 남이 고침 - 수정이 남는다", lambda d: d["blocks"].pop(1), lambda d: blk(d, "b2").update(runs=[{"t": "살아남"}]), "ours", 1,
     lambda m: ids(m) == ["b1", "b2", "b3", "t1", "b5"] and text(blk(m, "b2")) == "살아남"),
    ("순서 바꾸기 - 한쪽만 옮기면 그 순서", lambda d: d["blocks"].insert(0, d["blocks"].pop(2)), lambda d: blk(d, "b1").update(align="right"), "ours", 0,
     lambda m: ids(m) == ["b3", "b1", "b2", "t1", "b5"] and blk(m, "b1")["align"] == "right"),
    ("목록 속성 - 한쪽이 목록으로, 한쪽이 글", lambda d: blk(d, "b3").update(list={"kind": "number", "level": 0}), lambda d: blk(d, "b3").update(runs=[{"t": "글"}]), "ours", 0,
     lambda m: blk(m, "b3")["list"] == {"kind": "number", "level": 0} and text(blk(m, "b3")) == "글"),
    ("표 - 다른 칸을 고침", lambda d: cell(d, "r2", "c21")["blocks"][0].update(runs=[{"t": "가(나)"}]), lambda d: cell(d, "r2", "c22")["blocks"][0].update(runs=[{"t": "나(남)"}]), "ours", 0,
     lambda m: text(cell(m, "r2", "c21")["blocks"][0]) == "가(나)" and text(cell(m, "r2", "c22")["blocks"][0]) == "나(남)"),
    ("표 - 행 넣기 대 칸 고치기", lambda d: blk(d, "t1")["rows"].append({"id": "r3", "cells": [CELL("c31", P("p31", "새")), CELL("c32")]}), lambda d: cell(d, "r1", "c11")["blocks"][0].update(runs=[{"t": "머리(남)"}]), "ours", 0,
     lambda m: [r["id"] for r in blk(m, "t1")["rows"]] == ["r1", "r2", "r3"] and text(cell(m, "r1", "c11")["blocks"][0]) == "머리(남)"),
    ("표 - 같은 칸의 같은 문단을 둘 다 - 충돌", lambda d: cell(d, "r2", "c21")["blocks"][0].update(runs=[{"t": "나"}]), lambda d: cell(d, "r2", "c21")["blocks"][0].update(runs=[{"t": "남"}]), "ours", 1,
     lambda m: text(cell(m, "r2", "c21")["blocks"][0]) == "나"),
    ("표 - 칸 병합 속성 대 칸 채움", lambda d: cell(d, "r1", "c11").update(colspan=2), lambda d: cell(d, "r2", "c22").update(fill="#eeeeee"), "ours", 0,
     lambda m: cell(m, "r1", "c11")["colspan"] == 2 and cell(m, "r2", "c22")["fill"] == "#eeeeee"),
    ("쪽 설정 - 여백 대 방향", lambda d: d["page"].update(margin={"t": 30, "r": 20, "b": 25, "l": 20}), lambda d: d["page"].update(orient="landscape"), "ours", 0,
     lambda m: m["page"]["margin"]["t"] == 30 and m["page"]["orient"] == "landscape"),
    ("머리말 문단 대 본문 문단", lambda d: d["page"]["header"]["blocks"][0].update(runs=[{"t": "머리말(나)"}]), lambda d: blk(d, "b1").update(runs=[{"t": "본문(남)"}]), "ours", 0,
     lambda m: text(m["page"]["header"]["blocks"][0]) == "머리말(나)" and text(blk(m, "b1")) == "본문(남)"),
    ("스타일 - 다른 스타일을 고침", lambda d: d["styles"]["h1"].update(size=24), lambda d: d["styles"].update(quote={"based": "body", "italic": True}), "ours", 0,
     lambda m: m["styles"]["h1"]["size"] == 24 and m["styles"]["quote"]["italic"] is True and m["styles"]["body"] == {"size": 10.5}),
    ("제목 대 본문", lambda d: d.update(title="새 제목"), lambda d: blk(d, "b1").update(runs=[{"t": "본문"}]), "ours", 0,
     lambda m: m["title"] == "새 제목" and text(blk(m, "b1")) == "본문"),
    ("updated 는 내 것(서버가 다시 찍는다)", lambda d: d.update(updated="X"), lambda d: d.update(updated="Y"), "ours", 0, lambda m: m["updated"] == "X"),
    ("양쪽이 같은 변경 - 충돌 아님", lambda d: blk(d, "b1").update(runs=[{"t": "같음"}]), lambda d: blk(d, "b1").update(runs=[{"t": "같음"}]), "ours", 0, lambda m: text(blk(m, "b1")) == "같음"),
]


def run():
    out = []
    for name, fo, ft, prefer, nconf, ok in CASES:
        ours, theirs = mk(fo), mk(ft)
        keep = json.dumps([BASE, ours, theirs], ensure_ascii=False)
        merged, conflicts = deckmerge.merge3(BASE, ours, theirs, prefer)
        good = len(conflicts) == nconf and ok(merged) and json.dumps([BASE, ours, theirs], ensure_ascii=False) == keep and merged.get("kind") == "page"
        out.append({"name": name, "base": BASE, "ours": ours, "theirs": theirs, "prefer": prefer, "merged": merged, "conflicts": len(conflicts), "ok": good})
    return out


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    res = run()
    if "--dump" in sys.argv:
        print(json.dumps(res, ensure_ascii=False))
        sys.exit(0)
    bad = [r for r in res if not r["ok"]]
    for r in bad:
        print(f"FAIL {r['name']} - 충돌 {r['conflicts']} · 블록 {[b['id'] for b in r['merged'].get('blocks', [])]}")
    print(f"\n실패 {len(bad)}" if bad else f"\n전부 통과 ({len(res)}사례)")
    sys.exit(1 if bad else 0)
