# -*- coding: utf-8 -*-
"""덱 관리 - 덱 추가 · 이름(id) 바꾸기 · 제목 바꾸기 · 삭제(휴지통). 서버(/api/decks)와 CLI 가 같은 함수를 쓴다.

    python3 nexa.py deck list                              # 덱 목록(id · 제목 · 장 수)
    python3 nexa.py deck create <id> [--title "제목"] [--layout cover|blank|…]   # 1장짜리 새 덱(decks/<id>.json)
    python3 nexa.py deck rename <id> <새 id>               # 덱 파일과 딸린 것(요청·기록·첨부·content/<id>.json) 모두 옮긴다
    python3 nexa.py deck retitle <id> "새 제목"            # 덱(과 content)의 title
    python3 nexa.py deck delete <id>                       # decks/.trash/<id>-<시각>/ 로 옮긴다(되돌리려면 그 폴더에서 다시 복사)

덱 id = 파일 이름(decks/<id>.json, 편집기 덱 탭에 보이는 이름): 영문·숫자·-·_ 만, 'book' 은 통합본용.
서버가 떠 있으면 편집기 덱 탭의 ＋ 단추·오른쪽 클릭 메뉴가 같은 일을 한다(docs/editor.md).
"""
import datetime as dt
import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CONTENT, DECKS, OUT, WORKSPACE  # noqa: E402
from ledger import atomic_write  # noqa: E402

ID_RX = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
TRASH = DECKS / ".trash"


def _dumps(o):
    return json.dumps(o, ensure_ascii=False, indent=1) + "\n"


def check_id(i):
    if not ID_RX.match(i or ""):
        raise ValueError(f"덱 이름은 영문·숫자·-·_ (64자 이내): {i!r}")
    if i.endswith(".requests") or i.startswith("."):
        raise ValueError(f"쓸 수 없는 덱 이름: {i}")
    return i


def attached(i):
    """덱에 딸린 경로 [(현재, 새 이름을 받는 함수)] - 요청·기록·첨부·내용 원본."""
    return [(DECKS / f"{i}.json", lambda n: DECKS / f"{n}.json"),
            (DECKS / f"{i}.requests.json", lambda n: DECKS / f"{n}.requests.json"),
            (DECKS / ".history" / i, lambda n: DECKS / ".history" / n),
            (OUT / "attach" / i, lambda n: OUT / "attach" / n),
            (CONTENT / f"{i}.json", lambda n: CONTENT / f"{n}.json")]


def list_decks():
    out = []
    for f in sorted(DECKS.glob("*.json")) if DECKS.is_dir() else []:
        if f.name.endswith(".requests.json"):
            continue
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
            out.append({"id": f.stem, "title": d.get("title", f.stem), "slides": len(d.get("slides", [])), "content": (CONTENT / f"{f.stem}.json").is_file()})
        except (OSError, ValueError) as e:
            out.append({"id": f.stem, "title": f"(읽기 오류: {e})", "slides": 0, "content": False})
    return out


def create(i, title=None, layout="cover", part="day1"):
    """1장짜리 새 덱 - 레이아웃 견본 내용에 제목을 넣어 만든다(없는 레이아웃이면 빈 슬라이드)."""
    check_id(i)
    p = DECKS / f"{i}.json"
    if p.exists():
        raise ValueError(f"이미 있는 덱: {i}")
    from layouts import LAYOUTS, SAMPLES, build_slide
    title = (title or i).strip() or i
    if layout not in LAYOUTS:
        layout = "blank" if "blank" in LAYOUTS else next(iter(LAYOUTS))
    fields = {**(SAMPLES.get(layout) or {})}
    if "title" in fields or layout in ("cover", "section", "title"):
        fields["title"] = title
    try:
        slide = build_slide(layout, fields, part, "s01")
    except Exception:  # noqa: BLE001 - 견본 필드가 안 맞는 레이아웃이면 빈 장으로
        slide = build_slide("blank", {}, part, "s01")
    deck = {"id": i, "title": title, "part": part, "version": "0.1", "updated": dt.datetime.now().isoformat(timespec="seconds"), "source": "", "slides": [slide]}
    DECKS.mkdir(parents=True, exist_ok=True)
    atomic_write(p, _dumps(deck))
    return {"id": i, "title": title, "slides": 1, "path": str(p)}


def rename(i, new):
    """덱 id 바꾸기 - 덱 파일 안의 id, 요청 파일(첨부 경로 포함), 기록 폴더, 첨부 폴더, content/<id>.json 까지."""
    check_id(new)
    src = DECKS / f"{i}.json"
    if not src.is_file():
        raise ValueError(f"없는 덱: {i}")
    if i == new:
        raise ValueError("같은 이름이다")
    for cur, to in attached(i):
        if cur.exists() and to(new).exists():
            raise ValueError(f"이미 있다: {to(new).relative_to(WORKSPACE)}")
    moved = []
    for cur, to in attached(i):
        if cur.exists():
            to(new).parent.mkdir(parents=True, exist_ok=True)
            cur.rename(to(new))
            moved.append(str(to(new).relative_to(WORKSPACE)))
    for p in (DECKS / f"{new}.json", CONTENT / f"{new}.json"):  # 안의 id 도
        if p.is_file():
            try:
                d = json.loads(p.read_text(encoding="utf-8"))
                if isinstance(d, dict) and d.get("id") == i:
                    d["id"] = new
                    atomic_write(p, _dumps(d))
            except (OSError, ValueError):
                pass
    rq = DECKS / f"{new}.requests.json"  # 첨부 경로 out/attach/<옛>/… → <새>
    if rq.is_file():
        try:
            rs = json.loads(rq.read_text(encoding="utf-8"))
            old_prefix = f"out/attach/{i}/"
            for r in rs:
                for a in r.get("attachments") or []:
                    if isinstance(a, dict) and str(a.get("path", "")).startswith(old_prefix):
                        a["path"] = f"out/attach/{new}/" + a["path"][len(old_prefix):]
            atomic_write(rq, json.dumps(rs, ensure_ascii=False, indent=1))
        except (OSError, ValueError):
            pass
    return {"id": new, "from": i, "moved": moved}


def retitle(i, title):
    p = DECKS / f"{i}.json"
    if not p.is_file():
        raise ValueError(f"없는 덱: {i}")
    title = " ".join(str(title or "").split())[:200]
    if not title:
        raise ValueError("제목을 준다")
    d = json.loads(p.read_text(encoding="utf-8"))
    d["title"], d["updated"] = title, dt.datetime.now().isoformat(timespec="seconds")
    atomic_write(p, _dumps(d))
    c = CONTENT / f"{i}.json"
    if c.is_file():  # 내용 원본에도 - 다음 build 가 제목을 되돌리지 않게
        try:
            cd = json.loads(c.read_text(encoding="utf-8"))
            if isinstance(cd, dict):
                cd["title"] = title
                atomic_write(c, _dumps(cd))
        except (OSError, ValueError):
            pass
    return {"id": i, "title": title}


def delete(i):
    """휴지통(decks/.trash/<id>-<시각>/)으로 옮긴다 - 덱·요청·기록·첨부·content."""
    src = DECKS / f"{i}.json"
    if not src.is_file():
        raise ValueError(f"없는 덱: {i}")
    box = TRASH / f"{i}-{dt.datetime.now().strftime('%Y%m%dT%H%M%S')}"
    box.mkdir(parents=True, exist_ok=True)
    moved = []
    for cur, _ in attached(i):
        if cur.exists():
            dst = box / cur.relative_to(WORKSPACE)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(cur), str(dst))
            moved.append(str(cur.relative_to(WORKSPACE)))
    return {"id": i, "trash": str(box.relative_to(WORKSPACE)), "moved": moved}


def main():
    for st in (sys.stdout, sys.stderr):
        try:
            st.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass
    import argparse
    ap = argparse.ArgumentParser(description="덱 관리")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    c = sub.add_parser("create"); c.add_argument("id"); c.add_argument("--title"); c.add_argument("--layout", default="cover"); c.add_argument("--part", default="day1")
    r = sub.add_parser("rename"); r.add_argument("id"); r.add_argument("new")
    t = sub.add_parser("retitle"); t.add_argument("id"); t.add_argument("title")
    d = sub.add_parser("delete"); d.add_argument("id")
    a = ap.parse_args()
    try:
        if a.cmd == "list":
            for x in list_decks():
                print(f"{x['id']:16s} {x['slides']:3d}장  {x['title']}" + ("  (content 있음)" if x["content"] else ""))
        elif a.cmd == "create":
            x = create(a.id, a.title, a.layout, a.part); print(f"만듦: {x['path']} ({x['title']}, 1장) - 서버가 떠 있으면 편집기 덱 탭에 바로 보인다")
        elif a.cmd == "rename":
            x = rename(a.id, a.new); print(f"바꿈: {x['from']} → {x['id']}  옮긴 것: " + ", ".join(x["moved"]))
        elif a.cmd == "retitle":
            x = retitle(a.id, a.title); print(f"제목: {x['id']} → {x['title']}")
        elif a.cmd == "delete":
            x = delete(a.id); print(f"휴지통으로: {x['trash']}  ({', '.join(x['moved'])})")
    except ValueError as e:
        sys.exit(str(e))


if __name__ == "__main__":
    main()
