# -*- coding: utf-8 -*-
"""템플릿 고르기 — 디자인(색·글꼴·크기·검사 기준)은 엔진 templates/<이름>/ 에 있고, 작업 공간은 이름만 고른다(docs/templates.md).

    python3 nexa.py set_template                 # 고를 수 있는 템플릿 목록(이름·설명)과 현재 선택
    python3 nexa.py set_template keynote         # nexa-slide.json 의 "template" 을 바꾼다
    python3 nexa.py set_template --json          # 목록을 JSON 으로

고른 이름은 작업 공간 nexa-slide.json 의 "template" 에 저장된다(템플릿 파일은 바꾸지 않는다).
바꾼 뒤: ① 서버를 다시 시작해야 토큰·검사 기준이 바뀐다(python3 nexa.py restart — 웹 세션은 서버가 띄운 것이라 세션 안에서 재시작하지 말고
사용자에게 안내한다) ② 글자 크기 하한(sizes)은 빌드 때 적용 → build_deck <덱> --force ③ PPTX 는 다시 내보낸다.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CONFIG_NAME, LOCAL_NAME, TEMPLATE, TEMPLATES, WORKSPACE, load_template, read_config  # noqa: E402


def templates():
    """[{name, label, description, hidden, replacedBy}] — 폴더 순. 숨긴 것도 돌려주되 hidden 으로 표시한다."""
    out = []
    for p in sorted(TEMPLATES.iterdir()):
        if not (p / "template.json").is_file():
            continue
        t = load_template(p.name)  # extends 를 합친 label·description
        out.append({"name": p.name, "label": t.get("label", p.name), "description": t.get("description", ""),
                    "hidden": bool(t.get("hidden")), "replacedBy": t.get("replacedBy")})
    return out


def main():
    args = [a for a in sys.argv[1:] if a != "--json"]
    as_json = "--json" in sys.argv[1:]
    cur = TEMPLATE["name"]
    items = templates()
    if not args:
        shown = [t for t in items if not t["hidden"] or t["name"] == cur]
        if as_json:
            print(json.dumps({"current": cur, "templates": shown}, ensure_ascii=False))
            return
        print(f"현재: {cur}  ({WORKSPACE / CONFIG_NAME})")
        for t in shown:
            mark = "*" if t["name"] == cur else " "
            print(f"{mark} {t['name']:14s} {t['label']:20s} {t['description']}")
        print("바꾸기: python3 nexa.py set_template <이름> → 서버 재시작(nexa.py restart) → build_deck <덱> --force")
        return
    name = args[0]
    found = next((t for t in items if t["name"] == name), None)
    if found is None:
        sys.exit(f"없는 템플릿: {name} — {', '.join(t['name'] for t in items if not t['hidden'])}")
    if found["hidden"] and name != cur:
        sys.exit(f"{name} 은 목록에서 뺀 템플릿이다" + (f" — 대신 {found['replacedBy']}" if found.get("replacedBy") else ""))
    shared = read_config(shared=True)  # 공유 파일에만 쓴다(PC 별 nexa-slide.local.json 값은 섞지 않는다)
    shared["template"] = name
    (WORKSPACE / CONFIG_NAME).write_text(json.dumps(shared, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"템플릿 {cur} → {name} ({WORKSPACE / CONFIG_NAME})")
    if read_config().get("template", cur) != name:
        print(f"알림: 이 PC 의 {LOCAL_NAME} 에 template 이 있어 이 PC 에서는 그 값이 쓰인다")
    print("다음: 서버를 다시 시작해야 반영된다(python3 nexa.py restart — 웹 세션 안이면 사용자에게 재시작을 안내). "
          "글자 크기 하한은 build_deck <덱> --force 로 다시 빌드할 때 적용되고, PPTX 는 다시 내보낸다.")


if __name__ == "__main__":
    main()
