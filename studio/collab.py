# -*- coding: utf-8 -*-
"""동시 편집 2단계(docs/collab.md) - 함께 보는 사람(presence). 서버 메모리에만 두고 파일에 쓰지 않는다.

    PRESENCE.update(deck, tab, info)   이 탭이 어디를 보고 고치는지 - info = {user, where, editing}. 색은 탭에서 정한다
    PRESENCE.leave(deck, tab)          탭을 닫음(실시간 연결이 끊김)
    PRESENCE.snapshot(deck)            지금 함께 보는 탭 목록(TTL 초 소식이 없으면 빠진다)
    PRESENCE.version(deck)             목록이 바뀔 때마다 오르는 수 - 실시간 연결(/api/stream)이 바뀌었을 때만 보낸다

where 는 화면이 정한다: 슬라이드 {slide, els:[요소 id]} · 시트 {tab, range}. 서버는 내용을 보지 않고 그대로 나른다."""
import hashlib
import threading
import time

TTL = 15  # 초 - 이만큼 소식이 없으면 함께 보는 사람에서 뺀다(탭이 잠들거나 네트워크가 끊김)
COLORS = ["#E5484D", "#0B7A75", "#7C3AED", "#D97706", "#2563EB", "#BE185D", "#15803D", "#9333EA"]


def color_of(tab):
    """탭마다 같은 색 - 다른 사람 화면에 그 탭의 선택 테두리·이름표 색"""
    return COLORS[int(hashlib.sha1(str(tab).encode("utf-8")).hexdigest(), 16) % len(COLORS)]


class Presence:
    def __init__(self, ttl=TTL):
        self.ttl, self._lock, self._d, self._ver = ttl, threading.Lock(), {}, {}

    def _bump(self, deck):
        self._ver[deck] = self._ver.get(deck, 0) + 1

    def _prune(self, deck, now):
        d = self._d.get(deck) or {}
        old = [t for t, x in d.items() if now - x["t"] > self.ttl]
        for t in old:
            del d[t]
        if old:
            self._bump(deck)

    def update(self, deck, tab, info):
        if not tab:
            return
        now = time.time()
        with self._lock:
            d = self._d.setdefault(deck, {})
            prev = d.get(tab)
            cur = {"tab": tab, "user": str(info.get("user") or "")[:40], "color": color_of(tab),
                   "where": info.get("where") if isinstance(info.get("where"), dict) else {}, "editing": bool(info.get("editing")), "t": now}
            changed = not prev or any(prev.get(k) != cur[k] for k in ("user", "where", "editing"))
            d[tab] = cur
            if changed:
                self._bump(deck)

    def leave(self, deck, tab):
        with self._lock:
            if tab and tab in (self._d.get(deck) or {}):
                del self._d[deck][tab]
                self._bump(deck)

    def snapshot(self, deck):
        now = time.time()
        with self._lock:
            self._prune(deck, now)
            return [{k: v for k, v in x.items() if k != "t"} for x in (self._d.get(deck) or {}).values()]

    def version(self, deck):
        with self._lock:
            self._prune(deck, time.time())
            return self._ver.get(deck, 0)


PRESENCE = Presence()
