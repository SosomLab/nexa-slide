// 편집기 공용 뼈대 - 슬라이드(studio.js)·시트(sheet.js)·페이지(page.js)가 같이 쓰는 화면 도우미(docs/dev/page-editor/design.md 4-1).
//   NexaShell.create(opts) → { api, toast, setStatus, banner, closeMenu, openMenu }
//   화면 요소는 id 로 찾는다(세 화면이 같은 id 를 쓴다): #toast · #status · #banner · #bannerMsg. 팝업 메뉴는 body 에 .menu 로 붙인다.
//   opts: base(허브 중계 경로 접두) · tab(창 식별자 - X-Nexa-Tab) · esc(글 → HTML) ·
//         cache(fetch cache 값, 없으면 브라우저 기본) · guard(method, url) → 응답 객체를 돌려주면 요청을 보내지 않는다(미리 보기 등) ·
//         toastMs(기본 표시 시간) · toastBottom() → 토스트 아래 여백 CSS 값(다른 바와 겹치지 않게, "" = 기본 자리) ·
//         menuId(메뉴 요소 기본 id) · menuKeepFocus(메뉴를 눌러도 입력칸 초점을 뺏지 않는다) · menuFlipGap(화면 아래에 걸려 위로 뒤집을 때 좌표 기준 메뉴의 간격)
(function (root) {
  "use strict";
  function create(opts = {}) {
    const $ = (s) => document.querySelector(s);
    const esc = opts.esc || ((s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]));
    const base = opts.base || "";

    /** 서버 요청 → { ok, status, data, headers }. JSON 본문은 body 로(undefined 면 본문 없음) */
    async function api(method, url, body) {
      if (opts.guard) { const g = opts.guard(method, url); if (g) return g; }
      const headers = { "X-Nexa-Tab": opts.tab }; if (body !== undefined) headers["Content-Type"] = "application/json";
      const init = { method, headers, body: body !== undefined ? JSON.stringify(body) : undefined };
      if (opts.cache) init.cache = opts.cache;
      const r = await fetch(base + url, init);
      let data = null;
      try { data = await r.json(); } catch (e) { /* 빈 응답 */ }
      if (root.NexaMenu && root.NexaMenu.auth401) root.NexaMenu.auth401(r, data);  // 허브 로그인이 끊겼으면 로그인 페이지로(허브 중계로 열었을 때)
      return { ok: r.ok, status: r.status, data, headers: r.headers };
    }

    let toastT = 0;
    function toast(msg, ms = opts.toastMs || 2200) {
      const t = $("#toast"); t.textContent = msg; t.classList.add("show");
      if (opts.toastBottom) t.style.bottom = opts.toastBottom();
      clearTimeout(toastT); toastT = setTimeout(() => t.classList.remove("show"), ms);
    }
    function setStatus(kind, text) { const s = $("#status"); s.className = "chip sm " + kind; s.textContent = text; }
    function banner(on, msg) { $("#banner").classList.toggle("show", !!on); if (msg) $("#bannerMsg").textContent = msg; }

    function closeMenu() { document.querySelectorAll(".menu").forEach((m) => m.remove()); }
    /** items: [{label, key, icon, act, disabled, on, keep}] | "-" | {h: "제목"} | {html, bind(el, menu)} - anchor 요소 아래(또는 {x, y}). o: {id, right} */
    function openMenu(anchor, items, o = {}) {
      closeMenu();
      const m = document.createElement("div"); m.className = "menu";
      const id = o.id || opts.menuId; if (id) m.id = id;
      m.innerHTML = items.map((it, i) => it === "-" ? "<hr>" : it.h ? `<div class="h">${esc(it.h)}</div>` : it.html ? `<div data-i="${i}">${it.html}</div>`
        : `<button data-i="${i}" ${it.disabled ? "disabled" : ""}>${it.on ? "✓ " : ""}${it.icon ? `<span>${it.icon}</span>` : ""}<span>${esc(it.label)}</span>${it.key ? `<span class="k">${esc(it.key)}</span>` : ""}</button>`).join("");
      document.body.appendChild(m);
      const rect = anchor && anchor.getBoundingClientRect ? anchor.getBoundingClientRect() : null;
      let x, y;
      if (rect) { x = o.right ? rect.right - m.offsetWidth : rect.left; y = rect.bottom + 4; } else { x = anchor.x; y = anchor.y; }
      x = Math.max(6, Math.min(x, innerWidth - m.offsetWidth - 6));
      if (y + m.offsetHeight > innerHeight - 6) y = Math.max(6, (rect ? rect.top - 4 : y - (opts.menuFlipGap || 0)) - m.offsetHeight);  // 아래에 자리가 없으면 위로
      m.style.left = x + "px"; m.style.top = y + "px";
      if (opts.menuKeepFocus) m.addEventListener("mousedown", (e) => e.preventDefault());
      m.addEventListener("click", (e) => {
        const b = e.target.closest("button[data-i]"); if (!b || b.disabled) return;
        const it = items[+b.dataset.i]; if (!it.keep) closeMenu(); it.act && it.act();
      });
      items.forEach((it, i) => it.bind && it.bind(m.querySelector(`[data-i="${i}"]`), m));
      return m;
    }
    return { api, toast, setStatus, banner, closeMenu, openMenu };
  }
  root.NexaShell = { create };
})(typeof window !== "undefined" ? window : globalThis);
