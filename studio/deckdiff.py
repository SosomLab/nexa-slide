# -*- coding: utf-8 -*-
"""덱 비교 - 두 덱(옛것·새것)을 장·요소 단위로 비교해 변경 탭 항목을 만든다.

0.15.3 까지 편집기(studio.js diffDeck)에 JS 로 있던 규칙을 그대로 옮긴 것. 0.16.0 부터 비교는 서버(여기) 한 곳에서만 하고
편집기는 결과를 그리기만 한다. 규칙을 바꾸면 tests/fixtures/deckdiff 의 golden 과 check_changes.py 로 확인한다.

    diff_deck(old, new) → [{sid, idx, kind: 추가|수정|이동|삭제, moved: [a, b]|None, title, els: [{id, kinds, before, after, gone?}], extra, gone?}]

규칙
  - 장·요소는 id 로 짝을 맞춘다. 값 비교는 canon()(키 정렬 · 정수값 float → int) 문자열 동치 - JS 의 JSON.stringify 비교와 달리
    키 순서만 다른 같은 객체(build 가 쓴 덱을 편집기가 다시 저장)는 변경으로 보지 않는다(의도된 개선).
  - 요소 키: GEO → "위치·크기", TXT → "글자"(첫 TXT 키의 전→후 60자), src → "그림", 그 밖 → "모양". id 는 비교하지 않는다.
  - 장 이동 = 양쪽에 있는 장을 옛 순서로 늘어놓았을 때 새 순서의 최장 증가 부분 수열(엄격, patience) 밖의 장만.
    els 나 extra 가 있으면 kind 는 "수정"(moved 는 따로 남김), 없으면 "이동".
  - extra = 노트 · 레이아웃 · 바탕 · 부 순서 고정. 항목 순서 = 새 덱 순서(추가·수정·이동) 뒤에 옛 덱 순서(삭제, gone).
"""
import json
import re

from common import plain

GEO = ("x", "y", "w", "h", "x1", "y1", "x2", "y2", "z", "rot")
TXT = ("text", "rows", "header", "items", "code", "lines", "cells", "label", "title", "sub")
SHORT = 60
MAX_ELS = 200  # 한 장의 요소 변경이 이보다 많으면 앞 200개만 남기고 truncated 를 적는다
_MISSING = object()


def _norm(v):
    """정수값 float 를 int 로(329.0 → 329). JS 는 1.0 을 "1" 로 쓰므로 표기 차이를 없앤다."""
    if isinstance(v, float):
        return int(v) if v.is_integer() else v
    if isinstance(v, list):
        return [_norm(x) for x in v]
    if isinstance(v, dict):
        return {k: _norm(x) for k, x in v.items()}
    return v


def canon(v):
    """동치 비교용 문자열 - 키 정렬, 공백 없음, 한글 그대로."""
    if v is _MISSING:
        return None
    return json.dumps(_norm(v), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def short(v, n=SHORT):
    """글자 전→후 표시용 - 강조 표식을 벗기고 공백을 모아 n 자까지(넘치면 … )."""
    t = v if isinstance(v, str) else json.dumps(_norm("" if v is None else v), separators=(",", ":"), ensure_ascii=False)
    t = re.sub(r"\s+", " ", plain(t)).strip()
    return t[:n] + "…" if len(t) > n else t


def slide_title(s):
    els = s.get("elements") or []
    t = next((e for e in els if e.get("role") == "title"), None) or \
        next((e for e in els if e.get("type") == "text" and (e.get("size") or 20) >= 28), None)
    return plain(str(t.get("text") or "")).replace("\n", " ") if t else f"({s.get('layout') or '슬라이드'})"


def diff_el(a, b):
    kinds, before, after = [], "", ""
    keys = list(a.keys()) + [k for k in b.keys() if k not in a]
    for k in keys:
        if k == "id" or canon(a.get(k, _MISSING)) == canon(b.get(k, _MISSING)):
            continue
        if k in GEO:
            kind = "위치·크기"
        elif k in TXT:
            kind = "글자"
            if not before and not after:
                before, after = short(a.get(k)), short(b.get(k))
        elif k == "src":
            kind = "그림"
        else:
            kind = "모양"
        if kind not in kinds:
            kinds.append(kind)
    return {"kinds": kinds, "before": before, "after": after} if kinds else None


def _lis_stable(seq):
    """엄격 증가 patience LIS - 마지막 tails 원소에서 prev 로 역추적한 인덱스 집합(JS 와 같은 동률 선택)."""
    tails, prev = [], [-1] * len(seq)
    for i, v in enumerate(seq):
        lo, hi = 0, len(tails)
        while lo < hi:
            m = (lo + hi) >> 1
            if seq[tails[m]] < v:
                lo = m + 1
            else:
                hi = m
        prev[i] = tails[lo - 1] if lo else -1
        if lo == len(tails):
            tails.append(i)
        else:
            tails[lo] = i
    out, i = set(), (tails[-1] if tails else -1)
    while i >= 0:
        out.add(i)
        i = prev[i]
    return out


def _label(e):
    return short(e.get("text") or e.get("src") or e.get("type"))


def diff_deck(old, new):
    if (new or {}).get("kind") == "sheet" or (old or {}).get("kind") == "sheet":
        return diff_sheet(old or {}, new or {})
    os_, ns = old.get("slides") or [], new.get("slides") or []
    om = {s.get("id"): (s, i) for i, s in enumerate(os_)}
    nm = {s.get("id"): (s, i) for i, s in enumerate(ns)}
    oc = [s.get("id") for s in os_ if s.get("id") in nm]
    npos = {s.get("id"): i for i, s in enumerate([s for s in ns if s.get("id") in om])}
    stable_idx = _lis_stable([npos[i] for i in oc])
    stable = {oc[i] for i in stable_idx}
    items = []
    for i, s in enumerate(ns):
        sid = s.get("id")
        if sid not in om:
            items.append({"sid": sid, "idx": i, "kind": "추가", "moved": None, "title": slide_title(s), "els": [], "extra": []})
            continue
        o, oi = om[sid]
        oe = {e.get("id"): e for e in (o.get("elements") or [])}
        ne = {e.get("id"): e for e in (s.get("elements") or [])}
        els = []
        for e in s.get("elements") or []:
            eid = e.get("id")
            if eid not in oe:
                els.append({"id": eid, "kinds": ["추가"], "before": "", "after": _label(e)})
            else:
                d = diff_el(oe[eid], e)
                if d:
                    els.append({"id": eid, **d})
        for e in o.get("elements") or []:
            if e.get("id") not in ne:
                els.append({"id": e.get("id"), "kinds": ["삭제"], "before": _label(e), "after": "", "gone": True})
        extra = []
        if canon(o.get("notes") or "") != canon(s.get("notes") or ""):
            extra.append("노트")
        for k, name in (("layout", "레이아웃"), ("bg", "바탕"), ("part", "부")):
            if canon(o.get(k, _MISSING)) != canon(s.get(k, _MISSING)):
                extra.append(name)
        moved = sid not in stable
        if els or extra or moved:
            it = {"sid": sid, "idx": i, "kind": "수정" if (els or extra) else "이동", "moved": [oi + 1, i + 1] if moved else None,
                  "title": slide_title(s), "els": els[:MAX_ELS], "extra": extra}
            if len(els) > MAX_ELS:
                it["truncated"] = len(els) - MAX_ELS
            items.append(it)
    for i, s in enumerate(os_):
        if s.get("id") not in nm:
            items.append({"sid": s.get("id"), "idx": i, "kind": "삭제", "moved": None, "title": slide_title(s), "els": [], "extra": [], "gone": True})
    return items


def deck_fields(old, new):
    """장 밖(덱 수준)에서 바뀐 키 - title·part·version·fontPreset 등. slides·updated 는 뺀다."""
    skip = {"slides", "sheets", "updated"}
    keys = [k for k in old.keys() if k not in skip] + [k for k in new.keys() if k not in skip and k not in old]
    return [k for k in keys if canon(old.get(k, _MISSING)) != canon(new.get(k, _MISSING))]


def summary(items):
    out = {"수정": 0, "추가": 0, "삭제": 0, "이동": 0}
    for it in items:
        out[it["kind"]] = out.get(it["kind"], 0) + 1
    return out


def summary_text(items):
    c = summary(items)
    return " · ".join(f"{c[k]}장 {k}" for k in ("수정", "추가", "삭제", "이동") if c.get(k))


# ---------- 시트 문서(kind: sheet) - 탭 = 장, 셀·그림 = 요소. 같은 항목 형식이라 원장·묶음·변경 탭을 그대로 쓴다 ----------
CELL_VAL = ("v", "f")
CELL_SKIP = ("v",)  # 수식 칸의 계산값만 바뀐 것은 따로 세지 않는다(수식이 같으면 "값"이 아니다)
TAB_EXTRA = (("cols", "열 너비"), ("rows", "행 높이"), ("merges", "병합"), ("hiddenCols", "열 숨김"), ("hiddenRows", "행 숨김"),
             ("freeze", "틀 고정"), ("filter", "필터"), ("cond", "조건부 서식"), ("valid", "유효성"), ("size", "크기"),
             ("grid", "눈금선"), ("hidden", "탭 숨김"), ("tables", "표"))


def _draw_id(d, i):
    """sheet.js drawId 와 같다 - id, 없으면 src 파일 이름(확장자 뺌), 그것도 없으면 img<순번>"""
    if d.get("id"):
        return str(d["id"])
    base = re.sub(r"\.[^.]+$", "", str(d.get("src") or "").split("/")[-1])
    return base or f"img{i + 1}"


def _cell_text(o):
    if o is None:
        return ""
    if not isinstance(o, dict):
        return short(o)
    if o.get("f"):
        return short(o["f"] if str(o["f"]).startswith("=") else "=" + str(o["f"]))
    return short(o.get("v", ""))


def diff_cell(a, b):
    """셀 두 판 - 종류(값·수식·서식·추가·삭제)와 글 전→후. 같으면 None"""
    oa, ob = _cell_norm(a), _cell_norm(b)
    if canon(oa) == canon(ob):
        return None
    if oa is None:
        return {"kinds": ["추가"], "before": "", "after": _cell_text(b)}
    if ob is None:
        return {"kinds": ["삭제"], "before": _cell_text(a), "after": ""}
    kinds = []
    if canon(oa.get("f", _MISSING)) != canon(ob.get("f", _MISSING)):
        kinds.append("수식")
    elif not ob.get("f") and canon(oa.get("v", _MISSING)) != canon(ob.get("v", _MISSING)):
        kinds.append("값")
    rest = [k for k in list(oa) + [k for k in ob if k not in oa] if k not in CELL_VAL and canon(oa.get(k, _MISSING)) != canon(ob.get(k, _MISSING))]
    if any(k == "note" for k in rest):
        kinds.append("메모")
    if any(k == "link" for k in rest):
        kinds.append("링크")
    if any(k not in ("note", "link") for k in rest):
        kinds.append("서식")
    if not kinds:
        return None  # 수식 칸의 계산값(v)만 바뀜
    txt = bool({"값", "수식"} & set(kinds))
    return {"kinds": kinds, "before": _cell_text(a) if txt else "", "after": _cell_text(b) if txt else ""}


def _cell_sort(k):
    m = re.match(r"([A-Za-z]+)(\d+)$", k)
    if not m:
        return (1 << 30, 0)
    c = 0
    for ch in m.group(1).upper():
        c = c * 26 + ord(ch) - 64
    return (int(m.group(2)), c)


def diff_sheet(old, new):
    """시트 문서 비교 - 항목 = 탭(sid = 탭 id, title = 탭 이름), els = 셀(id = 칸 주소)·그림(id = 그림 id, kinds 에 "그림"),
    extra = 열 너비·병합·필터 등 탭 속성. 순서·이동 판정은 diff_deck 과 같다."""
    os_, ns = old.get("sheets") or [], new.get("sheets") or []
    om = {t.get("id"): (t, i) for i, t in enumerate(os_) if isinstance(t, dict)}
    nm = {t.get("id"): (t, i) for i, t in enumerate(ns) if isinstance(t, dict)}
    oc = [t.get("id") for t in os_ if isinstance(t, dict) and t.get("id") in nm]
    npos = {t.get("id"): i for i, t in enumerate([t for t in ns if isinstance(t, dict) and t.get("id") in om])}
    stable = {oc[i] for i in _lis_stable([npos[i] for i in oc])}
    items = []
    for i, t in enumerate(ns):
        if not isinstance(t, dict):
            continue
        sid, title = t.get("id"), str(t.get("name") or t.get("id") or "")
        if sid not in om:
            items.append({"sid": sid, "idx": i, "kind": "추가", "moved": None, "title": title, "els": [], "extra": []})
            continue
        o, oi = om[sid]
        a, b = o.get("cells") or {}, t.get("cells") or {}
        els = []
        for k in sorted(set(a) | set(b), key=_cell_sort):
            d = diff_cell(a.get(k), b.get(k))
            if d:
                els.append({"id": k, **d, **({"gone": True} if b.get(k) is None else {})})
        od = {_draw_id(d, j): d for j, d in enumerate(o.get("drawings") or []) if isinstance(d, dict)}
        nd = {_draw_id(d, j): d for j, d in enumerate(t.get("drawings") or []) if isinstance(d, dict)}
        for k, d in nd.items():
            if k not in od:
                els.append({"id": k, "kinds": ["그림", "추가"], "before": "", "after": short(d.get("src") or "")})
            elif canon(od[k]) != canon(d):
                geo = any(canon(od[k].get(x, _MISSING)) != canon(d.get(x, _MISSING)) for x in ("at", "dx", "dy", "w", "h"))
                els.append({"id": k, "kinds": ["그림", "위치·크기" if geo else "모양"], "before": "", "after": ""})
        for k, d in od.items():
            if k not in nd:
                els.append({"id": k, "kinds": ["그림", "삭제"], "before": short(d.get("src") or ""), "after": "", "gone": True})
        extra = [name for key, name in TAB_EXTRA if canon(o.get(key, _MISSING)) != canon(t.get(key, _MISSING))]
        if canon(o.get("name", _MISSING)) != canon(t.get("name", _MISSING)):
            extra.append("이름")
        moved = sid not in stable
        if els or extra or moved:
            it = {"sid": sid, "idx": i, "kind": "수정" if (els or extra) else "이동", "moved": [oi + 1, i + 1] if moved else None,
                  "title": title, "els": els[:MAX_ELS], "extra": extra}
            if len(els) > MAX_ELS:
                it["truncated"] = len(els) - MAX_ELS
            items.append(it)
    for i, t in enumerate(os_):
        if isinstance(t, dict) and t.get("id") not in nm:
            items.append({"sid": t.get("id"), "idx": i, "kind": "삭제", "moved": None, "title": str(t.get("name") or t.get("id") or ""),
                          "els": [], "extra": [], "gone": True})
    return items


def _cell_norm(raw):
    """셀 값 비교용 - 값만 있는 셀(1)과 {"v": 1} 을 같게 본다"""
    if raw is None:
        return None
    return raw if isinstance(raw, dict) else {"v": raw}


def cell_diff(old, new, limit=2000):
    """시트 문서 두 판의 바뀐 셀 - [{"tab", "name", "key", "before", "after"}] (before/after 는 셀 원래 모양, 없으면 None).
    요청 카드의 "AI 가 바꾼 셀 n개 · 보기 · 되돌리기"(/api/reqdiff)와 save_deck 출력에 쓴다. 탭은 id 로 짝짓는다."""
    out = []
    ot = {t.get("id"): t for t in (old or {}).get("sheets") or [] if isinstance(t, dict)}
    for t in (new or {}).get("sheets") or []:
        if not isinstance(t, dict):
            continue
        a = (ot.get(t.get("id")) or {}).get("cells") or {}
        b = t.get("cells") or {}
        for k in list(b) + [k for k in a if k not in b]:
            if _cell_norm(a.get(k)) != _cell_norm(b.get(k)):
                out.append({"tab": t.get("id"), "name": t.get("name", ""), "key": k, "before": a.get(k), "after": b.get(k)})
                if len(out) >= limit:
                    return out
    return out
