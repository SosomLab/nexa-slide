# -*- coding: utf-8 -*-
"""AI 제안 - 동시 편집 3단계 첫 조각(docs/collab.md). AI 의 큰 변경을 파일에 바로 쓰지 않고 제안으로 남겨, 사람이 장(시트는 탭)마다 골라 받는다.

    items(base, deck)              기준본 → AI 사본의 변경을 받을 단위로 - [{id, kind, title, detail}]
                                   슬라이드: "s:<장 id>"(수정·추가·삭제) · "order"(장 순서) · "deck"(덱 속성) / 시트: "t:<탭 id>"(셀·탭 속성) · "order" · "deck"
    apply(base, deck, chosen)      기준본에 고른 단위만 AI 사본 것으로 바꾼 문서 - 이것을 지금 파일과 3-way 병합(deckmerge)해 저장한다
    path(decks, deck, request)     제안 파일 decks/.history/<덱>/proposals/<요청>.json

제안 파일 = {request, created, base(판), baseDoc, deck(AI 사본), items}. 받은 단위는 items 에서 빠지고, 다 받거나 버리면 파일을 지운다."""
import copy
import json
from pathlib import Path

import deckdiff

ORDER, DECK = "order", "deck"
SKIP = ("updated", "slides", "sheets")


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
            n = len(deckdiff.cell_diff({"sheets": [b]} if b else {"sheets": []}, {"sheets": [d]} if d else {"sheets": []})) if d else len((b or {}).get("cells") or {})
            detail = f"셀 {n}개" if n else "탭 속성"
        else:
            title = deckdiff.slide_title(d or b) or i
            be = {e.get("id"): e for e in (b or {}).get("elements") or [] if isinstance(e, dict)}
            de = {e.get("id"): e for e in (d or {}).get("elements") or [] if isinstance(e, dict)}
            ch = [k for k in list(de) + [k for k in be if k not in de] if be.get(k) != de.get(k)]
            detail = f"요소 {len(ch)}개" if ch else "장 속성"
        out.append({"id": ("t:" if sheet else "s:") + i, "kind": kind, "title": title, "detail": detail})
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


def load(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
