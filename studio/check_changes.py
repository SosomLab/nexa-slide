# -*- coding: utf-8 -*-
"""덱 비교(deckdiff.py) 동일성 검사 - 고정 입력(fixture)으로 Python 결과를 golden(tests/fixtures/deckdiff/) 과 대조한다.

    python3 studio/check_changes.py              # golden 대조 + 속성 검사(난수 순열·삽입·삭제 3,000회)
    python3 studio/check_changes.py --js         # 0.15.3 기준 JS(tests/deckdiff_ref.js, node 필요)와도 대조 - 이식 검증용
    python3 studio/check_changes.py --write      # golden 을 지금 Python 결과로 다시 쓴다(규칙을 의도적으로 바꿨을 때만)

JS 와의 의도된 차이(허용 목록): ① 키 순서만 다른 같은 객체(JS 는 변경, Python 은 같음) ② 1 과 1.0(JS 는 변경, Python 은 같음).
그 밖의 차이가 있으면 첫 차이를 보고하고 1 로 끝난다.
"""
import copy
import json
import random
import subprocess
import sys
from pathlib import Path

STUDIO = Path(__file__).resolve().parent
sys.path.insert(0, str(STUDIO))
import deckdiff  # noqa: E402

ROOT = STUDIO.parent
FIX = ROOT / "tests" / "fixtures" / "deckdiff"
REF_JS = ROOT / "tests" / "deckdiff_ref.js"
EXAMPLE = ROOT / "example" / "decks" / "demo.json"


def base_deck():
    d = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    for s in d["slides"]:
        s.setdefault("notes", "")
    return d


def el(i, **kw):
    return {"id": f"e{i:02d}", "type": "text", "x": 10 * i, "y": 20, "w": 100, "h": 30, "text": f"글자 {i}", **kw}


def mk(n_slides=4, n_els=3):
    return {"id": "t", "title": "t", "slides": [{"id": f"s{k:02d}", "layout": "bullets", "notes": "", "bg": "surface", "part": "day1",
                                                   "elements": [el(i) for i in range(1, n_els + 1)]} for k in range(1, n_slides + 1)]}


def cases():
    """(이름, old, new, 허용 차이 태그)"""
    out = []
    demo = base_deck()
    out.append(("same-demo", demo, copy.deepcopy(demo), None))
    out.append(("empty-both", {"slides": []}, {"slides": []}, None))
    out.append(("empty-to-demo", {"slides": []}, demo, None))
    out.append(("demo-to-empty", demo, {"slides": []}, None))
    b = mk()
    n = copy.deepcopy(b); n["slides"].append({"id": "s99", "layout": "summary", "elements": [el(1, role="title", text="새 장")]}); out.append(("slide-add", b, n, None))
    n = copy.deepcopy(b); del n["slides"][1]; out.append(("slide-del", b, n, None))
    n = copy.deepcopy(b); n["slides"][0], n["slides"][1] = n["slides"][1], n["slides"][0]; out.append(("swap-adjacent", b, n, None))
    b5 = mk(5); n = copy.deepcopy(b5); n["slides"] = [n["slides"][i] for i in (3, 4, 0, 1, 2)]; out.append(("block-move", b5, n, None))
    n = copy.deepcopy(b5); n["slides"].reverse(); out.append(("reverse", b5, n, None))
    n = copy.deepcopy(b5); n["slides"].append(n["slides"].pop(0)); out.append(("first-to-last", b5, n, None))
    n = copy.deepcopy(b5); n["slides"].insert(0, n["slides"].pop()); out.append(("last-to-first", b5, n, None))
    n = copy.deepcopy(b); n["slides"][0]["elements"].append(el(9, text="추가 요소")); out.append(("el-add", b, n, None))
    n = copy.deepcopy(b); del n["slides"][0]["elements"][1]; out.append(("el-del", b, n, None))
    n = copy.deepcopy(b); n["slides"][0]["elements"][0]["text"] = "**굵게** 바뀐 ==글자== [[primary|색]]"; out.append(("el-text", b, n, None))
    n = copy.deepcopy(b); n["slides"][0]["elements"][0]["x"] = 11; n["slides"][0]["elements"][0]["w"] = 120; out.append(("el-geo", b, n, None))
    n = copy.deepcopy(b); n["slides"][0]["elements"][0].update({"type": "img", "src": "a.png"}); out.append(("el-img", b, n, None))
    n = copy.deepcopy(b); n["slides"][0]["elements"][0]["fill"] = "primary"; n["slides"][0]["elements"][0]["bold"] = True; out.append(("el-shape", b, n, None))
    n = copy.deepcopy(b); n["slides"][0]["elements"][0]["text"] = "a"; n["slides"][0]["elements"][0]["x"] = 1; n["slides"][0]["elements"][0]["fill"] = "x"; out.append(("el-multi", b, n, None))
    n = copy.deepcopy(b); n["slides"][1]["notes"] = "노트"; n["slides"][2]["layout"] = "table"; n["slides"][3]["bg"] = "primary-container"; n["slides"][0]["part"] = "day2"; out.append(("slide-extra", b, n, None))
    n = copy.deepcopy(b); n["slides"][0]["elements"][0]["text"] = "x"; n["slides"][0], n["slides"][1] = n["slides"][1], n["slides"][0]; out.append(("moved-and-edited", b, n, None))
    b2 = copy.deepcopy(b); b2["slides"][0]["elements"][0]["items"] = [{"text": "x", "sub": ["y"]}]
    n = copy.deepcopy(b2); n["slides"][0]["elements"][0]["items"] = [{"sub": ["y"], "text": "x"}]; out.append(("key-order-only", b2, n, "keyorder"))
    n = copy.deepcopy(b); n["slides"][0]["elements"][0]["x"] = 10.0; out.append(("int-vs-float", b, n, "float"))
    n = copy.deepcopy(b); n["slides"][0]["elements"][0]["x"] = 10.5; out.append(("float-real-change", b, n, None))
    n = copy.deepcopy(b); n["slides"][0]["elements"][0]["text"] = "가" * 59; out.append(("text-59", b, n, None))
    n = copy.deepcopy(b); n["slides"][0]["elements"][0]["text"] = "가" * 60; out.append(("text-60", b, n, None))
    n = copy.deepcopy(b); n["slides"][0]["elements"][0]["text"] = "가" * 61 + "  \n 끝"; out.append(("text-61-ws", b, n, None))
    n = copy.deepcopy(b); n["slides"][0]["elements"][0]["text"] = "😀" * 61; out.append(("emoji-61", b, n, "emoji"))
    n = copy.deepcopy(b); n["slides"][0]["elements"][0]["rows"] = [["a", "b"], ["c", "d"]]; out.append(("rows-added-key", b, n, None))
    n = copy.deepcopy(b); n["slides"][0]["elements"][0]["items"] = [{"text": "x", "sub": ["y"]}]; out.append(("items-json", b, n, None))
    big = mk(1, 230); n = copy.deepcopy(big)
    for e2 in n["slides"][0]["elements"]:
        e2["x"] += 1
    out.append(("els-over-200", big, n, "truncate"))
    n = copy.deepcopy(b); n["slides"][0]["elements"][0]["text"] = None; out.append(("text-to-null", b, n, None))
    n = copy.deepcopy(b); del n["slides"][0]["elements"][0]["text"]; out.append(("text-key-removed", b, n, None))
    n = copy.deepcopy(b); n["slides"][0]["elements"].insert(0, n["slides"][0]["elements"].pop()); out.append(("el-reorder-only", b, n, None))
    return out


def run_js(pairs):
    r = subprocess.run(["node", str(REF_JS)], input=json.dumps(pairs, ensure_ascii=False).encode("utf-8"), capture_output=True)
    if r.returncode != 0:
        sys.exit("node 실패: " + r.stderr.decode("utf-8", "replace"))
    return json.loads(r.stdout.decode("utf-8"))


def first_diff(a, b, path="$"):
    if type(a) is not type(b):
        return f"{path}: 형 {type(a).__name__} vs {type(b).__name__} ({json.dumps(a, ensure_ascii=False)[:80]} vs {json.dumps(b, ensure_ascii=False)[:80]})"
    if isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                return f"{path}.{k}: 한쪽에만 있음"
            d = first_diff(a[k], b[k], f"{path}.{k}")
            if d:
                return d
        return None
    if isinstance(a, list):
        if len(a) != len(b):
            return f"{path}: 길이 {len(a)} vs {len(b)}"
        for i, (x, y) in enumerate(zip(a, b)):
            d = first_diff(x, y, f"{path}[{i}]")
            if d:
                return d
        return None
    return None if a == b else f"{path}: {json.dumps(a, ensure_ascii=False)[:80]} vs {json.dumps(b, ensure_ascii=False)[:80]}"


def strip_trunc(items):
    return [{k: v for k, v in it.items() if k != "truncated"} for it in items]


def property_check(n=3000, seed=20261014):
    """removed ∪ stable ∪ moved = 옛 id, added ∪ stable ∪ moved = 새 id, LIS 길이 = 공통 수 - 이동 수."""
    rnd = random.Random(seed)
    for _ in range(n):
        k = rnd.randint(0, 12)
        old = mk(k, 1)
        ids = [s["id"] for s in old["slides"]]
        new_ids = [i for i in ids if rnd.random() > 0.2]
        rnd.shuffle(new_ids)
        for j in range(rnd.randint(0, 3)):
            new_ids.insert(rnd.randint(0, len(new_ids)), f"n{j}")
        new = {"slides": [{"id": i, "layout": "bullets", "notes": "", "elements": [el(1)]} for i in new_ids]}
        items = deckdiff.diff_deck(old, new)
        removed = {it["sid"] for it in items if it["kind"] == "삭제"}
        added = {it["sid"] for it in items if it["kind"] == "추가"}
        moved = {it["sid"] for it in items if it.get("moved")}
        common = set(ids) & set(new_ids)
        assert removed == set(ids) - set(new_ids), (ids, new_ids, items)
        assert added == set(new_ids) - set(ids), (ids, new_ids, items)
        assert moved <= common
        # 이동하지 않은 장은 옛·새 순서가 같아야 한다
        st_old = [i for i in ids if i in common and i not in moved]
        st_new = [i for i in new_ids if i in common and i not in moved]
        assert st_old == st_new, (ids, new_ids, moved)
    return n


def main():
    js, write = "--js" in sys.argv, "--write" in sys.argv
    cs = cases()
    py = [deckdiff.diff_deck(o, n) for _, o, n, _ in cs]
    bad = 0
    if js:
        jres = run_js([[o, n] for _, o, n, _ in cs])
        for (name, _, _, tag), p, j in zip(cs, py, jres):
            if tag == "keyorder":
                ok = (j and not p)  # JS 는 변경, Python 은 같음 - 의도된 차이
                print(f"  {'허용' if ok else '실패'}  {name}: JS {len(j)}건 / Python {len(p)}건 (의도된 차이: 키 순서)")
                bad += 0 if ok else 1
                continue
            if tag == "float":  # JSON 왕복에서 JS 도 10.0 을 10 으로 읽으므로 둘 다 0건이어야 한다
                ok = not j and not p
                print(f"  {'같음' if ok else '실패'}  {name}: JS {len(j)}건 / Python {len(p)}건")
                bad += 0 if ok else 1
                continue
            if tag == "truncate":  # Python 은 요소 200개 상한 - JS 결과를 같은 상한으로 잘라 비교
                j = [{**it, "els": it["els"][:deckdiff.MAX_ELS]} for it in j]
            if tag == "emoji":  # JS length 는 UTF-16 단위 - Python(코드포인트)이 정본
                d = first_diff(strip_trunc(p), j)
                print(f"  {'허용' if d else '같음'}  {name}: {d or ''} (Python 정본)")
                continue
            d = first_diff(strip_trunc(p), j)
            if d:
                bad += 1
                print(f"  실패  {name}: {d}")
            else:
                print(f"  같음  {name}")
    FIX.mkdir(parents=True, exist_ok=True)
    gold = FIX / "cases.json"
    if write or not gold.exists():
        gold.write_text(json.dumps({name: {"old": o, "new": n, "items": p} for (name, o, n, _), p in zip(cs, py)}, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"golden 기록: {gold} ({len(cs)}건)")
    else:
        g = json.loads(gold.read_text(encoding="utf-8"))
        for (name, _, _, _), p in zip(cs, py):
            exp = g.get(name)
            if exp is None:
                print(f"  golden 없음  {name}")
                bad += 1
                continue
            d = first_diff(p, exp["items"])
            if d:
                bad += 1
                print(f"  golden 불일치  {name}: {d}")
        print(f"golden 대조 {len(cs)}건 - 불일치 {bad}")
    n = property_check()
    print(f"속성 검사 {n}회 통과")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
