/* nexa-slide 실시간 - 동시 편집 2단계(docs/collab.md). 편집기(studio.js)와 시트 화면(sheet.js)이 같이 쓴다.
     탭당 SSE 하나(GET /api/stream/<덱>) - event: version(/api/version 과 같은 내용, 바뀔 때만) · presence(함께 보는 사람) · ping(10초)
     함께 보는 사람 보내기(POST /api/presence/<덱>) - 어디를 보고 고치는지(where)를 바뀔 때·7초마다, 닫을 때 leave
   쓰는 쪽:
     const LIVE = NexaLive.create({ api, base, deckId: () => id, tab, onVersion(v), onPresence(others), chip: "#liveChip" 넣을 자리 앞 요소 })
     LIVE.where(where, editing)   지금 선택(슬라이드 {slide, els} · 시트 {tab, range}) - 바뀌면 곧 보낸다
     LIVE.healthy()               SSE 가 살아 있으면 true - 그동안 2초 폴링은 쉬고 15초 안전망만
     LIVE.others()                다른 탭들 [{tab, user, color, where, editing}]
     LIVE.reconnect()             덱이 바뀌었을 때(편집기 덱 탭 전환) */
(function () {
  "use strict";
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  function create(o) {
    const BASE = o.base || "";
    let src = null, lastAt = 0, others = [], myWhere = {}, myEditing = false, sentKey = "", sendT = 0, beatT = 0, deck = null;
    const id = () => o.deckId();
    function connect() {
      if (src) { src.close(); src = null; }
      deck = id(); if (!deck || !window.EventSource) return;
      try { src = new EventSource(`${BASE}/api/stream/${encodeURIComponent(deck)}?tab=${encodeURIComponent(o.tab)}`); } catch (e) { src = null; return; }
      src.addEventListener("version", (e) => { lastAt = Date.now(); try { o.onVersion && o.onVersion(JSON.parse(e.data)); } catch (er) { /* 다음 이벤트·폴링에서 */ } });
      src.addEventListener("presence", (e) => { lastAt = Date.now(); try { others = (JSON.parse(e.data).list || []).filter((x) => x.tab !== o.tab); renderChip(); o.onPresence && o.onPresence(others); } catch (er) { /* 무시 */ } });
      src.addEventListener("ping", () => { lastAt = Date.now(); });
      src.onopen = () => { lastAt = Date.now(); sentKey = ""; push(); };  // 다시 붙으면 내 위치를 다시 알린다(서버는 끊길 때 지웠다)
      src.onerror = () => { /* EventSource 가 retry 로 다시 붙는다 - 그동안 healthy() 가 false 가 되어 폴링이 돈다 */ };
    }
    /** 내 위치 보내기 - 바뀌었으면 곧, 아니면 7초마다(서버 15초 TTL) */
    function push(force) {
      if (!deck) return;
      const key = JSON.stringify([myWhere, myEditing]);
      if (!force && key === sentKey) return;
      sentKey = key;
      o.api("POST", `/api/presence/${encodeURIComponent(deck)}`, { tab: o.tab, where: myWhere, editing: myEditing }).catch(() => { sentKey = ""; });
    }
    function where(w, editing) {
      myWhere = w || {}; myEditing = !!editing;
      clearTimeout(sendT); sendT = setTimeout(() => push(), 250);
    }
    function beat() { clearInterval(beatT); beatT = setInterval(() => { if (!document.hidden) push(true); }, 7000); }
    // 함께 보는 사람 칩 - 머리줄 세션 칩 앞에. 이름(없으면 "다른 창")·색 점, 누르면 그 사람이 보는 곳으로(쓰는 쪽 onGoto)
    function renderChip() {
      const anchor = o.chip && document.querySelector(o.chip); if (!anchor) return;
      let c = document.querySelector("#liveChip");
      if (!c) { c = document.createElement("span"); c.id = "liveChip"; c.className = "chip sm"; c.style.cssText = "gap:4px;cursor:default"; anchor.parentNode.insertBefore(c, anchor); }
      c.hidden = !others.length;
      const name = (x) => x.user || "다른 창";
      c.innerHTML = others.slice(0, 5).map((x) => `<span title="${esc(name(x))}${x.editing ? " · 편집 중" : ""}" style="display:inline-block;width:9px;height:9px;border-radius:50%;background:${esc(x.color)}"></span>`).join("")
        + `<span>함께 ${others.length}</span>`;
      c.title = "같은 문서를 보고 있는 창: " + others.map((x) => `${name(x)}${x.editing ? "(편집 중)" : ""}`).join(", ");
    }
    window.addEventListener("pagehide", () => { if (deck && navigator.sendBeacon) navigator.sendBeacon(`${BASE}/api/presence/${encodeURIComponent(deck)}`, new Blob([JSON.stringify({ tab: o.tab, leave: true })], { type: "application/json" })); });
    document.addEventListener("visibilitychange", () => { if (!document.hidden) push(true); });
    connect(); beat();
    return {
      where, healthy: () => !!src && Date.now() - lastAt < 25000, others: () => others,
      reconnect() { others = []; renderChip(); sentKey = ""; connect(); },
    };
  }
  window.NexaLive = { create };
})();
