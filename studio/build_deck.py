# -*- coding: utf-8 -*-
"""장 내용 원본(content/<id>.json) → 덱 JSON(decks/<id>.json).

    python3 studio/build_deck.py ch00            # 덱이 없을 때만 만든다
    python3 studio/build_deck.py ch00 --force    # 기존 덱을 덮어쓴다(.history 에 백업 후)
    python3 studio/build_deck.py ch00 --out x.json

편집기에서 사람이 고친 덱을 지키기 위해, 덱이 이미 있으면 --force 없이는 쓰지 않는다.
"""
import argparse
import datetime as dt
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CONFIG, CONTENT, DECKS, safe_id  # noqa: E402
from layouts import build_slide  # noqa: E402


def load_common():
    com = json.loads((CONTENT / "_common.json").read_text(encoding="utf-8"))
    ver = com.get("course_version", "")
    return json.loads(json.dumps(com, ensure_ascii=False).replace("{course_version}", ver))


def toc_order(toc):
    """목차 순서 = 교육 순서. (장, 이름, 부, '그 부의 N번째')"""
    return [(it[0], it[1], it[2] if len(it) > 2 else g["part"], f"{g['label']} {j + 1}번째")
            for g in toc["groups"] for j, it in enumerate(g["items"])]


def chapter_block(content):
    """장 블록 — 장 표지부터 장 정리까지(장 파일의 slides). 각 슬라이드에 그 장의 부(part)를 붙인다."""
    part = content.get("part", "day1")
    return [dict(s, _part=s.get("_part", part)) for s in content["slides"]]


def front(com, contents, current=None):
    """앞부분 공통 — 메인 표지 · 전체 목차 · 개정 이력.
    개정 이력: 장 파일 하나면 그 장의 이력, 여러 장(통합본)이면 장 열을 붙여 하나의 표로 합친다."""
    toc = dict(com["toc"])
    if current:
        toc["current"] = current
    out = [dict(com["cover"]), toc]
    revs = [(c["id"], c["revisions"]) for c in contents if c.get("revisions")]
    if len(contents) == 1 and revs:
        out.append({"layout": "revisions", **revs[0][1]})
    elif revs:
        rows = [[r[0], r[1], cid, *r[2:]] for cid, rv in revs for r in rv["rows"]]
        out.append({"layout": "revisions", "title": "개정 이력", "sub": "통합본 — 장별 이력을 모은 표",
                    "header": ["버전", "일자", "장", "내용", "작성·검토"], "colW": [100, 140, 90, 662, 160],
                    "rows": rows, "note": revs[0][1].get("note"), "crumb": "개정 이력"})
    return out


def end_slide(com, next_id=None):
    end = dict(com["end"])
    if next_id:
        order = toc_order(com["toc"])
        ids = [o[0] for o in order]
        if next_id in ids and ids.index(next_id) + 1 < len(ids):
            end["next"] = list(order[ids.index(next_id) + 1])
    return end


def assemble(content):
    """장 파일 하나 → 앞부분 공통 + 장 블록 + EoD(다음 장 안내)."""
    if not content.get("common"):
        return chapter_block(content)
    com = load_common()
    end = end_slide(com, content["id"])
    end["sub"] = content.get("chapterLabel", content["id"])
    return front(com, [content], content["id"]) + chapter_block(content) + [end]


def assemble_book(contents):
    """여러 장 → 통합본 한 파일: 앞부분 공통(개정 이력 통합) + 장 블록들(목차 순서) + EoD 하나."""
    com = load_common()
    end = end_slide(com)
    end["sub"] = "전체 과정"
    body = [s for c in contents for s in chapter_block(c)]
    return front(com, contents) + body + [end]


def to_deck(did, title, part, slides_src, meta):
    slides = []
    for i, s in enumerate(slides_src, 1):
        fields = {k: v for k, v in s.items() if k not in ("layout", "_part")}
        slides.append(build_slide(s["layout"], fields, s.get("_part", part), f"s{i:02d}"))
    return {"id": did, "title": title, "part": part, "version": meta.get("version", "0.1"),
            "updated": dt.datetime.now().isoformat(timespec="seconds"), "source": meta.get("source", ""),
            "slides": slides}


def build(content):
    return to_deck(content["id"], content.get("title", content["id"]), content.get("part", "day1"),
                   assemble(content), content)


def build_book(ids):
    contents = [json.loads((CONTENT / f"{i}.json").read_text(encoding="utf-8")) for i in ids]
    return to_deck("book", (CONFIG.get("title") or "통합본") + " — 통합본", "day1", assemble_book(contents),
                   {"source": "content/" + ", ".join(ids)})


def tidy(v):
    """정수값 float(329.0)는 int 로 — 편집기(JS)가 저장할 때 표기가 바뀌어 생기는 가짜 변경을 없앤다."""
    if isinstance(v, float):
        return int(v) if v.is_integer() else round(v, 2)
    if isinstance(v, list):
        return [tidy(x) for x in v]
    if isinstance(v, dict):
        return {k: tidy(x) for k, x in v.items()}
    return v


def edited_slides(prev, cur):
    """마지막 빌드(prev)와 지금 덱(cur)을 슬라이드 id 로 비교해 사람이 고친 곳을 한 줄씩 알려 준다."""
    P = {x["id"]: x for x in prev["slides"]}
    out = []
    for i, sl in enumerate(cur["slides"], 1):
        p = P.get(sl["id"])
        if p is None:
            out.append(f"{i}번({sl['id']}) 새 슬라이드")
            continue
        if sl.get("notes") != p.get("notes"):
            out.append(f"{i}번({sl['id']}) 발표자 노트")
        if sl.get("elements") != p.get("elements"):
            n = sum(1 for x, y in zip(sl["elements"], p["elements"]) if x != y) + abs(len(sl["elements"]) - len(p["elements"]))
            out.append(f"{i}번({sl['id']}) 요소 {n}개")
    gone = set(P) - {x["id"] for x in cur["slides"]}
    out += [f"{g} 삭제됨" for g in sorted(gone)]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("id", help="장 id(ch00) 또는 book(통합본)")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--discard-edits", action="store_true", help="마지막 빌드 뒤 편집기에서 고친 내용을 버리고 다시 만든다")
    ap.add_argument("--out")
    ap.add_argument("--chapters", nargs="*", help="book: 넣을 장(생략하면 목차 순서로 내용 파일이 있는 장 전부)")
    a = ap.parse_args()
    if not safe_id(a.id):
        sys.exit("잘못된 덱 id")
    if a.id == "book":
        ids = a.chapters or [o[0] for o in toc_order(load_common()["toc"])
                             if (CONTENT / f"{o[0]}.json").exists()]
        deck = build_book(ids)
    else:
        src = CONTENT / f"{a.id}.json"
        deck = build(json.loads(src.read_text(encoding="utf-8")))
    out = Path(a.out) if a.out else DECKS / f"{a.id}.json"
    if out.exists() and not a.force and not a.out:
        sys.exit(f"{out} 가 이미 있다 — 편집 내용을 지키려고 멈춘다. 덮어쓰려면 --force")
    out.parent.mkdir(parents=True, exist_ok=True)
    last = DECKS / ".history" / a.id / "last-build.json"
    if out.exists() and not a.out and last.exists() and not a.discard_edits:
        # 편집기(사람)가 마지막 빌드 뒤에 덱을 고쳤으면 멈춘다 — 고친 내용을 content 에 옮긴 뒤 다시 빌드하거나 --discard-edits
        cur = tidy(json.loads(out.read_text(encoding="utf-8")))
        prev = tidy(json.loads(last.read_text(encoding="utf-8")))
        edits = edited_slides(prev, cur)
        if edits:
            lines = ["편집기에서 고친 슬라이드가 있어 멈춘다(content 에 옮기지 않으면 사라진다):"]
            lines += ["  " + e for e in edits]
            lines.append("옮긴 뒤 다시 실행하거나, 버려도 되면 --discard-edits")
            sys.exit(chr(10).join(lines))
    if out.exists():
        h = DECKS / ".history" / a.id
        h.mkdir(parents=True, exist_ok=True)
        shutil.copy2(out, h / (dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f") + "-build.json"))
    out.write_text(json.dumps(tidy(deck), ensure_ascii=False, indent=1), encoding="utf-8")
    if not a.out:
        last.parent.mkdir(parents=True, exist_ok=True)
        last.write_text(json.dumps(tidy(deck), ensure_ascii=False, indent=1), encoding="utf-8")
    n = sum(len(s["elements"]) for s in deck["slides"])
    print(f"{out} — 슬라이드 {len(deck['slides'])}장, 요소 {n}개")


if __name__ == "__main__":
    main()
