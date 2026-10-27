/* nexa-slide 기본 메뉴 - 머리줄 왼쪽 위 메뉴 단추(☰)로 여는 왼쪽 서랍(GitHub 방식).
   편집기(index.html)와 시작 페이지(home.html)가 같이 쓴다.
     NexaMenu.mount(단추)            단추를 누르면 서랍을 연다(Esc·바깥·닫기 단추로 닫힘)
     NexaMenu.icon(이름)             같은 모양의 SVG 아이콘 문자열
     NexaMenu.go(경로)               작업 공간 열기 → 그 서버 주소로 이동 */
(function () {
  const P = {
    menu: '<path d="M3 6h18M3 12h18M3 18h18"/>',
    x: '<path d="M6 6l12 12M18 6L6 18"/>',
    home: '<path d="M3 10.5L12 3l9 7.5"/><path d="M5 9v12h5v-6h4v6h5V9"/>',
    plus: '<path d="M12 5v14M5 12h14"/>',
    book: '<path d="M4 19V5a2 2 0 0 1 2-2h14v14H6a2 2 0 0 0-2 2z"/><path d="M6 21h14v-4"/>',
    play: '<circle cx="12" cy="12" r="9"/><path d="M10 8.5v7l6-3.5z"/>',
    stop: '<circle cx="12" cy="12" r="9"/><rect x="9" y="9" width="6" height="6" rx="1"/>',
    layout: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 9h18M9 9v11"/>',
    globe: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c3 3.5 3 14.5 0 18M12 3c-3 3.5-3 14.5 0 18"/>',
    pen: '<path d="M4 20h4L19 9l-4-4L4 16z"/><path d="M13.5 6.5l4 4"/>',
    folder: '<path d="M3 6.5A1.5 1.5 0 0 1 4.5 5H9l2 2h8.5A1.5 1.5 0 0 1 21 8.5v9a1.5 1.5 0 0 1-1.5 1.5h-15A1.5 1.5 0 0 1 3 17.5z"/>',
    search: '<circle cx="11" cy="11" r="6.5"/><path d="M16 16l4.5 4.5"/>',
    repo: '<path d="M5 4.5A1.5 1.5 0 0 1 6.5 3H19v15H6.5A1.5 1.5 0 0 0 5 19.5z"/><path d="M5 19.5A1.5 1.5 0 0 0 6.5 21H19v-3"/>',
    git: '<circle cx="6" cy="6" r="2"/><circle cx="6" cy="18" r="2"/><circle cx="18" cy="8" r="2"/><path d="M6 8v8M18 10c0 4-6 3-10.5 6.5"/>',
    gear: '<circle cx="12" cy="12" r="3"/><path d="M12 2.5v3M12 18.5v3M2.5 12h3M18.5 12h3M5.3 5.3l2.1 2.1M16.6 16.6l2.1 2.1M5.3 18.7l2.1-2.1M16.6 7.4l2.1-2.1"/>',
    up: '<path d="M12 19V5M6 11l6-6 6 6"/>',
    ext: '<path d="M14 4h6v6M20 4l-9 9"/><path d="M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/>',
    eye: '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
    trash: '<path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13"/>',
    user: '<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4.4 3.6-7 8-7s8 2.6 8 7"/>',
    out: '<path d="M10 4H5a1 1 0 0 0-1 1v14a1 1 0 0 0 1 1h5"/><path d="M14 8l5 4-5 4M19 12H9"/>',
  };
  const icon = (n, s = 16) => `<svg class="nx-i" width="${s}" height="${s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${P[n] || ""}</svg>`;
  const mark = (s = 32) => `<svg width="${s}" height="${s}" viewBox="0 0 32 32" aria-hidden="true"><rect width="32" height="32" rx="9" fill="var(--p, #A91F24)"/><path d="M10 23V9l12 14V9" fill="none" stroke="#fff" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

  const CSS = `
  .nx-i { flex: none; }
  .nx-menubtn { width: 32px; height: 32px; border: 1px solid var(--line, #D8C2C0); background: var(--card, #fff); border-radius: 8px; display: inline-flex; align-items: center; justify-content: center; padding: 0; color: var(--ink2, #534343); cursor: pointer; }
  .nx-menubtn:hover { background: var(--tone, #F2EFEF); color: var(--ink, #1F1B1B); }
  .nx-back { position: fixed; inset: 0; background: rgba(0,0,0,.32); z-index: 1000; opacity: 0; transition: opacity .15s; }
  .nx-drawer { position: fixed; left: 0; top: 0; bottom: 0; width: min(320px, 88vw); background: var(--card, #fff); z-index: 1001; box-shadow: 0 8px 32px rgba(0,0,0,.24);
    border-radius: 0 14px 14px 0; display: flex; flex-direction: column; transform: translateX(-104%); transition: transform .18s ease; font: 14px/1.45 var(--font, "Malgun Gothic", sans-serif); color: var(--ink, #1F1B1B); }
  .nx-open .nx-back { opacity: 1; } .nx-open .nx-drawer { transform: none; }
  .nx-dh { display: flex; align-items: center; justify-content: space-between; padding: 16px 16px 8px; }
  .nx-dh a { display: inline-flex; border-radius: 9px; }
  .nx-close { width: 32px; height: 32px; border: 1px solid var(--line, #D8C2C0); background: none; border-radius: 8px; display: inline-flex; align-items: center; justify-content: center; color: var(--ink2, #534343); cursor: pointer; position: relative; }
  .nx-close:hover { background: var(--tone, #F2EFEF); }
  .nx-close:hover::after { content: attr(aria-label); position: absolute; top: 38px; right: 0; background: #1F1B1B; color: #fff; font-size: 12px; padding: 4px 8px; border-radius: 6px; white-space: nowrap; }
  .nx-body { overflow-y: auto; padding: 4px 8px 16px; flex: 1; }
  .nx-item { display: flex; align-items: center; gap: 10px; padding: 7px 10px; border-radius: 8px; color: inherit; text-decoration: none; cursor: pointer; border: 0; background: none; width: 100%; text-align: left; font: inherit; }
  .nx-item:hover { background: var(--tone, #F2EFEF); }
  .nx-item.on { background: var(--pc, #FFDAD6); color: var(--onpc, #410004); font-weight: 700; }
  .nx-item .nx-i { color: var(--ink2, #534343); }
  .nx-item small { margin-left: auto; color: var(--ink2, #534343); font-size: 11px; }
  .nx-sep { height: 1px; background: var(--line, #D8C2C0); margin: 8px 6px; opacity: .7; }
  .nx-sec { display: flex; align-items: center; justify-content: space-between; padding: 6px 10px 4px; font-size: 12px; font-weight: 700; color: var(--ink2, #534343); }
  .nx-sec button { border: 0; background: none; border-radius: 6px; width: 26px; height: 26px; display: inline-flex; align-items: center; justify-content: center; color: inherit; cursor: pointer; }
  .nx-sec button:hover { background: var(--tone, #F2EFEF); }
  .nx-find { margin: 2px 8px 6px; display: none; }
  .nx-find.on { display: block; }
  .nx-find input { width: 100%; box-sizing: border-box; border: 1px solid var(--line, #D8C2C0); border-radius: 8px; padding: 6px 10px; font: inherit; }
  .nx-av { width: 20px; height: 20px; border-radius: 50%; flex: none; display: inline-flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 700; color: #fff; }
  .nx-rt { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .nx-empty { padding: 6px 10px; color: var(--ink2, #534343); font-size: 12px; }
  .nx-menubtn { position: relative; }
  .nx-dot { position: absolute; top: -5px; right: -5px; min-width: 16px; height: 16px; border-radius: 999px; background: var(--p, #A91F24); color: #fff; font: 700 10px/16px var(--font, sans-serif); padding: 0 4px; box-sizing: border-box; text-align: center; pointer-events: none; }
  .nx-toast a { color: #fff; text-decoration: underline; margin-left: 8px; }
  .nx-toast.nx-reload { display: flex; align-items: center; gap: 10px; bottom: 20px; }
  .nx-toast.nx-reload button { font: inherit; border: 0; border-radius: 8px; padding: 4px 12px; cursor: pointer; }
  .nx-toast.nx-reload .nx-go { background: var(--p, #A91F24); color: #fff; font-weight: 700; }
  .nx-toast.nx-reload .nx-x { background: transparent; color: #fff; padding: 4px 6px; }
  .nx-badge { background: var(--p, #A91F24) !important; color: #fff !important; border-radius: 999px; padding: 0 7px; font-weight: 700; line-height: 18px; }
  .nx-lang { display: none; margin: 0 0 4px 0; padding: 4px 0 4px 22px; }
  .nx-lang.on { display: block; }
  .nx-lang .nx-item { padding: 5px 10px; gap: 6px; }
  .nx-lang .nx-ck { width: 16px; text-align: center; color: var(--p, #A91F24); font-weight: 700; flex: none; }
  .nx-lang .nx-item.sel { font-weight: 700; }
  .nx-toast { position: fixed; left: 50%; bottom: 28px; transform: translateX(-50%); background: #1F1B1B; color: #fff; padding: 9px 16px; border-radius: 10px; z-index: 1100; font: 13px var(--font, sans-serif); max-width: 80vw; }`;

  let root = null, home = null, finding = false, langOpen = false;
  // 허브 중계(/w/<id>/…)로 열린 Studio 면 그 접두 - 이 작업 공간의 것(Studio·/api/home)에만 붙인다. 홈·새로 만들기·열기는 허브(접두 없음)로 간다.
  const BASE = (location.pathname.match(/^\/w\/[^/]+/) || [""])[0];
  const here = () => { const p = location.pathname.slice(BASE.length); return p.endsWith("/home.html") ? (location.hash.slice(1) || "start") : p.startsWith("/review/slides") ? "review-slides" : p.startsWith("/review") ? "review" : p.startsWith("/studio") ? "studio" : ""; };
  const color = (s) => { let h = 0; for (const c of s) h = (h * 31 + c.charCodeAt(0)) >>> 0; return `hsl(${h % 360} 45% 45%)`; };

  function toast(msg, ms = 3200) {
    const t = document.createElement("div"); t.className = "nx-toast"; t.textContent = msg; document.body.appendChild(t);
    setTimeout(() => t.remove(), ms);
  }
  /** 허브 로그인이 없거나 끊겼으면(401 {"error":"login"}) 로그인 페이지로 - 돌아올 주소를 next 에 담는다. 보냈으면 true. */
  function auth401(r, d) {
    if (r.status !== 401 || !d || d.error !== "login") return false;
    location.href = (d.login || "/login") + "?next=" + encodeURIComponent(location.pathname + location.search + location.hash);
    return true;
  }
  async function post(url, body) {
    const r = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    let d = null; try { d = await r.json(); } catch (_) { /* 응답 없음 */ }
    auth401(r, d);
    return { ok: r.ok && d && d.ok !== false, status: r.status, data: d || {} };
  }
  async function logout() {
    await post("/api/auth/logout", {});
    location.href = "/login";
  }
  /** 작업 공간 열기 - 그 작업 공간 서버(포트가 다를 수 있다)를 띄우고 그 주소로 간다. */
  async function go(path) {
    toast("작업 공간을 여는 중...", 6000);
    const r = await post("/api/project", { action: "open", path });
    if (r.ok) { location.href = r.data.url; return r; }
    if (r.data.needInit && location.pathname.endsWith("/home.html")) { location.hash = "start"; window.dispatchEvent(new CustomEvent("nx-need-init", { detail: r.data })); }
    toast(r.data.error || "열지 못했습니다", 5000);
    return r;
  }

  // 표시 언어(i18n.js) - 누르면 아래에 목록(시스템 기본 · English · 한국어)이 펼쳐지고 고르면 즉시 바뀐다
  function langItems() {
    const I = window.I18N; if (!I) return "";
    const cur = I.lang(), opts = I.options(), now = opts.find((o) => o.value === cur) || opts[0];
    return `<button type="button" class="nx-item" data-langbtn aria-expanded="${langOpen}">${icon("globe")}<span>표시 언어</span><small>${esc(now.label)}</small></button>
      <div class="nx-lang${langOpen ? " on" : ""}" role="listbox">${opts.map((o) => `<button type="button" class="nx-item${o.value === cur ? " sel" : ""}" role="option" aria-selected="${o.value === cur}" data-lang="${o.value}"><span class="nx-ck">${o.value === cur ? "✓" : ""}</span><span>${esc(o.label)}</span></button>`).join("")}</div>`;
  }
  function items() {
    const cur = here();
    const it = (id, ic, label, href, extra = "") => `<a class="nx-item${cur === id ? " on" : ""}" href="${href}">${icon(ic)}<span>${label}</span>${extra}</a>`;
    const ws = home && home.current && home.current.workspace ? home.current : null;
    return [
      it("start", "home", "홈", "/studio/home.html#start"),
      it("new", "plus", "새 슬라이드 만들기", "/studio/home.html#new"),
      it("open", "folder", "폴더·저장소 열기", "/studio/home.html#open"),
      ws ? it("studio", "pen", "Studio", `${BASE}/studio/`, `<small>${esc(ws.title)}</small>`) : "",
      '<div class="nx-sep"></div>',
      it("tutorial", "book", "튜토리얼", "/studio/home.html#tutorial"),
      it("demo", "play", "데모", "/studio/home.html#demo"),
      it("templates", "layout", "템플릿", "/studio/home.html#templates"),
      it("samples", "globe", "샘플 둘러보기", "/studio/home.html#samples"),
      it("review", "search", "템플릿 검토", "/review"),
      it("review-slides", "layout", "슬라이드 유형 검토", "/review/slides"),
      '<div class="nx-sep"></div>',
      `<div class="nx-sec"><span>최근 작업</span><button type="button" data-find title="최근 작업 찾기">${icon("search", 15)}</button></div>`,
      `<div class="nx-find${finding ? " on" : ""}"><input type="search" placeholder="이름·경로로 찾기" data-q></div>`,
      '<div data-recent></div>',
      '<div class="nx-sep"></div>',
      it("settings", "gear", "기준 폴더 설정", "/studio/home.html#settings"),
      ...(home && home.engineWork ? [it("engine", "git", "서버 작업", "/studio/home.html#start",  // 허브 - 엔진 요청 큐. 승인 대기(관리자) 또는 세션이 꺼진 채 대기가 있으면 배지
        (NOTICE.admin && NOTICE.triage) ? `<small class="nx-badge" title="승인 대기 ${NOTICE.triage}건">${NOTICE.triage}</small>`
          : home.engineWork.pending && home.engineWork.sessionOff ? `<small class="nx-badge" title="처리 대기 ${home.engineWork.pending}건 · 엔진 세션 꺼짐${home.engineWork.startRequest ? " · 시작 요청됨" : ""}">${home.engineWork.pending}</small>` : "")] : []),
      langItems(),
      ...(home && home.user ? [  // 허브 로그인 사용자 - 계정(비밀번호 · 관리자면 사용자 관리) · 로그아웃
        it("account", "user", home.user.role === "admin" ? "계정 · 사용자 관리" : "계정", "/account", `<small>${esc(home.user.id)}</small>`),
        `<button type="button" class="nx-item" data-logout>${icon("out")}<span>로그아웃</span></button>`] : []),
    ].join("");
  }
  function renderRecent(q = "") {
    const box = root && root.querySelector("[data-recent]"); if (!box) return;
    const list = ((home && home.recent) || []).filter((r) => !q || `${r.title} ${r.path}`.toLowerCase().includes(q.toLowerCase()));
    box.innerHTML = list.length ? list.slice(0, 12).map((r) => `<button type="button" class="nx-item" data-path="${esc(r.path)}" title="${esc(r.path)}${r.exists ? "" : " (폴더 없음)"}">
        <span class="nx-av" style="background:${color(r.path)}">${esc((r.title || "?").trim().charAt(0).toUpperCase())}</span>
        <span class="nx-rt"${r.exists ? "" : ' style="opacity:.5;text-decoration:line-through"'}>${esc(r.title || r.path)}</span></button>`).join("")
      : `<div class="nx-empty">${q ? "찾는 작업이 없습니다" : "아직 연 작업이 없습니다"}</div>`;
  }
  async function load() {
    try { const r = await fetch(BASE + "/api/home", { cache: "no-store" }); home = await r.json(); if (auth401(r, home)) return; } catch (_) { home = null; }
    if (root) { root.querySelector(".nx-body").innerHTML = items(); renderRecent(); }
  }
  function build() {
    const st = document.createElement("style"); st.textContent = CSS; document.head.appendChild(st);
    root = document.createElement("div");
    root.innerHTML = `<div class="nx-back"></div><aside class="nx-drawer" role="dialog" aria-label="기본 메뉴">
      <div class="nx-dh"><a href="/studio/home.html#start" title="nexa-slide 홈">${mark(32)}</a>
        <button type="button" class="nx-close" aria-label="메뉴 닫기">${icon("x")}</button></div>
      <nav class="nx-body">${items()}</nav></aside>`;
    root.style.display = "none";
    document.body.appendChild(root);
    root.querySelector(".nx-back").onclick = close;
    root.querySelector(".nx-close").onclick = close;
    root.addEventListener("click", (e) => {
      const f = e.target.closest("[data-find]");
      if (f) { finding = !finding; root.querySelector(".nx-find").classList.toggle("on", finding); if (finding) root.querySelector("[data-q]").focus(); return; }
      const r = e.target.closest("[data-path]");
      if (r) { close(); go(r.dataset.path); return; }
      if (e.target.closest("[data-logout]")) { close(); logout(); return; }
      if (e.target.closest("[data-langbtn]")) { langOpen = !langOpen; root.querySelector(".nx-body").innerHTML = items(); renderRecent(); return; }
      const lg = e.target.closest("[data-lang]");
      if (lg) { langOpen = false; window.I18N.set(lg.dataset.lang); root.querySelector(".nx-body").innerHTML = items(); renderRecent(); return; }
      if (e.target.closest("a.nx-item")) setTimeout(close, 0);
    });
    root.addEventListener("input", (e) => { if (e.target.matches("[data-q]")) renderRecent(e.target.value); });
    document.addEventListener("keydown", (e) => { if (e.key === "Escape" && root.classList.contains("nx-open")) { e.stopPropagation(); close(); } }, true);
  }
  function open() {
    if (!root) build();
    root.style.display = ""; root.querySelector(".nx-body").innerHTML = items(); renderRecent();
    requestAnimationFrame(() => root.classList.add("nx-open"));
    root.querySelector(".nx-close").focus();
    load();
  }
  function close() {
    if (!root) return;
    root.classList.remove("nx-open");
    setTimeout(() => { if (!root.classList.contains("nx-open")) root.style.display = "none"; }, 200);
  }
  // ---------- 승인 대기 알림 - 허브 관리자에게(작업 공간 세션이 넘긴 엔진 요청은 승인해야 처리된다) ----------
  const NOTICE = { admin: false, triage: 0, n: 0, btn: null, title: document.title };
  async function notice() {
    if (document.hidden) return;
    if (NOTICE.off) return;
    let d; try { const r = await fetch("/api/engine/notice", { cache: "no-store" }); if (r.status === 404) { NOTICE.off = true; return; } if (!r.ok) return; d = await r.json(); } catch (e) { return; }  // 작업 공간 서버로 바로 열었으면 없음(404) - 한 번 보고 그만 묻는다
    if (!d.ok) return;
    if (d.ui && !BASE) {  // 허브 화면 파일이 바뀌었다(배포·병합) - 열려 있는 이 페이지는 옛 판이므로 새로 고침 안내(편집기는 자기 /api/version 의 engine 으로 따로 본다)
      if (!NOTICE.ui) NOTICE.ui = d.ui;
      else if (d.ui !== NOTICE.ui && !document.querySelector(".nx-reload")) reloadBar();
    }
    NOTICE.admin = !!d.admin;
    const n = d.admin ? d.triage + (d.startRequest && d.sessionOff ? 1 : 0) : 0;
    let seen = 0; try { seen = +(sessionStorage.getItem("nexa-notice-seen") || 0); } catch (e) { /* 저장소 없음 */ }
    if (d.admin && d.triage > seen) {  // 새로 생겼다 - 페이지마다 한 번만(탭 안에서 기억)
      const t = d.titles && d.titles.length ? ` - ${d.titles[0]}${d.titles.length > 1 ? ` 외 ${d.titles.length - 1}건` : ""}` : "";
      noticeToast(`승인 대기 엔진 요청 ${d.triage}건${t}`);
      try { if (window.Notification && Notification.permission === "granted") new Notification("nexa-slide - 승인 대기", { body: `엔진 요청 ${d.triage}건${t}`, tag: "nexa-triage" }); } catch (e) { /* 알림 불가 */ }
    }
    try { sessionStorage.setItem("nexa-notice-seen", String(d.admin ? d.triage : 0)); } catch (e) { /* 무시 */ }
    NOTICE.triage = d.triage;
    if (NOTICE.btn) {
      let dot = NOTICE.btn.querySelector(".nx-dot");
      if (n && !dot) { dot = document.createElement("span"); dot.className = "nx-dot"; NOTICE.btn.appendChild(dot); }
      if (dot) { if (n) { dot.textContent = n; } else dot.remove(); }
      NOTICE.btn.title = n ? `기본 메뉴 - 승인 대기 ${d.triage}건${d.startRequest && d.sessionOff ? " · 엔진 세션 시작 요청됨" : ""}` : "기본 메뉴 - 홈 · 새로 만들기 · 튜토리얼 · 데모 · 템플릿 · 샘플 · 최근 작업";
    }
    NOTICE.n = n;
    noticeTitle();
  }
  function noticeTitle() {  // 탭 제목 앞 (n) - 표시 언어(i18n.js)가 번역한 제목 위에 붙인다
    const base = window.I18N ? I18N.t(NOTICE.title) : NOTICE.title;
    document.title = NOTICE.n ? `(${NOTICE.n}) ${base}` : base;
  }
  document.addEventListener("nexa-lang", () => noticeTitle());
  function reloadBar() {
    const t = document.createElement("div"); t.className = "nx-toast nx-reload";
    t.innerHTML = `<span>nexa-slide 화면이 새 판으로 바뀌었습니다. 새로 고침해야 반영됩니다.</span><button type="button" class="nx-go">새로 고침</button><button type="button" class="nx-x" title="닫기">✕</button>`;
    t.querySelector(".nx-go").onclick = () => location.reload();
    t.querySelector(".nx-x").onclick = () => { NOTICE.ui = null; t.remove(); };  // 닫으면 지금 판을 기준으로 다시 본다(다음 변경 때 또 안내)
    document.body.appendChild(t);
  }
  function noticeToast(msg) {
    const t = document.createElement("div"); t.className = "nx-toast"; t.textContent = msg;
    const a = document.createElement("a"); a.href = "/studio/home.html#start"; a.textContent = "서버 작업 보기"; t.appendChild(a);
    if (window.Notification && Notification.permission === "default") {  // 데스크톱 알림 - 사용자가 눌러야 권한을 물을 수 있다
      const b = document.createElement("a"); b.href = "#"; b.textContent = "데스크톱 알림 켜기"; b.onclick = (e) => { e.preventDefault(); Notification.requestPermission(); t.remove(); }; t.appendChild(b);
    }
    document.body.appendChild(t); setTimeout(() => t.remove(), 12000);
  }
  function mount(btn) {
    btn.classList.add("nx-menubtn");
    btn.innerHTML = icon("menu", 18);
    NOTICE.btn = btn; NOTICE.title = document.title;
    if (!mount.started) { mount.started = true; setTimeout(notice, 1500); setInterval(notice, 10000); document.addEventListener("visibilitychange", () => { if (!document.hidden) notice(); }); }
    btn.setAttribute("aria-label", "기본 메뉴 열기");
    btn.title = "기본 메뉴 - 홈 · 새로 만들기 · 튜토리얼 · 데모 · 템플릿 · 샘플 · 최근 작업";
    btn.addEventListener("click", open);
    if (/[?&]menu=open(&|$)/.test(location.search)) setTimeout(open, 0);  // 메뉴를 연 채로 보여 주는 링크
  }
  // 언어가 바뀌면(다른 곳에서 I18N.set) 서랍이 열려 있을 때 선택 표시를 맞춘다
  document.addEventListener("nexa-lang", () => { if (root && root.classList.contains("nx-open")) { root.querySelector(".nx-body").innerHTML = items(); renderRecent(); } });
  window.NexaMenu = { mount, open, close, icon, mark, go, toast, post, esc, auth401, logout };
})();
