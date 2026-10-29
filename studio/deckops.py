# -*- coding: utf-8 -*-
"""작업(op) 저장 - 동시 편집 3-4(docs/collab.md). 화면 nexa-merge.js 의 NexaMerge.ops/applyOps 와 같은 규칙(골든 tests/deckops_cases.json).

    diff(old, new)               마지막 저장본 → 지금 문서의 차이를 작업 목록으로 - apply(old, diff(old, new)) == new
    apply(doc, ops, base=None)   지금 파일에 작업을 차례로 → (문서, 적용 수, 버린 작업[{i, op, why}])
    label(op)                    원장에 남길 한 줄(값은 빼고 어디를) - 서버 POST /api/ops 가 evidence.ops 에

작업 단위는 병합 단위와 같다(deckmerge) - 슬라이드: 덱 속성 · 장(추가·삭제·순서·장 속성) · 요소(추가·삭제·순서·속성, 위치 x·y·w·h·rot 는 한 묶음 "geom").
시트: 덱 속성 · 탭(추가·삭제·순서·탭 속성) · 셀 · 열 너비(cols)·행 높이(rows) 키. 값이 없어진 속성은 {"del": true}.
대상이 지금 파일에 없으면(그 사이 누가 지움) - 고치는 작업은 기준본(base)에서 요소·장을 찾아 되살리고(수정 > 삭제), 찾지 못하면 버린다."""
import copy

GEOM = ("x", "y", "w", "h", "rot")
SKIP = ("updated",)
MISSING = object()


def _kind(d):
    return "sheets" if (d or {}).get("kind") == "sheet" else "slides"


def _items(lst):
    return [x for x in lst or [] if isinstance(x, dict) and x.get("id") is not None]


def _props(old, new, skip):
    """dict 두 개의 속성 차이 - [(key, value | MISSING)]"""
    out = []
    for k in sorted(set(new) | set(old)):  # 키 순서는 정렬 - 화면(JS 는 숫자 같은 키를 앞에 둔다)과 같은 작업 순서
        if k in skip:
            continue
        a, b = old.get(k, MISSING), new.get(k, MISSING)
        if a != b:
            out.append((k, b))
    return out


def _setop(base, k, v):
    o = dict(base, key=k)
    if v is MISSING:
        o["del"] = True
    else:
        o["value"] = copy.deepcopy(v)
    return o


def _list_ops(old, new, pre, idk, add_op, del_op, order_op, inner):
    """장·탭·요소 목록 - 추가(바로 앞 id 뒤)·삭제·순서·안쪽 차이"""
    ops = []
    oi, ni = {x["id"]: x for x in _items(old)}, {x["id"]: x for x in _items(new)}
    nids = [x["id"] for x in _items(new)]
    for x in _items(old):
        if x["id"] not in ni:
            ops.append({"op": del_op, **pre, idk: x["id"]})
    common_old = [x["id"] for x in _items(old) if x["id"] in ni]
    common_new = [i for i in nids if i in oi]
    if common_old != common_new:
        ops.append({"op": order_op, **pre, "ids": common_new})
    for n, i in enumerate(nids):
        if i not in oi:
            ops.append({"op": add_op, **pre, idk: i, "after": nids[n - 1] if n else None, "value": copy.deepcopy(ni[i])})
        else:
            ops += inner(oi[i], ni[i])
    return ops


def diff(old, new):
    old, new = old or {}, new or {}
    key = _kind(new)
    ops = [_setop({"op": "deck-set"}, k, v) for k, v in _props(old, new, SKIP + ("slides", "sheets"))]
    if key == "sheets":
        def tab(a, b):
            t = {"tab": a["id"]}
            o = [_setop({"op": "tab-set", **t}, k, v) for k, v in _props(a, b, ("id", "cells", "cols", "rows"))]
            for part, op in (("cells", "cell"), ("cols", "cols"), ("rows", "rows")):
                o += [_setop({"op": op, **t}, k, v) for k, v in _props(a.get(part) or {}, b.get(part) or {}, ())]
            return o
        ops += _list_ops(old.get("sheets"), new.get("sheets"), {}, "tab", "tab-add", "tab-del", "tabs-order", tab)
        if (old.get("slides") or []) != (new.get("slides") or []):
            ops.append(_setop({"op": "deck-set"}, "slides", new.get("slides", MISSING)))
        return ops

    def slide(a, b):
        s = {"slide": a["id"]}
        o = [_setop({"op": "slide-set", **s}, k, v) for k, v in _props(a, b, ("id", "elements"))]

        def el(x, y):
            e = {"slide": a["id"], "el": x["id"]}
            r, geo = [], False
            for k, v in _props(x, y, ("id",)):
                if k in GEOM:
                    geo = True
                else:
                    r.append(_setop({"op": "set", **e}, k, v))
            if geo:
                r.insert(0, {"op": "set", **e, "key": "geom", "value": {k: y[k] for k in GEOM if k in y}})
            return r
        return o + _list_ops(a.get("elements"), b.get("elements"), s, "el", "add", "del", "order", el)
    return ops + _list_ops(old.get("slides"), new.get("slides"), {}, "slide", "slide-add", "slide-del", "slides-order", slide)


def label(o):
    """원장에 남길 작업 한 줄 - 값은 빼고 어디를(장·요소·탭·키)"""
    return " ".join(str(o[k]) for k in ("op", "slide", "tab", "el", "key") if o.get(k) is not None)[:120]


def _find(lst, i):
    return next((x for x in lst if isinstance(x, dict) and x.get("id") == i), None)


def _insert(lst, value, after):
    ids = [x.get("id") if isinstance(x, dict) else None for x in lst]
    if value.get("id") in ids:
        return
    lst.insert(ids.index(after) + 1 if after in ids else (0 if after is None else len(lst)), value)


def _reorder(lst, ids):
    """ids 순서로 - ids 에 없는 항목(그 사이 남이 더한 것)은 바로 앞 항목 뒤에 남긴다"""
    rank = {i: n for n, i in enumerate(ids)}
    known = sorted([x for x in lst if isinstance(x, dict) and x.get("id") in rank], key=lambda x: rank[x["id"]])
    out, k = [], 0
    for x in lst:
        if isinstance(x, dict) and x.get("id") in rank:
            out.append(known[k]); k += 1
        else:
            out.append(x)
    return out


def _put(o, target):
    if o.get("del"):
        target.pop(o["key"], None)
    else:
        target[o["key"]] = copy.deepcopy(o.get("value"))


def apply(doc, ops, base=None):
    out = copy.deepcopy(doc or {})
    key = _kind(out)
    dropped, n = [], 0
    for i, o in enumerate(ops or []):
        why = _apply1(out, key, o, base)
        if why:
            dropped.append({"i": i, "op": o.get("op"), "why": why})
        else:
            n += 1
    return out, n, dropped


def _revive(out, key, base, sid):
    """지금 파일에 없는 장·탭을 기준본에서 되살린다(기준본 자리 - 바로 앞 장 뒤)"""
    bl = _items((base or {}).get(key))
    b = _find(bl, sid)
    if b is None:
        return None
    lst = out.setdefault(key, [])
    n = [x["id"] for x in bl].index(sid)
    _insert(lst, copy.deepcopy(b), bl[n - 1]["id"] if n else None)
    return _find(lst, sid)


def _apply1(out, key, o, base):
    op = o.get("op")
    if op == "deck-set":
        _put(o, out); return None
    unit = "tab" if key == "sheets" else "slide"
    lst = out.setdefault(key, [])
    if op in ("slide-add", "tab-add"):
        _insert(lst, copy.deepcopy(o["value"]), o.get("after")); return None
    if op in ("slide-del", "tab-del"):
        out[key] = [x for x in lst if not (isinstance(x, dict) and x.get("id") == o.get(unit))]; return None
    if op in ("slides-order", "tabs-order"):
        out[key] = _reorder(lst, o.get("ids") or []); return None
    cur = _find(lst, o.get(unit))
    if cur is None:
        cur = _revive(out, key, base, o.get(unit))  # 수정 > 삭제
        if cur is None:
            return f"{'탭' if key == 'sheets' else '장'} {o.get(unit)} 없음"
    if op in ("slide-set", "tab-set"):
        _put(o, cur); return None
    if key == "sheets":
        part = {"cell": "cells", "cols": "cols", "rows": "rows"}.get(op)
        if not part:
            return f"모르는 작업 {op}"
        _put(o, cur.setdefault(part, {})); return None
    els = cur.setdefault("elements", [])
    if op == "add":
        _insert(els, copy.deepcopy(o["value"]), o.get("after")); return None
    if op == "del":
        cur["elements"] = [x for x in els if not (isinstance(x, dict) and x.get("id") == o.get("el"))]; return None
    if op == "order":
        cur["elements"] = _reorder(els, o.get("ids") or []); return None
    if op != "set":
        return f"모르는 작업 {op}"
    e = _find(els, o.get("el"))
    if e is None:  # 그 사이 지운 요소를 고쳤다 - 기준본에서 되살린다
        bs = _find(_items((base or {}).get("slides")), o.get("slide"))
        be = _find((bs or {}).get("elements") or [], o.get("el"))
        if be is None:
            return f"요소 {o.get('el')} 없음"
        bel = [x.get("id") for x in bs["elements"] if isinstance(x, dict)]
        n = bel.index(o.get("el"))
        _insert(els, copy.deepcopy(be), bel[n - 1] if n else None)
        e = _find(els, o.get("el"))
    if o.get("key") == "geom":
        for k in GEOM:
            if k in (o.get("value") or {}):
                e[k] = o["value"][k]
            else:
                e.pop(k, None)
    else:
        _put(o, e)
    return None
