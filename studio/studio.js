/* nexa-slide 편집기 - 덱 JSON 편집(자동 저장·외부 변경 감지·요청 메모·검사·기록·발표·PPTX 내보내기).
   렌더링은 render.js(Render.*) 가 한다. 서버 API 는 server.py 참고.

   화면 구성(Genspark 작업 화면 방식 차용, 슬라이드 디자인은 기존 그대로)
     머리줄     덱 탭 · 저장 상태 · 세션 칩 · 발표 · 기록 · 내보내기 ▾ · 더보기 ⋯ · 오른쪽 패널
     왼쪽 레일  썸네일(초안·대기·처리 중 요청 / 검사 배지) · 끌어서 순서 · 폭 조절
     모드 바    편집(E) · 선택(M) · 그리기(D) · 실행 취소 · 추가 ▾ · 검사 · ✨ 레이아웃 고치기 · ✨ 다듬기
     서식 줄    (편집 모드 + 요소 선택) 글꼴 · 크기(px/pt·프리셋) · 글자색 · 굵게 · 정렬 · 줄 간격 · 채우기 · 테두리 · 복제 · 삭제 · 잠금 · 위치 조정
     캔버스     확대(10~300%·맞춤·Ctrl+휠) · 요청 표시(번호 배지·영역) · 메모 팝오버 · 보낼 요청 바
     아래       노트 · 개요 · 검사 탭 · 이전/쪽 번호/다음 · 확대 슬라이더
     오른쪽     속성(전체) · 요청 목록 · 기록(자동 백업으로 되돌리기) */
(function () {
  "use strict";
  // 허브 중계(/w/<id>/studio/)로 열렸으면 그 접두를 서버 경로(/api·/out·그림) 앞에 붙인다. 작업 공간 서버로 바로 열면 빈 값(지금과 같음).
  const BASE = (location.pathname.match(/^\/w\/[^/]+/) || [""])[0];
  window.RENDER_BASE = BASE + "/";
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const esc = (s) => Render.esc(s == null ? "" : s);
  const GRID = 8, SW = 1280, SH = 720;
  const LS = { get(k, d) { try { const v = localStorage.getItem("nexa-" + k); return v == null ? d : v; } catch (e) { return d; } },
               set(k, v) { try { localStorage.setItem("nexa-" + k, v); } catch (e) { /* 저장소 없음 */ } } };
  // 아직 남기지 않은 요청 입력 - 덱·슬라이드(·요소)별로 보관해 슬라이드를 옮겨 다녀도·새로 고쳐도 남는다
  // 중계로 열면 여러 작업 공간이 한 주소(origin)의 저장소를 같이 쓰므로 작업 공간 이름을 앞에 붙여 섞이지 않게 한다
  const NS = BASE ? BASE.slice(3) + ":" : "";
  const typed = (key) => LS.get("typed-" + NS + key, "");
  const keep = (key, v) => { try { if (v.trim()) localStorage.setItem("nexa-typed-" + NS + key, v); else localStorage.removeItem("nexa-typed-" + NS + key); } catch (e) { /* 저장소 없음 */ } };

  // 편집기 창(탭) 식별자 - 변경 원장에서 "내 편집"(이 창에서 저장)과 다른 창의 저장을 구분한다. 탭마다 sessionStorage 가 따로라 새 탭은 새 id.
  const TAB = (() => { try { let t = sessionStorage.getItem("nexaTab"); if (!t) { t = (crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).slice(2)).slice(0, 8); sessionStorage.setItem("nexaTab", t); } return t; } catch (e) { return Math.random().toString(36).slice(2, 10); } })();
  const S = {
    tokens: null, decks: [], id: null, deck: null, version: null, reqVersion: "0", savedJson: null,
    cur: 0, sel: null, undo: [], redo: [], dirty: false, saving: false, conflict: false,
    reqs: [], reqOnlySlide: true, layouts: [], preview: false, pngs: [], renderAt: 0, editing: null, clip: null,
    tab: "props", brand: {}, session: null, check: null, chkOnlySlide: true, chkBox: null, template: null,
    multi: [], multiSlide: null,
    changes: [], chgRecent: [], chgMark: {}, chgVersion: "0", chgLatest: 0, chgHidden: new Set(), chgShown: new Set(), chgOff: LS.get("chgOff", "0") === "1", chgFilter: LS.get("chgFilter", "all"), chgMore: false,
    mode: LS.get("mode", "edit"), tool: "rect", zoom: null, btab: LS.get("btab", "notes"), memo: null, drawing: null, pan: null,
  };

  // ---------------------------------------------------------------- 공통
  async function api(method, url, body) {
    const headers = { "X-Nexa-Tab": TAB }; if (body !== undefined) headers["Content-Type"] = "application/json";
    const r = await fetch(BASE + url, { method, headers, body: body !== undefined ? JSON.stringify(body) : undefined });
    let data = null;
    try { data = await r.json(); } catch (e) { /* 빈 응답 */ }
    NexaMenu.auth401(r, data);  // 허브 로그인이 끊겼으면 로그인 페이지로(허브 중계로 열었을 때)
    return { ok: r.ok, status: r.status, data, headers: r.headers };
  }
  let toastT = 0;
  function toast(msg, ms = 2200) {
    const t = $("#toast"); t.textContent = msg; t.classList.add("show");
    const mb = $("#markbar");  // "보낼 요청" 바가 떠 있으면 그 바로 위에(겹치지 않게), 아니면 기본 자리
    t.style.bottom = mb && mb.classList.contains("show") ? `${Math.max(70, window.innerHeight - mb.getBoundingClientRect().top + 10)}px` : "";
    clearTimeout(toastT); toastT = setTimeout(() => t.classList.remove("show"), ms);
  }
  const slide = () => (S.deck && S.deck.slides[S.cur]) || null;
  const elById = (id, s = slide()) => (s ? s.elements.find((e) => e.id === id) : null);
  const selEl = () => (S.sel ? elById(S.sel) : null);
  // 다중 선택 - 주 선택(S.sel) + 함께 고른 요소(S.multi, 그 슬라이드에서만 유효). Shift/Ctrl+클릭 · 빈 곳 끌어 범위 선택
  const selIds = () => { const s = slide(); if (!S.sel || !s) return []; const extra = S.multiSlide === s.id ? S.multi.filter((id) => id !== S.sel && elById(id)) : []; return elById(S.sel) ? [S.sel, ...extra] : []; };
  const selEls = () => selIds().map((id) => elById(id)).filter(Boolean);
  const isMulti = () => selIds().length > 1;
  const isLine = (e) => e && (e.type === "line" || e.type === "arrow");
  const snap = (v, free) => (free ? Math.round(v) : Math.round(v / GRID) * GRID);
  const clone = (o) => JSON.parse(JSON.stringify(o));
  const deckJson = () => JSON.stringify(S.deck);

  function setStatus(kind, text) { const s = $("#status"); s.className = "chip sm " + kind; s.textContent = text; }

  // ---------------------------------------------------------------- 공통 팝업 메뉴
  function closeMenu() { $$(".menu").forEach((m) => m.remove()); }
  /** items: [{label, key, act, disabled, on}] | "-" | {h:"제목"} | {html, bind(m)} - anchor 요소 아래(또는 x,y) */
  function openMenu(anchor, items, opts = {}) {
    closeMenu();
    const m = document.createElement("div"); m.className = "menu"; m.id = opts.id || "menu";
    m.innerHTML = items.map((it, i) => it === "-" ? "<hr>" : it.h ? `<div class="h">${esc(it.h)}</div>` : it.html ? `<div data-i="${i}">${it.html}</div>`
      : `<button data-i="${i}" ${it.disabled ? "disabled" : ""}>${it.on ? "✓ " : ""}${it.icon ? `<span>${it.icon}</span>` : ""}<span>${esc(it.label)}</span>${it.key ? `<span class="k">${esc(it.key)}</span>` : ""}</button>`).join("");
    document.body.appendChild(m);
    let x, y;
    if (anchor && anchor.getBoundingClientRect) { const r = anchor.getBoundingClientRect(); x = opts.right ? r.right - m.offsetWidth : r.left; y = r.bottom + 4; }
    else { x = anchor.x; y = anchor.y; }
    x = Math.max(6, Math.min(x, innerWidth - m.offsetWidth - 6));
    if (y + m.offsetHeight > innerHeight - 6) y = Math.max(6, (anchor.getBoundingClientRect ? anchor.getBoundingClientRect().top : y) - m.offsetHeight - 4);
    m.style.left = x + "px"; m.style.top = y + "px";
    m.addEventListener("click", (e) => {
      const b = e.target.closest("button[data-i]"); if (!b || b.disabled) return;
      const it = items[+b.dataset.i]; if (!it.keep) closeMenu(); it.act && it.act();
    });
    items.forEach((it, i) => it.bind && it.bind(m.querySelector(`[data-i="${i}"]`), m));
    return m;
  }

  // ---------------------------------------------------------------- 기록(실행 취소)·저장
  function snapshot() { S.undo.push(deckJson()); if (S.undo.length > 150) S.undo.shift(); S.redo = []; updUndo(); }
  function updUndo() { $("#undoBtn").disabled = !S.undo.length; $("#redoBtn").disabled = !S.redo.length; }
  function undo() { if (!S.undo.length) return; S.redo.push(deckJson()); S.deck = JSON.parse(S.undo.pop()); afterChange(true); }
  function redo() { if (!S.redo.length) return; S.undo.push(deckJson()); S.deck = JSON.parse(S.redo.pop()); afterChange(true); }
  /** 변경 후: 화면 갱신 + 자동 저장 예약 */
  function afterChange(full) {
    if (S.cur >= S.deck.slides.length) S.cur = S.deck.slides.length - 1;
    if (S.sel && !selEl()) S.sel = null;
    S.dirty = true; setStatus("dirty", "저장 대기");
    updUndo();
    if (full) { renderAll(); ensureThumbVisible(S.cur); } else { renderCanvas(); renderThumb(S.cur); renderProps(); renderFtb(); renderOutline(); }
    scheduleSave();
  }
  let saveT = 0;
  function scheduleSave() { clearTimeout(saveT); saveT = setTimeout(save, 700); }
  async function save(force, extra) {
    if (!S.deck || S.conflict && !force) return;
    if (S.saving) { scheduleSave(); return; }
    const body = deckJson();
    if (!force && body === S.savedJson) { S.dirty = false; setStatus("saved", "저장됨"); return; } // 바뀐 것이 없으면 저장하지 않는다
    S.saving = true; setStatus("dirty", "저장 중…");
    const qs = extra ? "&" + new URLSearchParams(extra).toString() : "";
    const r = await api("PUT", `/api/deck/${S.id}?base=${encodeURIComponent(S.version || "")}${force ? "&force=1" : ""}${qs}`, JSON.parse(body));
    S.saving = false;
    if (r.ok) {
      S.version = r.data.version; S.deck.updated = r.data.updated; S.savedJson = deckJson(); scheduleCheck();
      if (JSON.parse(body).slides && deckJson() === S.savedJson) S.dirty = false;
      S.conflict = false; banner(false);
      setStatus(S.dirty ? "dirty" : "saved", S.dirty ? "저장 대기" : "저장됨");
      if (S.dirty) scheduleSave();
    } else if (r.status === 409) {
      S.conflict = true; setStatus("conflict", "충돌");
      banner(true, "저장하려는 사이 덱 파일이 밖에서(Claude 등) 바뀌었습니다. 어느 쪽을 남길까요?");
    } else { setStatus("error", "저장 실패"); toast("저장 실패: " + (r.data && r.data.error || r.status)); }
  }
  function banner(on, msg) { $("#banner").classList.toggle("show", !!on); if (msg) $("#bannerMsg").textContent = msg; }

  // ---------------------------------------------------------------- 불러오기·외부 변경 감지
  async function loadDeck(id, keep) {
    const r = await fetch(`${BASE}/api/deck/${id}`, { cache: "no-store" });
    if (r.status === 401) { NexaMenu.auth401(r, await r.json().catch(() => null)); return false; }
    if (!r.ok) { toast("덱을 불러오지 못했습니다"); return false; }
    const deck = await r.json();
    if (keep && S.deck && S.id === id) snapshot(); else { S.undo = []; S.redo = []; }
    S.id = id; S.deck = deck; S.version = r.headers.get("X-Deck-Version"); S.savedJson = deckJson();
    Render.setDeckFonts(deck.fontPreset);  // 덱 글꼴 세트(있으면)
    S.dirty = false; S.conflict = false; banner(false);
    if (!keep) { S.cur = 0; S.sel = null; closeMemo(); }
    if (S.cur >= deck.slides.length) S.cur = Math.max(0, deck.slides.length - 1);
    if (S.sel && !selEl()) S.sel = null;
    setStatus("saved", "저장됨"); updUndo();
    renderDeckTabs();
    await loadReqs(); await loadPngs();
    S.chkBox = null; scheduleCheck(50);
    renderAll(); revealThumb(S.cur, true);
    if (S.tab === "hist") loadHist();
    await loadChanges();
    return true;
  }
  async function poll() {
    if (!S.id) return;
    try {
      const r = await api("GET", `/api/version/${S.id}`);
      if (!r.ok) return;
      if (r.data.session) renderSession(r.data.session, r.data.activity);
      await checkWorkspace(r.data);
      if (r.data.requests !== S.reqVersion) await loadReqs();
      if (r.data.deck !== S.version && !S.saving) {
        if (S.dirty || S.editing) {
          if (!S.conflict) { S.conflict = true; setStatus("conflict", "충돌"); banner(true, "편집 중에 덱 파일이 밖에서(Claude 등) 바뀌었습니다. 어느 쪽을 남길까요?"); }
        } else await reloadExternal("밖에서 바뀐 덱을 다시 불러왔습니다");
      }
      if (r.data.changes !== undefined && r.data.changes !== S.chgVersion) await loadChanges();  // 내 저장·다른 창·Claude·빌드 - 원장이 자라면 변경 탭 갱신
    } catch (e) { setStatus("error", "서버 끊김"); }
  }

  // ---------------------------------------------------------------- 변경(서버 원장) - 편집기·Claude·빌드·외부의 모든 변경을 서버가 decks/.history/<덱>/changes.jsonl 에 남기고
  // 편집기는 묶음(group)과 슬라이드별 최근 수정(recent)을 받아 그린다. 비교 규칙은 서버 deckdiff.py 한 곳(0.16.0 전에는 여기 JS 에 있었다 - tests/deckdiff_ref.js).
  // 표시(썸네일 배지·개요 배지·캔버스 점선) = "표시 지우기" 뒤에 생긴, 내 편집이 아닌 묶음의 합 - 묶음마다 숨기기/표시.
  const ORG = { editor: "편집기", claude: "AI", build: "빌드", external: "외부" };
  const seenKey = () => "chgSeen-" + S.id;
  const isMine = (g) => g.origin === "editor" && !!g.actor && g.actor.tab === TAB;
  function ago(ts) {
    const t = Date.parse(ts || ""); if (!t) return "";
    const d = (Date.now() - t) / 1000;
    if (d < 60) return "방금"; if (d < 3600) return `${Math.floor(d / 60)}분 전`; if (d < 86400) return `${Math.floor(d / 3600)}시간 전`;
    return `${Math.floor(d / 86400)}일 전`;
  }
  const hhmm = (ts) => { const d = new Date(ts || 0); return isNaN(d) ? "" : d.toTimeString().slice(0, 5); };
  const dayText = (ts) => { const d = new Date(ts || 0); if (isNaN(d)) return ""; const n = new Date(); return d.toDateString() === n.toDateString() ? "오늘" : `${d.getMonth() + 1}/${d.getDate()}`; };
  function orgTitle(g) {
    const a = g.actor || {}, out = [];
    if (g.origin === "editor") out.push(isMine(g) ? "현재 편집기에서 수정" : `다른 편집기(${a.tab || "?"})에서 수정 - 협업`);
    if (g.origin === "claude") out.push(a.label ? `세션 ${a.label}` : "Claude 세션", a.request ? `요청 ${a.request}` : "", g.confidence === "inferred" ? "정황으로 추정(세션 연결·처리 중 요청)" : "서버 API 로 저장(정확)");
    if (g.origin === "build") out.push(a.note || "build_deck");
    if (g.origin === "external") out.push(g.action === "startup" ? "서버가 꺼진 사이에 바뀜(출처 모름)" : "출처를 알 수 없는 외부 변경(파일 직접 수정)");
    if (a.note && g.origin !== "build") out.push(a.note);
    if (g.evidence) out.push("근거: " + JSON.stringify(g.evidence));
    return out.filter(Boolean).join(" · ");
  }
  // 배지 글자 = 변경 탭 필터 칩 글자(편집 · 협업 · AI · 빌드 · 외부)
  const orgKey = (g) => (g.origin === "editor" ? (isMine(g) ? "mine" : "editor") : g.origin);
  const ORG_LABEL = { mine: "편집", editor: "협업", claude: "AI", build: "빌드", external: "외부" };
  const orgBadge = (g) => { const k = orgKey(g); return `<span class="org o-${esc(k)}${g.confidence === "inferred" ? " inf" : ""}" title="${esc(orgTitle(g))}">${esc(ORG_LABEL[k] || g.origin)}${g.confidence === "inferred" ? " 추정" : ""}</span>`; };
  const chgSummary = (sum) => ["수정", "추가", "삭제", "이동"].filter((k) => sum && sum[k]).map((k) => `${sum[k]}장 ${k}`).join(" · ");
  const inFilter = (g, f) => f === "all" || (f === "mine" ? isMine(g) : f === "editor" ? (g.origin === "editor" && !isMine(g)) : g.origin === f);
  // 표시 여부 - 직접 켠 묶음(chgShown)은 내 편집·확인한 것이라도 표시, 직접 끈 묶음(chgHidden)은 표시 안 함,
  // 그 밖에는 "표시 지우기" 이후의 내 편집이 아닌 묶음만
  const isMarked = (g, seen = +LS.get(seenKey(), 0)) => !S.chgOff && isOn(g, seen);
  const isOn = (g, seen = +LS.get(seenKey(), 0)) => S.chgShown.has(g.seq) || (!S.chgHidden.has(g.seq) && g.last > seen);  // 내 편집도 "확인함" 전까지 표시
  function rebuildMarks() {
    S.chgMark = {}; if (!S.id) return;
    const seen = +LS.get(seenKey(), 0), mark = (S.chgMark[S.id] = {});
    for (const g of S.changes) {
      if (!isMarked(g, seen)) continue;
      for (const it of g.items || []) if (!it.gone) { const m = (mark[it.sid] = mark[it.sid] || new Set()); (it.els || []).filter((e) => !e.gone).forEach((e) => m.add(e.id)); }
    }
  }
  const chgOf = (sid) => (S.chgMark[S.id] || {})[sid];
  function redrawMarks() { rebuildMarks(); renderChanges(); renderThumbs(); renderOutline(); if (!S.editing) renderCanvas(); }
  async function loadChanges(more) {
    if (!S.id) return;
    const before = more && S.changes.length ? `&before=${S.changes[S.changes.length - 1].seq}` : "";
    const r = await api("GET", `/api/changes/${S.id}?group=1&recent=1&limit=40${before}`); if (!r.ok) return;
    const gs = r.data.groups || [];
    S.changes = more ? S.changes.concat(gs) : gs;
    if (!more) { S.chgRecent = r.data.recent || []; S.chgLatest = r.data.latest || 0; S.chgVersion = r.data.ver; S.chgKeep = r.data.keep; }
    S.chgMore = !!r.data.more;
    redrawMarks();
  }
  // 확인함 - 지금까지(최근 변경까지)를 확인한 것으로: 모든 묶음을 미표시로. 이후 묶음마다 "표시"로 다시 볼 수 있다
  function markSeen() { LS.set(seenKey(), S.chgLatest); S.chgShown.clear(); S.chgHidden.clear(); redrawMarks(); }
  // 최근 3개 표시 - 가장 최근 묶음 3개의 "표시"를 대신 눌러 준다(내 편집 포함)
  function showRecent(n = 3) { S.changes.slice(0, n).forEach((g) => { S.chgHidden.delete(g.seq); S.chgShown.add(g.seq); }); redrawMarks(); }
  // 표시 끄기/켜기 - 변경 기록을 보지 않고 작업할 때. 묶음별 표시 상태는 그대로 두고 화면 표시만 모두 끈다(브라우저에 기억)
  function toggleOff() { S.chgOff = !S.chgOff; LS.set("chgOff", S.chgOff ? "1" : "0"); redrawMarks(); }
  async function reloadExternal(msg) {
    await loadDeck(S.id, true);  // loadDeck 가 원장도 다시 불러온다
    const g = S.changes.find((x) => !isMine(x));
    if (g && g.last > +LS.get(seenKey(), 0)) notice(`${msg} - ${ORG[g.origin] || g.origin}${g.confidence === "inferred" ? "(추정)" : ""} · ${chgSummary(g.summary) || "덱 설정"}. Ctrl+Z 로 되돌릴 수 있습니다.`, [{ act: "changes", label: "변경 보기", primary: true }]);
    else toast(msg + " (바뀐 내용 없음)");
  }
  function renderChanges() {
    const n = Object.keys(S.chgMark[S.id] || {}).length;
    $("#chgCnt").style.display = n ? "" : "none"; $("#chgCnt").textContent = n;
    const P = $("#tab-chg"); if (!P) return;
    const F = [["all", "전체", "모든 변경 - 편집기·Claude·빌드·외부"],
      ["mine", "편집", "현재 편집기에서 수정"],
      ["editor", "협업", "다른 편집기에서 수정"],
      ["claude", "AI", "AI에서 수정, 파일 직접 수정은 추정"],
      ["build", "빌드", "build_deck 으로 content 에서 덱을 다시 만든 변경"],
      ["external", "외부", "출처를 알 수 없는 변경 - 파일 수동 복사·수정, 서버가 꺼진 사이의 변경"]];
    const cnt = (k) => S.changes.filter((g) => inFilter(g, k)).length;
    const list = S.changes.filter((g) => inFilter(g, S.chgFilter));
    const recent = S.chgRecent.filter((r) => r.exists).slice(0, 8);
    P.innerHTML = `<div class="sec"><div class="chg-top"><h3>변경 - ${esc(S.id || "")}</h3>
        <button class="ib chg-ibtn${S.chgInfo ? " on" : ""}" id="chgInfoBtn" data-chg-info="1" title="설명 보기/숨기기" aria-expanded="${S.chgInfo ? "true" : "false"}"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="9.5"/><path d="M12 11v6"/><circle cx="12" cy="7.5" r=".6" fill="currentColor"/></svg></button></div>
      ${S.chgInfo ? `<div class="hint chg-info" id="chgInfo">편집기·Claude·빌드·외부에서 덱이 바뀔 때마다 서버가 원장(덱당 최근 ${S.chgKeep || 1000}건)에 남깁니다. 항목을 누르면 그 장·요소로 갑니다. 확인하지 않은 변경(내 편집 포함)은 썸네일 배지와 캔버스 파란 점선으로 표시하고, "확인함"은 지금까지를 미표시로, "최근 3개 표시"는 최근 묶음 3개를 표시, "표시 끄기"는 기록을 보지 않고 작업할 때 모든 표시를 감춥니다. 묶음마다 "표시/숨기기". 장기 보관을 대신하지 않습니다 - 되돌리기는 백업(최근 50개)이 남아 있을 때만.</div>` : ""}
      <div class="chg-fil" id="chgFilter">${F.map(([k, l, t]) => `<button data-chgf="${k}" class="f-${k}${S.chgFilter === k ? " on" : ""}" title="${esc(t)}">${l}${cnt(k) ? ` <b>${cnt(k)}</b>` : ""}</button>`).join("")}</div>
      <div class="chg-acts">
      <button class="chip sm" data-chg-seen="1" title="최근 변경까지 확인한 것으로 - 모든 묶음을 미표시로 바꾼다(묶음마다 '표시'로 다시 볼 수 있다)">확인함</button>
      <button class="chip sm" data-chg-recent="1" title="가장 최근 변경 묶음 3개를 표시한다(내 편집 포함) - 묶음마다 '표시'를 누르는 것과 같다">최근 3개 표시</button>
      <button class="chip sm${S.chgOff ? " on" : ""}" data-chg-off="1" title="${S.chgOff ? "변경 표시를 다시 켠다(묶음별 표시 상태는 그대로)" : "변경 기록을 보지 않고 작업 - 배지·점선을 모두 감춘다(묶음별 표시 상태는 그대로)"}">${S.chgOff ? "표시 켜기" : "표시 끄기"}</button></div></div>
      ${recent.length ? `<div class="sec"><h3>최근 수정 대상</h3><div class="hscroll"><table class="chg-tbl"><colgroup><col class="n"><col><col class="o"><col class="a"></colgroup>${recent.map((r) => { const k = [r.kind === "수정" ? "" : r.kind, ...(r.kinds || []), ...(r.extra || [])].filter(Boolean).join("·"); return `<tr data-csid="${esc(r.sid)}"><td class="n">${r.idx + 1}</td><td class="t" title="${esc(r.title || "")}${k ? ` - ${esc(k)}` : ""}">${esc(r.title || "")}</td><td class="o">${orgBadge(r)}</td><td class="hint a" title="${esc(r.ts || "")} (${esc(ago(r.ts))})">${esc(ago(r.ts).replace(/ 전$/, ""))}</td></tr>`; }).join("")}</table></div></div>` : ""}
      ${list.length ? list.map(groupHtml).join("") + (S.chgMore ? `<div class="row" style="justify-content:center;margin:8px 0"><button class="chip sm" data-chg-more="1">더 보기</button></div>` : `<div class="hint" style="text-align:center;margin:8px 0">원장의 시작</div>`)
        : `<div class="hint">${S.changes.length ? "이 필터에 해당하는 변경이 없습니다." : "아직 기록된 변경이 없습니다."}</div>`}`;
  }
  function groupHtml(g) {
    const on = isOn(g), mine = isMine(g);
    const tag = g.action === "restore" ? " · 되돌리기" : g.action === "startup" ? " · 서버 꺼진 사이" : g.action === "build" ? "" : "";
    return `<div class="chg-rec${on ? " on" : ""}"><div class="chg-h"><b title="${esc(g.ts || "")}${g.count > 1 ? ` ~ ${esc(g.ts_end || "")}` : ""}">${esc(dayText(g.ts))} ${esc(hhmm(g.ts))}</b>${orgBadge(g)}<span class="hint" style="margin:0">${g.actor && g.actor.label ? esc(g.actor.label) + " · " : ""}${esc(chgSummary(g.summary))}${g.fields && g.fields.length ? ` · 덱 ${esc(g.fields.join("·"))}` : ""}${g.count > 1 ? ` · 저장 ${g.count}회${g.approx ? "(요약)" : ""}` : ""}${tag}</span>
      ${g.backupExists ? `<button class="chip sm" data-chg-restore="${esc(g.backup)}" data-chg-at="${esc((g.ts || "").replace("T", " ").slice(0, 16))}" title="이 변경 직전 상태로 되돌린다(지금 상태도 기록에 남는다)">직전으로</button>` : `<button class="chip sm" disabled title="백업이 50개 상한으로 지워져 되돌릴 수 없습니다">직전으로</button>`}
      <button class="chip sm chg-tg" data-chg-tg="${g.seq}" title="이 묶음의 변경을 썸네일 배지·캔버스 파란 점선으로 ${on ? "그만 표시" : "표시"}${mine ? "(내 편집은 기본으로 표시하지 않는다)" : ""}">${on ? "숨기기" : "표시"}</button></div>` +
      (g.items || []).map((it) => `<div class="chg-it${it.gone ? " gone" : ""}" ${it.gone ? "" : `data-csid="${esc(it.sid)}"`}>
        <span class="k ${esc(it.kind)}">${esc(it.kind)}</span> <b>${it.idx + 1}.</b> ${esc(it.title || "")}${it.moved ? ` <span class="hint" style="margin:0">(순서 ${it.moved[0]} → ${it.moved[1]})</span>` : ""}${it.extra && it.extra.length ? ` <span class="hint" style="margin:0">· ${esc(it.extra.join("·"))}</span>` : ""}${it.truncated ? ` <span class="hint" style="margin:0">· 요소 ${it.truncated}개 더</span>` : ""}
        ${(it.els || []).map((e) => `<div class="chg-el${e.gone ? " gone" : ""}" ${e.gone ? "" : `data-cel="${esc(e.id)}"`}><code>${esc(e.id)}</code> ${esc((e.kinds || []).join("·"))}${e.before || e.after ? `<div class="chg-tx">${e.before ? `<s>${esc(e.before)}</s>` : ""}${e.before && e.after ? " → " : ""}${e.after ? `<span>${esc(e.after)}</span>` : ""}</div>` : ""}</div>`).join("")}</div>`).join("") + `</div>`;
  }
  async function restoreFrom(file, label) {
    if (!confirm(`${label} 시점으로 되돌릴까요? (지금 상태는 기록에 남습니다)`)) return false;
    const r = await api("GET", `/api/history/${S.id}?f=${encodeURIComponent(file)}`);
    if (!r.ok || !r.data || !r.data.slides) { toast("기록을 읽지 못했습니다"); return false; }
    snapshot(); S.deck = r.data; S.deck.id = S.id; S.sel = null; afterChange(true); await save(true, { action: "restore", note: file });
    toast("되돌렸습니다 (Ctrl+Z 로 취소 가능)"); return true;
  }
  async function onChangesClick(e) {
    if (e.target.closest("[data-chg-info]")) { S.chgInfo = !S.chgInfo; renderChanges(); return; }
    const f = e.target.closest("[data-chgf]"); if (f) { S.chgFilter = f.dataset.chgf; LS.set("chgFilter", S.chgFilter); renderChanges(); return; }
    if (e.target.closest("[data-chg-seen]")) { markSeen(); return; }
    if (e.target.closest("[data-chg-recent]")) { showRecent(3); return; }
    if (e.target.closest("[data-chg-off]")) { toggleOff(); return; }
    if (e.target.closest("[data-chg-more]")) { await loadChanges(true); return; }
    const rs = e.target.closest("[data-chg-restore]");
    if (rs) { if (await restoreFrom(rs.dataset.chgRestore, rs.dataset.chgAt)) { await loadChanges(); if (S.tab === "hist") loadHist(); } return; }
    const tg = e.target.closest("[data-chg-tg]");
    if (tg) {
      const k = +tg.dataset.chgTg, g = S.changes.find((x) => x.seq === k); if (!g) return;
      if (isOn(g)) { S.chgShown.delete(k); S.chgHidden.add(k); } else { S.chgHidden.delete(k); S.chgShown.add(k); }
      redrawMarks(); return;
    }
    const it = e.target.closest("[data-csid]"); if (!it) return;
    const i = S.deck.slides.findIndex((s) => s.id === it.dataset.csid); if (i < 0) { toast("그 슬라이드가 지금은 없습니다"); return; }
    goSlide(i); revealThumb(i, true);
    const el = e.target.closest("[data-cel]");
    if (el && elById(el.dataset.cel)) { S.sel = el.dataset.cel; renderAll(); }
  }

  // 덱 목록·설정·엔진 변경 감지 - 지금 보는 슬라이드와 상관없이 머리 아래 안내 띠로 알린다.
  // 새 덱·지운 덱: 덱 탭을 바로 갱신(새로 고침 불필요)하고 [열기]를 준다. 설정·엔진: 화면을 새로 고쳐야 반영되므로 [새로 고침]을 준다.
  function notice(msg, acts) {
    $("#noticeMsg").textContent = msg;
    $("#noticeActs").innerHTML = (acts || []).map((a) => `<button class="chip sm${a.primary ? " primary" : ""}" data-nact="${esc(a.act)}" data-arg="${esc(a.arg || "")}">${esc(a.label)}</button>`).join(" ");
    $("#notice").classList.add("show");
  }
  async function checkWorkspace(v) {
    if (!v.deckIds) return;  // 이전 서버
    const ids = v.deckIds.join(",");
    const W = S.ws;
    if (!W) { S.ws = { ids, decksVer: v.decksVer, config: v.config, engine: v.engine }; return; }
    if (ids !== W.ids || v.decksVer !== W.decksVer) {
      const before = new Set(S.decks.map((d) => d.id));
      const r = await api("GET", "/api/decks");
      if (r.ok) { S.decks = r.data; renderDeckTabs(); }
      const added = S.decks.filter((d) => !before.has(d.id));
      if (ids !== W.ids && !v.deckIds.includes(S.id)) {
        notice(`지금 보고 있는 덱(${S.id}) 파일이 없어졌습니다.`, [{ act: "reload", label: "새로 고침", primary: true }]);
      } else if (added.length) {
        notice(`새 덱 ${added.length}개가 생겼습니다 - ${added.map((d) => `${d.title || d.id}(${d.slides}장)`).join(", ")}. 위 덱 탭에도 추가했습니다.`,
          added.slice(0, 6).map((d, i) => ({ act: "open", arg: d.id, label: `${d.id} 열기`, primary: i === 0 })));
      }
      W.ids = ids; W.decksVer = v.decksVer;
    }
    if (v.config !== W.config) {  // 설정(템플릿 색·글꼴·로고·제목)은 다시 불러와 바로 적용 - 새로 고침 불필요
      W.config = v.config;
      await loadConfig(); await loadFonts();
      S.tokens = await (await fetch("tokens.json", { cache: "no-store" })).json();
      Render.setTokens(S.tokens); $("#rs-css").textContent = Render.css();
      if (S.deck) { renderAll(); revealThumb(S.cur); }
    }
    if (v.engine !== W.engine) {  // 편집기 코드·템플릿 파일은 화면을 새로 고쳐야 반영된다
      W.engine = v.engine;
      notice("편집기 코드·템플릿(엔진)이 바뀌었습니다. 새로 고침해야 반영됩니다.",
        [{ act: "reload", label: S.dirty ? "저장하고 새로 고침" : "새로 고침", primary: true }]);
    }
  }

  // ---------------------------------------------------------------- 그리기(화면)
  function renderAll() {
    renderThumbs(); renderCanvas(); renderProps(); renderReqs(); renderNotes(); renderPng(); renderOutline(); renderCheck(); renderFtb(); renderCounter();
    location.hash = `${S.id}/${S.cur + 1}`;
  }
  function renderDeckTabs() {
    // 탭에는 제목(시작 덱은 ★), id 는 엔진이 만든 짧은 해시라 툴팁·메뉴 머리에만 보인다
    $("#deckTabs").innerHTML = S.decks.map((d) => `<button data-deck="${esc(d.id)}" class="${d.id === S.id ? "on" : ""}${d.start ? " start" : ""}" title="${esc(d.title)} (${d.slides}장) · id ${esc(d.id)}${d.start ? " · 시작 덱" : ""} - 오른쪽 클릭: 제목·복제·시작 덱·삭제">${d.start ? "★ " : ""}${esc(d.title || d.id)}</button>`).join("")
      + `<button data-deckadd="1" class="add" title="새 덱 만들기 - 제목만 적으면 id 는 저절로">＋</button>`;
  }
  // ---------------------------------------------------------------- 덱 관리 - 추가·이름(id)·제목·삭제(휴지통). 서버 /api/decks = CLI `nexa.py deck …`
  async function deckAdmin(body, okMsg) {
    const r = await api("POST", "/api/decks", body);
    if (!r.ok) { toast("덱 관리 실패: " + ((r.data && r.data.error) || r.status), 6000); return null; }
    S.decks = (r.data.decks || []).map((d) => ({ id: d.id, title: d.title, slides: d.slides, start: !!d.start })); renderDeckTabs();
    if (okMsg) toast(okMsg, 4000);
    return r.data;
  }
  async function deckCreate() {
    const title = (prompt("새 덱 제목", "") || "").trim(); if (!title) return;
    const d = await deckAdmin({ action: "create", title }, `만들었습니다: ${title}`);
    if (d) { if (S.dirty) await save(); await loadDeck(d.id); }
  }
  function deckMenu(e, id) {
    e.preventDefault();
    const d = S.decks.find((x) => x.id === id) || { id, title: id };
    openMenu({ x: e.clientX, y: e.clientY }, [
      { h: `${d.title} · id ${d.id}` },
      { label: "제목 바꾸기…", act: async () => { const t = (prompt("덱 제목", d.title) || "").trim(); if (!t || t === d.title) return; const r = await deckAdmin({ action: "retitle", id, title: t }, "제목을 바꿨습니다"); if (r && S.id === id) { S.deck.title = t; S.savedJson = deckJson(); } } },
      { label: "복제…", act: async () => { const t = (prompt("복제한 덱의 제목", `${d.title} (복사)`) || "").trim(); if (!t) return; if (S.dirty && S.id === id) await save(); const r = await deckAdmin({ action: "copy", id, title: t }, `복제했습니다: ${t}`); if (r) await loadDeck(r.id); } },
      { label: d.start ? "시작 덱 해제" : "시작 덱으로", on: !!d.start, act: async () => { await deckAdmin({ action: "start", id: d.start ? "" : id }, d.start ? "시작 덱을 해제했습니다" : `시작 덱: ${d.title}`); } }, "-",
      { label: "덱 삭제(휴지통)…", act: async () => { if (!confirm(`덱 "${d.title}" 을 지울까요? decks/.trash/ 로 옮겨지며 요청·기록·첨부·content 도 같이 갑니다.`)) return; const r = await deckAdmin({ action: "delete", id }, `휴지통으로 옮겼습니다: ${d.title}`); if (r && S.id === id) { const next = S.decks[0]; if (next) await loadDeck(next.id); else location.href = BASE + "/studio/home.html"; } } },
    ]);
  }
  const reqsOf = (sid, st) => {  // 썸네일 배지 - 후속 요청은 thread 단위로 하나만 센다
    const l = S.reqs.filter((r) => r.slide === sid && (st ? r.status === st : r.status !== "done"));
    return [...new Map(l.map((r) => [r.thread || r.id, r])).values()];
  };
  function thumbHtml(s, i) {
    const dr = reqsOf(s.id, "draft").length, op = reqsOf(s.id, "open").length, wk = reqsOf(s.id, "working").length;
    return `<div class="thumb${i === S.cur ? " cur" : ""}" data-i="${i}" draggable="true"><span class="num">${i + 1}</span>
      <div class="vp">${Render.renderSlide(s, i + 1)}</div>
      <div class="tools"><button data-act="dup" title="복제">복제</button><button data-act="del" title="삭제">삭제</button></div>
      <div class="badges">${s.hidden ? `<span class="bd hid" title="숨김 슬라이드 - 발표·인쇄에서 건너뜀">숨김</span>` : ""}${dr ? `<span class="bd draft" title="보내지 않은 요청 메모">✎ ${dr}</span>` : ""}${op ? `<span class="bd req" title="세션에 보낸 요청(대기)">요청${op}</span>` : ""}${wk ? `<span class="bd work" title="세션 처리 중">처리${wk}</span>` : ""}${chgOf(s.id) ? `<span class="bd chg" title="내 편집이 아닌 변경이 있는 슬라이드 - 변경 탭">변경${chgOf(s.id).size || ""}</span>` : ""}${chkBadge(s.id)}</div></div>`;
  }
  function chkBadge(sid) {
    if (!S.check) return "";
    const its = S.check.issues.filter((x) => x.slide === sid); if (!its.length) return "";
    const e = its.filter((x) => x.severity === "ERROR").length;
    return `<span class="bd chk${e ? " err" : ""}" title="레이아웃 검사 - ERROR ${e} · WARNING ${its.length - e}">⚠ ${its.length}</span>`;
  }
  function fitThumbs() { $$("#left .thumb .vp").forEach((v) => { v.firstElementChild.style.transform = `scale(${v.clientWidth / SW})`; }); }
  function renderThumbs() {
    const L = $("#left"), top = L.scrollTop;
    $$("#left .thumb, #addSlide").forEach((x) => x.remove());
    L.insertAdjacentHTML("beforeend", S.deck.slides.map(thumbHtml).join("") + `<button class="chip" id="addSlide">＋ 새 슬라이드</button>`);
    fitThumbs(); L.scrollTop = top;
  }
  function ensureThumbVisible(i) {
    const L = $("#left"), t = $(`#left .thumb[data-i="${i}"]`); if (!L || !t) return;
    const lr = L.getBoundingClientRect(), tr = t.getBoundingClientRect(), m = 8;
    if (tr.top < lr.top) L.scrollTop -= lr.top - tr.top + m; else if (tr.bottom > lr.bottom) L.scrollTop += tr.bottom - lr.bottom + m;
  }
  function revealThumb(i, center) {
    const go = () => {
      const L = $("#left"), t = $(`#left .thumb[data-i="${i}"]`); if (!L || !t) return;
      const lr = L.getBoundingClientRect(), tr = t.getBoundingClientRect();
      if ((tr.top < lr.top || tr.bottom > lr.bottom) && center) L.scrollTop += (tr.top + tr.height / 2) - (lr.top + lr.height / 2); else ensureThumbVisible(i);
    };
    go(); requestAnimationFrame(() => requestAnimationFrame(go));
  }
  function renderThumb(i) { const t = $(`#left .thumb[data-i="${i}"]`); if (!t) return renderThumbs(); t.outerHTML = thumbHtml(S.deck.slides[i], i); fitThumbs(); }

  // ---------------------------------------------------------------- 확대
  let scale = 1;
  function fitScale() { const vp = $("#vpEdit"); return Math.max(0.05, Math.min((vp.clientWidth - 24) / SW, (vp.clientHeight - 24) / SH)) || 0.5; }
  function fitStage() {
    scale = S.zoom ? S.zoom / 100 : fitScale();
    const st = $("#stage"), wr = $("#stageWrap");
    st.style.transform = `scale(${scale})`;
    wr.style.width = SW * scale + "px"; wr.style.height = SH * scale + "px";
    const pct = Math.round(scale * 100);
    $("#zoomSlider").value = pct; $("#zoomPct").textContent = pct + "%";
    $("#zoomFit").classList.toggle("on", !S.zoom);
    if (S.preview) { const vp2 = $("#vpPng"); $("#pngWrap").style.transform = `scale(${Math.min(vp2.clientWidth / SW, vp2.clientHeight / SH) || 0.5})`; }
    drawSel(); renderMarks(); placeMemo();
  }
  function setZoom(pct, anchor) {
    const vp = $("#vpEdit"), old = scale;
    S.zoom = pct == null ? null : Math.max(10, Math.min(300, Math.round(pct)));
    // 확대 기준점(마우스 위치)을 유지한다
    const ax = anchor ? anchor.x : vp.clientWidth / 2, ay = anchor ? anchor.y : vp.clientHeight / 2;
    const sx = (vp.scrollLeft + ax) / old, sy = (vp.scrollTop + ay) / old;
    fitStage();
    if (S.zoom) { vp.scrollLeft = sx * scale - ax; vp.scrollTop = sy * scale - ay; }
  }

  function renderCanvas() {
    const s = slide();
    $("#host").innerHTML = s ? Render.renderSlide(s, S.cur + 1) : "";
    fitStage();
  }
  function renderElementDom(el) {
    const node = $(`#host .rs-el[data-id="${CSS.escape(el.id)}"]`);
    if (node) node.outerHTML = Render.renderElement(el, S.cur + 1); else renderCanvas();
  }
  function boxOf(el) { return isLine(el) ? Render.lineBox(el) : el; }
  /** 클릭한 자리의 맨 바깥 요소(묶음 안의 자식을 눌러도 묶음이 잡힌다) */
  function topEl(target) { let n = target.closest("#host .rs-el"); while (n && n.parentElement) { const up = n.parentElement.closest("#host .rs-el"); if (!up) break; n = up; } return n; }
  // 묶음: 고른 요소(2개 이상, 잠기지 않은 것)를 한 요소(type group, children 은 묶음 상자 기준 좌표)로 · 풀기: 자식을 절대 좌표로 되돌리고 새 id
  function groupSel() {
    const s = slide(); if (!s) return;
    const els = selEls().filter((x) => !x.locked && x.type !== "group");
    if (els.length < 2) { toast("잠기지 않은 요소를 2개 이상 고르세요(묶음은 다시 묶지 않습니다)"); return; }
    if (els.some((x) => ["table", "plan-table", "chart"].includes(x.type))) { toast("표·차트는 묶을 수 없습니다 - PPTX 묶음에 넣지 못합니다"); return; }
    const bs = els.map(boxOf), x = Math.min(...bs.map((b) => b.x)), y = Math.min(...bs.map((b) => b.y)), w = Math.max(...bs.map((b) => b.x + b.w)) - x, h = Math.max(...bs.map((b) => b.y + b.h)) - y;
    snapshot();
    const kids = els.map((el) => { const c = clone(el); if (isLine(c)) { c.x1 -= x; c.x2 -= x; c.y1 -= y; c.y2 -= y; Object.assign(c, Render.lineBox(c)); } else { c.x -= x; c.y -= y; } return c; });
    const at = Math.min(...els.map((el) => s.elements.indexOf(el)));
    els.forEach((el) => s.elements.splice(s.elements.indexOf(el), 1));
    const g = { id: newElId(s), type: "group", x, y, w, h, children: kids };
    s.elements.splice(at, 0, g); select(g.id); afterChange();
  }
  function ungroupSel() {
    const s = slide(), g = selEl(); if (!s || !g || g.type !== "group") { toast("묶음 요소를 고르세요"); return; }
    snapshot();
    const at = s.elements.indexOf(g); s.elements.splice(at, 1);
    const ids = (g.children || []).map((c, i) => { const e = clone(c); e.id = newElId(s); if (isLine(e)) { e.x1 += g.x; e.x2 += g.x; e.y1 += g.y; e.y2 += g.y; Object.assign(e, Render.lineBox(e)); } else { e.x += g.x; e.y += g.y; } if (g.rot) e.rot = (e.rot || 0) + g.rot; s.elements.splice(at + i, 0, e); return e.id; });
    setSelection(ids); afterChange();
  }
  /** 스마트 가이드 선 - 끌기 중 #ov 에 덧그린다(drawSel 이 지운 뒤) */
  function drawGuides(gs) {
    const ov = $("#ov"); if (!ov || !gs || !gs.length) return;
    ov.insertAdjacentHTML("beforeend", gs.map(([d, v]) => d === "v" ? `<div class="guide" style="left:${v}px;top:0;width:0;height:${SH}px"></div>` : `<div class="guide" style="top:${v}px;left:0;height:0;width:${SW}px"></div>`).join(""));
  }
  function drawSel() {
    const ov = $("#ov"); const el = selEl();
    if (!el || S.editing || S.mode === "draw") { ov.innerHTML = drag && drag.mode === "marquee" ? marqueeHtml() : ""; drawChkBox(); return; }
    if (isMulti()) {  // 다중 선택 - 요소마다 얇은 상자 + 전체 묶음 상자(크기 조절 손잡이 없음)
      const els = selEls(), bw = 2 / scale, bs = els.map(boxOf);
      const x1 = Math.min(...bs.map((b) => b.x)), y1 = Math.min(...bs.map((b) => b.y)), x2 = Math.max(...bs.map((b) => b.x + b.w)), y2 = Math.max(...bs.map((b) => b.y + b.h));
      ov.innerHTML = bs.map((b, i) => `<div class="selbox multi${els[i].locked ? " locked" : ""}" style="left:${b.x - bw}px;top:${b.y - bw}px;width:${b.w + 2 * bw}px;height:${b.h + 2 * bw}px;border-width:${bw}px"></div>`).join("")
        + `<div class="selbox group" style="left:${x1 - 3 * bw}px;top:${y1 - 3 * bw}px;width:${x2 - x1 + 6 * bw}px;height:${y2 - y1 + 6 * bw}px;border-width:${bw}px"></div>` + (drag && drag.mode === "marquee" ? marqueeHtml() : "");
      drawChkBox(); return;
    }
    const b = boxOf(el), hs = 11 / scale, bw = 2 / scale;
    let h = `<div class="selbox${el.locked ? " locked" : ""}${S.mode === "pick" ? " pick" : ""}" style="left:${b.x - bw}px;top:${b.y - bw}px;width:${b.w + 2 * bw}px;height:${b.h + 2 * bw}px;border-width:${bw * (S.mode === "pick" ? 1.5 : 1)}px"></div>`;
    if (!el.locked && S.mode === "edit") {
      const pts = isLine(el) ? [["p1", el.x1, el.y1], ["p2", el.x2, el.y2]]
        : [["nw", b.x, b.y], ["n", b.x + b.w / 2, b.y], ["ne", b.x + b.w, b.y], ["e", b.x + b.w, b.y + b.h / 2],
           ["se", b.x + b.w, b.y + b.h], ["s", b.x + b.w / 2, b.y + b.h], ["sw", b.x, b.y + b.h], ["w", b.x, b.y + b.h / 2]];
      h += pts.map(([d, x, y]) => `<div class="hd" data-h="${d}" style="left:${x - hs / 2}px;top:${y - hs / 2}px;width:${hs}px;height:${hs}px;border-width:${bw}px;cursor:${d.length === 2 && d[0] !== "p" ? d + "-resize" : d === "n" || d === "s" ? "ns-resize" : d === "e" || d === "w" ? "ew-resize" : "move"}"></div>`).join("");
    }
    ov.innerHTML = h + (drag && drag.mode === "marquee" ? marqueeHtml() : ""); drawChkBox();
  }
  function marqueeHtml() {
    const m = drag.box, bw = 1 / scale;
    return `<div class="marquee" style="left:${m.x}px;top:${m.y}px;width:${m.w}px;height:${m.h}px;border-width:${bw}px"></div>`;
  }

  // ---------------------------------------------------------------- 요청 표시(초안·대기·처리 중) - 번호 배지 + 영역
  function regionBox(rg) {
    if (!rg) return null;
    if (rg.box) return rg.box;
    if (rg.points && rg.points.length) {
      const xs = rg.points.map((p) => p[0]), ys = rg.points.map((p) => p[1]);
      return [Math.min(...xs), Math.min(...ys), Math.max(...xs) - Math.min(...xs), Math.max(...ys) - Math.min(...ys)];
    }
    return null;
  }
  function renderMarks() {
    const s = slide(), M = $("#marks"), D = $("#draw"); if (!M || !D) return;
    let h = "", svg = "";
    if (s && S.mode !== "draw" && LS.get("langTag", "1") === "1") {  // 코드 요소 언어 이름표(⋯ 더보기에서 끄고 켬, 기본 켜짐) - 편집 화면에만(슬라이드·발표·PPTX 에는 없음). 크기는 확대와 무관하게 일정
      const inv = 1 / scale;
      for (const e of s.elements) if (e.type === "code" && e.lang) {  // 언어를 고르지 않았거나 일반 글자면 이름표 없음
        const k = Render.langOf(e); if (k === "plain") continue;
        h += `<div class="langtag" style="left:${e.x + e.w}px;top:${e.y}px;transform:translate(-100%, -100%) scale(${inv});transform-origin:100% 100%" title="코드 언어 - 서식 줄 또는 속성 탭에서 바꾼다">${esc(langLabel(k))}</div>`;
      }
    }
    if (s) {
      const list = S.reqs.filter((r) => r.slide === s.id && r.status !== "done");
      list.forEach((r, k) => {
        const st = r.status === "draft" ? "" : r.status, n = k + 1, inv = 1 / scale;
        let bx = null;
        if (r.region) {
          const g = r.region;
          if (g.kind === "pin" && g.points) { const [x, y] = g.points[0]; svg += `<circle class="pin" cx="${x}" cy="${y}" r="${7 * inv}"></circle>`; bx = [x, y, 0, 0]; }
          else if (g.kind === "pen" && g.points) { svg += `<path class="${st}" d="M${g.points.map((p) => p.join(" ")).join(" L")}"></path>`; bx = regionBox(g); }
          else if (g.box) { svg += `<rect class="dr ${st}" x="${g.box[0]}" y="${g.box[1]}" width="${g.box[2]}" height="${g.box[3]}" rx="4"></rect>`; bx = g.box; }
        } else if (r.element || (r.elements && r.elements.length)) {
          for (const id of (r.elements && r.elements.length ? r.elements : [r.element])) {  // 여러 요소면 모두 테두리, 번호는 첫 요소에
            const el = elById(id, s);
            if (el) { const b = boxOf(el); if (!bx) bx = [b.x, b.y, b.w, b.h]; h += `<div class="mk ${st}" style="left:${b.x - 3}px;top:${b.y - 3}px;width:${b.w + 6}px;height:${b.h + 6}px;border-width:${2 * inv}px"></div>`; }
          }
        }
        if (!bx) bx = [16 + k * 30, 16, 0, 0];
        h += `<div class="mkn ${st}" title="${esc(r.text)}" style="left:${bx[0]}px;top:${bx[1]}px;transform:translate(-50%,-50%) scale(${inv})">${n}</div>`;
      });
    }
    if (S.drawing) svg += S.drawing.svg || "";
    const cm = s && chgOf(s.id);  // 밖에서 바뀐 요소 - 파란 점선
    if (cm) for (const id of cm) { const el = elById(id); if (!el) continue; const b = boxOf(el); h += `<div class="chgbox" style="left:${b.x - 4}px;top:${b.y - 4}px;width:${b.w + 8}px;height:${b.h + 8}px;border-width:${2 / scale}px"></div>`; }
    M.innerHTML = h; D.innerHTML = svg;
    renderMarkbar();
  }
  function renderMarkbar() {
    const drafts = S.reqs.filter((r) => r.status === "draft");
    const here = s => drafts.filter((r) => r.slide === s).length;
    const s = slide();
    $("#markbar").classList.toggle("show", drafts.length > 0);
    $("#markMsg").textContent = drafts.length ? `표시한 요청 ${drafts.length}개를 세션에 보낼까요?${s && here(s.id) !== drafts.length ? ` (이 슬라이드 ${here(s.id)}개)` : ""}` : "";
    $("#markSend").textContent = `요청 ${drafts.length}개 보내기`;
    $("#markDiscard").textContent = s && here(s.id) ? "이 슬라이드 취소" : "모두 취소";
  }

  // ---------------------------------------------------------------- 모드
  const MODE_HINT = { edit: "요소를 끌어 옮기고, 두 번 눌러 글자를 고친다", pick: "요소를 눌러 요청 메모를 단다 → 아래 바에서 한꺼번에 보내기", draw: "영역을 그려 요청 메모를 단다 → 아래 바에서 한꺼번에 보내기" };
  function setMode(m) {
    if (S.editing) endEdit(true);
    S.mode = m; LS.set("mode", m);
    document.body.classList.remove("m-edit", "m-pick", "m-draw"); document.body.classList.add("m-" + m);
    $$("#modeSeg button").forEach((b) => b.classList.toggle("on", b.dataset.mode === m));
    $("#modeHint").textContent = MODE_HINT[m];
    closeMemo(); drawSel(); renderFtb();
  }
  function setTool(t) { S.tool = t; $$("#drawTools [data-tool]").forEach((b) => b.classList.toggle("on", b.dataset.tool === t)); document.body.classList.toggle("t-pin", t === "pin"); }

  // ---------------------------------------------------------------- 메모 팝오버
  const QUICK = {
    text: ["다듬기", "더 길게", "더 짧게", "검증"], bullets: ["항목 줄이기", "두 장으로 나누기", "글자 크게"],
    table: ["두 장으로 나누기", "열 너비 맞추기", "글자 크게"], "plan-table": ["설명 다듬기", "글자 크게"],
    code: ["강조 줄 다시", "주석 정리", "글자 크게"], plan: ["강조 다시", "글자 크게"],
    pill: ["문구 바꾸기", "색 맞추기"], rect: ["정렬 맞추기", "꾸미기", "크기 맞추기"], ellipse: ["정렬 맞추기", "꾸미기"],
    arrow: ["방향 바꾸기", "정렬 맞추기"], line: ["정렬 맞추기"], image: ["크기 맞추기", "위치 바꾸기"],
    region: ["이 영역 정리", "겹침 해결", "여백 맞추기", "글자 크게"],
  };
  function openMemo(target) {
    S.memo = target;
    const many = (target.elements || []).filter((id) => elById(id));  // 여러 요소를 고른 채 - Shift/Ctrl+클릭·범위 선택
    if (many.length > 1) { target.elements = many; target.element = many[0]; } else delete target.elements;
    target.key = target.region ? null : S.id + "/" + slide().id + (target.elements ? "/" + target.elements.join("+") : target.element ? "/" + target.element : "");
    const el = target.element ? elById(target.element) : null;
    $("#memoTitle").textContent = target.region ? "영역 요청" : "요청";
    const label = (id) => { const x = elById(id); return x ? `${TYPE_KO[x.type] || x.type} ${x.id}` : id; };
    $("#memoTarget").textContent = `슬라이드 ${S.cur + 1}` + (target.elements ? ` · 요소 ${target.elements.length}개 (${target.elements.map(label).join(", ")})` : el ? ` · ${label(el.id)}` : target.region ? ` · ${{ rect: "박스", pen: "펜", pin: "핀" }[target.region.kind]}` : "");
    const ta = $("#memoTa"); ta.value = target.key ? typed(target.key) : ""; ta.placeholder = target.region ? (target.region.kind === "pin" ? "이 지점에서 무엇을 바꿀까요?" : "이 영역에서 무엇을 바꿀까요?") : target.elements ? `이 요소 ${target.elements.length}개에서 무엇을 바꿀까요?` : `이 ${el ? TYPE_KO[el.type] || "요소" : "슬라이드"}에서 무엇을 바꿀까요?`;
    let q = (target.region ? QUICK.region : (el && QUICK[el.type]) || []).slice();
    const issues = S.check ? S.check.issues.filter((x) => x.slide === slide().id && (!el || (x.elements || []).includes(el.id))) : [];
    if (issues.length) q.unshift("검사 결과 고치기");
    $("#memoQuick").innerHTML = q.map((t) => `<button data-q="${esc(t)}">${esc(t)}</button>`).join("");
    memoInput(); $("#memo").classList.add("show"); placeMemo(); ta.focus();
  }
  function closeMemo() { S.memo = null; $("#memo").classList.remove("show"); if (S.drawing) { S.drawing = null; renderMarks(); } }
  function memoInput() { if (S.memo && S.memo.key) keep(S.memo.key, $("#memoTa").value); const n = $("#memoTa").value.length; $("#memoCnt").textContent = `${n} / 2000`; $("#memoOk").disabled = !$("#memoTa").value.trim() && !(typeof ATT !== "undefined" && ATT.memo.length); }
  function placeMemo() {
    if (!S.memo) return;
    const m = $("#memo"), pane = $("#editPane").getBoundingClientRect(), st = $("#stage").getBoundingClientRect();
    let b = S.memo.region ? regionBox(S.memo.region) : null;
    if (!b && S.memo.element) { const el = elById(S.memo.element); if (el) { const x = boxOf(el); b = [x.x, x.y, x.w, x.h]; } }
    if (!b) b = [SW / 2, SH / 2, 0, 0];
    const L = st.left - pane.left + b[0] * scale, T = st.top - pane.top + b[1] * scale, W = b[2] * scale, Hh = b[3] * scale;
    const mw = m.offsetWidth || 320, mh = m.offsetHeight || 180;
    let x = L, y = T - mh - 8;                               // 기본: 요소 위쪽, 왼쪽 끝 맞춤(Genspark 와 같음)
    if (y < 8) y = T + Hh + 8;                               // 위쪽 공간이 없으면 아래로
    if (y + mh > pane.height - 8) { y = Math.max(8, Math.min(pane.height - mh - 8, T)); x = L + W + 10; } // 위아래 모두 모자라면 오른쪽
    x = Math.max(8, Math.min(x, pane.width - mw - 8)); y = Math.max(8, y);
    m.style.left = x + "px"; m.style.top = y + "px";
  }
  async function memoOk() {
    const t = $("#memoTa").value.trim(); if ((!t && !ATT.memo.length) || !S.memo) return;
    const body = { action: "add", status: "draft", slide: slide().id, element: S.memo.element || null, text: t || "(첨부 참고)" };
    if (S.memo.region) body.region = S.memo.region;
    if (S.memo.elements) body.elements = S.memo.elements;  // 여러 요소 - 첫 요소는 element 에도(옛 세션·표시 호환)
    if (ATT.memo.length) body.attachments = ATT.memo;
    const r = await api("POST", `/api/requests/${S.id}`, body);
    if (!r.ok) { toast("메모를 저장하지 못했습니다"); return; }
    if (S.memo.key) keep(S.memo.key, "");
    ATT.memo = []; attRender("memo");
    S.reqs = r.data; S.drawing = null; closeMemo(); afterReqs();
    toast("메모를 남겼습니다 - 아래 바에서 한꺼번에 보내기");
  }

  // ---------------------------------------------------------------- 요청 첨부 - 클립보드 그림(Ctrl+V)·끌어다 놓기·📎. 올리면 out/attach/<덱>/ 에 저장되고 요청의 attachments 로 담긴다
  const ATT = { memo: [], tab: [], fu: [], busy: 0 };
  const attIsImg = (a) => /^image\//.test(a.type || "");
  function attRender(which) {
    const box = $({ memo: "#memoAtt", tab: "#reqAtt", fu: "#fuAtt" }[which]); if (!box) return;
    box.innerHTML = ATT[which].map((a, i) => `<span class="a" title="${esc(a.name)} · ${Math.round((a.size || 0) / 1024)}KB" data-attv="${which}:${i}">${attIsImg(a) ? `<img src="${esc(BASE + a.url)}" alt="">` : `<span>📄</span>`}<span class="n">${esc(a.name)}</span><button class="x" data-attx="${which}:${i}" title="빼기">✕</button></span>`).join("")
      + (ATT.busy ? `<span class="a"><span class="spin"></span><span class="n">올리는 중…</span></span>` : "");
    if (which === "memo") memoInput();
  }
  function attUpload(which, files) {
    const list = [...files].filter((f) => f && f.size);
    if (!list.length) return;
    list.forEach((f) => {
      const rd = new FileReader();
      ATT.busy++; attRender(which);
      rd.onload = async () => {
        const data = String(rd.result).split(",")[1] || "";
        const name = f.name && f.name !== "image.png" ? f.name : `clip-${new Date().toISOString().slice(11, 19).replace(/:/g, "")}.${(f.type.split("/")[1] || "png").replace("jpeg", "jpg")}`;
        const r = await api("POST", `/api/attach/${S.id}`, { name, type: f.type, data });
        ATT.busy--;
        if (!r.ok) { toast("첨부하지 못했습니다: " + ((r.data && r.data.error) || r.status), 5000); attRender(which); return; }
        ATT[which].push(r.data); attRender(which);
      };
      rd.onerror = () => { ATT.busy--; attRender(which); toast("파일을 읽지 못했습니다"); };
      rd.readAsDataURL(f);
    });
  }
  function attFromClipboard(which, e) {
    const files = [];
    for (const it of (e.clipboardData && e.clipboardData.items) || []) if (it.kind === "file") { const f = it.getAsFile(); if (f) files.push(f); }
    if (!files.length) return false;
    e.preventDefault(); e.stopPropagation(); attUpload(which, files); return true;  // 같은 이벤트가 바깥(팝오버)의 핸들러에도 닿아 두 번 올라가지 않게
  }
  function attWire(el, which) {  // 붙여넣기·끌어다 놓기
    if (!el || el.dataset.attWired) return; el.dataset.attWired = "1";
    el.addEventListener("paste", (e) => attFromClipboard(which, e));
    el.addEventListener("dragover", (e) => { if ([...e.dataTransfer.types].includes("Files")) { e.preventDefault(); el.classList.add("dropping"); } });
    el.addEventListener("dragleave", () => el.classList.remove("dropping"));
    el.addEventListener("drop", (e) => { if (e.dataTransfer.files.length) { e.preventDefault(); e.stopPropagation(); el.classList.remove("dropping"); attUpload(which, e.dataTransfer.files); } });
  }
  function attPick(which) { const f = $("#attFile"); f.onchange = () => { attUpload(which, f.files); f.value = ""; }; f.click(); }
  const attUrl = (a) => BASE + (a.url || "/" + a.path);  // 중계(/w/<id>/)면 접두를 붙인 주소
  function attListHtml(list, rid) {  // 요청 목록의 축소판(읽기 전용) - 누르면 라이트박스(새 창 없음)
    if (!list || !list.length) return "";
    return `<div class="att ro">${list.map((a, i) => `<a class="a" href="${esc(attUrl(a))}" data-lb="${esc(rid || "")}:${i}" title="${esc(a.name)}">${attIsImg(a) ? `<img src="${esc(attUrl(a))}" alt="" loading="lazy">` : "📄"}<span class="n">${esc(a.name)}</span></a>`).join("")}</div>`;
  }
  const lbItems = (list) => (list || []).map((a) => ({ url: attUrl(a), name: a.name, size: a.size, type: a.type }));
  function attLightbox(rid, i) {  // 그 요청의 첨부부터, 토글로 이 슬라이드의 모든 요청 첨부
    const r = S.reqs.find((x) => x.id === rid); if (!r) return;
    const all = S.reqs.filter((x) => x.slide === r.slide && x.attachments && x.attachments.length).flatMap((x) => lbItems(x.attachments));
    NexaLightbox.open(lbItems(r.attachments), i, { title: `슬라이드 ${S.deck.slides.findIndex((s) => s.id === r.slide) + 1}`, alt: { label: "이 슬라이드의 모든 요청 첨부", items: all } });
  }
  async function sendDrafts() {
    const n = S.reqs.filter((r) => r.status === "draft").length; if (!n) return;
    const r = await api("POST", `/api/requests/${S.id}`, { action: "send" });
    if (!r.ok) { toast("보내지 못했습니다"); return; }
    S.reqs = r.data; afterReqs(); await flushReqs(true);
    toast(S.session && S.session.connected ? `요청 ${n}개를 세션에 보냈습니다` : `요청 ${n}개를 대기로 올렸습니다 - 세션이 연결되면 전달됩니다`, 3500);
  }
  /** 이 슬라이드에 초안이 있으면 그 슬라이드만, 없으면 전체 초안을 지운다(Genspark 와 같은 범위) */
  async function discardDrafts() {
    const here = S.reqs.some((r) => r.status === "draft" && r.slide === slide().id);
    const r = await api("POST", `/api/requests/${S.id}`, here ? { action: "discard", slide: slide().id } : { action: "discard" });
    if (r.ok) { S.reqs = r.data; afterReqs(); toast(here ? "이 슬라이드의 메모를 지웠습니다" : "모든 메모를 지웠습니다"); }
  }
  /** 바로 요청(모드 바 ✨ 버튼) - 초안을 거치지 않고 대기로 올리고 즉시 전달 */
  async function quickRequest(text) {
    const r = await api("POST", `/api/requests/${S.id}`, { action: "add", status: "open", slide: slide().id, element: null, text });
    if (!r.ok) { toast("요청하지 못했습니다"); return; }
    S.reqs = r.data; afterReqs(); await flushReqs(true);
    toast(S.session && S.session.connected ? "세션에 바로 요청했습니다" : "요청을 남겼습니다 - 세션이 연결되면 전달됩니다", 3000);
  }
  function aiFix() {
    const s = slide(), its = S.check ? S.check.issues.filter((x) => x.slide === s.id) : [];
    if (!its.length) { toast("이 슬라이드는 검사 결과가 없습니다"); return; }
    quickRequest(`이 슬라이드의 레이아웃 검사 결과를 고쳐 줘 - 기존 디자인·구성은 유지하고, 요소를 지워서 경고를 없애지 말 것.\n` +
      its.map((x) => `- ${x.severity} ${x.rule}: ${x.message}`).join("\n"));
  }
  function aiPolish() { quickRequest("이 슬라이드를 다듬어 줘 - 기존 스타일·레이아웃 규칙은 유지하고, 내용 논리·문장 길이·정렬·여백만 정리. 원문(각주 근거)의 의미는 바꾸지 말 것."); }
  function afterReqs() { renderReqs(); renderThumb(S.cur); renderMarks(); }

  // ---------------------------------------------------------------- 그리기 모드(영역)
  function drawDown(e) {
    const p = toSlide(e);
    if (S.tool === "pin") { openMemo({ region: { kind: "pin", points: [[Math.round(p.x), Math.round(p.y)]] } }); S.drawing = { svg: `<circle class="pin" cx="${p.x}" cy="${p.y}" r="${7 / scale}"></circle>` }; renderMarks(); return; }
    S.drawing = { kind: S.tool, p0: p, pts: [[p.x, p.y]], svg: "" };
    closeMemo(); S.drawing = { kind: S.tool, p0: p, pts: [[p.x, p.y]], svg: "" };
    e.preventDefault();
  }
  function drawMove(e) {
    const d = S.drawing; if (!d || !d.p0) return;
    const p = toSlide(e);
    if (d.kind === "rect") {
      const x = Math.min(p.x, d.p0.x), y = Math.min(p.y, d.p0.y), w = Math.abs(p.x - d.p0.x), h = Math.abs(p.y - d.p0.y);
      d.box = [Math.round(x), Math.round(y), Math.round(w), Math.round(h)];
      d.svg = `<rect class="dr" x="${x}" y="${y}" width="${w}" height="${h}" rx="4"></rect>`;
    } else {
      const last = d.pts[d.pts.length - 1];
      if (Math.hypot(p.x - last[0], p.y - last[1]) > 3 / scale) d.pts.push([Math.round(p.x), Math.round(p.y)]);
      d.svg = `<path d="M${d.pts.map((q) => q.join(" ")).join(" L")}"></path>`;
    }
    renderMarks();
  }
  function drawUp() {
    const d = S.drawing; if (!d || !d.p0) return;
    d.p0 = null;
    if (d.kind === "rect" && (!d.box || d.box[2] < 6 || d.box[3] < 6)) { S.drawing = null; renderMarks(); return; }
    if (d.kind === "pen" && d.pts.length < 3) { S.drawing = null; renderMarks(); return; }
    const region = d.kind === "rect" ? { kind: "rect", box: d.box } : { kind: "pen", points: d.pts, box: regionBox({ points: d.pts }) };
    const svg = d.svg; openMemo({ region }); S.drawing = { svg }; renderMarks();
  }

  // ---------------------------------------------------------------- 서식 도구줄(편집 모드 · 요소 선택)
  const TEXTY = new Set(["text", "pill", "rect", "ellipse", "shape"]);
  const SIZED = new Set(["text", "pill", "rect", "ellipse", "shape", "bullets", "table", "plan-table", "code", "plan", "chart"]);
  const TYPE_KO = { text: "글자", pill: "칩", rect: "상자", ellipse: "원", image: "그림", line: "선", arrow: "화살표", table: "표", "plan-table": "실행계획 표", code: "코드", plan: "실행계획", bullets: "글머리", curve: "곡선", shape: "도형", group: "묶음", chart: "차트", icon: "아이콘" };
  const SIZE_PRESETS = [10, 11, 12, 13, 14, 15, 16, 17, 18, 20, 22, 24, 28, 32, 36, 40, 48, 60, 72];
  function defSize(el) { return { pill: 14, code: 15, plan: 14, "plan-table": 15, table: 16 }[el.type] || 20; }
  function swatch(v) { return v ? Render.fillCss(v) : "transparent"; }  // 토큰·#hex(투명도)·그라데이션 객체 모두
  const fillLabel = (v) => !v ? "없음" : typeof v === "object" ? "그라데이션·투명도 (요소 JSON 에서 고침)" : v;
  // 서식 줄 - 요소 종류마다 자주 쓰는 설정을 바로 고친다(속성 탭과 같은 값). 종류별 "종류" 선택 → 글자 → 면·테두리/종류별 설정 → 공통(링크·그림자·회전) → 복제·삭제·잠금·위치·메모
  const ROTATABLE = (x) => !isLine(x) && !["table", "plan-table", "bullets", "code", "plan"].includes(x.type);
  const hasShadow = (x) => hasFill(x) || x.type === "image";
  function renderFtb() {
    const F = $("#ftb"), el = selEl();
    if (S.mode !== "edit" || !el || S.editing) { F.classList.remove("show"); F.innerHTML = ""; return; }
    const lk = !!el.locked, t = el.type; let h = "";
    const sel = (f, title, opts, cur) => `<select data-f="${f}" title="${title}">${opts.map(([k, l]) => `<option value="${esc(k)}"${cur === k ? " selected" : ""}>${esc(l)}</option>`).join("")}</select>`;
    const sw = (f, icon, title, v, dflt) => `<button class="ib" data-f="${f}" title="${title} - ${esc(fillLabel(v))}">${icon}<span class="sw" style="background:${swatch(v || dflt)}"></span></button>`;
    const vsep = `<span class="vsep"></span>`;
    if (t === "shape") h += sel("shape", "도형 종류", Render.shapeNames(), el.shape);
    if (t === "chart") h += sel("chart", "차트 종류", CHART_KINDS.map(([k, , l]) => [k, l]), el.chart || "column");
    if (t === "icon") h += sel("icon", "아이콘 종류", Render.iconNames(), el.icon);
    if (SIZED.has(t)) {
      const sz = el.size || defSize(el);
      if (TEXTY.has(t) || t === "table" || t === "bullets") h += `<select data-f="font" title="글꼴 역할 - 세트의 본문·제목·고정폭 글꼴 중 어느 것을 쓰는지${t === "table" ? " (표 본문 셀 - 열별 글꼴 colFont 가 없는 열)" : ""}"><option value="body"${!el.font || el.font === "body" ? " selected" : ""}>본문 글꼴</option><option value="heading"${el.font === "heading" ? " selected" : ""}>제목 글꼴</option><option value="mono"${el.font === "mono" ? " selected" : ""}>고정폭(코드)</option></select>`;
      h += `<input class="num" type="number" min="6" max="400" step="1" data-f="size" value="${sz}" title="글자 크기(px) - PPT pt = px × 0.75">
        <button class="ib" data-f="sizePreset" title="크기 프리셋">▾</button><span class="pt" title="PowerPoint 글자 크기">${+(sz * 0.75).toFixed(2)}pt</span>`;
      if (TEXTY.has(t) || t === "bullets") h += `<button class="ib" data-f="color" title="글자색 - ${esc(el.color || "기본")}"><b style="text-decoration:underline;text-decoration-color:${swatch(el.color || "on-surface")};text-decoration-thickness:3px">A</b></button>`;
      if (TEXTY.has(t)) {
        const bold = el.bold === undefined ? t === "pill" : !!el.bold;
        h += `${vsep}<button class="ib${bold ? " on" : ""}" data-f="bold" title="굵게 (Ctrl+B)"><b>B</b></button>`;
        const al = el.align || (t === "pill" || t === "ellipse" || t === "shape" ? "center" : "left");
        h += vsep + [["left", "⯇≡", "왼쪽"], ["center", "≡", "가운데"], ["right", "≡⯈", "오른쪽"]].map(([k, i, tt]) => `<button class="ib${al === k ? " on" : ""}" data-f="align" data-v="${k}" title="${tt} 정렬">${i}</button>`).join("");
        h += `<button class="ib" data-f="spacing" title="줄 간격·세로 정렬">↕ ▾</button>`;
        if (t === "text") h += `<button class="ib" data-f="conv" data-v="bullets" title="글머리 목록으로 바꾸기 - 줄마다 항목(앞에 공백 두 칸 = 하위 항목, 글 앞의 번호·기호는 자동 감지)">≡</button>`;
      }
      if (t === "bullets") {
        h += `${vsep}<button class="ib" data-f="marker" title="글머리 종류 - 항목 ${esc(el.marker || "●")} · 하위 ${esc(el.subMarker || "–")} (글 앞에 직접 적은 번호·기호가 우선)">${esc(el.marker === "none" ? "없음" : el.marker || "●")} ▾</button>` + sw("dot", "●", "점 색(기호 글머리)", el.dot, "primary")
          + `<button class="ib" data-f="spacing" title="줄 높이 · 항목 간격 · 하위 크기">↕ ▾</button><button class="ib" data-f="conv" data-v="text" title="글자 상자로 바꾸기 - 항목을 줄로 펼침(하위 항목은 앞에 공백 두 칸)">T</button>`;
      }
      if (t === "table") h += vsep + [["row+", "＋행", "맨 아래에 행 추가"], ["row-", "－행", "맨 아래 행 지우기"], ["col+", "＋열", "맨 오른쪽에 열 추가"], ["col-", "－열", "맨 오른쪽 열 지우기"]].map(([k, l, tt]) => `<button class="ib" data-f="tblop" data-v="${k}" title="${tt}">${l}</button>`).join("")
        + `<span class="pt" title="행 × 열">${(el.rows || []).length}×${((el.rows || [])[0] || []).length}</span>` + sw("headFill", "▀", "머리 행 면", el.headFill, "surface-container-high") + sw("headColor", "A", "머리 행 글자색", el.headColor, "on-surface");
      if (t === "chart") {
        const lg = el.legend || (((el.series || []).length > 1 || el.chart === "pie" || el.chart === "doughnut") ? "bottom" : "none");
        h += `${vsep}<button class="ib" data-f="legend" title="범례 - 누를 때마다 바뀜 (없음 → 아래 → 오른쪽)">${{ none: "범례 없음", bottom: "범례 아래", right: "범례 오른쪽" }[lg]}</button><button class="ib${el.labels ? " on" : ""}" data-f="labels" title="값 표시">값</button><button class="ib${el.grid === false ? "" : " on"}" data-f="grid" title="눈금선">▦</button>`;
      }
    }
    if (hasFill(el)) h += vsep + sw("fill", "🪣", "채우기", el.fill);
    if (hasStroke(el)) h += sw("stroke", "▢", "테두리", el.stroke);
    if (t === "icon") h += vsep + sw("fill", "🎨", "아이콘 색", el.fill) + sw("color", "◐", "대비 색(안쪽 무늬)", el.color);
    if (t === "image") h += `${vsep}<input class="num" type="number" min="0" max="100" step="5" data-f="opacity" value="${Math.round((el.opacity == null ? 1 : el.opacity) * 100)}" title="투명도 % (100 = 그대로)" style="width:58px"><span class="pt" style="min-width:0">%</span><button class="ib${el.crop && el.crop.some((v) => v) ? " on" : ""}" data-f="crop" title="자르기 % - 왼쪽·위·오른쪽·아래">✂ ▾</button>${sel("effect", "프레임 효과 - 원본은 그대로", EFFECTS, el.effect || "")}<button class="ib" data-f="imgpick" title="그림 바꾸기 - 새 그림 파일을 올려 이 자리에(폭 유지, 높이는 비율로)">🖼</button>${el.mermaid != null ? `<button class="ib" data-f="mermaid" title="다이어그램 코드 수정 (mermaid)">⌘</button>` : ""}`;
    if (t === "group") h += `${vsep}<button class="ib" data-f="ungroup" title="묶음 풀기 (Ctrl+Shift+G) - 자식 ${(el.children || []).length}개를 낱개로">⧈ 풀기</button>`;
    if (isLine(el)) {
      h += `<button class="ib" data-f="color" title="선 색">━<span class="sw" style="background:${swatch(el.color || "on-surface")}"></span></button>
        <input class="num" type="number" min="0.5" max="20" step="0.5" data-f="width" value="${el.width || 2}" title="두께(px)">
        <button class="ib" data-f="head" title="화살 머리 - 누를 때마다 바뀜">${{ none: "-", end: "→", start: "←", both: "↔" }[el.head || (el.type === "arrow" ? "end" : "none")]}</button>
        <button class="ib" data-f="dash" title="선 모양 - 누를 때마다 바뀜">${{ solid: "실선", dash: "파선", dot: "점선" }[el.dash || "solid"]}</button>`;
    }
    if (t === "code") h += `${vsep}<button class="ib" data-f="lang" title="코드 언어 - ${el.lang ? esc(langLabel(Render.langOf(el))) : "지정 안 함(SQL 색)"}">${el.lang ? esc(langLabel(Render.langOf(el))) : "언어"} ▾</button><button class="ib${el.lineNo === false ? "" : " on"}" data-f="lineno" title="줄 번호">#</button><button class="ib" data-f="copy" title="코드를 클립보드에 복사">📋</button>`;
    // 공통 - 링크(선 제외) · 그림자(면이 있는 것·그림) · 회전·뒤집기
    if (!isLine(el) || hasShadow(el) || ROTATABLE(el)) h += vsep;
    if (!isLine(el)) h += `<button class="ib${el.link ? " on" : ""}" data-f="link" title="링크 - ${esc(el.link || "없음")} (발표 화면에서 누르면 이동 · PPTX 도 같음)">🔗</button>`;
    if (hasShadow(el)) h += `<button class="ib${el.shadow ? " on" : ""}" data-f="shadow" title="그림자">◱</button>`;
    if (ROTATABLE(el)) h += `<button class="ib${el.rot || el.flipH || el.flipV ? " on" : ""}" data-f="rot" title="회전·뒤집기 - 지금 ${el.rot || 0}°${el.flipH ? " · 좌우" : ""}${el.flipV ? " · 상하" : ""}">↻ ▾</button>`;
    h += `${vsep}<button class="ib" data-f="dup" title="복제 (Ctrl+D)">⧉</button>
      <button class="ib" data-f="del" title="삭제 (Delete)" ${lk ? "disabled" : ""}>🗑</button>
      <button class="ib${lk ? " on" : ""}" data-f="lock" title="잠금 - 끌기·삭제 막기">🔒</button>
      <button class="ib" data-f="pos" title="위치 조정 - 정렬·순서·크기·좌표">✥ ▾</button>
      <span class="vsep"></span><button class="ib" data-f="memo" title="${isMulti() ? `이 요소 ${selIds().length}개에 요청 메모(세션에 보냄)` : "이 요소에 요청 메모(세션에 보냄)"}">💬</button>`;
    if (isMulti()) h = `<span class="multi-n" title="Shift/Ctrl+클릭으로 더하거나 빼기 · 빈 곳을 끌어 범위 선택 · Esc 해제. 서식은 그 속성이 있는 요소에만 적용">${selIds().length}개 선택</span><span class="vsep"></span>` + h;
    F.innerHTML = h; F.classList.add("show");
  }
  // 선택한 요소 모두에 같은 변경 - ok(요소)가 거짓인 요소는 건너뛴다(그 속성이 없는 종류). 서식 줄·위치 조정·속성 탭이 쓴다
  function mutate(fn, ok) {
    const els = selEls().filter((x) => !ok || ok(x)); if (!els.length) return;
    snapshot(); for (const el of els) { fn(el); if (isLine(el)) Object.assign(el, Render.lineBox(el)); } afterChange();
  }
  const hasFill = (x) => ["rect", "ellipse", "pill", "text", "plan", "shape"].includes(x.type);
  const hasStroke = (x) => ["rect", "ellipse", "pill", "text", "shape"].includes(x.type);
  const hasColor = (x) => TEXTY.has(x.type) || x.type === "bullets" || isLine(x);
  function palette(anchor, cur, allowNone, apply) {
    const T = S.tokens, groups = Object.entries(T.groups || {});
    const items = [];
    if (allowNone) items.push({ label: "없음", on: !cur, act: () => apply("") });
    for (const [g, names] of groups) {
      items.push({ h: g });
      items.push({ html: `<div class="pal">${names.map((n) => `<button data-c="${esc(n)}" class="${n === cur ? "on" : ""}" title="${esc(n)} ${Render.color(n)}" style="background:${Render.color(n)}"></button>`).join("")}</div>`,
        bind: (node) => node.addEventListener("click", (e) => { const b = e.target.closest("[data-c]"); if (b) { closeMenu(); apply(b.dataset.c); } }) });
    }
    openMenu(anchor, items);
  }
  function posMenu(anchor) {
    const el = selEl(); if (!el) return;
    if (isMulti()) return multiPosMenu(anchor);
    const b = boxOf(el);
    const al = (k) => mutate((e) => {
      if (isLine(e)) return;
      if (k === "l") e.x = 0; if (k === "c") e.x = Math.round((SW - e.w) / 2); if (k === "r") e.x = SW - e.w;
      if (k === "t") e.y = 0; if (k === "m") e.y = Math.round((SH - e.h) / 2); if (k === "b") e.y = SH - e.h;
    });
    openMenu(anchor, [
      { h: "슬라이드 기준 정렬" },
      { icon: "⇤", label: "왼쪽 정렬", act: () => al("l") }, { icon: "↔", label: "가로 중앙", act: () => al("c") }, { icon: "⇥", label: "오른쪽 정렬", act: () => al("r") }, "-",
      { icon: "⤒", label: "위쪽 정렬", act: () => al("t") }, { icon: "↕", label: "세로 중앙", act: () => al("m") }, { icon: "⤓", label: "아래쪽 정렬", act: () => al("b") }, "-",
      { icon: "▲", label: "앞으로 가져오기", key: "Ctrl+]", act: () => zorder("fwd") }, { icon: "▼", label: "뒤로 보내기", key: "Ctrl+[", act: () => zorder("bwd") },
      { icon: "⏫", label: "맨 앞으로 가져오기", key: "Alt+Ctrl+]", act: () => zorder("front") }, { icon: "⏬", label: "맨 뒤로 보내기", key: "Alt+Ctrl+[", act: () => zorder("back") }, "-",
      { html: `<div class="pos">${isLine(el) ? ["x1", "y1", "x2", "y2"].map((k) => `<div class="r"><label>${k}</label><input type="number" data-p="${k}" value="${el[k]}"> px</div>`).join("")
          : `<div class="r"><label>너비</label><input type="number" data-p="w" value="${b.w}"> <label>높이</label><input type="number" data-p="h" value="${b.h}"></div>
             <div class="r"><label>X</label><input type="number" data-p="x" value="${b.x}"> <label>Y</label><input type="number" data-p="y" value="${b.y}"></div>`}
          <div class="hint" style="margin:0">px · 슬라이드 1280×720</div></div>`,
        bind: (node) => node.addEventListener("change", (e) => { const k = e.target.dataset.p; if (k) mutate((x) => { x[k] = Math.round(+e.target.value); }); }) },
    ]);
  }
  // 다중 선택 위치 조정 - 고른 요소 묶음 기준 정렬, 가로·세로 같은 간격 분배, 같은 크기
  function multiPosMenu(anchor) {
    const els = selEls().filter((x) => !x.locked && !isLine(x)); const bs = els.map(boxOf);
    if (els.length < 2) { toast("잠기지 않은 상자 요소를 2개 이상 고르세요"); return; }
    const X1 = Math.min(...bs.map((b) => b.x)), Y1 = Math.min(...bs.map((b) => b.y)), X2 = Math.max(...bs.map((b) => b.x + b.w)), Y2 = Math.max(...bs.map((b) => b.y + b.h));
    const run = (fn) => { snapshot(); fn(); afterChange(); };
    const al = (k) => run(() => els.forEach((e) => {
      if (k === "l") e.x = X1; if (k === "c") e.x = Math.round((X1 + X2) / 2 - e.w / 2); if (k === "r") e.x = X2 - e.w;
      if (k === "t") e.y = Y1; if (k === "m") e.y = Math.round((Y1 + Y2) / 2 - e.h / 2); if (k === "b") e.y = Y2 - e.h;
    }));
    const dist = (ax) => run(() => {  // 양 끝은 그대로, 사이 간격을 같게
      const p = ax === "x" ? "x" : "y", d = ax === "x" ? "w" : "h", ord = [...els].sort((a, b) => a[p] - b[p]);
      const span = ord[ord.length - 1][p] + ord[ord.length - 1][d] - ord[0][p], sum = ord.reduce((t, e) => t + e[d], 0), gap = (span - sum) / (ord.length - 1);
      let cur = ord[0][p]; ord.forEach((e) => { e[p] = Math.round(cur); cur += e[d] + gap; });
    });
    const same = (k) => run(() => els.forEach((e) => { if (k !== "h") e.w = el.w; if (k !== "w") e.h = el.h; }));
    const el = selEl();
    openMenu(anchor, [
      { h: `선택한 ${els.length}개 기준 정렬` },
      { icon: "⇤", label: "왼쪽 맞춤", act: () => al("l") }, { icon: "↔", label: "가로 가운데", act: () => al("c") }, { icon: "⇥", label: "오른쪽 맞춤", act: () => al("r") }, "-",
      { icon: "⤒", label: "위쪽 맞춤", act: () => al("t") }, { icon: "↕", label: "세로 가운데", act: () => al("m") }, { icon: "⤓", label: "아래쪽 맞춤", act: () => al("b") }, "-",
      { h: "분배 (3개 이상)" },
      { icon: "⇹", label: "가로 같은 간격", disabled: els.length < 3, act: () => dist("x") }, { icon: "⇳", label: "세로 같은 간격", disabled: els.length < 3, act: () => dist("y") }, "-",
      { h: "크기 맞추기 (주 선택 기준)" },
      { label: "같은 너비", act: () => same("w") }, { label: "같은 높이", act: () => same("h") }, { label: "같은 크기", act: () => same("wh") }, "-",
      { icon: "⏫", label: "맨 앞으로 가져오기", act: () => zorder("front") }, { icon: "⏬", label: "맨 뒤로 보내기", act: () => zorder("back") },
    ]);
  }
  // 서식 줄 언어 고르기 - 찾기 칸이 있는 메뉴
  function langMenu(anchor) {
    const cur = Render.langOf(selEl());
    openMenu(anchor, [{ html: `<div class="lang-pick"><input type="search" placeholder="언어 찾기 - 이름·별칭" data-lq="1"><div class="lang-list"></div></div>`,
      bind: (node) => {
        const inp = node.querySelector("[data-lq]"), list = node.querySelector(".lang-list");
        const draw = () => {
          const q = inp.value.trim().toLowerCase();
          const ks = langKeys().filter((k) => !q || [k, S.langs[k].label, ...(S.langs[k].alias || [])].some((x) => x.toLowerCase().includes(q)));
          list.innerHTML = ks.map((k) => `<button data-lk="${esc(k)}" class="${k === cur ? "on" : ""}">${esc(S.langs[k].label)}<small>${esc(k)}</small></button>`).join("") || `<div class="hint">없음</div>`;
        };
        inp.addEventListener("input", draw);
        inp.addEventListener("keydown", (e) => { if (e.key === "Enter") { const b = list.querySelector("[data-lk]"); if (b) b.click(); } });
        list.addEventListener("click", (e) => { const b = e.target.closest("[data-lk]"); if (!b) return; closeMenu(); mutate((x) => { x.lang = b.dataset.lk; }, (x) => x.type === "code"); });
        draw(); setTimeout(() => inp.focus(), 0);
      } }]);
  }
  function zorder(k) {
    const s = slide(), els = selEls(); if (!els.length) return;
    snapshot();
    const order = (k === "fwd" || k === "back") ? [...els].sort((a, b) => s.elements.indexOf(b) - s.elements.indexOf(a)) : [...els].sort((a, b) => s.elements.indexOf(a) - s.elements.indexOf(b));
    if (k === "front" || k === "back") {  // 고른 요소들의 상대 순서를 지키며 맨 앞/뒤로
      const keep = s.elements.filter((x) => !els.includes(x)); els.forEach((x) => delete x.z);
      const sorted = [...els].sort((a, b) => s.elements.indexOf(a) - s.elements.indexOf(b));
      s.elements.splice(0, s.elements.length, ...(k === "front" ? [...keep, ...sorted] : [...sorted, ...keep]));
    } else {
      for (const el of order) {
        const i = s.elements.indexOf(el); s.elements.splice(i, 1); delete el.z;
        s.elements.splice(k === "fwd" ? Math.min(s.elements.length, i + 1) : Math.max(0, i - 1), 0, el);
      }
    }
    afterChange();
  }
  function onFtb(e) {
    const t = e.target.closest("[data-f]"); if (!t) return;
    const f = t.dataset.f, el = selEl(); if (!el) return;
    const same = (x) => x.type === el.type;
    if (e.type === "change") {
      if (f === "size") mutate((x) => { x.size = Math.max(6, Math.min(400, +t.value || defSize(x))); }, (x) => SIZED.has(x.type));
      if (f === "width") mutate((x) => { x.width = +t.value || 2; }, isLine);
      if (f === "font") mutate((x) => { if (t.value === "body") delete x.font; else x.font = t.value; }, (x) => TEXTY.has(x.type) || x.type === "table" || x.type === "bullets");
      if (f === "shape" || f === "chart" || f === "icon" || f === "effect") mutate((x) => setProp(x, f, t.value), same);
      if (f === "opacity") { const o = Math.max(0, Math.min(100, +t.value || 0)) / 100; mutate((x) => { if (o < 1) x.opacity = o; else delete x.opacity; }, (x) => x.type === "image"); }
      return;
    }
    if (t.tagName === "INPUT" || t.tagName === "SELECT") return;
    // ---- 종류별
    if (f === "dot") palette(t, el.dot, true, (c) => mutate((x) => { if (c) x.dot = c; else delete x.dot; }, (x) => x.type === "bullets"));
    if (f === "headFill") palette(t, el.headFill, true, (c) => mutate((x) => { if (c) x.headFill = c; else delete x.headFill; }, (x) => x.type === "table"));
    if (f === "headColor") palette(t, el.headColor, true, (c) => mutate((x) => { if (c) x.headColor = c; else delete x.headColor; }, (x) => x.type === "table"));
    if (f === "marker") openMenu(t, [
      { h: "항목" }, { html: `<div class="pal" style="grid-template-columns:repeat(6,auto)">${MARKER_OPTS.map(([k, l]) => `<button data-mk="${esc(k)}" class="${(el.marker || "●") === k ? " on" : ""}" style="width:auto;min-width:22px;padding:0 5px;background:#fff;font:12px var(--font)" title="${esc(l)}">${esc(l)}</button>`).join("")}</div>`, bind: (n) => n.addEventListener("click", (ev) => { const b = ev.target.closest("[data-mk]"); if (b) { closeMenu(); mutate((x) => setProp(x, "marker", b.dataset.mk), (x) => x.type === "bullets"); } }) },
      { h: "하위 항목" }, { html: `<div class="pal" style="grid-template-columns:repeat(6,auto)">${SUB_MARKER_OPTS.map(([k, l]) => `<button data-smk="${esc(k)}" class="${(el.subMarker || "–") === k ? " on" : ""}" style="width:auto;min-width:22px;padding:0 5px;background:#fff;font:12px var(--font)" title="${esc(l)}">${esc(l)}</button>`).join("")}</div>`, bind: (n) => n.addEventListener("click", (ev) => { const b = ev.target.closest("[data-smk]"); if (b) { closeMenu(); mutate((x) => setProp(x, "subMarker", b.dataset.smk), (x) => x.type === "bullets"); } }) }, "-",
      { label: "글 앞 번호·기호 감지", on: el.autoNum !== false, act: () => mutate((x) => setProp(x, "autoNum", x.autoNum === false ? "on" : "off"), (x) => x.type === "bullets") },
    ]);
    if (f === "spacing" && el.type === "bullets") {
      const lh = el.lineHeight || 1.4, gap = el.gap == null ? 14 : el.gap, sub = el.subSize || Math.round((el.size || defSize(el)) * 0.85);
      openMenu(t, [
        { h: `줄 높이 (지금 ${lh})` }, ...[1.0, 1.2, 1.3, 1.4, 1.5, 1.6, 1.8].map((v) => ({ label: String(v), on: Math.abs(lh - v) < 0.001, act: () => mutate((x) => { x.lineHeight = v; }, (x) => x.type === "bullets") })), "-",
        { h: `항목 간격 px (지금 ${gap})` }, ...[0, 6, 10, 14, 20, 28, 35, 44].map((v) => ({ label: String(v), on: gap === v, act: () => mutate((x) => { x.gap = v; }, (x) => x.type === "bullets") })), "-",
        { h: `하위 크기 px (지금 ${el.subSize || `자동 ${sub}`})` }, ...[-6, -4, -2, 0].map((d) => { const v = (el.size || defSize(el)) + d; return { label: `${v}${d ? ` (${d})` : " (같게)"}`, on: el.subSize === v, act: () => mutate((x) => { x.subSize = v; }, (x) => x.type === "bullets") }; }), { label: "자동", on: !el.subSize, act: () => mutate((x) => { delete x.subSize; }, (x) => x.type === "bullets") },
      ]);
      return;
    }
    if (f === "tblop") { snapshot(); tableOp(el, t.dataset.v); afterChange(); }
    if (f === "legend") { const o = ["none", "bottom", "right"], cur = el.legend || (((el.series || []).length > 1 || el.chart === "pie" || el.chart === "doughnut") ? "bottom" : "none"); const v = o[(o.indexOf(cur) + 1) % 3]; mutate((x) => setProp(x, "legend", v), same); }
    if (f === "labels") { const v = el.labels ? "off" : "on"; mutate((x) => setProp(x, "labels", v), same); }
    if (f === "grid") { const v = el.grid === false ? "on" : "off"; mutate((x) => setProp(x, "grid", v), same); }
    if (f === "crop") {
      const c = (el.crop || [0, 0, 0, 0]).map((v) => Math.round((v || 0) * 100));
      openMenu(t, [{ h: "자르기 % (왼쪽 · 위 · 오른쪽 · 아래)" }, { html: `<div style="display:flex;gap:4px;padding:4px 10px;align-items:center">${c.map((v, i) => `<input type="number" min="0" max="95" step="1" data-ci="${i}" value="${v}" title="${["왼쪽", "위", "오른쪽", "아래"][i]}" style="width:52px;border:1px solid var(--line);border-radius:6px;padding:3px 4px">`).join("")}<button class="chip sm primary" data-capply="1">적용</button></div>`,
        bind: (n) => { n.querySelector("[data-capply]").onclick = () => { const nv = [...n.querySelectorAll("[data-ci]")].map((i) => Math.max(0, Math.min(95, +i.value || 0)) / 100); closeMenu(); mutate((x) => { if (nv.some((v) => v)) x.crop = nv; else delete x.crop; }, (x) => x.type === "image"); }; n.addEventListener("keydown", (ev) => { if (ev.key === "Enter") n.querySelector("[data-capply]").click(); ev.stopPropagation(); }); } },
        "-", { label: "자르기 없음", disabled: !c.some(Boolean), act: () => mutate((x) => { delete x.crop; }, (x) => x.type === "image") }]);
    }
    if (f === "imgpick") imagePick(el);
    if (f === "mermaid") mermaidDialog(el);
    if (f === "ungroup") ungroupSel();
    if (f === "lineno") { const on = el.lineNo === false; mutate((x) => { if (on) delete x.lineNo; else x.lineNo = false; }, (x) => x.type === "code"); }
    if (f === "conv") { snapshot(); convertEl(el, t.dataset.v); afterChange(); }
    // ---- 공통
    if (f === "shadow") { const v = el.shadow ? "off" : "on"; mutate((x) => setProp(x, "shadow", v), hasShadow); }
    if (f === "link") openMenu(t, [{ h: "링크 - https://… · #3(슬라이드 번호) · #s07(슬라이드 id)" }, { html: `<div style="display:flex;gap:6px;padding:4px 10px"><input type="text" data-lk="1" value="${esc(el.link || "")}" placeholder="https://… · #3 · #s07" style="width:240px;border:1px solid var(--line);border-radius:6px;padding:4px 6px"><button class="chip sm primary" data-lapply="1">적용</button></div>`,
      bind: (n) => { const i = n.querySelector("[data-lk]"); n.querySelector("[data-lapply]").onclick = () => { const v = i.value; closeMenu(); mutate((x) => setProp(x, "link", v), (x) => !isLine(x)); }; i.addEventListener("keydown", (ev) => { if (ev.key === "Enter") n.querySelector("[data-lapply]").click(); ev.stopPropagation(); }); setTimeout(() => i.focus(), 20); } },
      "-", { label: "링크 지우기", disabled: !el.link, act: () => mutate((x) => { delete x.link; }, (x) => !isLine(x)) }]);
    if (f === "rot") openMenu(t, [
      { h: `회전 (지금 ${el.rot || 0}°) - 시계 방향, 중심 기준` }, ...[0, 90, 180, 270].map((v) => ({ label: `${v}°`, on: (el.rot || 0) === v, act: () => mutate((x) => setProp(x, "rot", v), ROTATABLE) })),
      { label: "+15°", act: () => mutate((x) => setProp(x, "rot", ((x.rot || 0) + 15) % 360), ROTATABLE) }, { label: "−15°", act: () => mutate((x) => setProp(x, "rot", ((x.rot || 0) - 15 + 360) % 360), ROTATABLE) }, "-",
      { icon: "⇋", label: "좌우 뒤집기", on: !!el.flipH, act: () => mutate((x) => { if (x.flipH) delete x.flipH; else x.flipH = true; }, ROTATABLE) },
      { icon: "⇅", label: "상하 뒤집기", on: !!el.flipV, act: () => mutate((x) => { if (x.flipV) delete x.flipV; else x.flipV = true; }, ROTATABLE) },
    ]);
    if (f === "sizePreset") openMenu(t, SIZE_PRESETS.map((v) => ({ label: `${v}px · ${+(v * 0.75).toFixed(2)}pt`, on: (el.size || defSize(el)) === v, act: () => mutate((x) => { x.size = v; }, (x) => SIZED.has(x.type)) })));
    if (f === "color") palette(t, el.color, false, (c) => mutate((x) => { x.color = c; }, hasColor));
    if (f === "fill") palette(t, el.fill, true, (c) => mutate((x) => { if (c) x.fill = c; else delete x.fill; }, hasFill));
    if (f === "stroke") palette(t, el.stroke, true, (c) => mutate((x) => { if (c) x.stroke = c; else delete x.stroke; }, hasStroke));
    if (f === "bold") { const on = !(el.bold === undefined ? el.type === "pill" : !!el.bold); mutate((x) => { x.bold = on; }, (x) => TEXTY.has(x.type)); }  // 주 선택 기준으로 모두 같은 값
    if (f === "align") mutate((x) => { x.align = t.dataset.v; }, (x) => TEXTY.has(x.type));
    if (f === "spacing") {
      const lh = el.lineHeight || (el.type === "text" ? 1.4 : 1.2), va = el.valign || (el.type === "text" ? "top" : "middle");
      openMenu(t, [
        { h: `줄 간격 (지금 ${lh})` }, ...[1.0, 1.2, 1.4, 1.5, 1.6, 1.8, 2.0].map((v) => ({ label: String(v), on: Math.abs(lh - v) < 0.001, act: () => mutate((x) => { x.lineHeight = v; }, (x) => TEXTY.has(x.type)) })), "-",
        { h: "세로 정렬" }, ...[["top", "위"], ["middle", "가운데"], ["bottom", "아래"]].map(([k, l]) => ({ label: l, on: va === k, act: () => mutate((x) => { x.valign = k; }, (x) => TEXTY.has(x.type)) })),
      ]);
    }
    if (f === "head") { const o = ["none", "end", "start", "both"], v = o[(o.indexOf(el.head || (el.type === "arrow" ? "end" : "none")) + 1) % 4]; mutate((x) => { x.head = v; }, isLine); }
    if (f === "dash") { const o = ["solid", "dash", "dot"], v = o[(o.indexOf(el.dash || "solid") + 1) % 3]; mutate((x) => { x.dash = v; }, isLine); }
    if (f === "copy") copyText(el.text || "");
    if (f === "lang") langMenu(t);
    if (f === "dup") dupEl();
    if (f === "del") delEl();
    if (f === "lock") { const on = !el.locked; mutate((x) => { if (on) x.locked = true; else delete x.locked; }); }
    if (f === "pos") posMenu(t);
    if (f === "memo") openMemo({ element: el.id, elements: selIds() });
  }

  // ---------------------------------------------------------------- 오른쪽 클릭 메뉴
  function ctxMenu(e) {
    if (S.mode !== "edit") return;
    const node = e.target.closest("#host .rs-el"); if (!node) return;
    e.preventDefault(); if (!selIds().includes(node.dataset.id)) select(node.dataset.id);
    const el = selEl(), lk = selEls().every((x) => x.locked);
    openMenu({ x: e.clientX, y: e.clientY }, [
      { label: isMulti() ? `복사 (${selIds().length}개)` : "복사", key: "Ctrl+C", act: () => { S.clip = selEls().map(clone); toast(`요소 ${S.clip.length}개 복사`); } },
      { label: "잘라내기", key: "Ctrl+X", disabled: lk, act: () => { S.clip = selEls().filter((x) => !x.locked).map(clone); delEl(); } },
      { label: "붙여넣기", key: "Ctrl+V", disabled: !S.clip, act: () => dupEl(S.clip) },
      { label: "복제", key: "Ctrl+D", act: () => dupEl() },
      { label: "묶기", key: "Ctrl+G", disabled: selEls().length < 2, act: () => groupSel() }, { label: "묶음 풀기", key: "Ctrl+Shift+G", disabled: !el || el.type !== "group", act: () => ungroupSel() },
      { label: "삭제", key: "Delete", disabled: lk, act: () => delEl() }, "-",
      { label: "앞으로 가져오기", key: "Ctrl+]", act: () => zorder("fwd") }, { label: "뒤로 보내기", key: "Ctrl+[", act: () => zorder("bwd") },
      { label: "맨 앞으로", key: "Alt+Ctrl+]", act: () => zorder("front") }, { label: "맨 뒤로", key: "Alt+Ctrl+[", act: () => zorder("back") }, "-",
      { label: "글자 편집", key: "Enter", act: () => startEdit(el) },
      { label: isMulti() ? `이 요소 ${selIds().length}개에 요청 메모` : "이 요소에 요청 메모", act: () => openMemo({ element: el.id, elements: selIds() }) },
    ]);
  }

  // ---------------------------------------------------------------- PPT 렌더 미리보기 · 내보내기
  async function loadPngs() { const r = await api("GET", `/api/render/${S.id}`); S.pngs = r.ok ? r.data.slides : []; }
  function renderPng() {
    if (!S.preview) return;
    const u = S.pngs[S.cur];
    $("#pngWrap").innerHTML = u ? `<img src="${esc(BASE + u)}" alt="">` : `<div class="empty">아직 렌더 없음 - "다시 렌더"</div>`;
    const stale = S.renderAt && S.deck && S.deck.updated && new Date(S.deck.updated).getTime() > S.renderAt;
    $("#pngInfo").textContent = u ? (stale ? "· 렌더 뒤에 편집됨 - 다시 렌더 필요" : "") : "";
    fitStage();
  }
  function togglePreview() { S.preview = !S.preview; document.body.classList.toggle("preview", S.preview); renderPng(); setTimeout(fitStage, 0); }
  async function doRender() {
    const b = $("#renderBtn"); b.disabled = true; b.innerHTML = `<span class="spin"></span> PowerPoint 렌더 중`;
    if (S.dirty) await save();
    const r = await api("POST", `/api/render/${S.id}`);
    b.disabled = false; b.textContent = "다시 렌더";
    if (r.ok) { S.pngs = r.data.slides; S.renderAt = Date.now(); renderPng(); toast("PowerPoint 렌더 완료"); }
    else toast("렌더 실패: " + (r.data && (r.data.error + " " + (r.data.log || "")) || r.status), 5000);
  }
  async function doExport(embed, install) {
    const b = $("#exportBtn"); b.disabled = true; b.innerHTML = `<span class="spin"></span> ${embed ? "글꼴 넣는 중" : "만드는 중"}`;
    if (S.dirty) await save();
    const r = await api("POST", `/api/export/${S.id}${embed ? `?embed=1${install ? "&install=1" : ""}` : ""}`);
    b.disabled = false; b.textContent = "내보내기 ▾";
    if (embed && r.status === 409 && r.data && r.data.needInstall) {  // PowerPoint 는 설치된 글꼴만 넣는다
      const names = r.data.needInstall.map((p) => p.split(/[\\/]/).pop()).join(", ");
      if (confirm(`PowerPoint 가 글꼴을 넣으려면 작업 공간 글꼴을 이 PC 에 설치해야 합니다(현재 사용자, 관리자 권한 불필요).

${names}

설치하고 계속할까요?`)) doExport(true, true);
      return;
    }
    const fn = (r.ok && r.data.name) || exportName(embed ? "-fonts.pptx" : ".pptx");  // 받는 파일 이름은 덱 제목(서버가 정한 이름 우선)
    if (r.ok) {
      const a = $("#dl"); a.href = BASE + r.data.url; a.setAttribute("download", fn); a.style.display = ""; a.textContent = `⬇ ${fn}`;
      toast(embed ? `글꼴을 넣은 PPTX 를 만들었습니다 - 글꼴 ${(r.data.typefaces || []).join(", ")} · ${r.data.sizeKB}KB` : "PPTX 를 만들었습니다 - ⬇ 로 받기 (쓴 글꼴은 out/" + S.id + ".fonts.json 에 기록)", 5000);
    }
    else toast("내보내기 실패: " + (r.data && (r.data.error + " " + (r.data.log || "")) || r.status), 6000);
  }
  /** 내보내기 파일 이름 = 덱 제목(파일 이름에 못 쓰는 글자는 공백으로) + 꼬리 - 저장 자체는 out/<id>… 이고 받을 때 이 이름이 된다(server.export_name 과 같은 규칙) */
  const exportName = (suffix) => ((S.deck && S.deck.title) || S.id).replace(/[\/:*?"<>|\u0000-\u001f]+/g, " ").replace(/\s+/g, " ").trim().slice(0, 120) + suffix;
  async function doExportPdf() {
    const b = $("#exportBtn"); b.disabled = true; b.innerHTML = `<span class="spin"></span> PDF 만드는 중`;
    if (S.dirty) await save();
    const r = await api("POST", `/api/export/${S.id}?pdf=1`);
    b.disabled = false; b.textContent = "내보내기 ▾";
    if (r.ok) { const fn = r.data.name || exportName(".pdf"); const a = $("#dl"); a.href = BASE + r.data.url; a.setAttribute("download", fn); a.style.display = ""; a.textContent = `⬇ ${fn}`; toast(`PDF 를 만들었습니다(${r.data.via === "powerpoint" ? "PowerPoint" : "Chrome"}) - ⬇ 로 받기`, 5000); }
    else toast("PDF 내보내기 실패: " + (r.data && (r.data.error + " " + (r.data.log || "")) || r.status), 8000);
  }
  function exportMenu(btn) {
    openMenu(btn, [
      { icon: "📄", label: "PPTX 내보내기 (편집 가능한 도형)", act: () => doExport() },
      { icon: "🔤", label: "PPTX 내보내기 - 글꼴 포함 (PowerPoint 필요)", act: () => doExport(true) },
      { icon: "🧾", label: "PDF 내보내기 (PowerPoint 또는 Chrome)", act: () => doExportPdf() },
      { icon: "📋", label: "쓴 글꼴 기록 보기 (마지막 내보내기)", act: () => window.open(`${BASE}/out/${S.id}.fonts.json`, "_blank") },
      { icon: "❓", label: "글꼴 받기·설치 안내", act: () => window.open(`${BASE}/studio/fonts.html`, "_blank") },
      { icon: "🖼", label: S.preview ? "PowerPoint 렌더 미리보기 닫기" : "PowerPoint 렌더 미리보기 (나란히)", act: togglePreview },
      { icon: "↻", label: "PowerPoint 로 다시 렌더 (Windows)", act: () => { if (!S.preview) togglePreview(); doRender(); } },
    ], { right: true });
  }

  // ---------------------------------------------------------------- 속성 패널(전체 속성 - 고급)
  function colorOptions(cur, allowNone) {
    const T = S.tokens; let h = allowNone ? `<option value="">(없음)</option>` : ""; let found = !cur;
    for (const [g, names] of Object.entries(T.groups)) {
      h += `<optgroup label="${esc(g)}">` + names.map((n) => { if (n === cur) found = true; return `<option value="${n}"${n === cur ? " selected" : ""}>${n}  ${Render.color(n)}</option>`; }).join("") + `</optgroup>`;
    }
    if (!found && cur) h += `<option value="${esc(cur)}" selected>${esc(cur)} (직접)</option>`;
    return h;
  }
  function colorRow(label, key, el, allowNone) {
    const v = el[key] || "", obj = typeof v === "object";  // 객체 = 그라데이션·투명도(요소 JSON 에서 고침) - 고르면 단색으로 바뀜
    return `<div class="row"><label>${label}</label><span class="sw" style="background:${swatch(v)}"></span><select class="colorSel" data-k="${key}" data-kind="color">${obj ? `<option value="" selected disabled>${esc(fillLabel(v))}</option>` : ""}${colorOptions(obj ? "" : v, allowNone)}</select></div>`;
  }
  const num = (label, key, el, step = 1) => `<div class="row"><label>${label}</label><input type="number" step="${step}" data-k="${key}" value="${el[key] == null ? "" : el[key]}"></div>`;
  function seg(label, key, el, opts, dflt) {
    const v = el[key] || dflt;
    return `<div class="row"><label>${label}</label><span class="seg" data-k="${key}">${opts.map(([k, t]) => `<button data-v="${k}" class="${k === v ? "on" : ""}">${t}</button>`).join("")}</span></div>`;
  }
  function elLabel(e) {
    const t = e.text || (e.items && (typeof e.items[0] === "string" ? e.items[0] : e.items[0] && e.items[0].text)) || e.src || "";
    return `${e.id} · ${TYPE_KO[e.type] || e.type}${t ? " · " + Render.plain(String(t)).slice(0, 28) : ""}`;
  }
  // 글머리 종류 선택지 - 기호 · 번호 매기기(순번 자동) · 없음 (render.js NUM_STYLES 와 같은 이름)
  const MARKER_OPTS = [["●", "●"], ["○", "○"], ["■", "■"], ["□", "□"], ["◆", "◆"], ["▪", "▪"], ["▸", "▸"], ["–", "–"], ["✓", "✓"], ["1.", "1."], ["1)", "1)"], ["(1)", "(1)"], ["a.", "a."], ["A.", "A."], ["①", "①"], ["가.", "가."], ["none", "없음"]];
  const SUB_MARKER_OPTS = [["–", "–"], ["·", "·"], ["◦", "◦"], ["▪", "▪"], ["▸", "▸"], ["✓", "✓"], ["1.", "1."], ["1)", "1)"], ["a.", "a."], ["a)", "a)"], ["①", "①"], ["none", "없음"]];
  /** 글자 상자 ↔ 글머리 목록 변환 - 위치·크기·글자색은 그대로. 글자→글머리: 줄마다 항목(앞 공백 = 하위), 글머리→글자: 항목을 줄로(하위는 공백 두 칸) */
  function convertEl(el, to) {
    if (to === "bullets" && el.type === "text") {
      el.type = "bullets"; el.items = textToBullets(el.text || "") ; if (!el.items.length) el.items = ["항목"]; delete el.text;
      el.size = el.size || 20; el.subSize = el.subSize || Math.round(el.size * 0.85); el.lineHeight = el.lineHeight || 1.55;
      ["bold", "align", "valign"].forEach((k) => delete el[k]);
    } else if (to === "text" && el.type === "bullets") {
      el.type = "text"; el.text = bulletsToText(el.items); el.lineHeight = el.lineHeight || 1.55;
      ["items", "subSize", "gap", "subGap", "dot", "subColor", "marker", "subMarker", "spread", "autoNum"].forEach((k) => delete el[k]);
    }
  }
  function bulletsToText(items) { return (items || []).map((it) => typeof it === "string" ? it : [it.text || "", ...(it.sub || []).map((x) => "  " + x)].join("\n")).join("\n"); }
  function textToBullets(t) {
    const out = [];
    for (const line of t.split("\n")) {
      if (!line.trim()) continue;
      if (/^\s/.test(line) && out.length) { let last = out[out.length - 1]; if (typeof last === "string") last = out[out.length - 1] = { text: last, sub: [] }; last.sub.push(line.trim()); }
      else out.push(line.trim());
    }
    return out;
  }
  const CELL_SPLIT = /\s*\|\s*(?![^[]*\]\])/;
  const tableToText = (rows) => (rows || []).map((r) => r.join(" | ")).join("\n");
  const textToTable = (t) => t.split("\n").filter((l) => l.trim()).map((l) => l.split(CELL_SPLIT));
  const showToText = (sh) => (sh || []).map(([a, b]) => (a === b ? `${a}` : `${a}-${b}`)).join(", ");
  function textToShow(t) { const out = []; for (const p of t.split(/[,\s]+/).filter(Boolean)) { const m = p.match(/^(\d+)(?:-(\d+))?$/); if (m) out.push([+m[1], +(m[2] || m[1])]); } return out; }

  // 요소에 실제로 적용되는 글꼴 - 역할(el.font 또는 유형: code·plan·plan-table 본문 = 고정폭, 표는 el.font·colFont) → 덱 글꼴 세트(fontPreset) 또는 작업 공간 세트의 역할별 글꼴(render.js 와 같은 규칙)
  function fontOf(el) {
    const role = ["code", "plan", "plan-table"].includes(el.type) ? "mono" : Render.fontRole(el.font);
    const set = (S.deck && S.deck.fontPreset && Render.presetFonts(S.deck.fontPreset)) || (S.tokens && S.tokens.fonts) || {};
    const f = set[role] || set.body || {};
    const from = S.deck && S.deck.fontPreset ? `덱 세트 ${S.deck.fontPreset}` : S.fonts && S.fonts.current ? `${S.fonts.source === "workspace" ? "작업 공간" : "템플릿"} 세트 ${S.fonts.current}` : "템플릿 기본";
    const have = (name) => { try { return !name || document.fonts.check(`12px "${name}"`); } catch (e) { return true; } };
    return { role, latin: f.latin || "", ea: f.ea || "", css: f.css || "", from, haveLatin: have(f.latin), haveEa: have(f.ea) };
  }
  function fontInfoHtml(el) {
    const fi = fontOf(el), px = +el.size || (el.type === "code" ? 14 : 20), pt = Math.round(px * 0.75 * 100) / 100;
    const bold = el.bold === undefined ? el.type === "pill" : !!el.bold;
    const miss = [!fi.haveLatin && fi.latin, !fi.haveEa && fi.ea].filter(Boolean);
    const heavy = /\b(bold|black|heavy|extrabold|semibold)\b/i.test(fi.latin + " " + fi.ea) ? " · 세트의 이 역할 글꼴 자체가 굵은 서체(굵게 토글과 별개)" : "";
    // 표: 열별 글꼴(colFont)이 있으면 열마다 역할을 보인다(머리 행은 항상 본문)
    const cols = el.type === "table" && Array.isArray(el.colFont) && el.colFont.some(Boolean)
      ? `<br>열별(colFont) · ${el.colFont.map((f, j) => `${j + 1} ${ROLE[Render.fontRole(f || el.font)]}`).join(" · ")} · 머리 행 본문` : "";
    return `<div class="finfo" title="이 요소에 실제로 적용되는 글꼴 - 역할·세트·크기">적용 글꼴 · ${ROLE[fi.role] || fi.role} · <b>${esc(fi.latin || "?")}</b>${fi.ea && fi.ea !== fi.latin ? ` + ${esc(fi.ea)}(한글)` : ""} · ${px}px = ${pt}pt${bold ? " · 굵게" : ""}${heavy}<br>${esc(fi.from)}${fi.css ? ` · CSS ${esc(fi.css)}` : ""}${cols}${miss.length ? `<br><span style="color:var(--warn)">이 브라우저에 없음: ${esc(miss.join(", "))} - 대체 글꼴로 보이는 중(PPTX 는 받는 PC 의 글꼴)</span>` : ""}</div>`;
  }
  /** 글꼴 세트 선택 줄 - 선택 상자는 세트 이름만(폭 안에서 말줄임), 그 아래 보조 글줄에 고른 세트의 글꼴 구성을 줄바꿈으로 전부 보인다(Material "supporting text" 꼴). 목록(펼침)은 브라우저가 내용 폭대로 그린다.
      cur = 고른 세트 이름(빈 값 = 기본), dflt = 기본일 때 실제로 쓰이는 세트 이름 */
  function fontSetRow(label, attr, cur, dfltLabel, dflt, scope) {
    const presets = (S.fonts && S.fonts.presets) || [];
    const eff = presets.find((p) => p.name === (cur || dflt));
    const sub = eff ? `${cur ? "" : `${esc(eff.name)} · `}${esc(eff.label)}` : (cur ? esc(cur) : "기본 글꼴");
    return `<div class="row"><label>${label}</label><select class="ell" ${attr} title="${esc(scope)} - ${esc(eff ? `${eff.name}: ${eff.label}` : "기본")}"><option value="">${dfltLabel}</option>${presets.map((p) => `<option value="${esc(p.name)}"${cur === p.name ? " selected" : ""}>${esc(p.name)} · ${esc(p.label)}</option>`).join("")}</select></div>
      <div class="sub" title="${esc(scope)}">${sub}</div>`;
  }
  function renderProps() {
    const P = $("#tab-props"), s = slide();
    if (!s) { P.innerHTML = ""; return; }
    const el = selEl();
    const list = `<div class="sec"><h3>요소 (${s.elements.length}) - 가려진 요소도 여기서 선택</h3><div class="ellist">${s.elements.map((e) => `<div data-sel="${esc(e.id)}" class="${selIds().includes(e.id) ? "on" : ""}" title="클릭 = 선택 · Ctrl+클릭 = 더하거나 빼기 · Shift+클릭 = 범위 선택">${esc(elLabel(e))}${e.locked ? " 🔒" : ""}</div>`).join("")}</div></div>`;
    if (!el) {
      P.innerHTML = `<div class="sec"><h3>슬라이드 ${S.cur + 1} · ${esc(s.id)} · 레이아웃 ${esc(s.layout || "-")}</h3>
        <div class="row"><label>배경</label><select class="colorSel" data-slide="bg">${colorOptions(s.bg || "surface")}</select></div>
        ${fontSetRow("글꼴 세트", 'data-slide="fontPreset"', s.fontPreset, `(덱 기본${S.deck.fontPreset ? ` - ${esc(S.deck.fontPreset)}` : ""})`, S.deck.fontPreset || (S.fonts && S.fonts.current), "이 슬라이드만")}
        ${fontSetRow("덱 글꼴 세트", 'data-deckfont="1"', S.deck.fontPreset, `(작업 공간 - ${esc((S.fonts && S.fonts.current) || "기본")})`, S.fonts && S.fonts.current, "덱 전체")}
        <div class="row"><label>구분(섹션)</label><input type="text" data-slide="section" value="${esc(s.section || "")}" placeholder="${s.layout === "chapter" ? "장 표지 - 제목으로 자동" : "(없음)"}" title="PPTX 구분(섹션) 이름 - 이 슬라이드부터 새 구분이 시작된다. 장 표지(chapter) 레이아웃은 비워도 제목으로 자동"></div>
        <div class="row"><label class="switch" title="발표·인쇄·PDF 에서 건너뛰고 PPTX 에서는 숨김 슬라이드가 된다"><input type="checkbox" data-slide="hidden" ${s.hidden ? "checked" : ""}><span class="track"></span>숨김 슬라이드</label></div>
        <div class="hint">요소를 누르면 위 서식 줄과 여기서 고칠 수 있다. 색은 토큰 이름으로 고른다(색의 의미 유지).</div></div>${list}`;
      return;
    }
    let h = `<div class="sec"><div class="elhead"><span class="ty">${esc(TYPE_KO[el.type] || el.type)}</span><span class="id">${esc(el.id)}</span><label class="switch" title="잠금 - 끌기·삭제 막기"><input type="checkbox" data-k="locked" ${el.locked ? "checked" : ""}><span class="track"></span>잠금</label></div>`;
    if (isMulti()) { const n = selIds().length, same = selEls().filter((x) => x.type === el.type).length;
      h += `<div class="hint multi-hint"><b>${n}개 선택</b> - 아래 값은 주 선택(${esc(el.id)}) 기준. 고치면 같은 종류 ${same}개에 함께 적용(위치·크기는 선이 아닌 모든 요소, 잠금은 전체, 글자 내용은 주 선택만).</div>`; }
    const grid = (keys) => `<div class="xywh">${keys.map((k) => `<div class="f"><label>${k}</label><input type="number" data-k="${k}" value="${el[k]}" title="${k} (px)"></div>`).join("")}</div>`;
    h += `<h3>위치·크기 <span class="hint">px · 슬라이드 1280×720</span></h3>${grid(isLine(el) ? ["x1", "y1", "x2", "y2"] : ["x", "y", "w", "h"])}
      ${!isLine(el) ? `<div class="row" style="margin-top:6px"><label>링크</label><input type="text" data-k="link" value="${esc(el.link || "")}" placeholder="https://… · #3(슬라이드 번호) · #s07(슬라이드 id)" title="발표 화면에서 누르면 이동(새 탭 또는 슬라이드). PPTX 도 같은 링크"></div>` : ""}
      ${!isLine(el) && !["table", "plan-table", "bullets", "code", "plan"].includes(el.type) ? `<div class="row" style="margin-top:6px"><label>회전(°)</label><input type="number" step="1" data-k="rot" value="${el.rot || 0}" title="시계 방향, 중심 기준 - PPT 와 같다" style="width:70px"><button class="chip sm${el.flipH ? " on" : ""}" data-flip="H" title="좌우 뒤집기">⇋ 좌우</button><button class="chip sm${el.flipV ? " on" : ""}" data-flip="V" title="상하 뒤집기">⇅ 상하</button></div>` : ""}
      <h3 style="margin-top:10px">순서</h3><div class="zrow"><button class="pbtn" data-z="back" title="맨 뒤로 보내기 (Alt+Ctrl+[)">⇊ 맨 뒤</button><button class="pbtn" data-z="bwd" title="뒤로 보내기 (Ctrl+[)">↓ 뒤로</button><button class="pbtn" data-z="fwd" title="앞으로 가져오기 (Ctrl+])">↑ 앞으로</button><button class="pbtn" data-z="front" title="맨 앞으로 가져오기 (Alt+Ctrl+])">⇈ 맨 앞</button></div></div>`;
    if (TEXTY.has(el.type)) {
      h += `${el.type === "text" ? `<div class="row" style="margin:0 0 6px"><button class="chip sm" data-conv="bullets" title="줄마다 항목인 글머리 목록으로 바꿉니다(앞에 공백 두 칸 = 하위 항목, 글 앞의 번호·기호는 자동 감지)">≡ 글머리 목록으로 바꾸기</button></div>` : ""}<div class="sec"><h3>글자 <span class="hint" title="인라인 강조 표기 - 겹쳐 쓸 수 있다. __밑줄__ · *기울임* · [[link:#3|글]] 은 슬라이드 링크">**굵게** · ==강조== · [[토큰|색]] · ~~취소~~ · ^{위}_{아래} · [[bg:토큰|형광]] · [[link:url|글]] · {page}</span></h3><textarea data-k="text" style="min-height:70px;font-family:var(--font);font-size:13px">${esc(el.text || "")}</textarea>
        <div class="row"><label>크기</label><input type="number" step="1" data-k="size" value="${el.size == null ? "" : el.size}" title="px (PPT = px × 0.75 pt)"><span class="hint" style="margin:0">px</span><span class="seg" data-k="bold" style="margin-left:auto"><button data-v="0" class="${(el.bold === undefined ? el.type === "pill" : el.bold) ? "" : "on"}">보통</button><button data-v="1" class="${(el.bold === undefined ? el.type === "pill" : el.bold) ? "on" : ""}" style="font-weight:700">굵게</button></span></div>
        ${seg("정렬", "align", el, [["left", "⇤ 왼쪽"], ["center", "↔ 가운데"], ["right", "⇥ 오른쪽"]], el.type === "pill" || el.type === "ellipse" ? "center" : "left")}
        ${seg("세로", "valign", el, [["top", "⤒ 위"], ["middle", "↕ 가운데"], ["bottom", "⤓ 아래"]], el.type === "text" ? "top" : "middle")}
        ${num("줄 높이", "lineHeight", el, 0.05)}${colorRow("글자색", "color", el)}
        ${seg("글꼴", "font", el, [["body", "본문"], ["heading", "제목"], ["mono", "고정폭"]], "body")}${fontInfoHtml(el)}</div>`;
    }
    if (el.type === "shape") h += `<div class="sec"><h3>도형</h3><div class="row"><label>종류</label><select data-k="shape">${Render.shapeNames().map(([k, ko]) => `<option value="${k}"${el.shape === k ? " selected" : ""}>${ko}</option>`).join("")}</select></div><div class="hint">PowerPoint 기본 도형(기본 조정값). 글은 도형의 글 영역에 가운데.</div></div>`;
    if (["rect", "ellipse", "pill", "text", "plan", "shape"].includes(el.type)) {
      h += `<div class="sec"><h3>면·테두리</h3>${colorRow("채우기", "fill", el, el.type === "text")}
        ${el.type !== "ellipse" && el.type !== "pill" && el.type !== "shape" ? `<div class="row"><label>모서리</label><select data-k="radius">${["", "r-s", "r-m", "r-l", "r-full"].map((r) => `<option value="${r}"${(el.radius || "") === r ? " selected" : ""}>${r || "없음"}</option>`).join("")}${typeof el.radius === "number" ? `<option selected value="${el.radius}">${el.radius}px</option>` : ""}</select></div>` : ""}
        ${colorRow("테두리", "stroke", el, true)}${el.stroke ? `<div class="row"><label>테두리 선</label><input type="number" min="0.5" max="20" step="0.5" data-k="strokeWidth" value="${el.strokeWidth || 1}" title="두께(px)" style="width:60px">${seg("", "strokeDash", el, [["solid", "실선"], ["dash", "파선"], ["dot", "점선"]], "solid").replace('<div class="row">', '<span class="row" style="margin:0 0 0 6px">').replace(/<\/div>$/, "</span>")}</div>` : ""}
        ${seg("그림자", "shadow", { shadow: el.shadow ? "on" : "off" }, [["off", "없음"], ["on", "있음"]], "off")}</div>`;
    }
    if (el.type === "chart") h += `<div class="sec"><h3>차트 <span class="hint">PPTX 는 PowerPoint 차트(편집 가능)</span></h3>
        ${seg("종류", "chart", el, CHART_KINDS.map(([k, , l]) => [k, l]), "column")}
        <div class="row"><label>제목</label><input type="text" data-k="title" value="${esc(el.title || "")}" placeholder="(없음)"></div>
        <h3 style="margin-top:8px">데이터 - 첫 줄 = 범주 | 계열 이름…, 다음 줄 = 범주 | 값…</h3><textarea data-chart="1" style="min-height:120px;font-family:Consolas,monospace;font-size:13px">${esc(chartToText(el))}</textarea>
        ${seg("범례", "legend", { legend: el.legend || (((el.series || []).length > 1 || el.chart === "pie" || el.chart === "doughnut") ? "bottom" : "none") }, [["none", "없음"], ["bottom", "아래"], ["right", "오른쪽"]], "none")}
        ${seg("값 표시", "labels", { labels: el.labels ? "on" : "off" }, [["off", "끔"], ["on", "켬"]], "off")}${seg("눈금선", "grid", { grid: el.grid === false ? "off" : "on" }, [["on", "켬"], ["off", "끔"]], "on")}
        ${num("글자 크기", "size", el)}${num("축 최댓값", "axisMax", el)}<div class="hint">색은 \`colors\` (요소 JSON, 색 토큰 또는 #hex 목록). 빈 값·글자는 없는 값.</div></div>`;
    if (el.type === "icon") h += `<div class="sec"><h3>아이콘</h3><div class="row"><label>종류</label><select data-k="icon">${Render.iconNames().map(([k, ko]) => `<option value="${k}"${el.icon === k ? " selected" : ""}>${ko}</option>`).join("")}</select></div>${colorRow("아이콘 색", "fill", el)}${colorRow("대비 색", "color", el)}<div class="hint">정사각형으로 그려진다(짧은 변 기준). PPTX 는 자유형 도형이라 PowerPoint 에서 색·크기를 고칠 수 있다.</div></div>`;
    if (el.type === "group") h += `<div class="sec"><h3>묶음 (${(el.children || []).length}개)</h3><div class="row"><button class="chip sm" data-act="ungroup" title="자식을 낱개로 되돌립니다 (Ctrl+Shift+G)">묶음 풀기</button><span class="hint" style="margin:0">${(el.children || []).map((c) => TYPE_KO[c.type] || c.type).join(" · ")}</span></div><div class="hint">자식은 묶음 상자 기준 좌표. 크기를 바꾸면 자식 위치·크기가 비율로 따라간다. 두 번 클릭 편집은 풀어서.</div></div>`;
    if (el.type === "image") h += `<div class="sec"><h3>그림</h3><div class="row"><label>경로</label><input type="text" data-k="src" value="${esc(el.src)}"></div>
        <div class="row"><label>자르기 %</label>${["l", "t", "r", "b"].map((k, i) => `<input type="number" min="0" max="95" step="1" data-crop="${i}" value="${Math.round(((el.crop || [0, 0, 0, 0])[i] || 0) * 100)}" title="${["왼쪽", "위", "오른쪽", "아래"][i]}" style="width:52px">`).join("")}</div>
        <div class="row"><label>투명도 %</label><input type="number" min="0" max="100" step="5" data-opacity="1" value="${Math.round((el.opacity == null ? 1 : el.opacity) * 100)}" title="100 = 그대로" style="width:70px">${seg("그림자", "shadow", { shadow: el.shadow ? "on" : "off" }, [["off", "없음"], ["on", "있음"]], "off").replace('<div class="row">', '<span class="row" style="margin:0">').replace(/<\/div>$/, "</span>")}</div><div class="row"><label>효과</label><select data-k="effect" title="프레임 효과 - 원본 파일은 그대로 두고 속성으로만 적용(PPTX 도 같은 효과)">${EFFECTS.map(([k, l]) => `<option value="${k}"${(el.effect || "") === k ? " selected" : ""}>${l}</option>`).join("")}</select>${el.effect ? seg("수준", "effectLevel", { effectLevel: String(el.effectLevel || 2) }, [["1", "약"], ["2", "중"], ["3", "강"]], "2").replace('<div class="row">', '<span class="row" style="margin:0 0 0 6px">').replace(/<\/div>$/, "</span>") : ""}</div>${el.effect === "frame" ? `${colorRow("테두리 색", "frameColor", el, true)}<div class="row"><label>테두리 px</label><input type="number" min="1" max="40" step="1" data-k="frameWidth" value="${el.frameWidth == null ? "" : el.frameWidth}" placeholder="수준 기본" title="액자 두께 - 비우면 수준(약 3·중 6·강 10)" style="width:70px"></div>` : ""}
        <div class="row"><button class="chip sm" data-imgpick="1" title="새 그림 파일을 올려 이 자리에 바꿔 넣습니다(폭 유지, 높이는 비율로)">그림 바꾸기…</button>${el.mermaid != null ? `<button class="chip sm" data-mermaid="1" title="mermaid 코드를 고쳐 다시 그립니다(폭 유지)">다이어그램 코드 수정…</button>` : ""}<span class="hint" style="margin:0">assetRoot 기준 경로 · 모서리 핸들은 비율 유지</span></div></div>`;
    if (isLine(el)) h += `<div class="sec"><h3>선</h3>${colorRow("색", "color", el)}${num("두께(px)", "width", el, 0.5)}
        ${seg("머리", "head", el, [["none", "없음"], ["end", "끝"], ["start", "시작"], ["both", "양쪽"]], el.type === "arrow" ? "end" : "none")}
        ${seg("점선", "dash", el, [["solid", "실선"], ["dash", "파선"], ["dot", "점선"]], "solid")}</div>`;
    if (el.type === "code") { const lk = Render.langOf(el), ln = el.lineNo !== false; h += `<div class="sec"><h3>코드</h3>${fontInfoHtml(el)}<textarea data-k="text" style="min-height:160px">${esc(el.text || "")}</textarea>
        <div class="row"><label>언어</label><label class="switch" style="margin:0 8px 0 0" title="캔버스 코드 블록 오른쪽 위 언어 이름표 표시 여부(편집 화면에만, 모든 코드 블록 공통)"><input type="checkbox" data-langtag="1"${LS.get("langTag", "1") === "1" ? " checked" : ""}><span class="track"></span></label>
          <input type="search" list="langList" data-lang="1" value="${el.lang ? esc(langLabel(lk)) : ""}" placeholder="언어 찾기 - 예: bash, c#, json, rust" title="입력하면 목록이 좁혀집니다 - 이름·별칭(sh, cs, js, py …)으로 찾기" style="flex:1;min-width:0"></div>
        <datalist id="langList">${langOptions()}</datalist>
        <div class="row"><label>줄 번호</label><label class="switch" style="margin-left:0" title="코드 왼쪽 줄 번호 열 - 끄면 화면·PPTX 모두 번호 없이"><input type="checkbox" data-linenosw="1"${ln ? " checked" : ""}><span class="track"></span></label>
          <button class="chip sm" data-copy="code" title="코드 글자를 클립보드에 복사(줄 번호·색 없이)" style="margin-left:auto">📋 복사</button></div>
        ${num("크기(px)", "size", el)}${num("줄 높이", "lineHeight", el, 0.05)}${num("시작 번호", "start", el)}
        <div class="row"><label>강조 줄</label><input type="text" data-list="focus" value="${esc((el.focus || []).join(", "))}" placeholder="예: 1, 9"></div>
        <div class="row"><label>발췌</label><input type="text" data-list="show" value="${esc(showToText(el.show))}" placeholder="예: 2, 13-24 (비우면 전체)"></div>
        <div class="row"><button class="chip sm" data-fit="code">높이를 줄 수에 맞추기</button><span class="hint">표시 ${Render.codeLines(el).length}줄 (15~18줄 이내 권장)</span></div></div>`; }
    if (el.type === "plan") h += `<div class="sec"><h3>실행계획 원문 - [[값]] = 경고 강조, [[ok:값]] = 개선 강조 (폭 불변)</h3><textarea data-k="text" style="min-height:180px">${esc(el.text || "")}</textarea>
        ${num("크기(px)", "size", el, 0.5)}${num("줄 높이", "lineHeight", el, 0.05)}${fontInfoHtml(el)}</div>`;
    if (el.type === "bullets") h += `<div class="sec"><h3>글머리 - 줄마다 항목, 앞에 공백 두 칸 = 하위 항목</h3><textarea data-bul="1" style="min-height:140px;font-family:var(--font);font-size:13px">${esc(bulletsToText(el.items))}</textarea>
        ${num("크기(px)", "size", el)}${num("하위 크기", "subSize", el)}${num("줄 높이", "lineHeight", el, 0.05)}${num("항목 간격", "gap", el)}
        ${colorRow("점 색", "dot", el)}${colorRow("글자색", "color", el)}${colorRow("하위 글자색", "subColor", el)}
        ${seg("글꼴", "font", el, [["body", "본문"], ["heading", "제목"], ["mono", "고정폭"]], "body")}${fontInfoHtml(el)}</div>
        <details class="sec fold" data-fold="bul-marker"${LS.get("fold-bul-marker", "0") === "1" ? " open" : ""}><summary><h3 style="display:inline-flex;margin:0">글머리 종류 <span class="hint" title="항목 글 앞에 직접 적은 번호·기호(1. · a) · ① · - · • …)가 있으면 그것이 먼저 쓰인다">글 앞의 번호·기호가 우선</span></h3></summary>
        ${seg("항목", "marker", el, MARKER_OPTS, "●")}${seg("하위 항목", "subMarker", el, SUB_MARKER_OPTS, "–")}
        ${seg("글 앞 번호·기호 감지", "autoNum", { autoNum: el.autoNum === false ? "off" : "on" }, [["on", "켬"], ["off", "끔"]], "on")}
        <div class="row"><button class="chip sm" data-conv="text" title="항목을 줄로 펼친 글자 상자로 바꿉니다(하위 항목은 앞에 공백 두 칸)">글자 상자로 바꾸기</button></div></details>`;
    if (el.type === "table") h += `<div class="sec"><h3>표 - 줄 = 행, 칸은 " | " 로 구분 (첫 행 = 머리)</h3>${fontInfoHtml(el)}<textarea data-tbl="1" style="min-height:140px">${esc(tableToText(el.rows))}</textarea>
        <div class="row"><label>행·열</label><button class="chip sm" data-tblop="row+" title="맨 아래에 행 추가">＋행</button><button class="chip sm" data-tblop="row-" title="맨 아래 행 지우기">－행</button><button class="chip sm" data-tblop="col+" title="맨 오른쪽에 열 추가">＋열</button><button class="chip sm" data-tblop="col-" title="맨 오른쪽 열 지우기">－열</button><span class="hint" style="margin:0">${(el.rows || []).length}×${((el.rows || [])[0] || []).length}</span></div>
        <div class="row"><label>셀 병합</label><input type="text" data-merge="1" value="${esc((el.merge || []).map((m) => m.join(",")).join("; "))}" placeholder="행,열,행수,열수; … (0부터 · 예: 0,0,1,2; 1,1,2,1)" title="왼쪽 위 셀이 행수×열수를 차지한다. 머리 행도 0행. 겹치면 앞 것만"></div>
        <div class="row"><label>셀 채움</label><input type="text" data-cellfill="1" value="${esc((el.cellFill || []).map((m) => m.map((v) => (v == null ? "*" : v)).join(",")).join("; "))}" placeholder="행,열,색; … (* = 줄 전체 · 예: 2,*,s1; 1,3,primary-container)" title="셀 바탕색 - 색은 토큰 이름(#hex 도 됨). 행이나 열에 * 를 쓰면 그 줄 전체. 머리 행도 0행. PPTX 셀 채움과 같다"></div>
        <div class="row"><label>셀 테두리</label><input type="text" data-borders="1" value="${esc((el.borders || []).map((m) => m.map((v) => (v == null ? "*" : v)).join(",")).join("; "))}" placeholder="행,열,변,색,두께; … (변 = T B L R 조합 · 예: 3,*,T,primary,2)" title="셀 테두리 - 변은 T(위) B(아래) L(왼) R(오른) 조합, 색·두께는 선택(기본 rule 색 1px). * = 그 줄 전체. 합계 행 위 굵은 선 = 행,*,T,색,2"></div>
        ${seg("격자", "gridLines", { gridLines: el.gridLines ? "on" : "off" }, [["off", "가로선만"], ["on", "모든 칸"]], "off")}
        <div class="row"><label>열 비율</label><input type="text" data-list="colW" value="${esc((el.colW || []).join(", "))}"></div>
        <div class="row"><label>행 비율</label><input type="text" data-list="rowH" value="${esc((el.rowH || []).join(", "))}" placeholder="비우면 고르게 · 예: 44, 46, 70"></div>
        ${num("크기(px)", "size", el)}${colorRow("머리 면", "headFill", el)}${colorRow("머리 글자", "headColor", el)}
        ${seg("유형", "font", el, [["body", "일반"], ["mono", "코드"], ["heading", "제목 글꼴"]], "body")}<div class="hint">일반 = 세트의 본문 글꼴 · 코드 = 고정폭(코드) 글꼴 - 본문 셀 전체(머리 행은 항상 본문). 열마다 다르게 하려면 아래 열별 글꼴.</div>
        <div class="row"><label>열별 글꼴</label><input type="text" data-list="colFont" value="${esc((el.colFont || []).map((f) => f || "").join(", "))}" placeholder="비우면 위 유형 · 예: body, mono, body" title="열마다 body(일반)·mono(코드)·heading(제목 글꼴) - 빈 칸은 위 유형. 머리 행은 항상 본문"></div></div>`;
    if (el.type === "plan-table") h += `<div class="sec"><h3>실행계획 표</h3>${fontInfoHtml(el)}<div class="hint">rows[].cells · depth(들여쓰기) · hl({열 번호: "warn"|"ok"}) · note(오른쪽 설명) - 아래 JSON 에서 고친다.</div></div>`;
    h += `<div class="sec"><h3>동작</h3><div class="zrow" style="grid-template-columns:repeat(3,1fr)"><button class="pbtn" data-act="dupEl" title="복제 (Ctrl+D)">⧉ 복제</button><button class="pbtn" data-act="reqEl" title="이 요소에 요청 메모(세션에 보냄)">💬 요청</button><button class="pbtn danger" data-act="delEl" title="삭제 (Del)" style="color:var(--err)">🗑 삭제</button></div></div>
      <details class="sec" style="padding:8px 12px"><summary class="hint" style="cursor:pointer;margin:0">요소 JSON (고급)</summary><textarea id="elJson" style="min-height:120px;margin-top:8px">${esc(JSON.stringify(el, null, 1))}</textarea>
      <div class="row"><button class="chip sm" id="applyJson">JSON 적용</button></div></details>`;
    P.innerHTML = h + list;
  }
  // 코드 언어 목록(code_langs.json) - 이름 · 별칭으로 찾는다
  const langLabel = (k) => (S.langs && S.langs[k] ? S.langs[k].label : k);
  const langKeys = () => Object.keys(S.langs || {}).filter((k) => k[0] !== "_");
  const langOptions = () => langKeys().map((k) => `<option value="${esc(S.langs[k].label)}">${esc([k, ...(S.langs[k].alias || [])].join(" "))}</option>`).join("");
  function findLang(v) {
    const q = String(v || "").trim().toLowerCase(); if (!q) return null;
    return langKeys().find((k) => k === q || S.langs[k].label.toLowerCase() === q || (S.langs[k].alias || []).includes(q)) || null;
  }
  async function copyText(t) {
    try { await navigator.clipboard.writeText(t); }
    catch (e) { const ta = document.createElement("textarea"); ta.value = t; document.body.appendChild(ta); ta.select(); document.execCommand("copy"); ta.remove(); }
    toast(`클립보드에 복사했습니다 (${t.split("\n").length}줄)`);
  }
  function setProp(el, k, v) {
    if (["x", "y", "w", "h", "x1", "y1", "x2", "y2", "size", "subSize", "lineHeight", "width", "gap", "start", "rot", "effectLevel", "strokeWidth", "frameWidth"].includes(k)) { if (v === "" || v == null || (k === "rot" && +v === 0)) delete el[k]; else el[k] = +v; }
    else if (k === "strokeDash") { if (v && v !== "solid") el.strokeDash = v; else delete el.strokeDash; }
    else if (k === "gridLines") { if (v === "on") el.gridLines = true; else delete el.gridLines; }  // 표 격자(모든 칸 테두리)
    else if (k === "locked") { if (v) el.locked = true; else delete el.locked; }
    else if (k === "bold") el.bold = v === "1";
    else if (k === "autoNum") { if (v === "off") el.autoNum = false; else delete el.autoNum; }  // 글 앞 번호·기호 감지(기본 켬)
    else if (k === "shadow") { if (v === "on") el.shadow = el.shadow || true; else delete el.shadow; }
    else if (k === "labels") { if (v === "on") el.labels = true; else delete el.labels; }
    else if (k === "grid") { if (v === "off") el.grid = false; else delete el.grid; }
    else if (k === "legend") { if (v === "none" && !((el.series || []).length > 1 || el.chart === "pie" || el.chart === "doughnut")) delete el.legend; else el.legend = v; }
    else if (k === "axisMax") { if (v === "" || v == null || +v <= 0) delete el.axisMax; else el.axisMax = +v; }
    else if (k === "title") { const t = String(v || "").trim(); if (t) el.title = t; else delete el.title; }
    else if (k === "link") { const t = String(v || "").trim(); if (t) el.link = t; else delete el.link; }
    else if (v === "" && ["fill", "stroke", "radius", "effect", "frameColor"].includes(k)) delete el[k];
    else el[k] = v;
    if (isLine(el)) Object.assign(el, Render.lineBox(el));
  }
  function onPropChange(e) {
    const t = e.target, el = selEl(), s = slide();
    if (t.dataset.slide === "bg") { snapshot(); s.bg = t.value; afterChange(); return; }
    if (t.dataset.slide === "fontPreset") { snapshot(); if (t.value) s.fontPreset = t.value; else delete s.fontPreset; afterChange(true); return; }  // 이 장만
    if (t.dataset.slide === "section") { snapshot(); const v = t.value.trim(); if (v) s.section = v; else delete s.section; afterChange(true); return; }  // PPTX 구분(섹션) 시작
    if (t.dataset.slide === "hidden") { snapshot(); if (t.checked) s.hidden = true; else delete s.hidden; afterChange(true); return; }
    if (t.dataset.deckfont) { snapshot(); if (t.value) S.deck.fontPreset = t.value; else delete S.deck.fontPreset; Render.setDeckFonts(S.deck.fontPreset); afterChange(true); return; }  // 덱 전체
    if (!el || t.id === "elJson") return;
    if (t.dataset.linenosw && el) { const on = t.checked; mutate((x) => { if (on) delete x.lineNo; else x.lineNo = false; }, (x) => x.type === "code"); return; }
    if (t.dataset.langtag) { LS.set("langTag", t.checked ? "1" : "0"); renderMarks(); return; }
    if (t.dataset.lang) {  // 언어 - 목록의 이름·별칭으로. 고른 코드 요소 모두
      if (!t.value.trim()) { mutate((x) => { delete x.lang; }, (x) => x.type === "code"); return; }  // 비우면 언어 지정 없음(이름표 없음)
      const k = findLang(t.value); if (!k) { toast(`모르는 언어: ${t.value} - 목록에서 고르세요`); return; }
      mutate((x) => { x.lang = k; }, (x) => x.type === "code"); return;
    }
    snapshot();
    if (t.dataset.k) {  // 다중 선택이면 공통 속성으로 - 같은 종류 요소 모두(위치·크기·잠금은 선이 아닌 모든 요소). 글자 내용은 주 선택만
      const k = t.dataset.k, v = t.type === "checkbox" ? t.checked : t.value;
      const geo = ["x", "y", "w", "h"].includes(k), all = k === "locked";
      const targets = k === "text" ? [el] : selEls().filter((x) => x === el || all || (geo ? !isLine(x) && !isLine(el) : x.type === el.type));
      targets.forEach((x) => setProp(x, k, v));
    }
    else if (t.dataset.list) {
      if (t.dataset.list === "show") { const sh = textToShow(t.value); if (sh.length) el.show = sh; else delete el.show; }
      else if (t.dataset.list === "colFont") {  // 열별 글꼴 역할 - 쉼표로 나눠 body/heading/mono 로 정규화("code" 도 mono, "-"·빈 칸 = 위 글꼴). 모두 비면 뺀다
        const a = t.value.split(",").map((x) => x.trim()).map((x) => (!x || x === "-" ? "" : Render.fontRole(x)));
        while (a.length && !a[a.length - 1]) a.pop();
        if (a.some(Boolean)) el.colFont = a; else delete el.colFont;
      }
      else { const a = t.value.split(/[,\s]+/).filter(Boolean).map(Number).filter((x) => !isNaN(x)); if (a.length) el[t.dataset.list] = a; else delete el[t.dataset.list]; }
    } else if (t.dataset.chart) { textToChart(t.value, el); }
    else if (t.dataset.crop != null) { const c = (el.crop || [0, 0, 0, 0]).slice(); c[+t.dataset.crop] = Math.max(0, Math.min(95, +t.value || 0)) / 100; if (c.some((v) => v)) el.crop = c; else delete el.crop; }
    else if (t.dataset.opacity) { const o = Math.max(0, Math.min(100, +t.value || 0)) / 100; if (o < 1) el.opacity = o; else delete el.opacity; }
    else if (t.dataset.merge) { const a = t.value.split(";").map((x) => x.split(",").map((v) => parseInt(v, 10))).filter((m) => m.length === 4 && m.every((v) => !isNaN(v))); if (a.length) el.merge = a; else delete el.merge; }
    else if (t.dataset.cellfill || t.dataset.borders) {  // 셀 채움 "행,열,색; …" · 셀 테두리 "행,열,변,색,두께; …" (* 또는 빈 칸 = 줄 전체)
      const ix = (v) => (v === "*" || v === "" ? null : parseInt(v, 10)), okIx = (v) => v == null || !isNaN(v);
      const rows = t.value.split(";").map((x) => x.split(",").map((v) => v.trim())).filter((m) => m.length >= 3 && m[2]);
      if (t.dataset.cellfill) { const a = rows.map((m) => [ix(m[0]), ix(m[1]), m[2]]).filter((m) => okIx(m[0]) && okIx(m[1])); if (a.length) el.cellFill = a; else delete el.cellFill; }
      else { const a = rows.filter((m) => /^[TBLRtblr]+$/.test(m[2])).map((m) => { const o = [ix(m[0]), ix(m[1]), m[2].toUpperCase()]; if (m[3] || (m[4] && !isNaN(+m[4]))) o.push(m[3] || ""); if (m[4] && !isNaN(+m[4])) o.push(+m[4]); return o; }).filter((m) => okIx(m[0]) && okIx(m[1])); if (a.length) el.borders = a; else delete el.borders; }
    }
    else if (t.dataset.bul) el.items = textToBullets(t.value);
    else if (t.dataset.tbl) el.rows = textToTable(t.value);
    afterChange();
  }
  document.addEventListener("toggle", (e) => { const d = e.target; if (d && d.matches && d.matches("details.fold[data-fold]")) LS.set("fold-" + d.dataset.fold, d.open ? "1" : "0"); }, true);
  function tableOp(el, op) {  // 표 행·열 더하기·빼기(머리 행·첫 열은 남긴다) - 속성 탭·서식 줄이 같이 쓴다(snapshot·afterChange 는 부르는 쪽)
    if (!el || el.type !== "table") return;
    const rows = el.rows || [], nc = (rows[0] || []).length;
    if (op === "row+") rows.push(Array.from({ length: nc }, () => ""));
    else if (op === "row-" && rows.length > 2) rows.pop();
    else if (op === "col+") { rows.forEach((r) => r.push("")); if (el.colW) el.colW.push(1); if (el.colFont) el.colFont.push(""); }
    else if (op === "col-" && nc > 1) { rows.forEach((r) => r.pop()); if (el.colW && el.colW.length > nc - 1) el.colW.pop(); if (el.colFont && el.colFont.length > nc - 1) el.colFont.pop(); }
    el.rows = rows;
  }
  function onPropClick(e) {
    const b = e.target.closest("button, [data-sel]"); if (!b) return;
    const el = selEl(), s = slide();
    if (b.dataset.sel) {  // 요소 목록: 클릭 = 선택(기준점) · Ctrl/⌘+클릭 = 더하거나 빼기 · Shift+클릭 = 기준점부터 이 요소까지 범위
      const id = b.dataset.sel, order = s.elements.map((x) => x.id);
      // 고른 요소에 따라 위쪽 절이 바뀌어 목록이 위아래로 움직인다 → 다시 그린 뒤 목록이 화면의 같은 자리에 있도록 패널 스크롤을 맞춘다
      const P = $("#tab-props"), before = $("#tab-props .ellist"), top0 = before ? before.getBoundingClientRect().top : null;
      if (e.shiftKey && (S.selAnchor || S.sel) && order.includes(S.selAnchor || S.sel)) {
        const a = order.indexOf(S.selAnchor || S.sel), c = order.indexOf(id), range = order.slice(Math.min(a, c), Math.max(a, c) + 1);
        setSelection([S.selAnchor || S.sel, ...range.filter((x) => x !== (S.selAnchor || S.sel))]);
      } else if (e.ctrlKey || e.metaKey) { toggleSel(id); if (!S.selAnchor) S.selAnchor = id; }
      else { select(id); S.selAnchor = id; }
      const after = $("#tab-props .ellist");
      if (after && top0 != null) {
        const want = P.scrollTop + (after.getBoundingClientRect().top - top0);
        P.scrollTop = want;
        if (P.scrollTop < want - 1) { P.style.paddingBottom = `${Math.ceil(want - P.scrollTop) + 40}px`; P.scrollTop = want; }  // 아래 내용이 모자라면 여백을 늘려 자리를 맞춘다
      }
      return;
    }
    if (b.dataset.lineno && el) { const on = b.dataset.lineno === "1"; mutate((x) => { if (on) delete x.lineNo; else x.lineNo = false; }, (x) => x.type === "code"); return; }
    if (b.dataset.copy === "code" && el) { copyText(el.text || ""); return; }
    const sg = b.closest(".seg");
    if (sg && el) { snapshot(); selEls().filter((x) => x === el || x.type === el.type).forEach((x) => setProp(x, sg.dataset.k, b.dataset.v)); afterChange(); return; }
    if (b.dataset.z && el) { zorder(b.dataset.z); return; }
    if (b.dataset.fit === "code" && el) { snapshot(); el.h = Math.round(24 + Render.codeLines(el).length * (el.size || 15) * (el.lineHeight || 1.6)); afterChange(); return; }
    if (b.dataset.conv && el) { snapshot(); convertEl(el, b.dataset.conv); afterChange(); return; }
    if (b.dataset.imgpick && el && el.type === "image") { imagePick(el); return; }
    if (b.dataset.mermaid && el && el.type === "image") { mermaidDialog(el); return; }
    if (b.dataset.flip && el) { snapshot(); const k = "flip" + b.dataset.flip; selEls().forEach((x) => { if (x[k]) delete x[k]; else x[k] = true; }); afterChange(); return; }
    if (b.dataset.tblop && el && el.type === "table") { snapshot(); tableOp(el, b.dataset.tblop); afterChange(); return; }
    if (b.id === "applyJson" && el) {
      try {
        const nv = JSON.parse($("#elJson").value);
        if (!nv || typeof nv !== "object" || !nv.type) throw new Error("type 필요");
        snapshot(); nv.id = nv.id || el.id; s.elements[s.elements.indexOf(el)] = nv; S.sel = nv.id;
        if (isLine(nv)) Object.assign(nv, Render.lineBox(nv));
        afterChange();
      } catch (err) { toast("JSON 오류: " + err.message); }
      return;
    }
    if (b.dataset.act === "dupEl") dupEl();
    if (b.dataset.act === "ungroup") ungroupSel();
    if (b.dataset.act === "delEl") delEl();
    if (b.dataset.act === "reqEl") openMemo({ element: el.id });
  }

  // ---------------------------------------------------------------- 요청 목록(오른쪽 탭)
  async function loadReqs() {
    const r = await api("GET", `/api/requests/${S.id}`);
    S.reqs = r.ok ? r.data : [];
    const v = await api("GET", `/api/version/${S.id}`); if (v.ok) S.reqVersion = v.data.requests;
    renderReqs(); if (S.deck) { renderThumbs(); renderMarks(); }
  }
  const ST = { draft: "초안", open: "대기", working: "처리 중", done: "완료" };
  // 후속 요청 - 같은 thread(뿌리 요청 id)를 한 묶음으로. 묶음 안은 오래된 순, 묶음끼리는 최근 활동이 위
  const threadKey = (r) => r.thread || r.id;
  function threadsOf(list) {
    const m = new Map();
    for (const r of list) { const k = threadKey(r); if (!m.has(k)) m.set(k, []); m.get(k).push(r); }
    const gs = [...m.values()].map((g) => g.sort((a, b) => String(a.created || "").localeCompare(String(b.created || "")) || String(a.id).localeCompare(String(b.id))));
    return gs.sort((a, b) => String(b[b.length - 1].created || "").localeCompare(String(a[a.length - 1].created || "")));
  }
  function fuFormHtml(r) {  // 마지막 요청 아래 인라인 입력칸 - 앞선 답은 접어서 인용
    return `<div class="fu-form">${r.reply ? `<details><summary>앞선 답 보기</summary><div class="quote">${esc(r.reply)}</div></details>` : ""}
      <textarea id="fuText" placeholder="이어서 묻거나 답하기 (Enter = 보내기, Shift+Enter = 줄바꿈 · 그림은 Ctrl+V)"></textarea><div class="att" id="fuAtt"></div>
      <div class="row" style="gap:6px;justify-content:flex-end"><button class="att-btn" data-attach="fu" title="그림 붙여넣기(Ctrl+V) · 끌어다 놓기 · 파일 고르기"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 11.5l-8.5 8.5a5 5 0 0 1-7-7l9-9a3.3 3.3 0 0 1 4.7 4.7l-9 9a1.6 1.6 0 0 1-2.3-2.3l8-8"/></svg>＋ 첨부</button><span style="flex:1"></span><button class="chip sm" data-fucancel="1">취소</button><button class="chip sm primary" data-fusend="1">보내기</button></div></div>`;
  }
  async function fuSend(parentId) {
    const t = ($("#fuText") && $("#fuText").value.trim()) || ""; if (!t && !ATT.fu.length) return;
    if (ATT.busy) { toast("첨부를 올리는 중입니다"); return; }
    const body = { action: "add", status: "open", parent: parentId, text: t || "(첨부 참고)" };
    if (ATT.fu.length) body.attachments = ATT.fu;
    const r = await api("POST", `/api/requests/${S.id}`, body);
    if (!r.ok) { toast("요청하지 못했습니다: " + ((r.data && r.data.error) || r.status), 5000); return; }
    S.fu = null; ATT.fu = []; S.reqs = r.data; afterReqs(); await flushReqs(true);
    toast(S.session && S.session.connected ? "후속 요청을 세션에 보냈습니다" : "후속 요청을 남겼습니다 - 세션이 연결되면 전달됩니다");
  }
  // 요청 탭 기본 보기 = 최근 24시간에 진행(만듦·상태 변경·답)된 것 + 아직 끝나지 않은 것. 이전 것은 [더보기] 기록 창(reqHist)에서 찾는다
  const DAY_MS = 864e5;
  const reqRecent = (r) => r.status !== "done" || Date.now() - Date.parse(r.updated || r.created || "") < DAY_MS;
  const reqIdx = (sid) => S.deck.slides.findIndex((x) => x.id === sid) + 1;
  /** 요청 카드 한 장 - 요청 탭과 기록 창이 같이 쓴다. hl = 찾기 강조 함수, fu = 후속 요청 단추·입력칸 */
  function reqCardHtml(r, k, last, o) {
    const hl = (o && o.hl) || esc, fu = !o || o.fu !== false;
    return `<div class="req ${r.status === "done" ? "done" : ""}${k ? " fu" : ""}" data-rid="${esc(r.id)}">
        <div class="meta"><span class="st ${esc(r.status || "open")}">${ST[r.status] || "대기"}</span>${k ? `<span class="fu-tag">후속</span>` : `<a href="#" data-goto="${esc(r.slide)}" data-el="${esc(r.element || "")}">슬라이드 ${reqIdx(r.slide) || "?"}${r.elements && r.elements.length > 1 ? ` · ${esc(r.elements[0])} 외 ${r.elements.length - 1}` : r.element ? " · " + esc(r.element) : ""}${r.region ? " · 영역" : ""}</a>`}<span>${esc((r.created || "").replace("T", " "))}</span>${r.updated && r.updated !== r.created ? `<span title="마지막 진행">↻ ${esc(r.updated.replace("T", " "))}</span>` : ""}${r.engineRequest ? `<a class="fu-tag" href="${esc(BASE.startsWith("/w/") ? `/engine?q=%23${r.engineRequest}` : "#")}" ${BASE.startsWith("/w/") ? 'target="_blank"' : ""} title="${esc(r.engineNote || "엔진 변경 요청으로 넘긴 요청 - 관리자 승인·처리·적용 뒤 자동으로 다시 열린다")}" style="text-decoration:none">엔진 요청 #${r.engineRequest}</a>` : ""}</div>${r.engineNote ? `<div class="hint" style="margin:2px 0 4px">${esc(r.engineNote)}</div>` : ""}
        <div class="txt">${hl(r.text)}</div>${attListHtml(r.attachments, r.id)}${r.reply ? `<div class="reply${r.status !== "done" ? " ask" : ""}"><b>${agentName()}</b> ${hl(r.reply)}</div>` : ""}
        <div class="acts">${r.status === "draft" ? "" : `<button class="chip sm" data-rs="${r.status === "done" ? "open" : "done"}" ${r.status === "done" ? 'title="같은 요청을 세션에 다시 보냅니다(답을 달려면 후속 요청)"' : ""}>${r.status === "done" ? "다시 열기" : "완료로 표시"}</button>`}${fu && last && r.status !== "draft" ? `<button class="chip sm primary" data-fu="1" title="이 요청에 이어서 묻거나 답합니다 - 앞선 요청과 답이 함께 세션에 전달됩니다">후속 요청</button>` : ""}<button class="chip sm" data-rdel="1">삭제</button></div>
        ${fu && last && S.fu === r.id ? fuFormHtml(r) : ""}</div>`;
  }
  const reqThreadsHtml = (list, o) => threadsOf(list).map((g) => `<div class="thread${g.length > 1 ? " multi" : ""}">${g.map((r, k) => reqCardHtml(r, k, k === g.length - 1, o)).join("")}</div>`).join("");
  function renderReqs() {
    const R = $("#tab-reqs"), s = slide(); if (!s) return;
    const open = S.reqs.filter((r) => r.status !== "done").length;
    const c = $("#reqCnt"); c.textContent = open; c.style.display = open ? "" : "none";
    const recent = S.reqs.filter(reqRecent), older = S.reqs.length - recent.length;
    const list = recent.filter((r) => !S.reqOnlySlide || r.slide === s.id);
    const drafts = S.reqs.filter((r) => r.status === "draft").length;
    R.innerHTML = `<div class="sec"><h3>${agentName()} 에게 요청</h3>
      <div class="hint">◎ <b>선택</b> 모드에서 요소를 누르거나 ✐ <b>그리기</b> 모드에서 영역을 그려 메모를 단 뒤, 아래 바의 <b>보내기</b>로 한꺼번에 보낸다. 슬라이드 전체 요청은 여기에.</div>
      <textarea id="reqText" data-key="${esc(S.id + "/" + s.id)}" style="min-height:60px;font-family:var(--font);font-size:13px" placeholder="슬라이드 ${S.cur + 1} 전체에 대한 요청 - 예: 이 표를 두 장으로 나눠 줘 (Enter = 남기기, Shift+Enter = 줄바꿈)">${esc(typed(S.id + "/" + s.id))}</textarea>
      <div class="att" id="reqAtt"></div>
      <div class="row"><button class="chip sm primary" id="reqAdd">메모 남기기</button><button class="att-btn" data-attach="tab" title="그림 붙여넣기(Ctrl+V) · 끌어다 놓기 · 파일 고르기"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 11.5l-8.5 8.5a5 5 0 0 1-7-7l9-9a3.3 3.3 0 0 1 4.7 4.7l-9 9a1.6 1.6 0 0 1-2.3-2.3l8-8"/></svg>＋ 첨부</button>${drafts ? `<button class="chip sm" id="reqSend">초안 ${drafts}개 보내기</button>` : ""}</div>
      <div class="hint">${S.session && S.session.connected ? (S.session.kind === "web" ? (S.session.state === "running" ? `웹 세션이 처리 중(턴 ${S.session.turn || "?"}) - 새로 보낸 요청은 이 턴이 끝난 뒤 바로 처리된다` : "웹 세션 대기 중 - 보낸 요청은 바로 처리된다") : "세션 연결됨 - 보낸 요청은 바로 전달된다") : `세션 연결 없음 - 보낸 요청은 저장되고, 세션이 감시를 시작하면 전달된다${sessOffNote()}`}</div>
      ${!(S.session && S.session.connected) && S.reqs.some((r) => r.status === "open") ? `<div class="warn" style="font-size:12px;margin-top:6px">세션이 꺼져 있어 대기 요청 ${S.reqs.filter((r) => r.status === "open").length}건이 처리되지 않습니다 - <a href="#" data-sess-start>웹 세션 시작…</a></div>` : ""}</div>
      <div class="row" style="align-items:center"><span class="seg" id="reqFilter"><button data-v="1" class="${S.reqOnlySlide ? "on" : ""}">이 슬라이드</button><button data-v="0" class="${S.reqOnlySlide ? "" : "on"}">최근 (${recent.length})</button></span><span style="flex:1"></span><button class="chip sm" id="reqMore" title="이전 요청까지 모두 찾아보기(편집 화면 위에 뜹니다)">더보기${older ? ` · 이전 ${older}` : ""}</button></div>
      ${older ? `<div class="hint" style="font-size:11.5px;margin:2px 0 6px">최근 24시간에 진행된 요청과 아직 끝나지 않은 요청만 보입니다 - 이전 것은 [더보기]</div>` : ""}
      ${list.length ? reqThreadsHtml(list) : `<div class="hint">요청이 없다.</div>`}`;
    attRender("tab"); attWire($("#reqText"), "tab");
    if (S.fu && $("#fuText")) { attRender("fu"); attWire($("#fuText"), "fu"); $("#fuText").focus(); }
    if ($("#reqHist")) renderReqHist();
  }
  // ---- 요청 기록·찾기 창([더보기]) - 편집 화면 위에 겹쳐 뜨는 창이라 편집 중인 덱·선택·저장 상태를 벗어나지 않는다. 슬라이드 링크를 누르면 닫고 그 슬라이드로.
  const RH = { q: "", scope: "all", st: "", tg: null };
  function openReqHist() {
    if ($("#reqHist")) { $("#reqHist input").focus(); return; }
    closeMenu();
    const back = document.createElement("div"); back.id = "reqHist";
    back.innerHTML = `<div class="box"><div class="rh-hd"><h3>요청 기록<small id="rhCnt"></small></h3><button type="button" class="chip sm" id="rhClose" title="닫기 (Esc)">✕</button></div>
      <div class="rh-sb"><input type="search" placeholder="내용·답으로 찾기 - 기본 퍼지(띄어쓰기·한두 글자 차이 허용) · #4 = 슬라이드 4, #4,5,7-10 = 여러 장" autocomplete="off" value="${esc(RH.q)}"><span id="rhTg" title="찾기 방식 - 기본은 퍼지(띄어쓰기·한두 글자 차이 허용)"></span></div>
      <div class="rh-fl"><span>범위</span><span class="seg" id="rhScope"><button data-v="all">전체</button><button data-v="slide">이 슬라이드</button></span><span>상태</span><span class="seg" id="rhSt"><button data-v="">전체</button>${Object.entries(ST).map(([k, v]) => `<button data-v="${k}">${v}</button>`).join("")}</span><span class="err" id="rhErr"></span></div>
      <div class="list" id="rhList"></div></div>`;
    document.body.appendChild(back);
    RH.tg = NexaSearch.toggles(back.querySelector("#rhTg"), "reqs", renderReqHist);
    const q = back.querySelector("input");
    q.addEventListener("input", () => { RH.q = q.value; renderReqHist(); });
    back.addEventListener("keydown", (e) => { if (e.key === "Escape") { closeReqHist(); e.preventDefault(); } e.stopPropagation(); });
    back.addEventListener("mousedown", (e) => { if (e.target === back) closeReqHist(); });
    back.querySelector("#rhClose").onclick = closeReqHist;
    back.addEventListener("click", (e) => {
      const b = e.target.closest("#rhScope button, #rhSt button"); if (!b) return;
      if (b.closest("#rhScope")) RH.scope = b.dataset.v; else RH.st = b.dataset.v;
      renderReqHist();
    });
    back.querySelector("#rhList").addEventListener("click", onReqClick);
    renderReqHist(); q.focus();
  }
  function closeReqHist() { const b = $("#reqHist"); if (b) b.remove(); }
  function renderReqHist() {
    const back = $("#reqHist"), s = slide(); if (!back || !s) return;
    // "#4" = 슬라이드 4 의 요청("#4,5,7-10" 처럼 여러 장·범위) - 나머지 낱말만 글 찾기에 쓴다
    const { nums, text } = NexaSearch.split(RH.q);
    const M = NexaSearch.matcher(text, RH.tg ? RH.tg() : {});
    const all = S.reqs.filter((r) => (RH.scope !== "slide" || r.slide === s.id) && (!RH.st || r.status === RH.st) && (!nums.size || nums.has(reqIdx(r.slide))));
    // 찾기는 대화(묶음) 단위 - 묶음 안 어느 요청이든 맞으면 묶음 전체를 보여 준다(앞뒤 맥락)
    const hit = M.empty ? all : threadsOf(all).filter((g) => g.some((r) => M.any([r.text, r.reply, r.element, ...(r.elements || []), ...((r.attachments || []).map((a) => a.name))]))).flat();
    back.querySelectorAll("#rhScope button").forEach((b) => b.classList.toggle("on", b.dataset.v === RH.scope));
    back.querySelectorAll("#rhSt button").forEach((b) => b.classList.toggle("on", b.dataset.v === RH.st));
    back.querySelector("#rhErr").textContent = M.error ? `정규식 오류: ${M.error}` : "";
    back.querySelector("#rhCnt").textContent = M.empty && !nums.size && !RH.st && RH.scope === "all" ? `전체 ${S.reqs.length}건` : `${hit.length} / ${S.reqs.length}건`;
    back.querySelector("#rhList").innerHTML = hit.length ? reqThreadsHtml(hit, { hl: M.hl, fu: false }) : `<div class="hint" style="padding:20px;text-align:center">${S.reqs.length ? "찾는 요청이 없습니다" : "요청이 없다."}</div>`;
  }
  async function onReqClick(e) {
    const b = e.target.closest("button, a"); if (!b) return;
    if (b.dataset.sessStart !== undefined) { e.preventDefault(); sessStartDlg(); return; }
    if (b.dataset.lb !== undefined) { e.preventDefault(); const [rid, i] = b.dataset.lb.split(":"); attLightbox(rid, +i); return; }
    if (b.id === "reqAdd") {
      const t = $("#reqText").value.trim(); if (!t && !ATT.tab.length) return;
      const body = { action: "add", status: "draft", slide: slide().id, element: null, text: t || "(첨부 참고)" };
      if (ATT.tab.length) body.attachments = ATT.tab;
      const r = await api("POST", `/api/requests/${S.id}`, body);
      if (r.ok) { keep(S.id + "/" + slide().id, ""); ATT.tab = []; S.reqs = r.data; afterReqs(); toast("메모를 남겼습니다 - 아래 바에서 보내기"); }
      return;
    }
    if (b.dataset.attach) { attPick(b.dataset.attach); return; }
    if (b.dataset.attx) { const [w, i] = b.dataset.attx.split(":"); ATT[w].splice(+i, 1); attRender(w); return; }
    const v = e.target.closest("[data-attv]"); if (v) { const [w, i] = v.dataset.attv.split(":"); NexaLightbox.open(lbItems(ATT[w]), +i); return; }
    if (b.id === "reqSend") { await sendDrafts(); return; }
    if (b.closest("#reqFilter")) { S.reqOnlySlide = b.dataset.v === "1"; renderReqs(); return; }
    if (b.id === "reqMore") { openReqHist(); return; }
    const card = b.closest(".req"); if (!card) return;
    const rid = card.dataset.rid;
    if (b.dataset.goto !== undefined) {
      e.preventDefault();
      if (b.closest("#reqHist")) closeReqHist();  // 기록 창에서 슬라이드 링크 → 창을 닫고 그 슬라이드로
      const i = S.deck.slides.findIndex((x) => x.id === b.dataset.goto);
      if (i >= 0) { S.cur = i; S.sel = b.dataset.el && elById(b.dataset.el, S.deck.slides[i]) ? b.dataset.el : null; renderAll(); revealThumb(S.cur); }
      return;
    }
    if (b.dataset.fu) { S.fu = S.fu === rid ? null : rid; ATT.fu = []; renderReqs(); return; }
    if (b.dataset.fucancel) { S.fu = null; ATT.fu = []; renderReqs(); return; }
    if (b.dataset.fusend) { await fuSend(rid); return; }
    let body = null;
    if (b.dataset.rs) body = { action: "update", id: rid, status: b.dataset.rs };
    if (b.dataset.rdel) { if (!confirm("이 요청을 지울까요?")) return; body = { action: "delete", id: rid }; }
    if (body) { const r = await api("POST", `/api/requests/${S.id}`, body); if (r.ok) { S.reqs = r.data; renderReqs(); renderThumbs(); renderMarks(); } }
  }

  // ---------------------------------------------------------------- 레이아웃 검사 (아래 "검사" 탭)
  let chkT = 0;
  function scheduleCheck(ms = 600) { clearTimeout(chkT); chkT = setTimeout(runCheck, ms); }
  async function runCheck() {
    if (!S.id) return;
    const r = await api("GET", `/api/check/${S.id}`); if (!r.ok) return;
    S.check = r.data; renderCheck(); renderThumbs(); drawChkBox();
  }
  function renderCheck() {
    const C = $("#bp-check"), c = S.check; if (!C) return;
    const cnts = [$("#chkCnt"), $("#chkCnt2")];
    if (!c) { C.innerHTML = `<div class="hint">검사 중…</div>`; cnts.forEach((x) => (x.style.display = "none")); return; }
    const s = slide(), mine = c.issues.filter((x) => s && x.slide === s.id);
    const tot = mine.length;
    cnts.forEach((x) => { x.textContent = tot; x.style.display = tot ? "" : "none"; x.style.background = mine.some((i) => i.severity === "ERROR") ? "var(--err)" : "var(--warn)"; });
    const list = S.chkOnlySlide ? mine : c.issues;
    C.innerHTML = `<div class="row" style="margin-top:0"><b>레이아웃 검사</b><span class="hint">덱 전체 ERROR ${c.errors} · WARNING ${c.warnings} · 템플릿 ${esc(c.template || "")} · 최소 ${Object.entries(c.minFontPt).map(([k, v]) => `${k} ${v}pt`).join(" · ")}</span>
      <span class="seg" id="chkFilter" style="margin-left:auto"><button data-v="1" class="${S.chkOnlySlide ? "on" : ""}">이 슬라이드 (${mine.length})</button><button data-v="0" class="${S.chkOnlySlide ? "" : "on"}">전체 (${c.issues.length})</button></span>
      <button class="chip sm" id="chkRun">다시 검사</button>${mine.length ? `<button class="chip sm" id="chkFix">✨ 세션에 고치기 요청</button>` : ""}</div>
      ${list.length ? list.map((x) => `<div class="chk" data-k="${c.issues.indexOf(x)}"><span class="sev ${x.severity}">${x.severity}</span>
        <b>${x.n}</b> <span class="rule">${esc(x.rule)}</span><div class="msg">${esc(x.message)}</div></div>`).join("") : `<div class="hint">문제 없음.</div>`}`;
  }
  function drawChkBox() {
    $$("#ov .chkbox").forEach((b) => b.remove());
    const x = S.chkBox, s = slide(); if (!x || !s || x.slide !== s.id || !x.box) return;
    const d = document.createElement("div"); d.className = "chkbox";
    Object.assign(d.style, { left: x.box[0] + "px", top: x.box[1] + "px", width: Math.max(4, x.box[2]) + "px", height: Math.max(4, x.box[3]) + "px" });
    $("#ov").appendChild(d);
  }
  function onChkClick(e) {
    if (e.target.id === "chkRun") { S.check = null; renderCheck(); runCheck(); return; }
    if (e.target.id === "chkFix") { aiFix(); return; }
    const f = e.target.closest("#chkFilter button"); if (f) { S.chkOnlySlide = f.dataset.v === "1"; renderCheck(); return; }
    const it = e.target.closest(".chk"); if (!it || !S.check) return;
    const x = S.check.issues[+it.dataset.k]; const i = S.deck.slides.findIndex((s) => s.id === x.slide);
    if (i < 0) return;
    S.chkBox = x; S.cur = i; S.sel = x.elements && elById(x.elements[0], S.deck.slides[i]) ? x.elements[0] : null;
    renderAll(); revealThumb(S.cur); drawChkBox();
  }

  // ---------------------------------------------------------------- 세션 연결(요청 감시)
  // 요청 상대 이름 - 연결된 세션의 에이전트(웹: agent · 수동: label 의 "claude"/"codex")에 따라, 연결 없으면 "AI"
  function agentName() {
    const st = S.session || {};
    if (!st.connected) return "AI";
    const a = (st.agent || st.label || "").toLowerCase();
    return /codex/.test(a) ? "Codex" : /claude/.test(a) ? "Claude" : "AI";
  }
  // 세션이 없을 때 마지막 웹 세션이 왜 끝났는지(서버 재시작·유휴·사용자 중지) - /api/session 의 last
  function sessOffNote() {
    const l = (S.session || {}).last; if (!l || !l.reason) return "";
    const why = { "server-stop": "서버 재시작으로 세션 종료됨", idle: "유휴로 세션 종료됨", user: "사용자가 세션 중지", error: "오류로 세션 종료됨" }[l.reason] || `세션 종료됨(${l.reason})`;
    const m = /^\d{4}-(\d\d)-(\d\d)T(\d\d:\d\d)/.exec(l.stoppedAt || ""); return ` · ${why}${m ? `(${+m[1]}/${+m[2]} ${m[3]})` : ""}`;
  }
  function renderSession(st, act) {
    const before = S.session && (S.session.connected + "/" + (S.session.agent || S.session.label || "")) ;
    S.session = st;
    if (before !== (st.connected + "/" + (st.agent || st.label || "")) && $("#tab-reqs") && $("#tab-reqs").classList.contains("on")) renderReqs();
    const c = $("#sessChip"); if (!c) return;
    // 활동(Claude Code 훅 - 작업 공간 .claude/settings.json): 감시 담당 세션이 대화 입력을 처리 중인지·요청 처리 중인지·대기인지
    const w = act && act.watcher;
    let label = st.connected ? (st.working ? `세션 처리 중 ${st.working}` : "세션 연결됨") : "세션 연결 없음";
    if (st.connected && w) {
      if (w.state === "busy" && w.source === "chat") label = `대화 작업 중 ${w.minutes ? w.minutes + "분째" : ""}${st.working ? ` · 요청 ${st.working} 대기` : st.open ? ` · 요청 ${st.open} 대기` : ""}`;
      else if (w.state === "busy") label = st.working ? `요청 처리 중 ${st.working}` : "작업 중";
      else if (w.state === "idle") label = st.working ? `세션 처리 중 ${st.working}` : "대기 - 요청 바로 처리";
    }
    if (act && act.othersBusy) label += ` · 다른 세션 ${act.othersBusy}`;
    const webBusy = st.connected && st.kind === "web" && st.state === "running";  // 하트비트의 state - 턴 실행 중(요청 status 와 무관하게 파랑)
    if (st.connected && st.kind === "web") label = `웹 세션${webBusy ? ` 처리 중 (턴 ${st.turn || "?"})` : ""} · ${st.model || st.agent || ""}${st.user ? ` · ${st.user}` : ""}${st.allowWeb ? " · 웹 허용" : ""}${(st.grants || []).map((g) => " · " + g).join("")}${st.working ? ` · 요청 ${st.working}` : ""}`;
    c.className = "chip sm " + (st.connected ? (st.working || webBusy || (w && w.state === "busy") ? "busy" : "on") : "off");
    c.innerHTML = `<span class="dot"></span>${esc(label)} ▾`;
    if (w && w.state === "busy" && w.source === "chat" && w.prompt) c.dataset.prompt = w.prompt; else delete c.dataset.prompt;
    c.title = st.connected ? `${st.sessionId ? `claude 세션 ID ${st.sessionId}\n` : ""}${st.label || "Claude Code"} · 마지막 확인 ${st.last_seen} (${st.age}초 전) · 대기 ${st.open} · 처리 중 ${st.working}${c.dataset.prompt ? `
대화 입력: ${c.dataset.prompt}` : ""}`
      : `세션 연결 없음${st.last_seen ? ` - 마지막 확인 ${st.last_seen}` : ""}${sessOffNote()}. 눌러서 웹 세션을 시작하거나, 터미널 세션에서 watch_requests.py --stream 을 Monitor 로 실행하면 연결된다`;
  }

  // ---------------------------------------------------------------- 웹 AI 세션(B-5) - 세션 칩 메뉴 · 시작 창 · 진행 패널(SSE) · 턴 로그
  const WSS = { src: null, events: [], agent: null };
  const GRANTS = [["git", "git 기록", "add·commit·branch·switch·merge·stash·tag"], ["push", "push", "git push·pull·fetch - 원격으로 보냄"], ["root", "저장소 루트 접근", "작업 공간을 품은 저장소 루트의 문서(작업일지·README·docs) 읽기·쓰기"]];
  function sessMenu(btn) {
    const st = S.session || {};
    const web = st.connected && st.kind === "web";
    const items = web
      ? [{ h: `웹 세션 · ${st.agent || ""} · ${st.model || ""}${st.user ? ` · ${st.user}` : ""}${st.allowWeb ? " · 웹 허용" : ""}${(st.grants || []).map((g) => " · " + g).join("")}` },
         ...(st.sessionId ? [{ icon: "#", label: `세션 ID ${st.sessionId.slice(0, 8)} 복사`, act: () => sidCopy(st) }, { icon: "›", label: "확인 명령(claude --resume) 복사", act: () => sidCopy(st, true) }] : []),
         { icon: "▶", label: "진행 보기", act: sessProgress }, { icon: "⟳", label: "모델 바꾸기…", act: sessModelDlg },
         { icon: "📄", label: "턴 로그…", act: () => sessLog(1) }, "-",
         { icon: "■", label: "세션 중지", act: sessStop }]
      : st.connected
        ? [{ h: `수동 세션 · ${st.label || ""}` }, { html: `<div class="hint" style="padding:4px 10px;max-width:280px">터미널의 Claude Code 세션이 요청 감시(watch_requests)로 맡고 있습니다. 웹 세션으로 바꾸려면 그 감시를 끝내세요.</div>` }]
        : [...(sessOffNote() ? [{ h: sessOffNote().replace(/^ · /, "") }] : []), { icon: "▶", label: "웹 세션 시작…", act: sessStartDlg }, { html: `<div class="hint" style="padding:4px 10px;max-width:280px">서버가 AI(claude·codex)를 띄워 편집기 요청을 처리합니다. 터미널 세션(Monitor)과 함께 쓸 수 없습니다.</div>` }];
    openMenu(btn, items, { right: false });
  }
  async function sidCopy(st, cmd) {  // 세션 식별자 - ID 복사, cmd 면 그 폴더에서 claude --resume <ID>(보기만; 웹 세션이 도는 중에 이어 쓰면 대화가 섞인다)
    const text = cmd ? (st.cwd ? `cd "${st.cwd}"; ` : "") + `claude --resume ${st.sessionId}` : st.sessionId, what = cmd ? "확인 명령을" : "세션 ID 를";
    try { await navigator.clipboard.writeText(text); toast(`${what} 복사했습니다 - ${text}`, 5000); }
    catch (e) { const ta = document.createElement("textarea"); ta.value = text; ta.style.position = "fixed"; ta.style.opacity = "0"; document.body.appendChild(ta); ta.select(); const ok = document.execCommand && document.execCommand("copy"); ta.remove(); if (ok) toast(`${what} 복사했습니다 - ${text}`, 5000); else prompt(what, text); }
    if (!(st.turn > 0)) setTimeout(() => toast("이 세션은 아직 첫 턴 전이라 claude --resume 로 열리지 않습니다 - 요청을 하나 처리한 뒤에 다시 시도", 6000), 600);
  }
  function sessBox(html) { $("#sessDlg .box").innerHTML = html; $("#sessDlg").classList.add("show"); }
  function sessClose() { $("#sessDlg").classList.remove("show"); if (WSS.src) { WSS.src.close(); WSS.src = null; } }
  async function sessStartDlg() {
    sessBox(`<div class="hint">에이전트·로그인 상태를 확인하는 중…</div>`);
    const r = await api("GET", "/api/agent");
    if (!r.ok) { sessBox(`<div class="hint">확인 실패: ${esc((r.data && r.data.error) || r.status)}</div><div class="row"><button class="chip sm" data-sd="close">닫기</button></div>`); return; }
    WSS.agent = r.data;
    const ag = r.data.agents, cur = r.data.agent, model = r.data.model;
    const opt = (name) => { const a = ag[name]; const ok = a.installed && a.loggedIn; return `<option value="${name}" ${name === cur ? "selected" : ""} ${ok ? "" : "disabled"}>${esc(a.label)}${a.verified ? "" : " (미확인)"}${ok ? "" : a.installed ? " - 로그인 안 됨" : " - 미설치"}</option>`; };
    const models = (name) => (r.data.models[name] || []).map((m) => `<option value="${esc(m)}" ${m === model ? "selected" : ""}>${esc(m)}</option>`).join("") + `<option value="__custom">직접 입력…</option>`;
    sessBox(`<div class="row" style="align-items:center;gap:8px"><h3 style="margin:0;flex:1">웹 세션 시작</h3><button class="chip sm" data-sd="close">닫기</button></div>
      <div class="hint">서버가 이 작업 공간에서 AI 를 턴마다 실행해 편집기 요청을 처리합니다. 쓰기 범위는 이 작업 공간 폴더뿐이며 <code>nexa.py</code> 명령만 허용됩니다.</div>
      <label class="f">에이전트</label><select id="sdAgent">${opt("claude")}${opt("codex")}</select>
      <div class="hint" id="sdHint">${esc(ag[cur].hint || "")}${ag[cur].hint && ag[cur].doc ? ` (엔진 ${esc(ag[cur].doc)})` : ""}</div>
      <label class="f">모델 <span class="hint">(기본: ${esc(model)} — ${esc(r.data.sources.model)})</span></label>
      <div class="row" style="gap:6px"><select id="sdModel">${models(cur)}</select><input type="text" id="sdModelText" placeholder="모델 ID 직접 입력" style="display:none;flex:1"></div>
      <label class="f" style="display:flex;align-items:center;gap:8px;font-weight:400"><input type="checkbox" id="sdSave"> 이 작업 공간 기본으로 저장 <select id="sdSaveAs" style="font-size:12px"><option value="local">이 PC 만(nexa-slide.local.json)</option><option value="shared">공유(nexa-slide.json)</option></select></label>
      ${r.data.allowWeb ? `<label class="f" style="display:flex;align-items:center;gap:8px;font-weight:400"><input type="checkbox" id="sdWeb" ${r.data.canAllowWeb ? "" : "disabled"}> 이 세션에 웹 검색 허용(WebSearch·WebFetch) ${r.data.canAllowWeb ? "" : '<span class="hint">- 관리자만</span>'}</label>
      <div class="hint" id="sdWebWarn" style="display:none;color:var(--err)">이 세션이 외부 웹을 검색·열람합니다 - 슬라이드·요청 내용이 검색어·URL 로 외부에 전달될 수 있습니다(claude 만).</div>` : ""}
      <div class="hint">한도: 유휴 ${esc(String(r.data.limits.sessionIdleMinutes))}분 · 턴 ${esc(String(r.data.limits.sessionTurnMinutes))}분 · 동시 ${esc(String(r.data.limits.sessionMax))}</div>
      <div class="row" style="justify-content:flex-end;gap:8px"><button class="chip sm" data-sd="close">취소</button><button class="chip sm primary" data-sd="start">시작</button></div>`);
    $("#sdAgent").onchange = () => { const n = $("#sdAgent").value; $("#sdModel").innerHTML = models(n); $("#sdHint").textContent = (ag[n].hint || "") + (ag[n].hint && ag[n].doc ? ` (엔진 ${ag[n].doc})` : ""); };
    if ($("#sdWeb")) $("#sdWeb").onchange = () => { $("#sdWebWarn").style.display = $("#sdWeb").checked ? "" : "none"; };
    const av = GRANTS.filter(([k]) => (r.data.grants || {})[k]);  // git·push·저장소 루트 - 전역이 켜진 것만(관리자만 체크)
    if (av.length) $("#sessDlg [data-sd=start]").parentElement.insertAdjacentHTML("beforebegin", `<div id="sdGrants">${av.map(([k, l, h]) => `<label class="f" style="display:flex;align-items:center;gap:8px;font-weight:400"><input type="checkbox" data-grant="${k}" ${r.data.canGrant ? "" : "disabled"}> 이 세션에 ${l} 허용 <span class="hint">- ${h}${r.data.canGrant ? "" : " · 관리자만"}</span></label>`).join("")}</div>`);
    $$("#sdGrants [data-grant]").forEach((c) => (c.onchange = () => { if (c.dataset.grant === "push" && c.checked) { const g = $("#sdGrants [data-grant=git]"); if (g) g.checked = true; } }));
    $("#sdModel").onchange = () => { $("#sdModelText").style.display = $("#sdModel").value === "__custom" ? "" : "none"; };
  }
  async function sessStart() {
    const agent = $("#sdAgent").value, model = $("#sdModel").value === "__custom" ? $("#sdModelText").value.trim() : $("#sdModel").value;
    if (!model) { toast("모델을 고르거나 입력하세요"); return; }
    const body = { action: "start", agent, model }; if ($("#sdSave").checked) body.saveAs = $("#sdSaveAs").value;
    if ($("#sdWeb") && $("#sdWeb").checked) body.allowWeb = true;
    const gr = $$("#sdGrants [data-grant]").filter((c) => c.checked).map((c) => c.dataset.grant); if (gr.length) body.grants = gr;
    const r = await api("POST", "/api/wsession", body);
    if (!r.ok) { toast("시작 실패: " + ((r.data && r.data.error) || r.status), 6000); return; }
    toast(`웹 세션 시작 - ${agent} · ${model}${r.data.allowWeb ? " · 웹 허용" : ""}${(r.data.grants || []).map((g) => " · " + g).join("")}`); renderSession({ ...(S.session || {}), connected: true, kind: "web", agent, model, user: r.data.startedBy, allowWeb: !!r.data.allowWeb, grants: r.data.grants || [], label: `web:${agent}`, open: r.data.open, working: r.data.working, last_seen: "", age: 0 });
    sessProgress();
  }
  async function sessStop() {
    if (!confirm("웹 세션을 중지할까요? 실행 중인 턴이 있으면 바로 종료됩니다.")) return;
    const r = await api("POST", "/api/wsession", { action: "stop" });
    if (!r.ok) { toast("중지하지 못했습니다: " + ((r.data && r.data.error) || r.status), 5000); return; }
    toast("웹 세션을 중지했습니다"); sessClose(); api("GET", "/api/session").then((x) => x.ok && renderSession(x.data));
  }
  async function sessModelDlg() {
    const r = await api("GET", "/api/agent"); const st = S.session || {};
    const list = r.ok ? (r.data.models[st.agent] || []) : [];
    sessBox(`<div class="row" style="align-items:center;gap:8px"><h3 style="margin:0;flex:1">모델 바꾸기</h3><button class="chip sm" data-sd="close">닫기</button></div>
      <div class="hint">지금 ${esc(st.model || "")} · 턴 실행 중이면 끝난 뒤 적용됩니다.</div>
      <div class="row" style="gap:6px"><select id="sdModel">${list.map((m) => `<option value="${esc(m)}" ${m === st.model ? "selected" : ""}>${esc(m)}</option>`).join("")}<option value="__custom">직접 입력…</option></select><input type="text" id="sdModelText" placeholder="모델 ID" style="display:none;flex:1"></div>
      <label class="f" style="display:flex;align-items:center;gap:8px;font-weight:400"><input type="checkbox" id="sdSave"> 이 작업 공간 기본으로 저장 <select id="sdSaveAs" style="font-size:12px"><option value="local">이 PC 만</option><option value="shared">공유</option></select></label>
      <div class="row" style="justify-content:flex-end;gap:8px"><button class="chip sm" data-sd="close">취소</button><button class="chip sm primary" data-sd="modelgo">바꾸기</button></div>`);
    $("#sdModel").onchange = () => { $("#sdModelText").style.display = $("#sdModel").value === "__custom" ? "" : "none"; };
  }
  async function sessModel() {
    const model = $("#sdModel").value === "__custom" ? $("#sdModelText").value.trim() : $("#sdModel").value;
    if (!model) { toast("모델을 고르거나 입력하세요"); return; }
    const body = { action: "model", model }; if ($("#sdSave").checked) body.saveAs = $("#sdSaveAs").value;
    const r = await api("POST", "/api/wsession", body);
    if (!r.ok) { toast("바꾸지 못했습니다: " + ((r.data && r.data.error) || r.status), 5000); return; }
    toast(r.data.pendingModel ? `턴이 끝난 뒤 ${model} 로 바뀝니다` : `모델을 ${model} 로 바꿨습니다`); sessClose();
  }
  function sessProgress() {
    sessBox(`<div class="row" style="align-items:center;gap:8px"><h3 style="margin:0;flex:1">웹 세션 진행</h3><span class="hint" id="sdState"></span><button class="chip sm" data-sd="log">턴 로그</button><button class="chip sm" data-sd="close">닫기</button></div>
      <div class="ev" id="sdEv"><div class="hint">연결 중…</div></div>
      <div class="row" style="justify-content:flex-end;gap:8px"><button class="chip sm" data-sd="model">모델 바꾸기…</button><button class="chip sm" data-sd="stop">세션 중지</button></div>`);
    if (WSS.src) WSS.src.close();
    WSS.events = [];
    const box = $("#sdEv"); box.innerHTML = "";
    const line = (e) => {
      const d = e.data || e; const t = (d.t || "").slice(11, 19);
      let txt = d.type;
      if (d.type === "state") txt = `상태 ${d.state}${d.reason ? ` (${d.reason})` : ""}${d.model ? ` · ${d.model}` : ""}`;
      else if (d.type === "turn.start") txt = `턴 ${d.turn} 시작 - 요청 ${d.count}건 (${d.reason}) · ${d.model}`;
      else if (d.type === "init") txt = `세션 ${String(d.sessionId || "").slice(0, 8)} · 모델 ${d.model}`;
      else if (d.type === "tool") txt = `도구 ${d.tool} ${d.summary || ""}`;
      else if (d.type === "text") txt = `✎ ${d.text}`;
      else if (d.type === "turn.end") txt = `턴 ${d.turn} 끝 - ${d.ok ? "정상" : "실패"}${d.costUsd != null ? ` · $${Number(d.costUsd).toFixed(4)}` : ""}${d.unhandled && d.unhandled.length ? ` · 처리 못 함 ${d.unhandled.length}` : ""}${d.error ? ` · ${d.error}` : ""}`;
      else if (d.type === "model") txt = `모델 → ${d.model}${d.pending ? " (턴 끝난 뒤)" : ""}`;
      else if (d.type === "warn" || d.type === "error") txt = `${d.type === "warn" ? "경고" : "오류"} ${d.message || ""}`;
      else if (d.type === "idle") txt = `유휴 ${d.minutes}분 초과 - 끊음`;
      const div = document.createElement("div"); div.className = "e " + d.type; div.textContent = `${t} ${txt}`;
      box.appendChild(div); box.scrollTop = box.scrollHeight;
    };
    try {
      const src = new EventSource(`${BASE}/api/wsession/events`); WSS.src = src;
      ["state", "turn.start", "init", "text", "tool", "tool_result", "turn.end", "warn", "error", "model", "idle"].forEach((k) => src.addEventListener(k, (ev) => { try { const d = JSON.parse(ev.data); if (k === "state" && !d.seq) { $("#sdState").textContent = `${d.state} · ${d.agent || ""} · ${d.model || ""}`; } line({ ...d, type: d.type || k }); if (d.type === "state" || k === "state") $("#sdState").textContent = `${d.state}`; } catch (e) { /* 무시 */ } }));
      src.onerror = () => { const div = document.createElement("div"); div.className = "e warn"; div.textContent = "연결이 끊겨 다시 붙는 중…"; box.appendChild(div); };
    } catch (e) { box.textContent = "이 브라우저는 SSE 를 지원하지 않습니다"; }
  }
  async function sessLog(n) {
    const r = await api("GET", `/api/wsession/log?turn=${n}`);
    const lines = r.ok ? r.data.lines : [];
    sessBox(`<div class="row" style="align-items:center;gap:8px"><h3 style="margin:0;flex:1">턴 ${n} 로그 <span class="hint">(어댑터 출력 원문 ${lines.length}줄)</span></h3>
      <button class="chip sm" data-sd="logprev">◀</button><button class="chip sm" data-sd="lognext">▶</button><button class="chip sm" data-sd="progress">진행</button><button class="chip sm" data-sd="close">닫기</button></div>
      <div class="ev">${lines.length ? lines.map((l) => `<div class="e">${esc(l.length > 400 ? l.slice(0, 400) + " …" : l)}</div>`).join("") : '<div class="hint">로그 없음</div>'}</div>`);
    WSS.logTurn = n;
  }
  $("#sessDlg").addEventListener("click", (e) => {
    if (e.target === $("#sessDlg")) { sessClose(); return; }
    const b = e.target.closest("[data-sd]"); if (!b) return;
    const k = b.dataset.sd;
    if (k === "close") sessClose(); else if (k === "start") sessStart(); else if (k === "model") sessModelDlg(); else if (k === "modelgo") sessModel();
    else if (k === "stop") sessStop(); else if (k === "log") sessLog(1); else if (k === "progress") sessProgress();
    else if (k === "logprev") sessLog(Math.max(1, (WSS.logTurn || 1) - 1)); else if (k === "lognext") sessLog((WSS.logTurn || 1) + 1);
  });
  async function flushReqs(quiet) {
    const r = await api("POST", `/api/flush/${S.id}`);
    if (!r.ok) { if (!quiet) toast("보내기 신호를 쓰지 못했습니다"); return; }
    renderSession(r.data.session);
  }

  // ---------------------------------------------------------------- 아래 패널(노트·개요·검사)
  function setBtab(b) {
    S.btab = b; LS.set("btab", b);
    $$("#bTabs [data-b]").forEach((x) => x.classList.toggle("on", x.dataset.b === b));
    $$("#bottom .bpanel").forEach((p) => p.classList.toggle("on", p.id === "bp-" + b));
    $("#bottom").classList.remove("fold"); LS.set("bfold", "0"); $("#bFold").textContent = "▾";
    setTimeout(fitStage, 0);
  }
  function toggleBottom() { const f = !$("#bottom").classList.contains("fold"); $("#bottom").classList.toggle("fold", f); $("#bFold").textContent = f ? "▴" : "▾"; LS.set("bfold", f ? "1" : "0"); setTimeout(fitStage, 0); }
  function renderNotes() {
    const s = slide(), n = s ? s.notes || "" : "";
    if (document.activeElement !== $("#notesTa")) $("#notesTa").value = n;
    $("#notesInfo").textContent = n ? `· ${n.length}자` : "· 비어 있음";
  }
  let notesSnap = false, notesT = 0;
  function onNotes() {
    const s = slide(); if (!s) return;
    if (!notesSnap) { snapshot(); notesSnap = true; }
    s.notes = $("#notesTa").value; $("#notesInfo").textContent = s.notes ? `· ${s.notes.length}자` : "· 비어 있음"; S.dirty = true; setStatus("dirty", "저장 대기");
    clearTimeout(notesT); notesT = setTimeout(() => { notesSnap = false; }, 1500);
    scheduleSave();
  }
  function slideTitle(s) {
    const t = s.elements.find((e) => e.role === "title") || s.elements.find((e) => e.type === "text" && (e.size || 20) >= 28);
    return t ? Render.plain(String(t.text || "")).replace(/\n/g, " ") : `(${s.layout || "슬라이드"})`;
  }
  function renderOutline() {
    if (!S.deck) return;
    $("#outlineList").innerHTML = S.deck.slides.map((s, i) => `<div data-i="${i}" class="${i === S.cur ? "on" : ""}"><span class="n">${i + 1}</span><span>${esc(slideTitle(s))}</span>${chgOf(s.id) ? `<span class="bd chg">변경</span>` : ""}<span class="hint" style="margin:0 0 0 auto">${esc(s.layout || "")}</span></div>`).join("");
  }
  function renderCounter() { $("#slideCounter").textContent = S.deck ? `${S.cur + 1} / ${S.deck.slides.length}` : "- / -"; }

  // ---------------------------------------------------------------- 기록(자동 백업으로 되돌리기)
  async function loadHist() {
    const H = $("#tab-hist"); H.innerHTML = `<div class="hint">불러오는 중…</div>`;
    const r = await api("GET", `/api/history/${S.id}`);
    const list = r.ok ? r.data : [];
    H.innerHTML = `<div class="sec"><h3>기록 - ${esc(S.id)}</h3><div class="hint">편집기가 저장할 때마다·build 로 덮어쓰기 전·밖에서 바뀌기 직전에 남긴 자동 백업이다(최근 50개 - 장기 보관이 아니다). 무엇이 바뀌었는지는 변경 탭. 되돌리면 지금 상태도 기록에 남으므로 다시 돌아올 수 있다(Ctrl+Z 도 가능).</div></div>
      ${list.length ? list.map((h) => `<div class="hist"><span class="k ${h.kind}">${h.kind === "build" ? "빌드 전" : h.kind === "ext" ? "외부 변경 전" : "저장 전"}</span><span>${esc(h.at.replace("T", " "))}</span><span class="sp"></span>
        <button class="chip sm" data-hf="${esc(h.file)}">되돌리기</button></div>`).join("") : `<div class="hint">기록이 없다.</div>`}`;
  }
  async function onHistClick(e) {
    const b = e.target.closest("[data-hf]"); if (!b) return;
    if (await restoreFrom(b.dataset.hf, b.closest(".hist").children[1].textContent)) { loadHist(); loadChanges(); }
  }

  // ---------------------------------------------------------------- 발표
  function present(fromCur) {
    const P = $("#present"); P.classList.add("show");
    S.pIdx = fromCur ? S.cur : 0; S.pStart = Date.now();
    try {  // 발표자 보기(presenter.html)와 쪽 맞추기
      if (S.pch) S.pch.close();
      S.pch = new BroadcastChannel("nexa-present:" + S.id);
      S.pch.onmessage = (e) => { const d = e.data || {}; if (typeof d.goto === "number") { S.pIdx = Math.max(0, Math.min(S.deck.slides.length - 1, d.goto)); renderPresent(); } else if (d.hello) S.pch.postMessage({ idx: S.pIdx }); };
    } catch (e) { S.pch = null; }
    if (P.requestFullscreen) P.requestFullscreen().catch(() => {});
    renderPresent();
  }
  function renderPresent() {
    const s = S.deck.slides[S.pIdx]; if (!s) return;
    const st = $("#presentStage"); st.innerHTML = Render.renderSlide(s, S.pIdx + 1);
    const notes = $("#present").classList.contains("notes"), avail = innerHeight * (notes ? 0.64 : 1);
    const k = Math.min(innerWidth / SW, avail / SH);
    st.style.transform = `scale(${k})`; st.style.left = (innerWidth - SW * k) / 2 + "px"; st.style.top = (avail - SH * k) / 2 + "px";
    $("#presentNotes").textContent = s.notes || "(노트 없음)";
    const sec = Math.floor((Date.now() - S.pStart) / 1000);
    $("#presentInfo").textContent = `${S.pIdx + 1} / ${S.deck.slides.length} · ${String(Math.floor(sec / 60)).padStart(2, "0")}:${String(sec % 60).padStart(2, "0")}`;
    if (S.pch) S.pch.postMessage({ idx: S.pIdx });
  }
  function openPresenter() { window.open(`${BASE}/studio/presenter.html?deck=${encodeURIComponent(S.id)}&n=${S.pIdx + 1}`, "nexa-presenter", "width=1100,height=680"); }
  /** 요소 링크(link) - "#3" 은 3번 슬라이드, "#<슬라이드 id>", 그 밖은 주소(새 탭). 발표 화면에서 누르면 */
  /** 발표 화면 이동 - 숨김 슬라이드(hidden)는 건너뛴다. 끝이면 그대로 */
  function pStep(d) {
    const n = S.deck.slides.length; let i = S.pIdx;
    do { i += d; } while (i >= 0 && i < n && S.deck.slides[i].hidden);
    if (i >= 0 && i < n) S.pIdx = i; else S.pIdx = Math.max(0, Math.min(n - 1, S.pIdx));
  }
  function followLink(v) {
    if (!v) return false;
    if (v.startsWith("#")) { const key = v.slice(1); const n = /^\d+$/.test(key) ? +key : S.deck.slides.findIndex((s) => s.id === key) + 1; if (n >= 1 && n <= S.deck.slides.length) { S.pIdx = n - 1; renderPresent(); return true; } toast(`없는 슬라이드: ${v}`); return true; }
    window.open(v, "_blank", "noopener"); return true;
  }
  function endPresent() { if (S.pch) { try { S.pch.close(); } catch (e) { /* 무시 */ } S.pch = null; } $("#present").classList.remove("show"); if (document.fullscreenElement) document.exitFullscreen().catch(() => {}); goSlide(S.pIdx); }
  function presentKey(e) {
    const k = e.key;
    if (k === "Escape") { endPresent(); return; }
    if (["ArrowRight", "ArrowDown", "PageDown", " ", "Enter"].includes(k)) pStep(1);
    else if (["ArrowLeft", "ArrowUp", "PageUp", "Backspace"].includes(k)) pStep(-1);
    else if (k === "Home") { S.pIdx = -1; pStep(1); } else if (k === "End") { S.pIdx = S.deck.slides.length; pStep(-1); }
    else if (k.toLowerCase() === "n") $("#present").classList.toggle("notes");
    else if (k.toLowerCase() === "p") openPresenter();
    else return;
    e.preventDefault(); renderPresent();
  }

  // ---------------------------------------------------------------- 선택·끌기·크기 조절
  function select(id) { S.sel = id; S.multi = []; S.multiSlide = null; drawSel(); renderProps(); renderFtb(); }
  function setSelection(ids) {  // 여러 요소를 한 번에 고른다(첫 요소가 주 선택)
    ids = ids.filter((id) => elById(id));
    S.sel = ids[0] || null; S.multi = ids.slice(1); S.multiSlide = slide() ? slide().id : null;
    drawSel(); renderProps(); renderFtb();
  }
  function toggleSel(id) {  // Shift/Ctrl+클릭 - 더하거나 뺀다
    const ids = selIds();
    setSelection(ids.includes(id) ? ids.filter((x) => x !== id) : [...ids, id]);
  }
  function toSlide(e) { const r = $("#stage").getBoundingClientRect(); return { x: (e.clientX - r.left) / scale, y: (e.clientY - r.top) / scale }; }
  let drag = null;
  function onDown(e) {
    if (e.button === 1 || (e.button === 0 && spaceDown)) { // 가운데 버튼·스페이스+끌기 = 화면 이동
      const vp = $("#vpEdit"); S.pan = { x: e.clientX, y: e.clientY, l: vp.scrollLeft, t: vp.scrollTop }; document.body.classList.add("panning"); e.preventDefault(); return;
    }
    if (e.button !== 0 || S.editing) return;
    if (S.mode === "draw") { drawDown(e); return; }
    const hd = e.target.closest(".hd"), p = toSlide(e);
    if (S.mode === "pick") {
      const node = topEl(e.target);
      if (!node) { select(null); closeMemo(); return; }
      select(node.dataset.id); openMemo({ element: node.dataset.id }); e.preventDefault(); return;
    }
    if (hd && !isMulti()) { const el = selEl(); if (!el) return; drag = { mode: "resize", h: hd.dataset.h, el, orig: clone(el), p0: p, moved: false, before: deckJson() }; e.preventDefault(); return; }
    const node = topEl(e.target), add = e.shiftKey || e.ctrlKey || e.metaKey;
    if (!node) {  // 빈 곳 - 끌면 범위 선택(Shift/Ctrl 이면 더하기), 그냥 누르면 선택 해제
      drag = { mode: "marquee", p0: p, box: { x: p.x, y: p.y, w: 0, h: 0 }, base: add ? selIds() : [], moved: false };
      e.preventDefault(); return;
    }
    const id = node.dataset.id;
    if (add) { toggleSel(id); e.preventDefault(); return; }
    if (!selIds().includes(id)) select(id);
    const els = selEls().filter((x) => !x.locked); if (!els.length) return;
    drag = { mode: "move", el: elById(id), els, origs: els.map(clone), orig: clone(elById(id)), p0: p, moved: false, before: deckJson() };
    e.preventDefault();
  }
  function onMove(e) {
    if (S.pan) { const vp = $("#vpEdit"); vp.scrollLeft = S.pan.l - (e.clientX - S.pan.x); vp.scrollTop = S.pan.t - (e.clientY - S.pan.y); return; }
    if (S.drawing && S.drawing.p0) { drawMove(e); return; }
    if (!drag) return;
    const p = toSlide(e), dx = p.x - drag.p0.x, dy = p.y - drag.p0.y, free = e.shiftKey, el = drag.el, o = drag.orig;
    if (!drag.moved && Math.hypot(dx, dy) * scale < 3) return;
    drag.moved = true;
    if (drag.mode === "marquee") {
      drag.box = { x: Math.min(drag.p0.x, p.x), y: Math.min(drag.p0.y, p.y), w: Math.abs(dx), h: Math.abs(dy) };
      drawSel(); return;
    }
    if (drag.mode === "move") {  // 잡은 요소 기준으로 격자에 맞춘 이동량을 고른 요소 모두에 - 그 뒤 스마트 가이드(다른 요소·슬라이드 가운데)에 붙인다
      const b0 = boxOf(o); let mx = snap(b0.x + dx, free) - b0.x, my = snap(b0.y + dy, free) - b0.y;
      const guides = [];
      if (!free) {
        const bs = drag.origs.map(boxOf), gx1 = Math.min(...bs.map((b) => b.x)) + mx, gy1 = Math.min(...bs.map((b) => b.y)) + my, gx2 = Math.max(...bs.map((b) => b.x + b.w)) + mx, gy2 = Math.max(...bs.map((b) => b.y + b.h)) + my;
        const moving = new Set(drag.els.map((x) => x.id)), others = slide().elements.filter((x) => !moving.has(x.id)).map(boxOf);
        const tx = [[0, "edge"], [SW / 2, "center"], [SW, "edge"]].concat(others.flatMap((b) => [[b.x, "edge"], [b.x + b.w / 2, "center"], [b.x + b.w, "edge"]]));
        const ty = [[0, "edge"], [SH / 2, "center"], [SH, "edge"]].concat(others.flatMap((b) => [[b.y, "edge"], [b.y + b.h / 2, "center"], [b.y + b.h, "edge"]]));
        const TH = 6 / scale + 2;
        const bestX = [[gx1, "l"], [(gx1 + gx2) / 2, "c"], [gx2, "r"]].flatMap(([v, w]) => tx.map(([t]) => [Math.abs(t - v), t - v, t])).filter((c) => c[0] <= TH).sort((a, b) => a[0] - b[0])[0];
        const bestY = [[gy1, "t"], [(gy1 + gy2) / 2, "m"], [gy2, "b"]].flatMap(([v, w]) => ty.map(([t]) => [Math.abs(t - v), t - v, t])).filter((c) => c[0] <= TH).sort((a, b) => a[0] - b[0])[0];
        if (bestX) { mx += bestX[1]; guides.push(["v", bestX[2]]); }
        if (bestY) { my += bestY[1]; guides.push(["h", bestY[2]]); }
      }
      drag.guides = guides;
      drag.els.forEach((x, i) => {
        const q = drag.origs[i];
        if (isLine(x)) { x.x1 = q.x1 + mx; x.x2 = q.x2 + mx; x.y1 = q.y1 + my; x.y2 = q.y2 + my; Object.assign(x, Render.lineBox(x)); } else { x.x = q.x + mx; x.y = q.y + my; }
        renderElementDom(x);
      });
      drawSel(); drawGuides(drag.guides); renderMarks(); return;
    } else if (drag.h === "p1" || drag.h === "p2") {
      const k = drag.h === "p1" ? ["x1", "y1"] : ["x2", "y2"];
      el[k[0]] = snap(o[k[0]] + dx, free); el[k[1]] = snap(o[k[1]] + dy, free); Object.assign(el, Render.lineBox(el));
    } else {
      let x1 = o.x, y1 = o.y, x2 = o.x + o.w, y2 = o.y + o.h; const h = drag.h;
      if (h.includes("w")) x1 = snap(o.x + dx, free); if (h.includes("e")) x2 = snap(o.x + o.w + dx, free);
      if (h.includes("n")) y1 = snap(o.y + dy, free); if (h.includes("s")) y2 = snap(o.y + o.h + dy, free);
      if ((el.type === "image" || el.type === "icon") && h.length === 2) { const ratio = o.w / o.h, w = Math.max(4, x2 - x1), hh = w / ratio; if (h.includes("n")) y1 = y2 - hh; else y2 = y1 + hh; }
      el.x = Math.round(Math.min(x1, x2 - 4)); el.y = Math.round(Math.min(y1, y2 - 4)); el.w = Math.round(Math.max(4, x2 - x1)); el.h = Math.round(Math.max(4, y2 - y1));
      if (el.type === "group" && o.children) {  // 묶음 크기 조절 - 자식 위치·크기를 비율로(글자 크기는 그대로)
        const sx = el.w / (o.w || 1), sy = el.h / (o.h || 1);
        el.children = o.children.map((c) => { const k = clone(c); if (isLine(k)) { k.x1 *= sx; k.x2 *= sx; k.y1 *= sy; k.y2 *= sy; Object.assign(k, Render.lineBox(k)); } else { k.x = Math.round(k.x * sx); k.y = Math.round(k.y * sy); k.w = Math.max(4, Math.round(k.w * sx)); k.h = Math.max(4, Math.round(k.h * sy)); } return k; });
      }
    }
    renderElementDom(el); drawSel(); renderMarks();
  }
  function onUp() {
    if (S.pan) { S.pan = null; document.body.classList.remove("panning"); return; }
    if (S.drawing && S.drawing.p0) { drawUp(); return; }
    if (!drag) return;
    const d = drag; drag = null;
    if (d.mode === "marquee") {
      if (!d.moved) { if (!d.base.length) select(null); else drawSel(); return; }
      const m = d.box, s = slide();  // 상자 안에 완전히 들어간 요소(잠긴 요소 포함 - 이동은 안 됨)
      const inside = s.elements.filter((x) => { const b = boxOf(x); return b.x >= m.x && b.y >= m.y && b.x + b.w <= m.x + m.w && b.y + b.h <= m.y + m.h; }).map((x) => x.id);
      setSelection([...d.base, ...inside.filter((id) => !d.base.includes(id))]);
      if (inside.length) toast(`${selIds().length}개 선택 - 끌어서 함께 이동, 서식 줄은 고른 요소 모두에 적용`);
      return;
    }
    if (d.moved) { S.undo.push(d.before); S.redo = []; afterChange(); }
  }

  // ---------------------------------------------------------------- 글자 직접 편집
  function startEdit(el) {
    if (!el || el.locked || S.mode !== "edit") return;
    let raw;
    if (TEXTY.has(el.type) || el.type === "code" || el.type === "plan") raw = el.text || "";
    else if (el.type === "bullets") raw = bulletsToText(el.items);
    else if (el.type === "table") raw = tableToText(el.rows);
    else return;
    const b = boxOf(el), ed = document.createElement("div");
    ed.className = "editor"; ed.setAttribute("contenteditable", "plaintext-only");
    if (ed.contentEditable !== "plaintext-only") ed.setAttribute("contenteditable", "true");
    const mono = el.type === "code" || el.type === "plan" || Render.fontRole(el.font) === "mono";
    Object.assign(ed.style, { left: b.x + "px", top: b.y + "px", minWidth: Math.max(80, b.w) + "px", minHeight: Math.max(24, b.h) + "px",
      fontSize: (el.size || 20) + "px", lineHeight: (el.lineHeight || 1.4), fontFamily: mono ? "Consolas, 'Malgun Gothic', monospace" : "'Malgun Gothic', sans-serif" });
    ed.textContent = raw;
    $("#stage").appendChild(ed);
    S.editing = { el, ed, before: deckJson() };
    drawSel(); renderFtb(); ed.focus();
    const rg = document.createRange(); rg.selectNodeContents(ed); const sel = getSelection(); sel.removeAllRanges(); sel.addRange(rg);
    ed.addEventListener("keydown", (e) => {
      e.stopPropagation();
      if (e.key === "Escape" || (e.key === "Enter" && (e.ctrlKey || e.metaKey))) { e.preventDefault(); endEdit(true); }
      else if (e.key === "Enter" && ed.contentEditable === "true") { e.preventDefault(); document.execCommand("insertText", false, "\n"); }
    });
    ed.addEventListener("blur", () => endEdit(true));
  }
  function endEdit(commit) {
    const E = S.editing; if (!E) return;
    S.editing = null;
    const t = E.ed.innerText.replace(/\r/g, "").replace(/\n$/, "");
    E.ed.remove();
    const el = E.el;
    if (commit) {
      const old = el.type === "bullets" ? bulletsToText(el.items) : el.type === "table" ? tableToText(el.rows) : el.text || "";
      if (t !== old) {
        S.undo.push(E.before); S.redo = [];
        if (el.type === "bullets") el.items = textToBullets(t); else if (el.type === "table") el.rows = textToTable(t); else el.text = t;
        afterChange(); return;
      }
    }
    drawSel(); renderFtb();
  }

  // ---------------------------------------------------------------- 요소·슬라이드 조작
  function newElId(s) { let n = s.elements.length + 1; while (s.elements.some((e) => e.id === "e" + String(n).padStart(2, "0"))) n++; return "e" + String(n).padStart(2, "0"); }
  function newSlideId() { let n = S.deck.slides.length + 1; while (S.deck.slides.some((s) => s.id === "s" + String(n).padStart(2, "0"))) n++; return "s" + String(n).padStart(2, "0"); }
  function delEl() {
    const s = slide(), els = selEls().filter((x) => !x.locked); if (!els.length) return;
    snapshot(); for (const el of els) s.elements.splice(s.elements.indexOf(el), 1); S.sel = null; S.multi = []; afterChange();
    if (els.length > 1) toast(`요소 ${els.length}개 삭제 (Ctrl+Z 로 되돌리기)`);
  }
  function dupEl(src) {  // src = 붙여넣기(복사한 요소 하나 또는 여러 개), 없으면 지금 선택
    const s = slide(), list = src ? (Array.isArray(src) ? src : [src]) : selEls(); if (!s || !list.length) return;
    snapshot(); const ids = [];
    for (const el of list) {
      const c = clone(el); c.id = newElId(s); delete c.locked;
      if (isLine(c)) { c.x1 += 16; c.x2 += 16; c.y1 += 16; c.y2 += 16; Object.assign(c, Render.lineBox(c)); } else { c.x += 16; c.y += 16; }
      s.elements.push(c); ids.push(c.id);
    }
    S.sel = ids[0]; S.multi = ids.slice(1); S.multiSlide = s.id; afterChange();
  }
  function addEl(kind) {
    const s = slide(); if (!s) return;
    const part = S.deck.part || "day1";
    const base = {
      text: { type: "text", x: 480, y: 320, w: 320, h: 40, text: "새 글자", size: 20, color: "on-surface", lineHeight: 1.4 },
      bullets: { type: "bullets", x: 400, y: 260, w: 480, h: 180, items: ["첫째 항목", { text: "둘째 항목", sub: ["하위 항목"] }, "셋째 항목"], size: 20, subSize: 17, lineHeight: 1.55 },
      pill: { type: "pill", x: 560, y: 340, w: 120, h: 30, text: "칩", size: 14, fill: `${part}-container`, color: `on-${part}-container`, bold: true },
      rect: { type: "rect", x: 480, y: 280, w: 320, h: 160, fill: "surface-container", radius: "r-m" },
      ellipse: { type: "ellipse", x: 600, y: 320, w: 80, h: 80, fill: part, color: "white", text: "", size: 20, bold: true },
      arrow: { type: "arrow", x1: 480, y1: 360, x2: 800, y2: 360, color: "on-surface", width: 2, head: "end" },
      code: { type: "code", x: 64, y: 184, w: 640, h: 0, text: "SELECT d.item_cd\nFROM   trx_demand d\nWHERE  d.tenant_id = :t;", lang: "sql", size: 14, lineHeight: 1.6, radius: "r-m" },
      table: { type: "table", x: 64, y: 184, w: 640, h: 96, rows: [["열 1", "열 2"], ["값", "값"]], colW: [1, 1], size: 16, headFill: `${part}-container`, headColor: `on-${part}-container`, rule: "surface-container-high" },
      image: { type: "image", x: 560, y: 320, w: Math.round(40 * (S.brand.logoRatio || 765 / 237)), h: 40, src: S.brand.logo || "assets/brand/logo.png" },
    }[kind] || (kind.startsWith("shape:") ? shapeBase(kind.slice(6), part) : kind.startsWith("chart:") ? chartBase(kind.slice(6)) : kind.startsWith("icon:") ? { type: "icon", icon: kind.slice(5), x: 600, y: 320, w: 80, h: 80, fill: part } : null);
    if (!base) return;
    snapshot();
    const el = { id: newElId(s), ...base };
    if (isLine(el)) Object.assign(el, Render.lineBox(el));
    if (el.type === "code") el.h = Math.round(24 + Render.codeLines(el).length * el.size * el.lineHeight);
    s.elements.push(el); S.sel = el.id; afterChange();
  }
  // 도형 기본 크기(PowerPoint 처럼 종류마다) - 채우기는 장 색, 글은 비워 둔다(두 번 클릭해 쓴다)
  const SHAPE_SIZE = { rightArrow: [200, 90], leftArrow: [200, 90], upArrow: [90, 200], downArrow: [90, 200], leftRightArrow: [240, 90], chevron: [160, 80], homePlate: [160, 80], callout: [200, 110], roundCallout: [200, 110], can: [120, 150], cube: [140, 140], star5: [140, 140], plus: [120, 120] };
  // 차트 기본 데이터 - 범주 4개 · 계열 2개(원형은 1개)
  const CHART_KINDS = [["column", "▮▮", "세로 막대"], ["stackedColumn", "▮", "누적 세로 막대"], ["bar", "▬", "가로 막대"], ["line", "⟋", "꺾은선"], ["area", "◢", "영역"], ["pie", "◔", "원형"], ["doughnut", "◎", "도넛"]];
  function chartBase(kind) {
    const pie = kind === "pie" || kind === "doughnut";
    return { type: "chart", chart: kind, x: 340, y: 180, w: 600, h: 360, size: 14, categories: ["1분기", "2분기", "3분기", "4분기"],
      series: pie ? [{ name: "비중", values: [35, 25, 25, 15] }] : [{ name: "계열 1", values: [120, 150, 110, 180] }, { name: "계열 2", values: [80, 95, 130, 140] }], labels: pie };
  }
  function chartMenu(btn) { openMenu(btn, [{ h: "차트" }, ...CHART_KINDS.map(([k, i, l]) => ({ icon: i, label: l, act: () => addEl("chart:" + k) }))]); }
  const chartToText = (el) => ["범주 | " + (el.series || []).map((s) => s.name || "").join(" | "), ...(el.categories || []).map((c, i) => [c, ...(el.series || []).map((s) => (s.values || [])[i] == null ? "" : (s.values || [])[i])].join(" | "))].join("\n");
  function textToChart(t, el) {  // 첫 줄 = "범주 | 계열 이름…", 다음 줄들 = "범주 | 값…" (빈 값 = 없음)
    const rows = t.split("\n").map((l) => l.split(CELL_SPLIT).map((x) => x.trim())).filter((r) => r.some(Boolean));
    if (!rows.length) return;
    const head = rows[0], names = head.slice(1);
    el.series = names.map((nm, j) => ({ name: nm || `계열 ${j + 1}`, values: rows.slice(1).map((r) => (r[j + 1] === "" || r[j + 1] == null || isNaN(+r[j + 1]) ? null : +r[j + 1])) }));
    el.categories = rows.slice(1).map((r) => r[0] || "");
  }
  function shapeBase(shape, part) {
    const [w, h] = SHAPE_SIZE[shape] || [160, 120];
    return { type: "shape", shape, x: Math.round(640 - w / 2), y: Math.round(360 - h / 2), w, h, fill: `${part}-container`, color: `on-${part}-container`, text: "", size: 18 };
  }
  // ＋ 추가 → 도형… : 도형 격자(아이콘 = render.js 경로)
  function shapeMenu(btn) {
    const grid = `<div class="shpgrid">${Render.shapeNames().map(([k, ko]) => `<button type="button" class="shp" data-shape="${k}" title="${esc(ko)}"><svg viewBox="-2 -2 52 40" width="40" height="30"><path d="${Render.shapePath(k, 48, 36)}" fill="currentColor"/></svg></button>`).join("")}</div>`;
    openMenu(btn, [{ h: "도형" }, { html: grid, bind: (div) => div.querySelectorAll("[data-shape]").forEach((b) => { b.onclick = () => { closeMenu(); addEl("shape:" + b.dataset.shape); }; }) }]);
  }
  // ＋ 추가 → 다이어그램… : 요소 묶음을 넣는다(SmartArt 대신 - 넣은 뒤 요소마다 자유롭게 고친다)
  const DIAGRAMS = [["process", "⮞⮞⮞", "프로세스 (갈매기)"], ["flow", "▭→▭", "흐름 (상자·화살표)"], ["cycle", "↻", "순환"], ["hierarchy", "⏢", "계층 (조직도)"], ["columns", "▥", "열 목록"], ["venn", "◎", "벤 다이어그램"], ["timeline", "⋯", "타임라인"], ["matrix", "▦", "매트릭스 2×2"], ["pyramid", "▲", "피라미드"]];
  function diagramMenu(btn) { openMenu(btn, [{ h: "다이어그램" }, ...DIAGRAMS.map(([k, i, l]) => ({ icon: i, label: l, act: () => addDiagram(k) }))]); }
  function addDiagram(kind) {
    const s = slide(); if (!s) return;
    const part = S.deck.part || "day1", P1 = part, P2 = `${part}-container`, C1 = "white", C2 = `on-${part}-container`;
    const out = [], R = (o) => out.push(o);
    const box = (x, y, w, h, text, strong) => R({ type: "rect", x, y, w, h, text, size: 18, bold: !!strong, fill: strong ? P1 : P2, color: strong ? C1 : C2, radius: "r-m", align: "center" });
    const arrow = (x1, y1, x2, y2) => R({ type: "arrow", x1, y1, x2, y2, color: "on-surface-variant", width: 2, head: "end" });
    const line = (x1, y1, x2, y2) => R({ type: "line", x1, y1, x2, y2, color: "on-surface-variant", width: 2 });
    const label = (x, y, w, h, text, size = 16) => R({ type: "text", x, y, w, h, text, size, color: "on-surface", align: "center", lineHeight: 1.3 });
    if (kind === "process") [1, 2, 3, 4].forEach((n, i) => R({ type: "shape", shape: i ? "chevron" : "homePlate", x: 160 + i * 240, y: 300, w: 250, h: 100, text: `${n}단계`, size: 18, fill: i % 2 ? P2 : P1, color: i % 2 ? C2 : C1 }));
    else if (kind === "flow") [1, 2, 3, 4].forEach((n, i) => { box(160 + i * 250, 300, 190, 90, `${n}단계`, i === 0); if (i < 3) arrow(350 + i * 250, 345, 410 + i * 250, 345); });
    else if (kind === "cycle") {
      box(540, 160, 200, 80, "계획", true); box(820, 320, 200, 80, "실행"); box(540, 480, 200, 80, "점검"); box(260, 320, 200, 80, "개선");
      arrow(740, 200, 900, 320); arrow(920, 400, 760, 520); arrow(540, 520, 380, 400); arrow(360, 320, 520, 200);
    } else if (kind === "hierarchy") {
      box(540, 170, 200, 70, "최고 책임자", true);
      [0, 1, 2].forEach((i) => { box(260 + i * 280, 330, 200, 70, `부서 ${i + 1}`); line(360 + i * 280, 290, 360 + i * 280, 330); [0, 1].forEach((j) => { box(260 + i * 280, 440 + j * 80, 200, 60, `팀 ${i + 1}-${j + 1}`); }); line(300 + i * 280, 400, 300 + i * 280, 470); });
      line(640, 240, 640, 290); line(360, 290, 920, 290);
    } else if (kind === "columns") [0, 1, 2].forEach((i) => { box(170 + i * 330, 190, 300, 56, `항목 ${i + 1}`, true); R({ type: "rect", x: 170 + i * 330, y: 246, w: 300, h: 300, fill: "surface-container", radius: "r-m" }); R({ type: "bullets", x: 186 + i * 330, y: 262, w: 268, h: 270, items: ["요점 하나", "요점 둘", "요점 셋"], size: 17, subSize: 15 }); });
    else if (kind === "venn") { R({ type: "ellipse", x: 340, y: 200, w: 340, h: 340, fill: { color: P1, alpha: 0.55 }, text: "A", color: C1, size: 24, bold: true, pad: [0, 170, 0, 0] }); R({ type: "ellipse", x: 600, y: 200, w: 340, h: 340, fill: { color: `${part}-fixed-dim`, alpha: 0.55 }, text: "B", color: C1, size: 24, bold: true, pad: [0, 0, 0, 170] }); label(560, 340, 160, 60, "공통", 20); }
    else if (kind === "timeline") { line(160, 380, 1120, 380); [0, 1, 2, 3].forEach((i) => { const x = 240 + i * 270; R({ type: "ellipse", x: x - 12, y: 368, w: 24, h: 24, fill: P1 }); R({ type: "pill", x: x - 50, y: 320, w: 100, h: 30, text: `${2024 + i}년`, size: 14, fill: P2, color: C2, bold: true }); label(x - 110, 410, 220, 70, `단계 ${i + 1}\n설명`); }); }
    else if (kind === "matrix") { [["높음·높음", 0, 0, true], ["높음·낮음", 1, 0], ["낮음·높음", 0, 1], ["낮음·낮음", 1, 1]].forEach(([t, cx, cy, st]) => box(380 + cx * 270, 170 + cy * 200, 260, 190, t, st)); label(140, 170, 230, 390, "세로축 ↑", 16); label(380, 570, 530, 40, "가로축 →", 16); }
    else if (kind === "pyramid") [0, 1, 2].forEach((i) => { const w = 240 + i * 140; box(640 - w / 2, 190 + i * 120, w, 100, `${i + 1}단계`, i === 0); });
    if (!out.length) return;
    snapshot();
    const ids = out.map((o) => { const el = { id: newElId(s), ...o }; if (isLine(el)) Object.assign(el, Render.lineBox(el)); s.elements.push(el); return el.id; });
    setSelection(ids); afterChange();
  }
  // ---- 그림 삽입: 파일 고르기(＋ 추가 → 그림 파일…) · 편집기에서 Ctrl+V(클립보드 그림) · 캔버스에 끌어다 놓기 → /api/image(작업 공간 assets/images/) → image 요소
  const EFFECTS = [["", "없음"], ["softEdge", "부드러운 가장자리"], ["round", "둥근 모서리"], ["circle", "원형"], ["frame", "액자(흰 테두리·그림자)"], ["glow", "빛(글로우)"]];  // render.js effectCss · export_pptx.apply_effect
  const IMG_MAX = [640, 400];  // 처음 넣을 때 최대 크기(비율 유지) - 큰 사진이 슬라이드를 덮지 않게
  function imageSize(dataUrl) { return new Promise((res) => { const im = new Image(); im.onload = () => res([im.naturalWidth || 1, im.naturalHeight || 1]); im.onerror = () => res([320, 200]); im.src = dataUrl; }); }
  async function addImageFiles(files, at) {
    const s = slide(); if (!s) return;
    const list = [...files].filter((f) => f && f.size && /^image\//.test(f.type || ""));
    if (!list.length) { toast("그림 파일(png·jpg·gif·webp·svg)만 넣을 수 있습니다", 4000); return; }
    const ids = []; let k = 0;
    for (const f of list) {
      const dataUrl = await new Promise((res, rej) => { const rd = new FileReader(); rd.onload = () => res(String(rd.result)); rd.onerror = rej; rd.readAsDataURL(f); }).catch(() => null);
      if (!dataUrl) { toast("파일을 읽지 못했습니다"); continue; }
      const [nw, nh] = await imageSize(dataUrl);
      const name = f.name && f.name !== "image.png" ? f.name : `clip-${new Date().toISOString().slice(11, 19).replace(/:/g, "")}.${(f.type.split("/")[1] || "png").replace("jpeg", "jpg").replace("svg+xml", "svg")}`;
      const r = await api("POST", "/api/image", { name, type: f.type, data: dataUrl.split(",")[1] || "" });
      if (!r.ok) { toast("그림을 올리지 못했습니다: " + ((r.data && r.data.error) || r.status), 5000); continue; }
      const sc = Math.min(1, IMG_MAX[0] / nw, IMG_MAX[1] / nh), w = Math.max(8, Math.round(nw * sc)), h = Math.max(8, Math.round(nh * sc));
      const cx = at ? at.x : 640, cy = at ? at.y : 360;
      if (!ids.length) snapshot();
      const el = { id: newElId(s), type: "image", x: Math.round(Math.max(0, Math.min(1280 - w, cx - w / 2 + k * 24))), y: Math.round(Math.max(0, Math.min(720 - h, cy - h / 2 + k * 24))), w, h, src: r.data.src };
      s.elements.push(el); ids.push(el.id); k++;
    }
    if (ids.length) { setSelection(ids); afterChange(); toast(`그림 ${ids.length}개를 넣었습니다 - assets/images/`); }
  }
  function imagePick(replaceEl) {
    const f = $("#imgFile"); if (!f) return;
    f.onchange = async () => {
      const files = [...f.files]; f.value = "";
      if (replaceEl) {  // 속성 [그림 바꾸기…] - 같은 자리에 새 그림(폭 유지, 높이는 비율로)
        const file = files.find((x) => /^image\//.test(x.type || "")); if (!file) return;
        const dataUrl = await new Promise((res) => { const rd = new FileReader(); rd.onload = () => res(String(rd.result)); rd.readAsDataURL(file); });
        const [nw, nh] = await imageSize(dataUrl);
        const r = await api("POST", "/api/image", { name: file.name, type: file.type, data: dataUrl.split(",")[1] || "" });
        if (!r.ok) { toast("그림을 올리지 못했습니다: " + ((r.data && r.data.error) || r.status), 5000); return; }
        snapshot(); replaceEl.src = r.data.src; replaceEl.h = Math.max(8, Math.round(replaceEl.w * nh / nw)); afterChange();
      } else addImageFiles(files, null);
    };
    f.click();
  }
  // ---- 다이어그램(코드, mermaid): 코드 창 → POST /api/mermaid → PNG(assets/images/) → image 요소(mermaid 코드를 같이 둔다 - 속성 [다이어그램 코드 수정…])
  const MERMAID_SAMPLE = "flowchart LR\n  A[요청] --> B{검토}\n  B -->|승인| C[처리]\n  B -->|거절| D[반려]";
  function codeDialog(title, value, hint, onOk) {
    const back = document.createElement("div");
    back.style.cssText = "position:fixed;inset:0;background:rgba(0,0,0,.35);z-index:60;display:flex;align-items:center;justify-content:center";
    back.innerHTML = `<div style="background:#fff;border-radius:14px;padding:16px 18px;width:min(640px,92vw);box-shadow:0 8px 30px rgba(0,0,0,.25);font:14px var(--font)"><h3 style="margin:0 0 8px;font-size:15px">${esc(title)}</h3><div class="hint" style="margin:0 0 6px">${hint}</div><textarea id="dlgCode" style="width:100%;min-height:220px;font:13px Consolas,monospace;border:1px solid var(--line);border-radius:8px;padding:8px">${esc(value)}</textarea><div style="display:flex;justify-content:flex-end;gap:6px;margin-top:10px"><button type="button" class="chip" id="dlgCancel">취소</button><button type="button" class="chip primary" id="dlgOk">그리기</button></div></div>`;
    document.body.appendChild(back);
    const ta = back.querySelector("#dlgCode"); ta.focus();
    const close = () => back.remove();
    back.querySelector("#dlgCancel").onclick = close;
    back.addEventListener("keydown", (e) => { if (e.key === "Escape") close(); if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) back.querySelector("#dlgOk").click(); });
    back.querySelector("#dlgOk").onclick = async () => { const ok = back.querySelector("#dlgOk"); ok.disabled = true; ok.textContent = "그리는 중…"; const done = await onOk(ta.value); if (done) close(); else { ok.disabled = false; ok.textContent = "그리기"; } };
  }
  async function renderMermaid(code, replaceEl) {
    const r = await api("POST", "/api/mermaid", { code, name: "diagram" });
    if (!r.ok) { toast("다이어그램을 그리지 못했습니다: " + ((r.data && r.data.error) || r.status), 8000); return false; }
    const s = slide(); if (!s) return false;
    const nw = r.data.w || 640, nh = r.data.h || 400, sc = Math.min(1, 800 / nw, 500 / nh), w = Math.max(8, Math.round(nw * sc)), h = Math.max(8, Math.round(nh * sc));
    snapshot();
    if (replaceEl) { replaceEl.src = r.data.src; replaceEl.mermaid = code; replaceEl.h = Math.max(8, Math.round(replaceEl.w * nh / nw)); }
    else { const el = { id: newElId(s), type: "image", x: Math.round(640 - w / 2), y: Math.round(360 - h / 2), w, h, src: r.data.src, mermaid: code }; s.elements.push(el); S.sel = el.id; }
    afterChange(); toast("다이어그램을 그렸습니다 - " + r.data.src); return true;
  }
  const mermaidDialog = (el) => codeDialog(el ? "다이어그램 코드 수정 (mermaid)" : "다이어그램 코드 (mermaid)", el ? el.mermaid || "" : MERMAID_SAMPLE,
    "flowchart · sequenceDiagram · classDiagram · stateDiagram · erDiagram · gantt · pie 등 mermaid 문법. 그리면 작업 공간 assets/images/ 에 PNG(+.mmd)로 저장되고 그림 요소가 된다. Ctrl+Enter = 그리기",
    (code) => renderMermaid(code.trim(), el));
  function wireImageDrop() {  // 캔버스에 그림 파일 끌어다 놓기(놓은 자리에) · 편집기 어디서나 Ctrl+V 그림(글 편집·메모·요청 입력 중이 아닐 때)
    const st = $("#stageWrap") || $("#stage"); if (!st) return;
    st.addEventListener("dragover", (e) => { if ([...e.dataTransfer.types].includes("Files")) { e.preventDefault(); st.classList.add("dropping"); } });
    st.addEventListener("dragleave", () => st.classList.remove("dropping"));
    st.addEventListener("drop", (e) => { st.classList.remove("dropping"); if (!e.dataTransfer.files.length) return; e.preventDefault(); e.stopPropagation(); addImageFiles(e.dataTransfer.files, toSlide(e)); });
    document.addEventListener("paste", (e) => {
      const t = e.target, tag = (t && t.tagName) || "";
      if (tag === "INPUT" || tag === "TEXTAREA" || (t && t.isContentEditable) || (t && t.closest && t.closest("#memo, #tab-reqs, .popover, .modal-back"))) return;  // 글 입력·메모·요청 양식은 제 처리기가 맡는다
      const files = []; for (const it of (e.clipboardData && e.clipboardData.items) || []) if (it.kind === "file") { const f = it.getAsFile(); if (f && /^image\//.test(f.type || "")) files.push(f); }
      if (!files.length) return;
      e.preventDefault(); addImageFiles(files, null);
    });
  }
  // ---- 삽입 패널: 한 단에 검색 + 묶음별 타일(하위 메뉴 없음). 글자를 치면 바로 걸러지고 Enter 는 첫 타일. Canva·Figma 의 '요소' 패널 꼴
  function insertItems() {
    const base = [["text", "T", "글자", "텍스트 text"], ["bullets", "≡", "글머리 목록", "bullets list 번호"], ["pill", "◖◗", "칩", "pill badge 태그"], ["rect", "▭", "상자", "사각형 rect box"], ["ellipse", "◯", "원", "타원 circle"], ["arrow", "→", "화살표", "선 line connector"]];
    const data = [["table", "▦", "표", "table 격자"], ["code", "{ }", "코드", "code sql"]].concat(CHART_KINDS.map(([k, i, l]) => [`chart:${k}`, i, l, `차트 chart ${k}`]));
    const icons = Render.iconNames().map(([k, ko]) => [`icon:${k}`, `<svg viewBox="0 0 24 24" width="22" height="22"><g>${(Render.ICONS ? Render.ICONS[k] : null) ? "" : ""}</g>${iconSvgInner(k)}</svg>`, ko, `아이콘 icon ${k}`]);
    const media = [["imgfile", "🖼", "그림 파일…", "image photo 사진 업로드"], ["image", "🏷", "로고", "brand logo"], ["mermaid", "⤳", "다이어그램 코드…", "mermaid flowchart sequence 코드"]];
    const shapes = Render.shapeNames().map(([k, ko]) => [`shape:${k}`, `<svg viewBox="-2 -2 52 40" width="34" height="26"><path d="${Render.shapePath(k, 48, 36)}" fill="currentColor"/></svg>`, ko, `도형 shape ${k}`]);
    const diagrams = DIAGRAMS.map(([k, i, l]) => [`diagram:${k}`, i, l, `다이어그램 diagram smartart ${k}`]);
    return [["기본", base], ["데이터", data], ["미디어", media], ["도형", shapes], ["아이콘", icons], ["다이어그램", diagrams]];
  }
  function iconSvgInner(k) { const el = { type: "icon", icon: k, w: 24, h: 24, fill: "primary", color: "white" }; const m = Render.renderElement(el, 1).match(/<g[^>]*>([\s\S]*?)<\/g>/); return m ? `<g>${m[1]}</g>` : ""; }
  function runInsert(kind) {
    if (kind === "imgfile") return imagePick(null);
    if (kind === "mermaid") return mermaidDialog(null);
    if (kind.startsWith("diagram:")) return addDiagram(kind.slice(8));
    return addEl(kind);
  }
  function addMenu(btn) {
    const groups = insertItems();
    const html = `<div class="inspanel"><input type="search" class="insq" placeholder="무엇을 넣을까요? 예: 차트, 별, 화살표  (Enter = 첫 항목)" autocomplete="off">
      ${groups.map(([g, items]) => `<div class="insg" data-g="${esc(g)}"><div class="h">${esc(g)}</div><div class="instiles">${items.map(([k, i, l, kw]) => `<button type="button" class="tile" data-ins="${esc(k)}" data-kw="${esc((l + " " + (kw || "")).toLowerCase())}" title="${esc(l)}"><span class="ic">${i}</span><span class="lb">${esc(l)}</span></button>`).join("")}</div></div>`).join("")}
      <div class="hint" style="padding:4px 8px 2px">명령 팔레트 <kbd>Ctrl</kbd>+<kbd>K</kbd> 에서도 넣을 수 있습니다</div></div>`;
    openMenu(btn, [{ html, bind: (div) => {
      const q = div.querySelector(".insq"); setTimeout(() => q.focus(), 0);
      const filter = () => { const t = q.value.trim().toLowerCase(); div.querySelectorAll(".tile").forEach((b) => { b.style.display = !t || b.dataset.kw.includes(t) ? "" : "none"; }); div.querySelectorAll(".insg").forEach((g) => { g.style.display = [...g.querySelectorAll(".tile")].some((b) => b.style.display !== "none") ? "" : "none"; }); };
      q.addEventListener("input", filter);
      q.addEventListener("keydown", (e) => { if (e.key === "Enter") { const first = [...div.querySelectorAll(".tile")].find((b) => b.style.display !== "none"); if (first) { closeMenu(); runInsert(first.dataset.ins); } e.preventDefault(); } if (e.key === "Escape") closeMenu(); e.stopPropagation(); });
      div.querySelectorAll(".tile").forEach((b) => { b.onclick = () => { closeMenu(); runInsert(b.dataset.ins); }; });
    } }]);
  }
  // ---- 명령 팔레트(Ctrl+K): 넣기 + 동작을 글자로 찾아 Enter. 최근 쓴 것이 위
  function commandList() {
    const el = selEl(), sel = selEls().length;
    const ins = insertItems().flatMap(([g, items]) => items.map(([k, , l, kw]) => ({ id: "ins:" + k, label: `${l}`, group: `넣기 · ${g}`, kw: (l + " " + (kw || "")).toLowerCase(), run: () => runInsert(k) })));
    const btn = (id) => { const b = $("#" + id); if (b) b.click(); else toast("지금은 쓸 수 없습니다"); };
    const cmds = [
      { id: "present", label: "발표 (처음부터)", key: "F5", kw: "발표 present play", run: () => present(false) },
      { id: "presentCur", label: "발표 (지금 슬라이드부터)", key: "Shift+F5", kw: "발표 present", run: () => present(true) },
      { id: "pptx", label: "PPTX 내보내기", kw: "export pptx 파워포인트", run: () => doExport() },
      { id: "pdf", label: "PDF 내보내기", kw: "export pdf 인쇄", run: () => doExportPdf() },
      { id: "check", label: "레이아웃 검사", kw: "check 검사 겹침 넘침", run: () => btn("chkBtn") },
      { id: "aifix", label: "레이아웃 고치기 (세션에 요청)", kw: "fix ai 세션 고치기", run: () => btn("aiFixBtn") },
      { id: "polish", label: "다듬기 (세션에 요청)", kw: "polish 다듬기 ai", run: () => btn("aiPolishBtn") },
      { id: "dupSlide", label: "슬라이드 복제", kw: "slide duplicate 복제", run: () => dupSlide(S.cur) },
      { id: "delSlide", label: "슬라이드 삭제", kw: "slide delete 삭제", run: () => delSlide(S.cur) },
      { id: "group", label: "묶기", key: "Ctrl+G", kw: "group 묶음", disabled: sel < 2, run: () => groupSel() },
      { id: "ungroup", label: "묶음 풀기", key: "Ctrl+Shift+G", kw: "ungroup", disabled: !el || el.type !== "group", run: () => ungroupSel() },
      { id: "dup", label: "요소 복제", key: "Ctrl+D", kw: "duplicate", disabled: !el, run: () => dupEl() },
      { id: "del", label: "요소 삭제", key: "Delete", kw: "delete remove", disabled: !el, run: () => delEl() },
      { id: "front", label: "맨 앞으로", kw: "z order front", disabled: !el, run: () => zorder("front") },
      { id: "back", label: "맨 뒤로", kw: "z order back", disabled: !el, run: () => zorder("back") },
      { id: "maxi", label: "최대화 배치 켜기/끄기", key: "Ctrl+Shift+M", kw: "maximize layout 배치", run: () => setMaxi(!document.body.classList.contains("maxi")) },
      { id: "right", label: "오른쪽 패널 보이기/숨기기", key: "Ctrl+\\", kw: "panel 패널", run: () => toggleRight() },
      { id: "zoomFit", label: "화면 맞춤", key: "Ctrl+0", kw: "zoom fit 확대", run: () => setZoom(null) },
      { id: "help", label: "단축키 도움말", key: "?", kw: "help shortcuts 단축키", run: () => showHelp() },
    ].map((c) => ({ ...c, group: "동작" }));
    const recent = (LS.get("cmd-recent", "") || "").split(",").filter(Boolean);
    const all = [...cmds, ...ins];
    return all.sort((a, b) => (recent.indexOf(b.id) >= 0 ? recent.length - recent.indexOf(b.id) : 0) - (recent.indexOf(a.id) >= 0 ? recent.length - recent.indexOf(a.id) : 0));
  }
  function commandPalette() {
    closeMenu();
    const back = document.createElement("div"); back.id = "cmdpal";
    back.innerHTML = `<div class="box"><input type="search" placeholder="무엇을 할까요? 넣기·발표·내보내기·검사… (↑↓ 고르고 Enter)" autocomplete="off"><div class="list"></div></div>`;
    document.body.appendChild(back);
    const q = back.querySelector("input"), list = back.querySelector(".list"); let items = commandList(), cur = 0;
    const render = () => {
      const t = q.value.trim().toLowerCase(), show = items.filter((c) => !t || c.label.toLowerCase().includes(t) || c.kw.includes(t)).slice(0, 40);
      cur = Math.max(0, Math.min(cur, show.length - 1));
      list.innerHTML = show.length ? show.map((c, i) => `<div class="it${i === cur ? " on" : ""}${c.disabled ? " dis" : ""}" data-i="${i}"><span class="g">${esc(c.group)}</span><span class="l">${esc(c.label)}</span>${c.key ? `<span class="k">${esc(c.key)}</span>` : ""}</div>`).join("") : `<div class="empty">찾는 것이 없습니다</div>`;
      list.dataset.n = show.length; list._show = show;
    };
    const close = () => back.remove();
    const run = (c) => { if (!c || c.disabled) return; close(); LS.set("cmd-recent", [c.id, ...(LS.get("cmd-recent", "") || "").split(",").filter((x) => x && x !== c.id)].slice(0, 8).join(",")); c.run(); };
    q.addEventListener("input", () => { cur = 0; render(); });
    q.addEventListener("keydown", (e) => {
      if (e.key === "ArrowDown") { cur = Math.min(+list.dataset.n - 1, cur + 1); render(); e.preventDefault(); }
      else if (e.key === "ArrowUp") { cur = Math.max(0, cur - 1); render(); e.preventDefault(); }
      else if (e.key === "Enter") { run(list._show[cur]); e.preventDefault(); }
      else if (e.key === "Escape") close();
      e.stopPropagation();
    });
    list.addEventListener("click", (e) => { const it = e.target.closest(".it"); if (it) run(list._show[+it.dataset.i]); });
    back.addEventListener("mousedown", (e) => { if (e.target === back) close(); });
    render(); q.focus();
  }
  function goSlide(i) { if (!S.deck) return; S.cur = Math.max(0, Math.min(S.deck.slides.length - 1, i)); S.sel = null; S.chkBox = S.chkBox && S.chkBox.slide === slide().id ? S.chkBox : null; closeMemo(); renderAll(); ensureThumbVisible(S.cur); }
  function dupSlide(i) { snapshot(); const c = clone(S.deck.slides[i]); c.id = newSlideId(); S.deck.slides.splice(i + 1, 0, c); S.cur = i + 1; S.sel = null; afterChange(true); }
  function delSlide(i) {
    if (S.deck.slides.length <= 1) return toast("마지막 슬라이드는 지울 수 없습니다");
    if (!confirm(`슬라이드 ${i + 1}을(를) 지울까요? (Ctrl+Z 로 되돌리기 가능)`)) return;
    snapshot(); S.deck.slides.splice(i, 1); S.sel = null; afterChange(true);
  }
  // ---------------------------------------------------------------- 슬라이드 추가 창 - 목적별 유형(studio/slide_types.json) 또는 레이아웃
  const AD = { tab: "type", group: "", data: null, layouts: null, mode: "add" };
  async function openAddDlg(mode) {
    AD.mode = mode === "replace" ? "replace" : mode === "end" ? "end" : "add";  // end = 맨 아래(왼쪽 레일 "+ 새 슬라이드"), add = 지금 슬라이드 다음(오른쪽 단추 메뉴)
    $("#adTitle").textContent = AD.mode === "replace" ? `유형 바꾸기 - 슬라이드 ${S.cur + 1}` : "슬라이드 추가";
    $("#adHint").textContent = AD.mode === "replace" ? "누르면 지금 슬라이드를 그 유형으로 바꿉니다 - 제목·발표자 노트·슬라이드 id(요청 메모)는 그대로 옮깁니다(Ctrl+Z 로 되돌리기)."
      : (AD.mode === "end" ? "누르면 맨 아래(마지막 슬라이드 다음)에 들어갑니다(Ctrl+Z 로 되돌리기). 특정 슬라이드 다음에 넣으려면 그 썸네일 오른쪽 단추 → 아래에 새 슬라이드." : "누르면 지금 슬라이드 다음에 들어갑니다(Ctrl+Z 로 되돌리기).") + " 유형 = 이 장이 하는 일(목적·구성) - 예시 내용이 채워져 있으니 고쳐 쓰세요.";
    $("#addDlg").classList.add("show"); $("#adQ").value = "";
    if (!AD.data) {
      $("#adBody").innerHTML = `<div class="hint">유형을 불러오는 중…</div>`;
      const r = await api("GET", `/api/slidetypes?part=${encodeURIComponent(S.deck.part || "day1")}&lang=${encodeURIComponent(window.I18N ? I18N.effective() : "ko")}`);  // 예시 글 언어
      AD.data = r.ok ? r.data : { groups: [], types: [] };
    }
    renderAddDlg(); setTimeout(() => $("#adQ").focus(), 30);
  }
  function closeAddDlg() { $("#addDlg").classList.remove("show"); }
  function fitAdd() { $$("#adBody .ad-vp").forEach((v) => { if (v.firstElementChild) v.firstElementChild.style.transform = `scale(${v.clientWidth / SW})`; }); }
  async function renderAddDlg() {
    $$("#adTab button").forEach((b) => b.classList.toggle("on", b.dataset.adtab === AD.tab));
    const q = $("#adQ").value.trim().toLowerCase();
    if (AD.tab === "layout") {
      if (!AD.layouts) { const r = await api("GET", "/api/layouts"); AD.layouts = r.ok ? r.data : []; }
      $("#adGroups").innerHTML = "";
      const ls = AD.layouts.filter((l) => !q || `${l.label} ${l.name}`.toLowerCase().includes(q));
      $("#adBody").innerHTML = `<div class="ad-grid">${ls.map((l) => `<button class="ad-card" data-adlayout="${esc(l.name)}"><b>${esc(l.label)}</b><span class="lay">${esc(l.name)}</span></button>`).join("")}</div>`;
      return;
    }
    const d = AD.data;
    $("#adGroups").innerHTML = [["", "전체"], ...d.groups.map((g) => [g.id, I18N.pick(g, "label")])].map(([id, l]) =>
      `<button data-adgroup="${id}" class="${AD.group === id ? "on" : ""}">${esc(l)} <small>${id ? d.types.filter((t) => t.group === id).length : d.types.length}</small></button>`).join("");
    const show = d.types.filter((t) => t.slide && (!AD.group || t.group === AD.group) && (!q || `${t.label} ${t.purpose} ${t.layout} ${t.layoutLabel}`.toLowerCase().includes(q)));
    const blankCard = !q || "빈 슬라이드 blank".includes(q) ? `<div class="ad-gt">빈 슬라이드<small>템플릿 기본 항목(로고·쪽번호·바닥 경로)만 - 본문은 직접 추가</small></div>
      <div class="ad-grid"><button class="ad-card" data-adlayout="blank" title="로고·쪽번호·바닥 경로만 있는 빈 장"><div class="ad-vp">${AD.blank ? Render.renderSlide(AD.blank, 1) : ""}</div><b>빈 슬라이드</b><small>로고 · 쪽번호만</small><span class="lay">blank</span></button></div>` : "";
    if (!AD.blank) api("POST", "/api/newslide", { layout: "blank", part: S.deck.part || "day1", id: "blank" }).then((r) => { if (r.ok) { AD.blank = r.data; renderAddDlg(); } });
    $("#adBody").innerHTML = blankCard + d.groups.filter((g) => show.some((t) => t.group === g.id)).map((g) => `<div class="ad-gt">${esc(I18N.pick(g, "label"))}<small>${esc(I18N.pick(g, "desc"))}</small></div>
      <div class="ad-grid">${show.filter((t) => t.group === g.id).map((t) => `<button class="ad-card" data-adtype="${esc(t.id)}" title="${esc(I18N.pick(t, "purpose"))}${t.image ? `\n이미지: ${esc(t.image)}` : ""}">
        <div class="ad-vp">${Render.renderSlide(t.slide, 1)}</div><b>${esc(I18N.pick(t, "label"))}</b><small>${esc(I18N.pick(t, "purpose"))}</small><span class="lay">${esc(t.layout)}${t.image ? " · 사진 자리" : ""}</span></button>`).join("")}</div>`).join("")
      || `<div class="hint">찾는 유형이 없습니다.</div>`;
    requestAnimationFrame(fitAdd);
  }
  const titleEl = (sl) => (sl.elements || []).find((e) => e.role === "title" && e.text != null);
  function insertSlide(s) {
    if (AD.mode === "replace") {  // 유형 바꾸기 - 제목·노트·id 를 옮긴다
      const old = slide(), ot = titleEl(old), nt = titleEl(s);
      if (ot && nt) nt.text = ot.text;
      if (old.notes) s.notes = old.notes;
      s.id = old.id;
      snapshot(); S.deck.slides[S.cur] = s; S.sel = null; afterChange(true); closeAddDlg();
      toast("유형을 바꿨습니다 - 제목·노트는 옮겼고 본문은 예시 내용입니다 (Ctrl+Z 로 되돌리기)", 4000);
      return;
    }
    const at = AD.mode === "end" ? S.deck.slides.length : S.cur + 1;
    snapshot(); S.deck.slides.splice(at, 0, s); S.cur = at; S.sel = null; afterChange(true); closeAddDlg();
    toast("슬라이드를 추가했습니다 - 예시 내용을 고쳐 쓰세요 (Ctrl+Z 로 되돌리기)");
  }
  async function onAddDlg(e) {
    if (e.target === $("#addDlg") || e.target.closest("[data-adclose]")) return closeAddDlg();
    const tb = e.target.closest("[data-adtab]"); if (tb) { AD.tab = tb.dataset.adtab; return renderAddDlg(); }
    const g = e.target.closest("[data-adgroup]"); if (g) { AD.group = g.dataset.adgroup; return renderAddDlg(); }
    const t = e.target.closest("[data-adtype]");
    if (t) { const ty = AD.data.types.find((x) => x.id === t.dataset.adtype); const s = clone(ty.slide); s.id = newSlideId(); return insertSlide(s); }
    const l = e.target.closest("[data-adlayout]");
    if (l) {
      const res = await api("POST", "/api/newslide", { layout: l.dataset.adlayout, part: S.deck.part || "day1", id: newSlideId() });
      if (!res.ok) return toast("새 슬라이드 실패");
      insertSlide(res.data);
    }
  }
  async function layoutMenu(btn) {
    if (!S.layouts.length) { const r = await api("GET", "/api/layouts"); S.layouts = r.ok ? r.data : []; }
    openMenu(btn, S.layouts.map((l) => ({ label: `${l.label}`, key: l.name, act: async () => {
      const res = await api("POST", "/api/newslide", { layout: l.name, part: S.deck.part || "day1", id: newSlideId() });
      if (!res.ok) return toast("새 슬라이드 실패");
      snapshot(); S.deck.slides.splice(S.cur + 1, 0, res.data); S.cur += 1; S.sel = null; afterChange(true);
    } })));
  }
  function thumbMenu(e, i) {
    e.preventDefault(); goSlide(i);
    openMenu({ x: e.clientX, y: e.clientY }, [
      { label: "슬라이드 복제", act: () => dupSlide(i) }, { label: "아래에 새 슬라이드…", act: () => openAddDlg() }, { label: "유형 바꾸기…", act: () => openAddDlg("replace") },
      { label: "삭제", act: () => delSlide(i) }, "-", { label: "이 슬라이드에 요청 메모", act: () => openMemo({ element: null }) },
      { label: "여기서부터 발표", key: "Shift+F5", act: () => present(true) },
    ]);
  }
  // 썸네일 끌어서 순서 바꾸기
  let dragFrom = -1;
  function onThumbDragStart(e) { const t = e.target.closest(".thumb"); if (!t) return; dragFrom = +t.dataset.i; e.dataTransfer.effectAllowed = "move"; e.dataTransfer.setData("text/plain", String(dragFrom)); }
  function onThumbDragOver(e) {
    const t = e.target.closest(".thumb"); if (!t || dragFrom < 0) return; e.preventDefault();
    $$(".thumb").forEach((x) => x.classList.remove("drop-before", "drop-after"));
    const r = t.getBoundingClientRect(); t.classList.add(e.clientY < r.top + r.height / 2 ? "drop-before" : "drop-after");
  }
  function onThumbDrop(e) {
    const t = e.target.closest(".thumb"); if (!t || dragFrom < 0) return; e.preventDefault();
    const r = t.getBoundingClientRect(); let to = +t.dataset.i + (e.clientY < r.top + r.height / 2 ? 0 : 1);
    const from = dragFrom; dragFrom = -1;
    $$(".thumb").forEach((x) => x.classList.remove("drop-before", "drop-after"));
    if (to === from || to === from + 1) return;
    snapshot(); const [s] = S.deck.slides.splice(from, 1); if (to > from) to--; S.deck.slides.splice(to, 0, s); S.cur = to; afterChange(true);
  }

  // ---------------------------------------------------------------- 탭·키보드·도움말
  function switchTab(t) {
    S.tab = t; document.body.classList.remove("noright");
    $$(".tabs .chip").forEach((b) => b.classList.toggle("on", b.dataset.tab === t)); $$(".panel").forEach((p) => p.classList.toggle("on", p.id === "tab-" + t));
    if (t === "hist") loadHist();
    if (t === "chg") loadChanges();
    setTimeout(() => { fitStage(); fitThumbs(); }, 0);
  }
  // 최대화 배치 - 노트·개요·검사 탭과 패널을 오른쪽 패널 아래로 옮기고(가운데는 슬라이드만), 복원하면 제자리로
  function setMaxi(on) {
    const b = $("#bottom"), t = $("#bTabs"), foot = $("#foot"), dock = $("#rDock");
    if (on) { document.body.classList.remove("noright"); dock.append(t, b); }
    else { foot.insertBefore(t, foot.firstChild); foot.parentNode.insertBefore(b, foot); }
    document.body.classList.toggle("maxi", on); LS.set("maxi", on ? "1" : "0");
    if (S.zoom) S.zoom = null;
    setTimeout(() => { fitStage(); fitThumbs(); }, 0);
  }
  function toggleRight() { const n = !document.body.classList.contains("noright"); if (n && document.body.classList.contains("maxi")) setMaxi(false); /* 오른쪽을 숨기면 노트가 갈 곳이 없으니 먼저 복원 */ document.body.classList.toggle("noright", n); LS.set("noright", n ? "1" : "0"); setTimeout(() => { fitStage(); fitThumbs(); }, 0); }
  const HELP = [
    ["명령 팔레트", "<kbd>Ctrl</kbd>+<kbd>K</kbd> 또는 <kbd>/</kbd> - 넣기·발표·내보내기·검사를 글자로 찾아 <kbd>Enter</kbd>"],
    ["넣기", "＋ 추가 패널에서 글자를 치면 바로 걸러짐 · <kbd>Enter</kbd> = 첫 항목"],
    ["묶음", "<kbd>Ctrl</kbd>+<kbd>G</kbd> 묶기 · <kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>G</kbd> 풀기"],
    ["스마트 가이드", "끌 때 다른 요소의 가장자리·가운데, 슬라이드 가운데에 붙는다(빨간 안내선) · <kbd>Shift</kbd> = 자유"],
    ["모드", "<kbd>E</kbd> 편집 · <kbd>M</kbd> 선택(요청 메모) · <kbd>D</kbd> 그리기(영역 메모)"],
    ["여러 요소", "<kbd>Shift</kbd>/<kbd>Ctrl</kbd>+클릭 더하기·빼기 · 빈 곳을 끌어 범위 선택 · <kbd>Ctrl</kbd>+<kbd>A</kbd> 이 장 전체 · 끌기·방향키로 함께 이동 · 서식 줄·속성은 공통 적용 · ✥ = 맞춤·분배·같은 크기"],
    ["최대화 배치", "아래 ⛶ 최대화 = 노트·개요·검사를 오른쪽 아래로 옮겨 슬라이드를 크게 · 🗗 복원 · <kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>M</kbd>"],
    ["패널 크기", "왼쪽·아래·오른쪽 경계를 끌어 조절 · 두 번 클릭 = 처음 크기 · 슬라이드는 새 영역에 자동 맞춤"],
    ["슬라이드 이동", "<kbd>PageUp</kbd> <kbd>PageDown</kbd> · 선택이 없을 때 방향키 · <kbd>Home</kbd> <kbd>End</kbd>"],
    ["확대", "<kbd>Ctrl</kbd>+휠 · <kbd>Ctrl</kbd>+<kbd>=</kbd>/<kbd>-</kbd> · <kbd>Ctrl</kbd>+<kbd>0</kbd> 화면 맞춤 · <kbd>Ctrl</kbd>+<kbd>1</kbd> 100%"],
    ["화면 이동", "<kbd>Space</kbd>+끌기 · 가운데 버튼 끌기 · 휠"],
    ["요소", "끌기 = 이동(8px 격자, <kbd>Shift</kbd> = 자유) · 방향키 1px / <kbd>Shift</kbd> 8px · <kbd>Enter</kbd>/두 번 클릭 = 글자 편집 · <kbd>Delete</kbd> 삭제"],
    ["편집", "<kbd>Ctrl</kbd>+<kbd>Z</kbd>/<kbd>Y</kbd> · <kbd>Ctrl</kbd>+<kbd>C</kbd>/<kbd>X</kbd>/<kbd>V</kbd>/<kbd>D</kbd> · <kbd>Ctrl</kbd>+<kbd>B</kbd> 굵게 · <kbd>Ctrl</kbd>+<kbd>S</kbd> 즉시 저장"],
    ["순서", "<kbd>Ctrl</kbd>+<kbd>]</kbd> 앞으로 · <kbd>Ctrl</kbd>+<kbd>[</kbd> 뒤로 · <kbd>Alt</kbd>+<kbd>Ctrl</kbd>+<kbd>]</kbd>/<kbd>[</kbd> 맨 앞/맨 뒤"],
    ["발표", "<kbd>F5</kbd> 처음부터 · <kbd>Shift</kbd>+<kbd>F5</kbd> 현재부터 · 발표 중 <kbd>N</kbd> 노트·시간 · <kbd>Esc</kbd> 끝"],
    ["패널", "<kbd>Ctrl</kbd>+<kbd>\\</kbd> 오른쪽 패널 · <kbd>Esc</kbd> 선택·메모 닫기 · <kbd>?</kbd> 이 도움말"],
  ];
  function showHelp() { $("#help .box").innerHTML = `<h3 style="margin:0 0 10px">단축키</h3><table>${HELP.map(([a, b]) => `<tr><td><b>${a}</b></td><td>${b}</td></tr>`).join("")}</table><div class="hint" style="margin-top:10px">아무 곳이나 누르거나 Esc 로 닫기</div>`; $("#help").classList.add("show"); }
  let spaceDown = false;
  function onKey(e) {
    if ($("#present").classList.contains("show")) { presentKey(e); return; }
    if ($("#addDlg").classList.contains("show")) { if (e.key === "Escape") closeAddDlg(); return; }
    if ($("#help").classList.contains("show")) { if (e.key === "Escape" || e.key === "?") $("#help").classList.remove("show"); return; }
    const inField = /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement.tagName) || S.editing;
    const k = e.key, kl = k.toLowerCase(), ctrl = e.ctrlKey || e.metaKey;
    if (ctrl && kl === "k") { e.preventDefault(); commandPalette(); return; }
    if (ctrl && kl === "s") { e.preventDefault(); save(); return; }
    if (k === "F5") { e.preventDefault(); present(e.shiftKey); return; }
    if (ctrl && k === "\\") { e.preventDefault(); toggleRight(); return; }
    if (ctrl && e.shiftKey && kl === "m") { e.preventDefault(); setMaxi(!document.body.classList.contains("maxi")); return; }
    if (ctrl && (k === "=" || k === "+")) { e.preventDefault(); setZoom(scale * 100 * 1.15); return; }
    if (ctrl && k === "-") { e.preventDefault(); setZoom(scale * 100 / 1.15); return; }
    if (ctrl && k === "0") { e.preventDefault(); setZoom(null); return; }
    if (ctrl && k === "1") { e.preventDefault(); setZoom(100); return; }
    if (inField) return;
    if (k === "Escape") { if (S.memo) { closeMemo(); return; } closeMenu(); select(null); return; }
    if (k === " " && !e.repeat) { spaceDown = true; document.body.classList.add("panning"); e.preventDefault(); return; }
    if (k === "?") { showHelp(); return; }
    if (k === "/" && !ctrl) { e.preventDefault(); commandPalette(); return; }
    if (!ctrl && !e.altKey) { if (kl === "e") return setMode("edit"); if (kl === "m") return setMode("pick"); if (kl === "d") return setMode("draw"); }
    if (ctrl && kl === "z" && !e.shiftKey) { e.preventDefault(); undo(); return; }
    if (ctrl && (kl === "y" || (kl === "z" && e.shiftKey))) { e.preventDefault(); redo(); return; }
    if (ctrl && kl === "a" && S.mode === "edit" && slide()) { e.preventDefault(); setSelection(slide().elements.filter((x) => !x.locked).map((x) => x.id)); return; }
    if (ctrl && kl === "d") { e.preventDefault(); dupEl(); return; }
    if (ctrl && kl === "g") { e.preventDefault(); if (e.shiftKey) ungroupSel(); else groupSel(); return; }
    if (ctrl && kl === "c" && selEl()) { S.clip = selEls().map(clone); toast(`요소 ${S.clip.length}개 복사`); return; }
    if (ctrl && kl === "x" && selEl() && selEls().some((x) => !x.locked)) { S.clip = selEls().filter((x) => !x.locked).map(clone); delEl(); return; }
    if (ctrl && kl === "v" && S.clip) { e.preventDefault(); dupEl(S.clip); return; }
    if (ctrl && kl === "b" && selEl() && TEXTY.has(selEl().type)) { e.preventDefault(); mutate((x) => { const cur = x.bold === undefined ? x.type === "pill" : !!x.bold; x.bold = !cur; }); return; }
    if (ctrl && (k === "]" || k === "[")) { e.preventDefault(); zorder(e.altKey ? (k === "]" ? "front" : "back") : (k === "]" ? "fwd" : "bwd")); return; }
    if (k === "PageDown") { goSlide(S.cur + 1); e.preventDefault(); return; }
    if (k === "PageUp") { goSlide(S.cur - 1); e.preventDefault(); return; }
    if (!selEl() && (k === "Home" || k === "End")) { goSlide(k === "Home" ? 0 : S.deck.slides.length - 1); e.preventDefault(); return; }
    const el = selEl();
    if (!el) { if (k === "ArrowDown" || k === "ArrowRight") { goSlide(S.cur + 1); e.preventDefault(); } else if (k === "ArrowUp" || k === "ArrowLeft") { goSlide(S.cur - 1); e.preventDefault(); } return; }
    if (S.mode !== "edit") return;
    if (k === "Delete" || k === "Backspace") { e.preventDefault(); delEl(); return; }
    if ((k === "Enter" || k === "F2") && !isMulti()) { e.preventDefault(); startEdit(el); return; }
    const d = e.shiftKey ? GRID : 1, mv = { ArrowLeft: [-d, 0], ArrowRight: [d, 0], ArrowUp: [0, -d], ArrowDown: [0, d] }[k];
    const movable = selEls().filter((x) => !x.locked);
    if (mv && movable.length) {
      e.preventDefault(); snapshot();
      for (const x of movable) { if (isLine(x)) { x.x1 += mv[0]; x.x2 += mv[0]; x.y1 += mv[1]; x.y2 += mv[1]; Object.assign(x, Render.lineBox(x)); } else { x.x += mv[0]; x.y += mv[1]; } }
      afterChange();
    }
  }

  // ---------------------------------------------------------------- 시작
  async function loadFonts() { const r = await api("GET", "/api/fonts"); S.fonts = r.ok ? r.data : { presets: [], current: "" }; renderFontChip(); }
  async function setFonts(name) {
    const r = await api("POST", "/api/fonts", { preset: name });
    if (!r.ok) { toast("글꼴 세트를 바꾸지 못했습니다"); return; }
    await applyFonts(r.data);
    toast(`글꼴 세트: ${name} - PPTX 는 다음 내보내기부터 적용`, 4000);
  }
  async function applyFonts(info) {  // 글꼴 정보·토큰을 다시 읽어 화면에 적용
    S.fonts = info; renderFontChip();
    S.tokens = await (await fetch("tokens.json", { cache: "no-store" })).json();
    Render.setTokens(S.tokens); $("#rs-css").textContent = Render.css();
    if (document.fonts && document.fonts.ready) await document.fonts.ready;
    if (S.deck) { renderAll(); revealThumb(S.cur); }
    if ($("#fontDlg").classList.contains("show")) showFonts();
  }
  // 작업 공간이 직접 지정한 글꼴 세트(nexa-slide.json fontPresets)를 쓰면 머리줄에 칩으로 알린다 - 누르면 글꼴 창
  function renderFontChip() {
    const f = S.fonts, c = $("#fontChip"); if (!c) return;
    const on = !!(f && f.source === "workspace");
    c.style.display = on ? "" : "none";
    if (on) { c.textContent = `글꼴 · ${(f.fonts.body || {}).latin || f.current} · 작업 공간`; c.title = `작업 공간이 직접 지정한 글꼴 세트 "${f.current}" - 눌러서 확인·수정`; }
  }
  const ROLE = { body: "본문", heading: "제목", mono: "코드" };
  function showFonts() {
    const f = S.fonts || { presets: [], fonts: {}, files: [] }, cur = f.current, ws = f.source === "workspace";
    const def = ws ? f.workspacePresets[cur] : f.fonts;  // 템플릿 세트면 지금 값으로 새 작업 공간 세트를 시작
    const files = f.files || [];
    $("#fontDlg .box").innerHTML = `<div class="row" style="align-items:center;gap:8px"><h3 style="margin:0;flex:1">글꼴 - 지금 세트 <b>${esc(cur || "(템플릿 기본)")}</b>
        <span class="bd ${ws ? "chg" : ""}" style="font-size:12px">${ws ? "작업 공간 지정" : "템플릿 기본"}</span></h3><button class="chip sm" data-fd="close">닫기</button></div>
      <div class="hint">기본 세트(default·modern)는 엔진 템플릿에 있고, 회사 서체 같은 전용 글꼴은 이 작업 공간이 <code>nexa-slide.json</code> 의 <code>fontPresets</code> 와 <code>fonts/</code> 폴더로 관리합니다.
        글꼴은 되도록 무료 글꼴로 - <a href="${BASE}/studio/fonts.html" target="_blank">글꼴 받기·설치 안내 ↗</a> (쓰는 글꼴이 무료·시스템 기본·전용 중 무엇인지 확인)</div>
      <h4>역할별 글꼴</h4><table>${["body", "heading", "mono"].map((k) => { const v = (f.fonts || {})[k] || {}; const ms = v.measure || {};
        return `<tr><td><b>${ROLE[k]}</b> <code>${k}</code></td><td>${esc(v.latin || "-")} / ${esc(v.ea || "-")}<div style="font-family:${esc(v.css || "inherit")};font-size:18px;margin-top:2px">가나다 ABC 123 - 견본 글자</div>
          <div class="hint">측정 ${esc(ms.regular || "-")} · ${esc(ms.bold || "-")}</div></td></tr>`; }).join("")}</table>
      <h4>작업 공간 글꼴 파일 <span class="hint" style="margin:0">${esc(f.fontsDir || "")}</span></h4>
      ${files.length ? `<table>${files.map((x) => `<tr><td><code>${esc(x.file)}</code></td><td>${esc(x.family)} ${esc(x.style)}</td><td>${x.installed ? "설치됨" : `<b style="color:#93000A">미설치</b>`}</td></tr>`).join("")}</table>
        ${files.some((x) => !x.installed) ? `<div class="hint">PowerPoint 에서도 쓰려면 설치: <code>python3 nexa.py install_fonts</code> (편집기는 설치 없이 이 파일을 씁니다)</div>` : ""}`
        : `<div class="hint">fonts/ 에 글꼴 파일이 없습니다. 전용 글꼴은 이 폴더에 .ttf·.otf 로 둡니다.</div>`}
      <h4>${ws ? `작업 공간 세트 <code>${esc(cur)}</code> 수정` : "작업 공간 세트 만들기 (지금 값에서 시작)"}</h4>
      <div class="hint">역할마다 <code>css</code>(화면 글꼴 목록) · <code>latin</code>·<code>ea</code>(PPTX 글꼴 이름 - 영문·한글) · <code>measure</code>(검사용 파일, fonts/ 또는 설치 폴더에서 찾음). 빠진 역할은 기본값.</div>
      <div class="row" style="gap:6px;margin:6px 0"><label class="hint" style="margin:0">세트 이름</label><input id="fdName" value="${esc(ws ? cur : "custom")}" style="width:160px"></div>
      <textarea id="fdJson" spellcheck="false" style="width:100%;min-height:220px;font:12.5px Consolas,monospace">${esc(JSON.stringify(def, null, 2))}</textarea>
      <div class="row" style="gap:6px;justify-content:flex-end;margin-top:6px"><span class="hint" id="fdErr" style="margin:0 auto 0 0;color:#93000A"></span>
        <button class="chip sm primary" data-fd="save">저장하고 이 세트 쓰기</button></div>`;
    $("#fontDlg").classList.add("show");
  }
  async function onFontDlg(e) {
    if (e.target === $("#fontDlg")) { $("#fontDlg").classList.remove("show"); return; }
    const b = e.target.closest("[data-fd]"); if (!b) return;
    if (b.dataset.fd === "close") { $("#fontDlg").classList.remove("show"); return; }
    let pr;
    try { pr = JSON.parse($("#fdJson").value); } catch (err) { $("#fdErr").textContent = "JSON 형식 오류: " + err.message; return; }
    const r = await api("POST", "/api/fonts", { savePreset: $("#fdName").value.trim(), preset: pr, select: true });
    if (!r.ok) { $("#fdErr").textContent = (r.data && r.data.error) || "저장하지 못했습니다"; return; }
    await applyFonts(r.data); toast("작업 공간 글꼴 세트를 저장했습니다 - PPTX 는 다음 내보내기부터", 4000);
  }
  function moreMenu(btn) {
    const f = S.fonts || { presets: [] };
    openMenu(btn, [
      { h: "글꼴 세트 - 템플릿 기본" }, ...f.presets.filter((p) => p.source !== "workspace").map((p) => ({ label: `${p.name} - ${p.label}`, on: p.name === f.current, act: () => setFonts(p.name) })),
      ...(f.presets.some((p) => p.source === "workspace") ? [{ h: "글꼴 세트 - 작업 공간 지정(nexa-slide.json)" }, ...f.presets.filter((p) => p.source === "workspace").map((p) => ({ label: `${p.name} - ${p.label}`, on: p.name === f.current, act: () => setFonts(p.name) }))] : []),
      { label: "글꼴 설정 보기·수정…", act: showFonts }, "-",
      { h: `템플릿: ${S.template ? I18N.pick(S.template, "label") : "-"}` },
      { label: "코드 언어 이름표 표시", on: LS.get("langTag", "1") === "1", act: () => { LS.set("langTag", LS.get("langTag", "1") === "1" ? "0" : "1"); renderMarks(); renderProps(); } },
      { label: "단축키 보기", key: "?", act: showHelp },
      { label: "편집기 화면 배치 초기화", act: () => { ["mode", "btab", "bfold", "noright", "railW", "rightW", "bottomH", "maxi", "langTag"].forEach((k) => LS.set(k, "")); location.reload(); } },
    ], { right: true });
  }
  async function loadConfig() {
    const r = await api("GET", "/api/config"); if (!r.ok) return;
    if (r.data.mode === "hub") { location.replace("/studio/home.html"); return false; }  // 작업 공간 없음 → 시작 페이지
    S.brand = r.data.brand || {}; S.template = r.data.template || null;
    document.title = `${r.data.title} - nexa-slide`;
    $("#appTitle").textContent = r.data.title || "nexa-slide";
    $("#appTitle").title = `작업 공간 ${r.data.path} · 포트 ${r.data.port}${S.template ? ` · 템플릿 ${S.template.name}` : ""}`;
    if (S.brand.logo) { const l = $("#brandLogo"); l.src = BASE + "/" + S.brand.logo; l.alt = S.brand.name || ""; l.style.display = ""; l.onerror = () => (l.style.display = "none"); }
    if (S.brand.favicon) $("#favicon").href = BASE + "/" + S.brand.favicon;
  }
  async function switchDeck(id) { if (id === S.id) return; if (S.dirty) await save(); await loadDeck(id); }
  async function init() {
    if (window.NexaMenu) NexaMenu.mount($("#menuBtn"));
    if ((await loadConfig()) === false) return;
    S.tokens = await (await fetch("tokens.json", { cache: "no-store" })).json();
    Render.setTokens(S.tokens); $("#rs-css").textContent = Render.css();
    await loadFonts();
    try { S.langs = await (await fetch("code_langs.json", { cache: "no-store" })).json(); Render.setLangs(S.langs); } catch (e) { S.langs = null; }
    const r = await api("GET", "/api/decks"); S.decks = r.ok ? r.data : [];
    if (LS.get("noright", "0") === "1") document.body.classList.add("noright");
    // 기본 배치(0.17.2): 왼쪽 226 · 오른쪽 392 · 노트는 아래. 이 배치가 바뀌면 LAYOUT_VER 를 올려 저장된 크기·최대화를 한 번 비운다
    const LAYOUT_VER = "2";
    if (LS.get("layoutVer", "") !== LAYOUT_VER) { ["railW", "rightW", "bottomH", "maxi"].forEach((k) => LS.set(k, "")); LS.set("layoutVer", LAYOUT_VER); }
    for (const [k, v] of [["railW", "--railW"], ["rightW", "--rightW"], ["bottomH", "--bottomH"]]) { const n = +LS.get(k, 0); if (n) document.documentElement.style.setProperty(v, n + "px"); }
    setMode(["edit", "pick", "draw"].includes(S.mode) ? S.mode : "edit"); setTool("rect");
    setBtab(S.btab); if (LS.get("bfold", "0") === "1") toggleBottom();
    if (!S.decks.length) { location.replace("/studio/home.html"); return; }  // 작업할 덱이 없으면 시작 페이지
    const [hid, hn] = decodeURIComponent(location.hash.slice(1)).split("/");
    await loadDeck(S.decks.some((d) => d.id === hid) ? hid : (S.decks.find((d) => d.start) || S.decks[0]).id);  // 주소의 덱 > 시작 덱(★) > 첫 덱
    if (hn) { goSlide(+hn - 1); revealThumb(S.cur, true); }
    window.addEventListener("load", () => revealThumb(S.cur, true), { once: true });
    window.addEventListener("hashchange", async () => {
      const [h, n] = decodeURIComponent(location.hash.slice(1)).split("/");
      if (h && h !== S.id && S.decks.some((d) => d.id === h)) await switchDeck(h);
      const k = +n - 1; if (n && k !== S.cur && k >= 0) goSlide(k);
      revealThumb(S.cur, true);
    });

    // 머리줄
    $("#deckTabs").addEventListener("click", (e) => { if (e.target.closest("[data-deckadd]")) { deckCreate(); return; } const b = e.target.closest("[data-deck]"); if (b) switchDeck(b.dataset.deck); });
    $("#deckTabs").addEventListener("contextmenu", (e) => { const b = e.target.closest("[data-deck]"); if (b) deckMenu(e, b.dataset.deck); });
    $("#tab-chg").addEventListener("click", onChangesClick); renderChanges();
    $("#layMax").onclick = () => setMaxi(true); $("#layRestore").onclick = () => setMaxi(false);
    if (LS.get("maxi", "0") === "1") setMaxi(true);
    // 변경 탭 설명(ⓘ) - 다른 단추·객체를 누르면 자동으로 숨긴다
    document.addEventListener("pointerdown", (e) => { if (S.chgInfo && !e.target.closest("#chgInfoBtn, #chgInfo")) { S.chgInfo = false; renderChanges(); } }, true);
    $("#fontDlg").addEventListener("click", onFontDlg);
    $("#addDlg").addEventListener("click", onAddDlg); $("#adQ").addEventListener("input", renderAddDlg);
    window.addEventListener("resize", () => { if ($("#addDlg").classList.contains("show")) fitAdd(); }); $("#fontChip").onclick = showFonts;
    $("#noticeClose").onclick = () => $("#notice").classList.remove("show");
    $("#noticeActs").addEventListener("click", async (e) => {
      const b = e.target.closest("[data-nact]"); if (!b) return;
      $("#notice").classList.remove("show");
      if (b.dataset.nact === "open") await switchDeck(b.dataset.arg);
      if (b.dataset.nact === "changes") switchTab("chg");
      if (b.dataset.nact === "reload") { if (S.dirty) await save(); location.reload(); }
    });
    $("#undoBtn").onclick = undo; $("#redoBtn").onclick = redo;
    $("#exportBtn").onclick = (e) => exportMenu(e.currentTarget);
    $("#moreBtn").onclick = (e) => moreMenu(e.currentTarget);
    $("#sessChip").onclick = (e) => sessMenu(e.currentTarget);  // 웹 세션 시작·끊기·모델·진행
    $("#presentBtn").onclick = (e) => present(!!e.shiftKey);  // Shift+클릭 = 현재 슬라이드부터(Shift+F5 와 같다)
    $("#histBtn").onclick = () => switchTab("hist");
    $("#rightBtn").onclick = toggleRight;
    $("#renderBtn").onclick = doRender;
    api("GET", "/api/session").then((x) => x.ok && renderSession(x.data));
    $("#bnTheirs").onclick = async () => { S.dirty = false; await reloadExternal("외부 버전을 불러왔습니다(내 편집은 Ctrl+Z 로 복구)"); };
    $("#bnMine").onclick = async () => { S.conflict = false; await save(true); };
    // 모드 바
    $$("#modeSeg [data-mode]").forEach((b) => (b.onclick = () => setMode(b.dataset.mode)));
    $$("#drawTools [data-tool]").forEach((b) => (b.onclick = () => setTool(b.dataset.tool)));
    $("#addBtn").onclick = (e) => addMenu(e.currentTarget);
    wireImageDrop();
    $("#chkBtn").onclick = () => { S.chkOnlySlide = true; setBtab("check"); renderCheck(); };
    $("#aiFixBtn").onclick = aiFix; $("#aiPolishBtn").onclick = aiPolish;
    // 서식 줄
    $("#ftb").addEventListener("click", onFtb); $("#ftb").addEventListener("change", onFtb);
    // 메모 팝오버 · 보낼 요청 바
    $("#memoTa").addEventListener("input", memoInput);
    attWire($("#memoTa"), "memo"); attWire($("#memo"), "memo");
    $("#memo").addEventListener("click", (e) => {
      const b = e.target.closest("[data-attach],[data-attx]");
      if (!b) { const v = e.target.closest("[data-attv]"); if (v) { const [w, i] = v.dataset.attv.split(":"); NexaLightbox.open(lbItems(ATT[w]), +i); } return; }
      if (b.dataset.attach) attPick("memo"); else { const [w, i] = b.dataset.attx.split(":"); ATT[w].splice(+i, 1); attRender(w); }
    });
    $("#memoTa").addEventListener("keydown", (e) => {
      e.stopPropagation();
      if (e.key === "Escape") { closeMemo(); select(null); }
      if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); memoOk(); } // Enter = 추가, Shift+Enter = 줄바꿈
    });
    $("#memoQuick").addEventListener("click", (e) => { const b = e.target.closest("[data-q]"); if (!b) return; const ta = $("#memoTa"); ta.value = (ta.value ? ta.value.trimEnd() + " " : "") + b.dataset.q; memoInput(); ta.focus(); });
    $("#memoCancel").onclick = closeMemo; $("#memoOk").onclick = memoOk;
    $("#markSend").onclick = sendDrafts; $("#markDiscard").onclick = discardDrafts;
    // 왼쪽 레일
    const left = $("#left");
    left.addEventListener("click", (e) => {
      if (e.target.id === "addSlide") return openAddDlg("end");
      const t = e.target.closest(".thumb"); if (!t) return;
      const i = +t.dataset.i, act = e.target.dataset.act;
      if (act === "dup") dupSlide(i); else if (act === "del") delSlide(i); else goSlide(i);
    });
    left.addEventListener("contextmenu", (e) => { const t = e.target.closest(".thumb"); if (t) thumbMenu(e, +t.dataset.i); });
    left.addEventListener("dragstart", onThumbDragStart); left.addEventListener("dragover", onThumbDragOver); left.addEventListener("drop", onThumbDrop);
    left.addEventListener("dragend", () => { dragFrom = -1; $$(".thumb").forEach((x) => x.classList.remove("drop-before", "drop-after")); });
    // 스플리터 셋 - 왼쪽 레일 폭 · 아래 패널 높이 · 오른쪽 패널 폭. 끌면 바로 반영, 두 번 누르면 처음 크기, 값은 브라우저에 기억.
    // 크기가 바뀌면 슬라이드를 새 영역에 맞춰(확대를 "맞춤"으로) 다시 그리고 썸네일도 새 폭에 맞춘다.
    const relayout = () => { if (S.zoom) S.zoom = null; fitThumbs(); fitStage(); };
    const splitter = (node, cssVar, lsKey, axis, sign, min, max, measure) => {
      node.addEventListener("pointerdown", (e) => {
        e.preventDefault(); const p0 = axis === "x" ? e.clientX : e.clientY, v0 = measure();
        document.body.classList.add("splitting");
        const mv = (ev) => { const v = Math.max(min(), Math.min(max(), v0 + sign * ((axis === "x" ? ev.clientX : ev.clientY) - p0))); document.documentElement.style.setProperty(cssVar, Math.round(v) + "px"); relayout(); };
        const up = () => { window.removeEventListener("pointermove", mv); window.removeEventListener("pointerup", up); document.body.classList.remove("splitting"); LS.set(lsKey, Math.round(measure())); relayout(); };
        window.addEventListener("pointermove", mv); window.addEventListener("pointerup", up);
      });
      node.addEventListener("dblclick", () => { document.documentElement.style.removeProperty(cssVar); LS.set(lsKey, ""); setTimeout(relayout, 0); });
    };
    splitter($("#railSplit"), "--railW", "railW", "x", 1, () => 120, () => Math.min(480, innerWidth * 0.35), () => left.getBoundingClientRect().width);
    splitter($("#rightSplit"), "--rightW", "rightW", "x", -1, () => 240, () => Math.min(720, innerWidth * 0.5), () => $("#right").getBoundingClientRect().width);
    splitter($("#bottomSplit"), "--bottomH", "bottomH", "y", -1, () => 48, () => Math.max(120, innerHeight * 0.55), () => $("#bottom .bpanel.on") ? $("#bottom .bpanel.on").getBoundingClientRect().height : 98);
    // 그 밖의 크기 변화(창 크기·패널 접기·오른쪽 패널 숨기기)도 같은 방식으로 다시 맞춘다
    if (window.ResizeObserver) { let rT = 0; new ResizeObserver(() => { clearTimeout(rT); rT = setTimeout(() => { fitThumbs(); fitStage(); }, 30); }).observe($("#vpEdit")); }
    // 캔버스
    const stage = $("#stage"), vp = $("#vpEdit");
    stage.addEventListener("pointerdown", onDown);
    vp.addEventListener("pointerdown", (e) => { if (e.target === vp || e.target.id === "stageWrap") { if (spaceDown || e.button === 1) onDown(e); else { select(null); closeMemo(); } } });
    window.addEventListener("pointermove", onMove); window.addEventListener("pointerup", onUp);
    stage.addEventListener("dblclick", (e) => { if (S.mode !== "edit") return; const n = topEl(e.target); if (n) { select(n.dataset.id); startEdit(selEl()); } });
    stage.addEventListener("contextmenu", ctxMenu);
    vp.addEventListener("wheel", (e) => { if (!(e.ctrlKey || e.metaKey)) return; e.preventDefault(); const r = vp.getBoundingClientRect(); setZoom(scale * 100 * (e.deltaY < 0 ? 1.1 : 1 / 1.1), { x: e.clientX - r.left, y: e.clientY - r.top }); }, { passive: false });
    vp.addEventListener("scroll", () => placeMemo());
    // 아래 패널 · 바닥줄
    $("#bTabs").addEventListener("click", (e) => { const b = e.target.closest("[data-b]"); if (b) { if (b.classList.contains("on") && !$("#bottom").classList.contains("fold")) toggleBottom(); else setBtab(b.dataset.b); } });
    $("#bFold").onclick = toggleBottom;
    $("#outlineList").addEventListener("click", (e) => { const d = e.target.closest("[data-i]"); if (d) { goSlide(+d.dataset.i); revealThumb(S.cur); } });
    $("#bp-check").addEventListener("click", onChkClick);
    $("#prevBtn").onclick = () => goSlide(S.cur - 1); $("#nextBtn").onclick = () => goSlide(S.cur + 1);
    $("#zoomSlider").addEventListener("input", (e) => setZoom(+e.target.value));
    $("#zoomIn").onclick = () => setZoom(scale * 100 * 1.15); $("#zoomOut").onclick = () => setZoom(scale * 100 / 1.15);
    $("#zoomPct").onclick = () => setZoom(100); $("#zoomFit").onclick = () => setZoom(null);
    // 오른쪽 패널
    $$(".tabs .chip").forEach((b) => (b.onclick = () => switchTab(b.dataset.tab)));
    const P = $("#tab-props"); P.addEventListener("change", onPropChange); P.addEventListener("search", (e) => { if (e.target.dataset.lang && !e.target.value) onPropChange(e); });  // ✕ 로 지우면 바로 반영
    P.addEventListener("click", onPropClick);  // 속성 패널의 단추·요소 목록(주석 뒤에 묻혀 있어 눌러도 안 되던 회귀)
    document.addEventListener("error", (e) => {  // 그림 읽기 실패 재시도 - 많은 그림이 한꺼번에 내려받다 끊기면(ERR_ABORTED 등) 0.5·1.5·4초 뒤 다시(캐시 우회), 3번까지
      const im = e.target; if (!(im instanceof HTMLImageElement) || !im.classList.contains("rs-img")) return;
      const n = +(im.dataset.retry || 0); if (n >= 3) return;
      im.dataset.retry = n + 1;
      const base = (im.dataset.src0 = im.dataset.src0 || im.getAttribute("src"));
      setTimeout(() => { if (im.isConnected) im.src = base + (base.includes("?") ? "&" : "?") + "r=" + (n + 1) + "_" + Date.now(); }, [500, 1500, 4000][n]);
    }, true);
    $("#tab-reqs").addEventListener("click", onReqClick);
    $("#tab-reqs").addEventListener("input", (e) => { if (e.target.id === "reqText") keep(e.target.dataset.key, e.target.value); });
    $("#tab-reqs").addEventListener("keydown", (e) => { // 슬라이드 요청 칸도 메모 팝오버처럼: Enter = 메모 남기기(초안), Shift+Enter = 줄바꿈
      if (e.target.id === "reqText" && e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); $("#reqAdd").click(); }
      if (e.target.id === "fuText" && e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); fuSend(e.target.closest(".req").dataset.rid); }
      if (e.target.id === "fuText" && e.key === "Escape") { S.fu = null; ATT.fu = []; renderReqs(); }
    });
    $("#tab-hist").addEventListener("click", onHistClick);
    $("#notesTa").addEventListener("input", onNotes);
    // 발표 · 도움말
    $("#present").addEventListener("click", (e) => { const ln = e.target.closest("[data-link]"); if (ln && followLink(ln.dataset.link)) return; pStep(e.clientX < innerWidth / 3 ? -1 : 1); renderPresent(); });
    document.addEventListener("fullscreenchange", () => { if (!document.fullscreenElement && $("#present").classList.contains("show")) endPresent(); });
    setInterval(() => { if ($("#present").classList.contains("show")) renderPresent(); }, 1000);
    $("#help").addEventListener("click", () => $("#help").classList.remove("show"));
    // 전역
    new ResizeObserver(() => fitStage()).observe(vp);
    document.addEventListener("keydown", onKey);
    document.addEventListener("keyup", (e) => { if (e.key === " ") { spaceDown = false; if (!S.pan) document.body.classList.remove("panning"); } });
    document.addEventListener("pointerdown", (e) => { if (!e.target.closest(".menu") && !e.target.closest("#ftb") && !e.target.closest("#addBtn,#exportBtn,#moreBtn,#sessChip")) closeMenu(); });
    window.addEventListener("resize", () => { fitStage(); fitThumbs(); if ($("#present").classList.contains("show")) renderPresent(); });
    window.addEventListener("beforeunload", (e) => { if (S.dirty) { save(); e.preventDefault(); e.returnValue = ""; } });
    setInterval(poll, 2000);
  }
  init().catch((e) => { console.error(e); setStatus("error", "오류"); toast("초기화 오류: " + e.message, 6000); });
})();
