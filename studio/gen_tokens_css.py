# -*- coding: utf-8 -*-
"""tokens.json(단일 원본) ↔ 디자인 기준 tokens.css 값 일치 확인·생성.

대상 CSS 는 작업 공간 nexa-slide.json 의 "designCss"(작업 공간 기준 경로). 없으면 할 일이 없으므로 알리고 끝낸다.

    python3 studio/gen_tokens_css.py            # 확인만: 색·반경 값이 다르면 목록을 보이고 종료 코드 1
    python3 studio/gen_tokens_css.py --write    # tokens.css 의 --이름: 값 을 tokens.json 값으로 바꿔 쓴다(주석·배치 유지),
                                                    # tokens.css 에 없는 토큰은 :root 끝에 추가

tokens.json 에만 있는 스튜디오 전용 토큰(on-lab-container, white)은 확인 대상에서 뺀다.
"""
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
STUDIO = Path(__file__).resolve().parent
sys.path.insert(0, str(STUDIO))
from common import CONFIG, TOKENS, WORKSPACE  # noqa: E402

CSS = (WORKSPACE / CONFIG["designCss"]).resolve() if CONFIG.get("designCss") else None
STUDIO_ONLY = {"on-lab-container", "white"}
DECL = re.compile(r"--([\w-]+)\s*:\s*([^;]+);")


def expected():
    t = json.loads(TOKENS.read_text(encoding="utf-8"))
    out = {}
    for k, v in t["colors"].items():
        if k in STUDIO_ONLY:
            continue
        out[k] = f"var(--{v})" if not v.startswith("#") else v.upper()
    for k, v in t["radius"].items():
        out[k] = f"{v}px"
    return out


def main():
    if CSS is None or not CSS.is_file():
        print("designCss 가 설정되지 않았거나 파일이 없다 — nexa-slide.json 의 \"designCss\" 를 확인")
        return 0
    exp = expected()
    css = CSS.read_text(encoding="utf-8")
    have = {m.group(1): m.group(2).strip() for m in DECL.finditer(css)}
    diffs = [(k, have.get(k), v) for k, v in exp.items() if (have.get(k) or "").upper() != v.upper()]
    if "--write" in sys.argv:
        def sub(m):
            k = m.group(1)
            return f"--{k}: {exp[k]};" if k in exp else m.group(0)
        new = DECL.sub(sub, css)
        missing = [k for k in exp if k not in have]
        if missing:
            add = "\n  /* tokens.json 에서 추가 */\n" + "".join(f"  --{k}: {exp[k]};\n" for k in missing)
            new = new[: new.rindex("}")] + add + "}\n"
        CSS.write_text(new, encoding="utf-8")
        print(f"{CSS} 갱신 — 바뀐 값 {len(diffs)}개")
        return
    if diffs:
        for k, a, b in diffs:
            print(f"  --{k}: tokens.css={a}  tokens.json={b}")
        print(f"값이 다른 토큰 {len(diffs)}개 — --write 로 tokens.css 를 맞춘다")
        sys.exit(1)
    print(f"tokens.css 와 tokens.json 값 일치 ({len(exp)}개)")


if __name__ == "__main__":
    main()
