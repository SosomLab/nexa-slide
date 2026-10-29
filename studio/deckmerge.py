# -*- coding: utf-8 -*-
"""덱·시트 문서 3-way 병합 - 동시 편집 1단계(docs/collab.md 4절 1단계).

    merged, conflicts = merge3(base, ours, theirs, prefer="ours")

base   = 보낸 쪽이 고치기 시작한 버전(편집기가 읽은 판, AI 사본을 만든 판)
ours   = 지금 저장하려고 보낸 문서
theirs = 지금 파일(그 사이 다른 사람·AI·빌드가 저장한 것)
prefer = 같은 단위를 양쪽이 다르게 고쳤을 때 이기는 쪽. 서버는 사람끼리면 나중 저장(ours), AI 저장이면 사람(theirs).

병합 단위(서로 다른 단위를 고치면 둘 다 남는다)
- 슬라이드 덱: 덱 속성 → 장(id) → 장 속성 · 요소(id) → 요소 속성. 위치·크기(x·y·w·h·rot)는 한 묶음.
- 시트 문서: 탭(id) → 탭 속성(cols·rows 는 열·행마다) · 셀(키) → 셀 내용(f 가 있으면 f, 없으면 v) · 서식 키마다.
  계산값 v 는 내용과 같이 움직이고(수식 셀은 화면이 다시 계산), 서식은 키마다 따로 병합한다.
- 순서(장·요소·탭): 한쪽만 순서를 바꿨으면 그쪽, 아니면 theirs. 한쪽만 더한 항목은 그쪽 목록에서 바로 앞 항목 뒤에 넣는다.
- 삭제 대 수정: 수정이 이긴다(데이터를 잃지 않는 쪽) - 충돌로 남긴다. 양쪽이 같은 id 를 새로 만들면 속성 병합.
충돌 = [{"path": "slides/s01/elements/e03/text", "kept": "ours"|"theirs", "ours": …, "theirs": …}] - 진 값은 원장·알림에 남긴다.
입력은 고치지 않는다(복사해 쓴다). 화면 쪽 같은 규칙은 nexa-merge.js(있다면)와 tests/deckmerge_cases.json 으로 맞춘다."""
import copy

MISSING = object()  # 없는 키·항목
GEOM = ("x", "y", "w", "h", "rot")  # 요소의 위치·크기 - 한 묶음
SKIP_TOP = ("updated",)  # 저장할 때 서버가 새로 넣는 값 - 병합하지 않는다


def _eq(a, b):
    if a is MISSING or b is MISSING:
        return a is b
    return a == b


class _M:
    def __init__(self, prefer):
        assert prefer in ("ours", "theirs"), prefer
        self.prefer, self.conflicts = prefer, []

    def val(self, path, b, o, t):
        """값 하나 - 한쪽만 바꿨으면 그쪽, 둘 다 같게 바꿨으면 그 값, 다르게 바꿨으면 prefer(충돌로 남김)."""
        if _eq(o, t):
            return o
        if _eq(o, b):
            return t
        if _eq(t, b):
            return o
        kept = self.prefer
        self.conflicts.append({"path": path, "kept": kept, "ours": None if o is MISSING else o, "theirs": None if t is MISSING else t})
        return o if kept == "ours" else t

    def keys(self, path, b, o, t, special=None, groups=()):
        """객체 키마다 val. special = {키: 함수(path, b, o, t)} 는 그 함수로, groups = 한 묶음으로 다룰 키들."""
        special = special or {}
        b, o, t = (x if isinstance(x, dict) else {} for x in (b, o, t))
        out, grouped = {}, {k for g in groups for k in g}
        for g in groups:  # 묶음 - 묶음 전체를 값 하나로
            pick = lambda d: tuple(d.get(k, MISSING) for k in g)  # noqa: E731
            n = len(self.conflicts)
            r = self.val(f"{path}/{'·'.join(g)}", pick(b), pick(o), pick(t))
            for c in self.conflicts[n:]:  # 충돌 기록에는 묶음을 {키: 값}(없는 키는 뺌)으로 - 원장·응답 JSON 에 MISSING 이 새지 않게
                for side, d in (("ours", o), ("theirs", t)):
                    c[side] = {k: d[k] for k in g if k in d}
            for k, v in zip(g, r):
                if v is not MISSING:
                    out[k] = v
        order = list(t) + [k for k in o if k not in t] + [k for k in b if k not in t and k not in o]
        for k in order:
            if k in grouped or k in out:
                continue
            bv, ov, tv = b.get(k, MISSING), o.get(k, MISSING), t.get(k, MISSING)
            r = special[k](f"{path}/{k}", bv, ov, tv) if k in special else self.val(f"{path}/{k}", bv, ov, tv)
            if r is not MISSING:
                out[k] = r
        return {k: out[k] for k in order + [k for k in out if k not in order] if k in out}

    def ilist(self, path, b, o, t, item):
        """id 가 있는 항목 목록(장·요소·탭) - 항목마다 item(path, b, o, t), 삭제 대 수정은 수정, 순서는 바꾼 쪽."""
        lists = [x if isinstance(x, list) else [] for x in (b, o, t)]
        if any(not isinstance(x, dict) or not x.get("id") for L in lists for x in L):  # id 없는 항목 - 목록 통째로 값 하나
            return self.val(path, b, o, t)
        bi, oi, ti = ({x["id"]: x for x in L} for L in lists)
        kept = {}
        for i in list(ti) + [i for i in oi if i not in ti] + [i for i in bi if i not in ti and i not in oi]:
            bx, ox, tx = bi.get(i, MISSING), oi.get(i, MISSING), ti.get(i, MISSING)
            p = f"{path}/{i}"
            if bx is MISSING:  # 새 항목 - 한쪽만이면 그것, 양쪽이 같은 id 로 만들었으면 속성 병합
                kept[i] = item(p, {}, ox, tx) if ox is not MISSING and tx is not MISSING else (ox if ox is not MISSING else tx)
            elif ox is MISSING and tx is MISSING:
                continue
            elif ox is MISSING or tx is MISSING:  # 한쪽이 지움 - 다른 쪽이 고치지 않았으면 지우고, 고쳤으면 고친 것을 남긴다
                other = tx if ox is MISSING else ox
                if _eq(other, bx):
                    continue
                self.conflicts.append({"path": p, "kept": "theirs" if ox is MISSING else "ours", "ours": None if ox is MISSING else "(수정)", "theirs": None if tx is MISSING else "(수정)", "rule": "삭제 대 수정 - 수정을 남김"})
                kept[i] = other
            else:
                kept[i] = item(p, bx, ox, tx)
        # 순서 - 양쪽에 다 있는 id 의 상대 순서를 한쪽만 바꿨으면 그쪽 목록이 기준
        ids_b, ids_o, ids_t = ([x["id"] for x in L] for L in lists)
        common = [i for i in ids_b if i in oi and i in ti]
        rel = lambda ids: [i for i in ids if i in common]  # noqa: E731
        moved_o, moved_t = rel(ids_o) != common, rel(ids_t) != common
        primary, other = (ids_o, ids_t) if moved_o and not moved_t else (ids_t, ids_o)
        seq = [i for i in primary if i in kept]
        for src in (other, ids_b):  # 기준 목록에 없는 항목(다른 쪽이 더했거나 수정이 이겨 살아난 것) - 그 목록의 바로 앞 항목 뒤에
            for n, i in enumerate(src):
                if i in kept and i not in seq:
                    prev = next((src[m] for m in range(n - 1, -1, -1) if src[m] in seq), None)
                    seq.insert(seq.index(prev) + 1 if prev else 0, i)
        return [copy.deepcopy(kept[i]) for i in seq]

    # ---- 슬라이드 덱
    def element(self, path, b, o, t):
        return self.keys(path, b, o, t, groups=(GEOM,))

    def slide(self, path, b, o, t):
        return self.keys(path, b, o, t, special={"elements": lambda p, *x: self.ilist(p, *(v if v is not MISSING else [] for v in x), self.element)})

    # ---- 시트 문서
    @staticmethod
    def _cell(raw):
        """셀 → (내용, 서식). 내용 = ("f", 수식, v) 또는 ("v", 값) · 빈 칸은 None. 서식 = 그 밖의 키들."""
        if raw is MISSING or raw is None:
            return None, {}
        o = raw if isinstance(raw, dict) else {"v": raw}
        fmt = {k: v for k, v in o.items() if k not in ("v", "f")}
        if o.get("f"):
            return ("f", o["f"], o.get("v")), fmt
        return (("v", o["v"]) if "v" in o else None), fmt

    def cell(self, path, b, o, t):
        (bc, bf), (oc, of), (tc, tf) = self._cell(b), self._cell(o), self._cell(t)
        key = lambda c: None if c is None else c[:2]  # noqa: E731 - 수식 셀은 수식으로 비교(계산값 v 는 다시 계산되므로)
        kc = self.val(f"{path}/내용", key(bc), key(oc), key(tc))
        content = None if kc is None else next(c for c in (oc, tc, bc) if c is not None and c[:2] == kc)
        if content is not None and content[0] == "f" and oc is not None and tc is not None and oc[:2] == tc[:2] == kc:
            # 같은 수식 - 계산값(v)은 캐시라 충돌로 치지 않고, 기준에서 바뀐 쪽(새로 계산한 쪽)을 쓴다
            bv = bc[2] if bc is not None and bc[:2] == kc else None
            content = ("f", kc[1], tc[2] if oc[2] == bv else oc[2])
        fmt = self.keys(path, bf, of, tf)
        out = dict(fmt)
        if content is not None:
            if content[0] == "f":
                out["f"] = content[1]
                if content[2] is not None:
                    out["v"] = content[2]
            else:
                out["v"] = content[1]
        if not out:
            return MISSING
        return out["v"] if list(out) == ["v"] else out

    def cells(self, path, b, o, t):
        b, o, t = (x if isinstance(x, dict) else {} for x in (b, o, t))
        out = {}
        for k in list(t) + [k for k in o if k not in t] + [k for k in b if k not in t and k not in o]:
            r = self.cell(f"{path}/{k}", b.get(k, MISSING), o.get(k, MISSING), t.get(k, MISSING))
            if r is not MISSING:
                out[k] = r
        return out

    def tab(self, path, b, o, t):
        one = lambda p, *x: self.keys(p, *(v if v is not MISSING else {} for v in x))  # noqa: E731 - 열 너비·행 높이는 열·행마다
        return self.keys(path, b, o, t, special={"cells": self.cells, "cols": one, "rows": one})

    def deck(self, b, o, t):
        b, o, t = (x if isinstance(x, dict) else {} for x in (b, o, t))
        lst = lambda item: (lambda p, *x: self.ilist(p, *(v if v is not MISSING else [] for v in x), item))  # noqa: E731
        res = self.keys("", {k: v for k, v in b.items() if k not in SKIP_TOP}, {k: v for k, v in o.items() if k not in SKIP_TOP},
                        {k: v for k, v in t.items() if k not in SKIP_TOP}, special={"slides": lst(self.slide), "sheets": lst(self.tab)})
        for k in SKIP_TOP:
            if k in o:
                res[k] = o[k]
        return res


def merge3(base, ours, theirs, prefer="ours"):
    """(병합 결과, 충돌 목록). 입력은 고치지 않는다."""
    m = _M(prefer)
    merged = m.deck(copy.deepcopy(base), copy.deepcopy(ours), copy.deepcopy(theirs))
    for c in m.conflicts:
        c["path"] = c["path"].lstrip("/")
    return merged, m.conflicts


def describe(conflicts, limit=8):
    """충돌을 사람이 읽을 한 줄씩 - 응답·원장·AI reply 에 쓴다."""
    out = []
    for c in conflicts[:limit]:
        who = "보낸 쪽" if c["kept"] == "ours" else "파일 쪽"
        out.append(f"{c['path']}: {c.get('rule') or '양쪽이 다르게 고침'} → {who} 값을 남김")
    if len(conflicts) > limit:
        out.append(f"… 외 {len(conflicts) - limit}건")
    return out
