# -*- coding: utf-8 -*-
"""페이지 문서 변경 비교(deckdiff.diff_page) 시험.  python studio/tests/pagediff_test.py"""
import copy
import sys
from pathlib import Path

import os

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
# deckdiff 가 부르는 common 은 작업 공간이 있어야 뜬다 - 예제 작업 공간을 쓴다(읽기만)
os.environ.setdefault("NEXA_SLIDE_WORKSPACE", str(Path(__file__).resolve().parents[2] / "example"))
import deckdiff as D  # noqa: E402

fails, n = [], 0


def check(name, ok, got=None):
    global n
    n += 1
    if not ok:
        fails.append(name)
        print(f"FAIL {name}" + (f" - {got!r}" if got is not None else ""))


sys.stdout.reconfigure(encoding="utf-8", errors="replace")
P = lambda i, t, **kw: {"id": i, "type": "p", "runs": [{"t": t}] if t else [], **kw}  # noqa: E731
OLD = {"id": "d", "title": "문서", "kind": "page", "slides": [], "updated": "a", "page": {"size": "A4"}, "styles": {"body": {"size": 10.5}},
       "blocks": [P("b1", "첫 문단"), P("b2", "둘째 문단"), P("b3", "셋째"),
                  {"id": "t1", "type": "table", "cols": [50, 50], "rows": [{"id": "r1", "cells": [{"id": "c1", "blocks": [P("p1", "가")]}, {"id": "c2", "blocks": [P("p2", "나")]}]}]},
                  {"id": "im", "type": "image", "src": "a.png"}]}
check("같으면 변경 없음", D.diff_deck(OLD, copy.deepcopy(OLD)) == [])
new = copy.deepcopy(OLD); new["updated"] = "b"
check("저장 시각만 다르면 변경·필드 없음", D.diff_deck(OLD, new) == [] and D.deck_fields(OLD, new) == [])
new = copy.deepcopy(OLD); new["blocks"][1]["runs"] = [{"t": "둘째 문단 고침", "b": True}]
it = D.diff_deck(OLD, new)
check("글 수정 - 전·후 글", len(it) == 1 and it[0]["sid"] == "b2" and it[0]["kind"] == "수정" and it[0]["els"] == [{"id": "b2", "kinds": ["수정"], "before": "둘째 문단", "after": "둘째 문단 고침"}] and it[0]["extra"] == [], it)
new = copy.deepcopy(OLD); new["blocks"][0].update(align="center", style="h1", list={"kind": "bullet", "level": 0})
it = D.diff_deck(OLD, new)
check("문단 속성만 - 바뀐 속성 이름", len(it) == 1 and it[0]["kind"] == "수정" and it[0]["els"] == [] and sorted(it[0]["extra"]) == ["목록", "스타일", "정렬"], it)
new = copy.deepcopy(OLD); new["blocks"].insert(1, P("n1", "새 문단")); new["blocks"].pop(3)
it = D.diff_deck(OLD, new)
check("넣기·지우기", [(x["sid"], x["kind"]) for x in it] == [("n1", "추가"), ("b3", "삭제")] and it[0]["title"] == "새 문단" and it[1].get("gone") is True, it)
new = copy.deepcopy(OLD); new["blocks"].insert(0, new["blocks"].pop(2))
it = D.diff_deck(OLD, new)
check("순서 바꾸기 - 옮긴 블록만", [(x["sid"], x["kind"], x["moved"]) for x in it] == [("b3", "이동", [3, 1])], it)
new = copy.deepcopy(OLD); new["blocks"][3]["rows"][0]["cells"][1]["blocks"][0]["runs"] = [{"t": "나 고침"}]
it = D.diff_deck(OLD, new)
check("표 칸 수정 - 표 블록 하나로", len(it) == 1 and it[0]["sid"] == "t1" and it[0]["els"][0]["before"] == "가 | 나" and it[0]["els"][0]["after"] == "가 | 나 고침" and it[0]["extra"] == ["표 내용"], it)
new = copy.deepcopy(OLD); new["blocks"][4]["src"] = "b.png"; new["blocks"][4]["w"] = 50
it = D.diff_deck(OLD, new)
check("그림 바꾸기", it[0]["sid"] == "im" and it[0]["title"] == "[그림 b.png]" and sorted(it[0]["extra"]) == ["그림", "크기"], it)
new = copy.deepcopy(OLD); new["title"] = "새 제목"; new["page"] = {"size": "A4", "orient": "landscape"}; new["styles"]["h1"] = {"size": 20}
check("덱 수준 - 제목·쪽 설정·스타일", D.diff_deck(OLD, new) == [] and D.deck_fields(OLD, new) == ["title", "page", "styles"], D.deck_fields(OLD, new))
check("요약 - 수정·추가·삭제·이동 수", D.summary(D.diff_deck(OLD, {**copy.deepcopy(OLD), "blocks": [P("b1", "첫 문단!"), P("n9", "새")]}))["수정"] == 1)
check("슬라이드·시트 비교는 그대로", D.diff_deck({"slides": [{"id": "s1", "elements": []}]}, {"slides": [{"id": "s1", "elements": []}]}) == [] and D.diff_deck({"kind": "sheet", "sheets": []}, {"kind": "sheet", "sheets": []}) == [])

print(f"\n실패 {len(fails)}" if fails else f"\n전부 통과 ({n}사례)")
sys.exit(1 if fails else 0)
