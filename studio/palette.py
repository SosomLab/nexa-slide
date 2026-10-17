# -*- coding: utf-8 -*-
"""팔레트 파생(순수 함수) - 색 5개(primary · surface · on-surface · accent1 · accent2)로 템플릿 토큰의 역할 색을 만든다.

    python3 studio/palette.py "#0F5257" "#FFFFFF" "#1C2324" "#263238" "#5D4037"     # 파생 결과와 대비 경고를 JSON 으로

회사 템플릿 만들기 마법사(hub.create_template · home.html)와 CLI 가 같이 쓴다. 서버·작업 공간에 의존하지 않는다(import 만으로 아무것도 읽지 않는다).
규칙(docs/dev/template-wizard-design.md 3-1):
  - container = 그 색을 surface 쪽으로 85% 섞은 것(어두운 바탕이면 75% - 어두운 바탕에서는 더 진하게 남겨야 구분된다)
  - on-색 = 흑/백 중 대비(WCAG)가 큰 쪽. 4.5:1 미만이면 경고(warnings)로 알린다 - 값은 그대로 두고 사용자가 "고급"에서 고친다
  - on-*-container = 그 색을 on-surface 쪽으로 60% 섞은 진한 색(바탕 글자색 톤), 대비가 모자라면 on-surface
  - day3 = primary 와 accent2 의 중간
  - surface-dim · surface-container(-high) = surface 를 on-surface 쪽으로 4·6·10% / outline-variant 는 on-surface 를 surface 쪽으로 78%
  - panel(어두운 띠) = on-surface, on-panel = surface (어두운 바탕이면 surface-container-high / on-surface)
WCAG 상대 휘도·대비 공식은 check_layout.py 가 여기 것을 쓴다(한 곳에만).
"""
import json
import re
import sys

MIN_CONTRAST = 4.5  # WCAG AA 본문 글자
INPUT_KEYS = ("primary", "surface", "on-surface", "accent1", "accent2")
# 파생되는 역할 - 이 순서대로 결과를 돌려준다(화면의 "고급" 목록 순서)
DERIVED_KEYS = ("primary", "on-primary", "primary-container", "on-primary-container",
                "surface", "surface-dim", "surface-container", "surface-container-high", "on-surface", "on-surface-variant", "outline-variant",
                "panel", "on-panel",
                "day1", "day1-container", "on-day1-container", "day2", "day2-container", "on-day2-container", "day3", "day3-container", "on-day3-container")
# 대비를 확인할 (글자, 바탕) 짝
CONTRAST_PAIRS = (("on-primary", "primary"), ("on-surface", "surface"), ("on-surface-variant", "surface"), ("on-panel", "panel"),
                  ("on-primary-container", "primary-container"), ("on-day1-container", "day1-container"), ("on-day2-container", "day2-container"),
                  ("on-day3-container", "day3-container"))


def norm_hex(v):
    """'#abc' · 'ABCDEF' · '#AABBCC' → '#AABBCC'. 색이 아니면 None."""
    if not isinstance(v, str):
        return None
    s = v.strip().lstrip("#")
    if re.fullmatch(r"[0-9A-Fa-f]{3}", s):
        s = "".join(c * 2 for c in s)
    if not re.fullmatch(r"[0-9A-Fa-f]{6}", s):
        return None
    return "#" + s.upper()


def rgb(hexv):
    h = norm_hex(hexv)
    if h is None:
        raise ValueError(f"색이 아니다: {hexv!r}")
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def to_hex(r, g, b):
    return "#%02X%02X%02X" % tuple(max(0, min(255, int(round(x)))) for x in (r, g, b))


def lum(hexv):
    """상대 휘도(WCAG 2.x) - #RRGGBB. 색이 아니면 None."""
    h = norm_hex(hexv)
    if h is None:
        return None
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4  # noqa: E731
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def contrast(a, b):
    """두 색의 대비(1~21). 둘 중 하나가 색이 아니면 None."""
    la, lb = lum(a), lum(b)
    if la is None or lb is None:
        return None
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def mix(a, b, t):
    """a 에서 b 쪽으로 t(0~1) 만큼 - t=0 이면 a, 1 이면 b."""
    ra, rb = rgb(a), rgb(b)
    t = max(0.0, min(1.0, float(t)))
    return to_hex(*(x + (y - x) * t for x, y in zip(ra, rb)))


def is_dark(hexv):
    """어두운 바탕인가(휘도 0.5 미만 → 글자는 밝게)."""
    return (lum(hexv) or 0) < 0.5


def on_color(bg, dark="#000000", light="#FFFFFF"):
    """bg 위에 놓을 글자색 - 흑/백 중 대비가 큰 쪽."""
    return light if contrast(light, bg) >= contrast(dark, bg) else dark


def _on_container(role_color, container, on_surface):
    """container 위 글자 - 역할 색을 on-surface 쪽으로 60% 섞은 진한 색. 대비가 모자라면 on-surface, 그래도 모자라면 흑/백."""
    cand = mix(role_color, on_surface, 0.6)
    for c in (cand, on_surface, on_color(container)):
        if contrast(c, container) >= MIN_CONTRAST:
            return c
    return cand


def derive(colors):
    """{primary, surface, on-surface, accent1, accent2} (+ 이미 정한 파생값 - 그대로 둔다) → DERIVED_KEYS 전부.
    잘못된 색은 ValueError. 돌려주는 값은 모두 '#RRGGBB'."""
    src = {k: norm_hex(colors.get(k)) for k in INPUT_KEYS}
    missing = [k for k, v in src.items() if v is None]
    if missing:
        raise ValueError("색이 아니거나 비었다: " + ", ".join(missing))
    p, s, on_s, a1, a2 = (src[k] for k in INPUT_KEYS)
    dark = is_dark(s)
    ct = 0.75 if dark else 0.85  # container 가 surface 쪽으로 가는 비율
    out = {"primary": p, "surface": s, "on-surface": on_s, "day1": a1, "day2": a2, "day3": mix(p, a2, 0.5)}
    out["on-primary"] = on_color(p)
    out["primary-container"] = mix(p, s, ct)
    out["on-primary-container"] = _on_container(p, out["primary-container"], on_s)
    out["surface-dim"] = mix(s, on_s, 0.04)
    out["surface-container"] = mix(s, on_s, 0.06)
    out["surface-container-high"] = mix(s, on_s, 0.10)
    # 보조 글자색 - on-surface 를 surface 쪽으로 25% 섞되 대비 4.5 가 되는 데까지만 옅게
    t = 0.25
    while t > 0 and contrast(mix(on_s, s, t), s) < MIN_CONTRAST:
        t = round(t - 0.05, 2)
    out["on-surface-variant"] = mix(on_s, s, t)
    out["outline-variant"] = mix(on_s, s, 0.78)
    if dark:
        out["panel"], out["on-panel"] = out["surface-container-high"], on_s
    else:
        out["panel"], out["on-panel"] = on_s, s
    for k in ("day1", "day2", "day3"):
        out[f"{k}-container"] = mix(out[k], s, ct)
        out[f"on-{k}-container"] = _on_container(out[k], out[f"{k}-container"], on_s)
    for k, v in (colors or {}).items():  # 사용자가 "고급"에서 정한 파생값은 그대로(입력 5색은 위에서 정규화됨)
        if k in DERIVED_KEYS and k not in INPUT_KEYS and norm_hex(v):
            out[k] = norm_hex(v)
    return {k: out[k] for k in DERIVED_KEYS}


def warnings(colors):
    """대비 경고 - CONTRAST_PAIRS 중 MIN_CONTRAST 미만인 짝 [{fg, bg, ratio}]. 색이 빠진 짝은 건너뛴다."""
    out = []
    for fg, bg in CONTRAST_PAIRS:
        r = contrast(colors.get(fg), colors.get(bg)) if colors.get(fg) and colors.get(bg) else None
        if r is not None and r < MIN_CONTRAST:
            out.append({"fg": fg, "bg": bg, "ratio": round(r, 2)})
    return out


def build(colors):
    """마법사 한 번 호출 - {colors: 파생 전부, warnings: [...]}."""
    d = derive(colors)
    return {"colors": d, "warnings": warnings(d)}


def main(argv):
    if len(argv) != 5:
        sys.exit(__doc__)
    print(json.dumps(build(dict(zip(INPUT_KEYS, argv))), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main(sys.argv[1:])
