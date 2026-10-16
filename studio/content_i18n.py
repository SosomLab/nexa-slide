# -*- coding: utf-8 -*-
"""견본 내용(레이아웃 견본·슬라이드 유형 예시·시작용 내용)의 언어 - 빌드 단계에서 쓴다(화면 사전과 별개).
    tr(obj, lang)        JSON 구조 안의 문자열을 studio/i18n/content.<lang>.json(원문 → 번역)으로 바꾼다. 없는 글은 그대로.
                         여러 줄 글은 통째로 없으면 줄마다 찾는다. ko 또는 사전 없음이면 그대로 돌려준다.
    content_dir(base, lang)  시작용 내용 폴더 - <base>/content.<lang> 이 있으면 그것, 없으면 <base>/content
docs/dev/i18n.md 3절. 사용자 덱 내용에는 쓰지 않는다."""
import json
import re
from pathlib import Path

I18N_DIR = Path(__file__).resolve().parent / "i18n"
SKIP_KEYS = {"src", "img", "image", "mermaid", "path", "url", "measure", "id", "layout", "css", "latin", "ea", "fill", "color", "font"}  # 경로·코드·식별자·토큰 값은 번역하지 않는다
_maps = {}
_HANGUL = re.compile(r"[가-힣]")


def load_map(lang):
    lang = (lang or "ko").lower()
    if lang in _maps:
        return _maps[lang]
    m = {}
    if lang != "ko":  # content.<lang>.json + content.<lang>.*.json(시작용 내용 등 묶음별 파일) 을 합친다
        for p in sorted(I18N_DIR.glob(f"content.{lang}*.json")):
            if p.name != f"content.{lang}.json" and not p.name.startswith(f"content.{lang}."):
                continue
            try:
                m.update({k: v for k, v in json.loads(p.read_text(encoding="utf-8")).items() if not k.startswith("_") and isinstance(v, str)})
            except (OSError, ValueError):
                continue
    _maps[lang] = m
    return m


_keys_cache = {}


def _keys(m):
    """부분 치환용 키 - 두 글자 이상·한 줄짜리, 긴 것부터(레이아웃이 라벨을 이어 붙인 글: '**누가** … · **언제까지** …'). 한글 경계로만 맞춘다."""
    k = id(m)
    if k not in _keys_cache:
        ks = sorted((x for x in m if len(x) >= 2 and "\n" not in x), key=len, reverse=True)
        _keys_cache[k] = [(re.compile(r"(?<![가-힣])" + re.escape(x) + r"(?![가-힣])"), m[x]) for x in ks]
    return _keys_cache[k]


def tr_str(s, m):
    if not isinstance(s, str) or not m or not _HANGUL.search(s):
        return s
    if s in m:
        return m[s]
    if "\n" in s:
        return "\n".join(tr_str(line, m) for line in s.split("\n"))
    for pat, v in _keys(m):  # 통째로 없으면 안에 든 표현을 긴 것부터
        if pat.search(s):
            s = pat.sub(v, s)
            if not _HANGUL.search(s):
                break
    return s


def tr(obj, lang):
    """구조(dict·list)를 깊이 따라가며 문자열만 바꾼다 - 키는 그대로. mermaid 코드·경로(src·img) 같은 값은 사전에 없으면 그대로다."""
    m = load_map(lang)
    if not m:
        return obj
    if isinstance(obj, str):
        return tr_str(obj, m)
    if isinstance(obj, list):
        return [tr(v, lang) for v in obj]
    if isinstance(obj, dict):
        return {k: (v if k in SKIP_KEYS else tr(v, lang)) for k, v in obj.items()}
    return obj


def content_dir(base, lang):
    """시작용 내용 폴더 - <base>/content.<lang> 이 있으면 그것(번역본), 없으면 <base>/content."""
    base = Path(base)
    lang = (lang or "ko").lower()
    if lang != "ko" and (base / f"content.{lang}").is_dir():
        return base / f"content.{lang}"
    return base / "content"


def langs():
    """번역이 있는 언어 - content.<lang>.json 이 있는 것."""
    return sorted(p.stem.split(".", 1)[1] for p in I18N_DIR.glob("content.*.json"))
