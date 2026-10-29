# -*- coding: utf-8 -*-
"""AI 제안 - 동시 편집 3단계 첫 조각(docs/collab.md). AI 의 큰 변경을 파일에 바로 쓰지 않고 제안으로 남겨, 사람이 장(시트는 탭)마다 골라 받는다.

    items(base, deck)              기준본 → AI 사본의 변경을 받을 단위로 - [{id, kind, title, detail, subs?}]
                                   슬라이드: "s:<장 id>"(수정·추가·삭제) · "order"(장 순서) · "deck"(덱 속성) / 시트: "t:<탭 id>"(셀·탭 속성) · "order" · "deck"
                                   수정된 장·탭은 subs 에 더 작은 단위(3-3) - 요소 "s:<장>:<요소>"(무엇이·글 전→후) · 셀 "t:<탭>:<셀>"(값 전→후)
    apply(base, deck, chosen)      기준본에 고른 단위만 AI 사본 것으로 바꾼 문서 - 이것을 지금 파일과 3-way 병합(deckmerge)해 저장한다
    pick(its, chosen)              요청한 id 를 받을 id 로(일부를 이미 처리한 장·탭은 남은 요소·셀로 풀어서) + 처리 뒤 남는 items
    path(decks, deck, request)     제안 파일 decks/.history/<덱>/proposals/<요청>.json

제안 파일 = {request, created, base(판), baseDoc, deck(AI 사본), items}. 받은 단위는 items 에서 빠지고, 다 받거나 버리면 파일을 지운다."""
import copy
import json
from pathlib import Path

import deckdiff

ORDER, DECK = "order", "deck"
SKIP = ("updated", "slides", "sheets")
SUBS_MAX = 300  # 탭 하나에서 셀 단위로 보여 줄 수 - 넘으면 탭째로만 받는다


def _cell_text(raw):
    """셀 전→후 표시 - 수식은 수식, 값은 값, 없으면 (빈 칸)"""
    if raw is None:
        return "(빈 칸)"
    o = raw if isinstance(raw, dict) else {"v": raw}
    if o.get("f"):
        return deckdiff.short(o["f"])
    return deckdiff.short(o["v"]) if "v" in o else "(서식)"


def path(decks, deck, request):
    return Path(decks) / ".history" / deck / "proposals" / f"{request}.json"


def _lists(d):
    key = "sheets" if (d or {}).get("kind") == "sheet" else "slides"
    return key, [x for x in (d or {}).get(key) or [] if isinstance(x, dict) and x.get("id")]


def items(base, deck):
    """기준본 → AI 사본에서 바뀐 단위. 바뀐 것이 없으면 []"""
    key, bl = _lists(base)
    _, dl = _lists(deck)
    bi, di = {x["id"]: x for x in bl}, {x["id"]: x for x in dl}
    sheet = key == "sheets"
    out = []
    for x in dl + [x for x in bl if x["id"] not in di]:
        i = x["id"]
        b, d = bi.get(i), di.get(i)
        if b == d:
            continue
        kind = "추가" if b is None else "삭제" if d is None else "수정"
        if sheet:
            title = (d or b).get("name") or i
            cd = deckdiff.cell_diff({"sheets": [b]} if b else {"sheets": []}, {"sheets": [d]} if d else {"sheets": []}) if d else []
            n = len(cd) if d else len((b or {}).get("cells") or {})
            detail = f"셀 {n}개" if n else "탭 속성"
            subs = [{"id": f"t:{i}:{c['key']}", "kind": "추가" if c["before"] is None else "삭제" if c["after"] is None else "수정", "title": c["key"],
                     "detail": f"{_cell_text(c['before'])} → {_cell_text(c['after'])}"} for c in cd[:SUBS_MAX]] if b and d else []
            more = bool(b and d) and (len(cd) > SUBS_MAX or {k: v for k, v in b.items() if k != "cells"} != {k: v for k, v in d.items() if k != "cells"})
        else:
            title = deckdiff.slide_title(d or b) or i
            be = {e.get("id"): e for e in (b or {}).get("elements") or [] if isinstance(e, dict)}
            de = {e.get("id"): e for e in (d or {}).get("elements") or [] if isinstance(e, dict)}
            ch = [k for k in list(de) + [k for k in be if k not in de] if be.get(k) != de.get(k)]
            detail = f"요소 {len(ch)}개" if ch else "장 속성"
            subs = []
            more = bool(b and d) and {k: v for k, v in b.items() if k != "elements"} != {k: v for k, v in d.items() if k != "elements"}
            for k in ch if b and d else []:
                eb, ed = be.get(k), de.get(k)
                if eb is None or ed is None:
                    subs.append({"id": f"s:{i}:{k}", "kind": "추가" if eb is None else "삭제", "title": k, "detail": deckdiff.short((ed or eb).get("text") or (ed or eb).get("type") or "")})
                else:
                    df = deckdiff.diff_el(eb, ed) or {"kinds": [], "before": "", "after": ""}
                    subs.append({"id": f"s:{i}:{k}", "kind": "수정", "title": k, "detail": "·".join(df["kinds"]) + (f" {df['before']} → {df['after']}" if df["before"] or df["after"] else "")})
        it = {"id": ("t:" if sheet else "s:") + i, "kind": kind, "title": title, "detail": detail}
        if subs:
            it["subs"] = subs
            if more:  # 요소·셀 말고도 바뀐 것(장·탭 속성) - 요소·셀을 다 처리해도 장·탭째로 남는다
                it["more"] = True
        out.append(it)
    common = [x["id"] for x in bl if x["id"] in di]
    if [x["id"] for x in dl if x["id"] in bi] != common:
        out.append({"id": ORDER, "kind": "순서", "title": "탭 순서" if sheet else "장 순서", "detail": ""})
    bf = {k: v for k, v in (base or {}).items() if k not in SKIP}
    df = {k: v for k, v in (deck or {}).items() if k not in SKIP}
    if bf != df:
        out.append({"id": DECK, "kind": "수정", "title": "문서 설정", "detail": ", ".join(sorted(k for k in set(bf) | set(df) if bf.get(k) != df.get(k)))[:80]})
    return out


def apply(base, deck, chosen):
    """기준본에서 고른 단위만 AI 사본 것으로 - 고르지 않은 단위는 기준본 그대로(그래서 병합하면 지금 파일의 그 부분이 남는다)."""
    chosen = set(chosen)
    out = copy.deepcopy(base)
    key, bl = _lists(base)
    _, dl = _lists(deck)
    pre = "t:" if key == "sheets" else "s:"
    di = {x["id"]: x for x in dl}
    lst = [copy.deepcopy(x) for x in bl]
    ids = [x["id"] for x in lst]
    for x in list(lst):  # 수정·삭제
        i = x["id"]
        if pre + i not in chosen:
            continue
        if i in di:
            lst[ids.index(i)] = copy.deepcopy(di[i])
        else:
            n = ids.index(i); del lst[n]; del ids[n]
    dids = [x["id"] for x in dl]
    for n, i in enumerate(dids):  # 추가 - AI 사본에서 바로 앞 항목 뒤에
        if i in ids or pre + i not in chosen:
            continue
        prev = next((dids[m] for m in range(n - 1, -1, -1) if dids[m] in ids), None)
        at = ids.index(prev) + 1 if prev else 0
        lst.insert(at, copy.deepcopy(di[i])); ids.insert(at, i)
    # 더 작은 단위(3-3) - 장(탭)째로 고르지 않은 수정 장·탭에서 고른 요소·셀만
    subs = {}
    for c in chosen:
        unit, _, sub = c.rpartition(":")
        if unit.count(":") == 1 and unit.split(":")[0] in ("s", "t") and unit not in chosen and sub:
            subs.setdefault(unit.split(":", 1)[1], set()).add(sub)
    ids = [x["id"] for x in lst]
    for i, keys in subs.items():
        if i not in ids or i not in di:
            continue
        cur, ai = lst[ids.index(i)], di[i]
        inner = "cells" if key == "sheets" else "elements"
        if "*" in keys:  # 장·탭 속성만(요소·셀 말고)
            for k in set(cur) | set(ai):
                if k in (inner, "id"):
                    continue
                if k in ai:
                    cur[k] = copy.deepcopy(ai[k])
                else:
                    cur.pop(k, None)
            keys = keys - {"*"}
        if key == "sheets":
            cells = cur.setdefault("cells", {})
            for k in keys:
                if k in (ai.get("cells") or {}):
                    cells[k] = copy.deepcopy(ai["cells"][k])
                else:
                    cells.pop(k, None)
        else:
            els = cur.setdefault("elements", [])
            aels = [e for e in ai.get("elements") or [] if isinstance(e, dict)]
            aids = [e.get("id") for e in aels]
            for k in keys:
                eids = [e.get("id") for e in els]
                if k in aids and k in eids:
                    els[eids.index(k)] = copy.deepcopy(aels[aids.index(k)])
                elif k in aids:  # AI 가 더한 요소 - AI 사본에서 바로 앞 요소 뒤에
                    n = aids.index(k)
                    prev = next((aids[m] for m in range(n - 1, -1, -1) if aids[m] in eids), None)
                    els.insert(eids.index(prev) + 1 if prev else 0, copy.deepcopy(aels[n]))
                elif k in eids:
                    del els[eids.index(k)]
    if ORDER in chosen:  # 순서 - AI 사본 순서(사본에 없는 항목은 원래 자리 근처 끝에)
        rank = {i: k for k, i in enumerate(dids)}
        lst.sort(key=lambda x: rank.get(x["id"], len(rank)))
    out[key] = lst
    if DECK in chosen:
        for k in set(base) | set(deck):
            if k in SKIP:
                continue
            if k in deck:
                out[k] = copy.deepcopy(deck[k])
            else:
                out.pop(k, None)
    return out


def pick(its, chosen):
    """받기·버리기에 고른 id → (실제로 쓸 id, 남는 items). 모르는 id 는 버린다.
    일부 요소·셀을 이미 처리한 장·탭(part)을 통째로 고르면 남은 요소·셀만 고른 것으로 - 버린 요소가 되살아나지 않게(장·탭 속성은 빠진다)."""
    want, use = set(chosen), []
    for it in its:
        sub_ids = [s["id"] for s in it.get("subs") or []]
        if it["id"] in want:
            use += sub_ids + ([it["id"] + ":*"] if it.get("more") else []) if it.get("part") else [it["id"]]
        else:
            use += [k for k in sub_ids if k in want]
    done, left = set(use), []
    for it in its:
        if it["id"] in done or it["id"] + ":*" in done:
            continue
        subs = [s for s in it.get("subs") or [] if s["id"] not in done]
        if it.get("subs") and len(subs) < len(it["subs"]):
            if not subs and not it.get("more"):
                continue
            it = {**it, "subs": subs, "part": True, "detail": f"남은 {len(subs)}개" if subs else "장·탭 속성"}
            if not subs:
                it.pop("subs")
        left.append(it)
    return use, left


def label(its, k):
    """받은 id 의 이름 - 장·탭은 제목, 요소·셀은 "제목 요소" """
    for it in its:
        if it["id"] == k:
            return it["title"]
        for s in it.get("subs") or []:
            if s["id"] == k:
                return f"{it['title']} {s['title']}"
    return k


def load(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
