/* nexa-slide 편집기 — 덱 JSON 편집(자동 저장·외부 변경 감지·요청 메모·검사·기록·발표·PPTX 내보내기).
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
  window.RENDER_BASE = "/";
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const esc = (s) => Render.esc(s == null ? "" : s);
  const GRID = 8, SW = 1280, SH = 720;
  const LS = { get(k, d) { try { const v = localStorage.getItem("nexa-" + k); return v == null ? d : v; } catch (e) { return d; } },
               set(k, v) { try { localStorage.setItem("nexa-" + k, v); } catch (e) { /* 저장소 없음 */ } } };
  // 아직 남기지 않은 요청 입력 — 덱·슬라이드(·요소)별로 보관해 슬라이드를 옮겨 다녀도·새로 고쳐도 남는다
  const typed = (key) => LS.get("typed-" + key, "");
  const keep = (key, v) => { try { if (v.trim()) localStorage.setItem("nexa-typed-" + key, v); else localStorage.removeItem("nexa-typed-" + key); } catch (e) { /* 저장소 없음 */ } };

  const S = {
    tokens: null, decks: [], id: null, deck: null, version: null, reqVersion: "0", savedJson: null,
    cur: 0, sel: null, undo: [], redo: [], dirty: false, saving: false, conflict: false,
    reqs: [], reqOnlySlide: true, layouts: [], preview: false, pngs: [], renderAt: 0, editing: null, clip: null,
    tab: "props", brand: {}, session: null, check: null, chkOnlySlide: true, chkBox: null, template: null,
    changes: [], chgMark: {}, chgSeq: 0,
    mode: LS.get("mode", "edit"), tool: "rect", zoom: null, btab: LS.get("btab", "notes"), memo: null, drawing: null, pan: null,
  };

  // ---------------------------------------------------------------- 공통
  async function api(method, url, body) {
    const r = await fetch(url, { method, headers: body !== undefined ? { "Content-Type": "application/json" } : {}, body: body !== undefined ? JSON.stringify(body) : undefined });
    let data = null;
    try { data = await r.json(); } catch (e) { /* 빈 응답 */ }
    return { ok: r.ok, status: r.status, data, headers: r.headers };
  }
  let toastT = 0;
  function toast(msg, ms = 2200) {
    const t = $("#toast"); t.textContent = msg; t.classList.add("show");
    clearTimeout(toastT); toastT = setTimeout(() => t.classList.remove("show"), ms);
  }
  const slide = () => (S.deck && S.deck.slides[S.cur]) || null;
  const elById = (id, s = slide()) => (s ? s.elements.find((e) => e.id === id) : null);
  const selEl = () => (S.sel ? elById(S.sel) : null);
  const isLine = (e) => e && (e.type === "line" || e.type === "arrow");
  const snap = (v, free) => (free ? Math.round(v) : Math.round(v / GRID) * GRID);
  const clone = (o) => JSON.parse(JSON.stringify(o));
  const deckJson = () => JSON.stringify(S.deck);

  function setStatus(kind, text) { const s = $("#status"); s.className = "chip sm " + kind; s.textContent = text; }

  // ---------------------------------------------------------------- 공통 팝업 메뉴
  function closeMenu() { $$(".menu").forEach((m) => m.remove()); }
  /** items: [{label, key, act, disabled, on}] | "-" | {h:"제목"} | {html, bind(m)} — anchor 요소 아래(또는 x,y) */
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
  async function save(force) {
    if (!S.deck || S.conflict && !force) return;
    if (S.saving) { scheduleSave(); return; }
    const body = deckJson();
    if (!force && body === S.savedJson) { S.dirty = false; setStatus("saved", "저장됨"); return; } // 바뀐 것이 없으면 저장하지 않는다
    S.saving = true; setStatus("dirty", "저장 중…");
    const r = await api("PUT", `/api/deck/${S.id}?base=${encodeURIComponent(S.version || "")}${force ? "&force=1" : ""}`, JSON.parse(body));
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
    const r = await fetch(`/api/deck/${id}`, { cache: "no-store" });
    if (!r.ok) { toast("덱을 불러오지 못했습니다"); return false; }
    const deck = await r.json();
    if (keep && S.deck && S.id === id) snapshot(); else { S.undo = []; S.redo = []; }
    S.id = id; S.deck = deck; S.version = r.headers.get("X-Deck-Version"); S.savedJson = deckJson();
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
    return true;
  }
  async function poll() {
    if (!S.id) return;
    try {
      const r = await api("GET", `/api/version/${S.id}`);
      if (!r.ok) return;
      if (r.data.session) renderSession(r.data.session);
      await checkWorkspace(r.data);
      if (r.data.requests !== S.reqVersion) await loadReqs();
      if (r.data.deck !== S.version && !S.saving) {
        if (S.dirty || S.editing) {
          if (!S.conflict) { S.conflict = true; setStatus("conflict", "충돌"); banner(true, "편집 중에 덱 파일이 밖에서(Claude 등) 바뀌었습니다. 어느 쪽을 남길까요?"); }
        } else await reloadExternal("밖에서 바뀐 덱을 다시 불러왔습니다");
      }
    } catch (e) { setStatus("error", "서버 끊김"); }
  }

  // ---------------------------------------------------------------- 외부 변경 기록 — 밖에서(Claude 등) 바뀐 덱을 불러올 때 전·후를 비교해
  // 무엇이 바뀌었는지 남긴다: 오른쪽 "변경" 탭 목록 · 썸네일·개요 배지 · 캔버스 점선 테두리. 기록은 이 화면을 연 동안만 유지(최근 30건).
  const GEO = new Set(["x", "y", "w", "h", "x1", "y1", "x2", "y2", "z", "rot"]);
  const TXT = new Set(["text", "rows", "header", "items", "code", "lines", "cells", "label", "title", "sub"]);
  const short = (v, n = 60) => { const t = Render.plain(typeof v === "string" ? v : JSON.stringify(v ?? "")).replace(/\s+/g, " ").trim(); return t.length > n ? t.slice(0, n) + "…" : t; };
  function diffEl(a, b) {
    const keys = new Set([...Object.keys(a), ...Object.keys(b)]), kinds = new Set();
    let before = "", after = "";
    for (const k of keys) {
      if (k === "id" || JSON.stringify(a[k]) === JSON.stringify(b[k])) continue;
      if (GEO.has(k)) kinds.add("위치·크기");
      else if (TXT.has(k)) { kinds.add("글자"); if (!before && !after) { before = short(a[k]); after = short(b[k]); } }
      else if (k === "src") kinds.add("그림");
      else kinds.add("모양");
    }
    return kinds.size ? { kinds: [...kinds], before, after } : null;
  }
  function diffDeck(old, nw) {
    const om = new Map(old.slides.map((s, i) => [s.id, [s, i]])), nm = new Map(nw.slides.map((s, i) => [s.id, [s, i]]));
    // 이동: 양쪽에 있는 장의 순서에서 가장 긴 "순서가 유지된 흐름"(최장 증가 부분 수열) 밖의 장만 옮긴 것으로 본다
    const oc = old.slides.filter((s) => nm.has(s.id)).map((s) => s.id), np = new Map(nw.slides.filter((s) => om.has(s.id)).map((s, i) => [s.id, i]));
    const seq = oc.map((id) => np.get(id)), tails = [], prev = new Array(seq.length);
    seq.forEach((v, i) => {
      let lo = 0, hi = tails.length; while (lo < hi) { const m = (lo + hi) >> 1; if (seq[tails[m]] < v) lo = m + 1; else hi = m; }
      prev[i] = lo ? tails[lo - 1] : -1; tails[lo] = i;
    });
    const stable = new Set(); for (let i = tails.length ? tails[tails.length - 1] : -1; i >= 0; i = prev[i]) stable.add(oc[i]);
    const items = [];
    nw.slides.forEach((s, i) => {
      if (!om.has(s.id)) { items.push({ sid: s.id, idx: i, kind: "추가", title: slideTitle(s), els: [], extra: [] }); return; }
      const [o, oi] = om.get(s.id), els = [], extra = [];
      const oe = new Map((o.elements || []).map((e) => [e.id, e])), ne = new Map((s.elements || []).map((e) => [e.id, e]));
      for (const e of s.elements || []) {
        if (!oe.has(e.id)) els.push({ id: e.id, kinds: ["추가"], before: "", after: short(e.text || e.src || e.type) });
        else { const d = diffEl(oe.get(e.id), e); if (d) els.push({ id: e.id, ...d }); }
      }
      for (const e of o.elements || []) if (!ne.has(e.id)) els.push({ id: e.id, kinds: ["삭제"], before: short(e.text || e.src || e.type), after: "", gone: true });
      if (JSON.stringify(o.notes ?? "") !== JSON.stringify(s.notes ?? "")) extra.push("노트");
      for (const k of ["layout", "bg", "part"]) if (JSON.stringify(o[k]) !== JSON.stringify(s[k])) extra.push(k === "bg" ? "바탕" : k === "layout" ? "레이아웃" : "부");
      const moved = !stable.has(s.id);
      if (els.length || extra.length || moved)
        items.push({ sid: s.id, idx: i, kind: els.length || extra.length ? "수정" : "이동", moved: moved ? [oi + 1, i + 1] : null, title: slideTitle(s), els, extra });
    });
    old.slides.forEach((s, i) => { if (!nm.has(s.id)) items.push({ sid: s.id, idx: i, kind: "삭제", title: slideTitle(s), els: [], extra: [], gone: true }); });
    return items;
  }
  function recordChange(old, nw) {
    const items = diffDeck(old, nw);
    if (!items.length) return null;
    const rec = { n: ++S.chgSeq, at: new Date().toTimeString().slice(0, 8), deck: S.id, items, shown: true };  // 새 묶음은 표시된 채로
    S.changes.unshift(rec); S.changes.length = Math.min(S.changes.length, 30);
    rebuildMarks();
    return rec;
  }
  // 표시(배지·점선) = 표시 중인 변경 묶음들의 합 — 묶음마다 켜고 끈다
  function rebuildMarks() {
    S.chgMark = {};
    for (const r of S.changes) {
      if (!r.shown) continue;
      const mark = (S.chgMark[r.deck] = S.chgMark[r.deck] || {});
      for (const it of r.items) if (!it.gone) { const m = (mark[it.sid] = mark[it.sid] || new Set()); it.els.filter((e) => !e.gone).forEach((e) => m.add(e.id)); }
    }
  }
  function chgSummary(items) {
    const c = {}; items.forEach((it) => (c[it.kind] = (c[it.kind] || 0) + 1));
    return ["수정", "추가", "삭제", "이동"].filter((k) => c[k]).map((k) => `${c[k]}장 ${k}`).join(" · ");
  }
  const chgOf = (sid) => (S.chgMark[S.id] || {})[sid];
  async function reloadExternal(msg) {
    const old = S.deck ? clone(S.deck) : null;
    await loadDeck(S.id, true);
    const rec = old ? recordChange(old, S.deck) : null;
    renderAll(); renderChanges();
    if (rec) notice(`${msg} — ${chgSummary(rec.items)}. Ctrl+Z 로 되돌릴 수 있습니다.`, [{ act: "changes", label: "변경 보기", primary: true }]);
    else toast(msg + " (바뀐 내용 없음)");
  }
  function renderChanges() {
    const n = Object.values(S.chgMark[S.id] || {}).length;
    $("#chgCnt").style.display = n ? "" : "none"; $("#chgCnt").textContent = n;
    const P = $("#tab-chg"); if (!P) return;
    P.innerHTML = `<div class="sec"><h3>변경 — 밖에서 바뀐 내용</h3><div class="hint">Claude 등이 덱 파일을 바꿔 다시 불러올 때마다 전·후를 비교해 남깁니다(이 화면을 연 동안, 최근 30건). 항목을 누르면 그 슬라이드·요소로 갑니다. 바뀐 요소는 캔버스에 파란 점선으로 표시됩니다.</div>
      ${S.changes.length ? `<div class="row" style="gap:6px;margin-top:6px">${S.changes.some((r) => r.shown) ? `<button class="chip sm" data-chg-all="0">표시 지우기</button>` : ""}${S.changes.some((r) => !r.shown) ? `<button class="chip sm" data-chg-all="1">모두 다시 표시</button>` : ""}</div>` : ""}</div>` +
      (S.changes.length ? S.changes.map((r) => `<div class="chg-rec${r.shown ? " on" : ""}"><div class="chg-h"><b>${esc(r.at)}</b> <span class="hint" style="margin:0">${esc(r.deck)} · ${esc(chgSummary(r.items))}</span>
        <button class="chip sm chg-tg" data-chg-tg="${r.n}" title="이 묶음의 변경을 썸네일·개요 배지와 캔버스 점선으로 ${r.shown ? "그만 표시" : "다시 표시"}">${r.shown ? "숨기기" : "표시"}</button></div>` +
        r.items.map((it) => `<div class="chg-it${it.gone ? " gone" : ""}" ${it.gone ? "" : `data-cdeck="${esc(r.deck)}" data-csid="${esc(it.sid)}"`}>
          <span class="k ${it.kind}">${it.kind}</span> <b>${it.idx + 1}.</b> ${esc(it.title)}${it.moved ? ` <span class="hint" style="margin:0">(순서 ${it.moved[0]} → ${it.moved[1]})</span>` : ""}${it.extra.length ? ` <span class="hint" style="margin:0">· ${esc(it.extra.join("·"))}</span>` : ""}
          ${it.els.map((e) => `<div class="chg-el${e.gone ? " gone" : ""}" ${e.gone ? "" : `data-cel="${esc(e.id)}"`}><code>${esc(e.id)}</code> ${esc(e.kinds.join("·"))}${e.before || e.after ? `<div class="chg-tx">${e.before ? `<s>${esc(e.before)}</s>` : ""}${e.before && e.after ? " → " : ""}${e.after ? `<span>${esc(e.after)}</span>` : ""}</div>` : ""}</div>`).join("")}</div>`).join("") + `</div>`).join("")
        : `<div class="hint">아직 밖에서 바뀐 내용이 없습니다.</div>`);
  }
  async function onChangesClick(e) {
    const all = e.target.closest("[data-chg-all]"), tg = e.target.closest("[data-chg-tg]");
    if (all || tg) {
      if (all) S.changes.forEach((r) => (r.shown = all.dataset.chgAll === "1"));
      else { const r = S.changes.find((x) => x.n === +tg.dataset.chgTg); if (r) r.shown = !r.shown; }
      rebuildMarks(); renderAll(); renderChanges(); return;
    }
    const it = e.target.closest("[data-csid]"); if (!it) return;
    if (it.dataset.cdeck !== S.id) await switchDeck(it.dataset.cdeck);
    const i = S.deck.slides.findIndex((s) => s.id === it.dataset.csid); if (i < 0) { toast("그 슬라이드가 지금은 없습니다"); return; }
    goSlide(i); revealThumb(i, true);
    const el = e.target.closest("[data-cel]");
    if (el && elById(el.dataset.cel)) { S.sel = el.dataset.cel; renderAll(); }
  }

  // 덱 목록·설정·엔진 변경 감지 — 지금 보는 슬라이드와 상관없이 머리 아래 안내 띠로 알린다.
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
        notice(`새 덱 ${added.length}개가 생겼습니다 — ${added.map((d) => `${d.id}(${d.slides}장)`).join(", ")}. 위 덱 탭에도 추가했습니다.`,
          added.slice(0, 6).map((d, i) => ({ act: "open", arg: d.id, label: `${d.id} 열기`, primary: i === 0 })));
      }
      W.ids = ids; W.decksVer = v.decksVer;
    }
    if (v.config !== W.config) {  // 설정(템플릿 색·글꼴·로고·제목)은 다시 불러와 바로 적용 — 새로 고침 불필요
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
    $("#deckTabs").innerHTML = S.decks.map((d) => `<button data-deck="${esc(d.id)}" class="${d.id === S.id ? "on" : ""}" title="${esc(d.title)} (${d.slides}장)">${esc(d.id)}</button>`).join("");
  }
  const reqsOf = (sid, st) => S.reqs.filter((r) => r.slide === sid && (st ? r.status === st : r.status !== "done"));
  function thumbHtml(s, i) {
    const dr = reqsOf(s.id, "draft").length, op = reqsOf(s.id, "open").length, wk = reqsOf(s.id, "working").length;
    return `<div class="thumb${i === S.cur ? " cur" : ""}" data-i="${i}" draggable="true"><span class="num">${i + 1}</span>
      <div class="vp">${Render.renderSlide(s, i + 1)}</div>
      <div class="tools"><button data-act="dup" title="복제">복제</button><button data-act="del" title="삭제">삭제</button></div>
      <div class="badges">${dr ? `<span class="bd draft" title="보내지 않은 요청 메모">✎ ${dr}</span>` : ""}${op ? `<span class="bd req" title="세션에 보낸 요청(대기)">요청 ${op}</span>` : ""}${wk ? `<span class="bd work" title="세션 처리 중">처리 ${wk}</span>` : ""}${chgOf(s.id) ? `<span class="bd chg" title="밖에서 바뀐 슬라이드 — 변경 탭">변경${chgOf(s.id).size ? " " + chgOf(s.id).size : ""}</span>` : ""}${chkBadge(s.id)}</div></div>`;
  }
  function chkBadge(sid) {
    if (!S.check) return "";
    const its = S.check.issues.filter((x) => x.slide === sid); if (!its.length) return "";
    const e = its.filter((x) => x.severity === "ERROR").length;
    return `<span class="bd chk${e ? " err" : ""}" title="레이아웃 검사 — ERROR ${e} · WARNING ${its.length - e}">⚠ ${its.length}</span>`;
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
  function drawSel() {
    const ov = $("#ov"); const el = selEl();
    if (!el || S.editing || S.mode === "draw") { ov.innerHTML = ""; drawChkBox(); return; }
    const b = boxOf(el), hs = 11 / scale, bw = 2 / scale;
    let h = `<div class="selbox${el.locked ? " locked" : ""}${S.mode === "pick" ? " pick" : ""}" style="left:${b.x - bw}px;top:${b.y - bw}px;width:${b.w + 2 * bw}px;height:${b.h + 2 * bw}px;border-width:${bw * (S.mode === "pick" ? 1.5 : 1)}px"></div>`;
    if (!el.locked && S.mode === "edit") {
      const pts = isLine(el) ? [["p1", el.x1, el.y1], ["p2", el.x2, el.y2]]
        : [["nw", b.x, b.y], ["n", b.x + b.w / 2, b.y], ["ne", b.x + b.w, b.y], ["e", b.x + b.w, b.y + b.h / 2],
           ["se", b.x + b.w, b.y + b.h], ["s", b.x + b.w / 2, b.y + b.h], ["sw", b.x, b.y + b.h], ["w", b.x, b.y + b.h / 2]];
      h += pts.map(([d, x, y]) => `<div class="hd" data-h="${d}" style="left:${x - hs / 2}px;top:${y - hs / 2}px;width:${hs}px;height:${hs}px;border-width:${bw}px;cursor:${d.length === 2 && d[0] !== "p" ? d + "-resize" : d === "n" || d === "s" ? "ns-resize" : d === "e" || d === "w" ? "ew-resize" : "move"}"></div>`).join("");
    }
    ov.innerHTML = h; drawChkBox();
  }

  // ---------------------------------------------------------------- 요청 표시(초안·대기·처리 중) — 번호 배지 + 영역
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
        } else if (r.element) {
          const el = elById(r.element, s);
          if (el) { const b = boxOf(el); bx = [b.x, b.y, b.w, b.h]; h += `<div class="mk ${st}" style="left:${b.x - 3}px;top:${b.y - 3}px;width:${b.w + 6}px;height:${b.h + 6}px;border-width:${2 * inv}px"></div>`; }
        }
        if (!bx) bx = [16 + k * 30, 16, 0, 0];
        h += `<div class="mkn ${st}" title="${esc(r.text)}" style="left:${bx[0]}px;top:${bx[1]}px;transform:translate(-50%,-50%) scale(${inv})">${n}</div>`;
      });
    }
    if (S.drawing) svg += S.drawing.svg || "";
    const cm = s && chgOf(s.id);  // 밖에서 바뀐 요소 — 파란 점선
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
    target.key = target.region ? null : S.id + "/" + slide().id + (target.element ? "/" + target.element : "");
    const el = target.element ? elById(target.element) : null;
    $("#memoTitle").textContent = target.region ? "영역 요청" : "요청";
    $("#memoTarget").textContent = `슬라이드 ${S.cur + 1}` + (el ? ` · ${TYPE_KO[el.type] || el.type} ${el.id}` : target.region ? ` · ${{ rect: "박스", pen: "펜", pin: "핀" }[target.region.kind]}` : "");
    const ta = $("#memoTa"); ta.value = target.key ? typed(target.key) : ""; ta.placeholder = target.region ? (target.region.kind === "pin" ? "이 지점에서 무엇을 바꿀까요?" : "이 영역에서 무엇을 바꿀까요?") : `이 ${el ? TYPE_KO[el.type] || "요소" : "슬라이드"}에서 무엇을 바꿀까요?`;
    let q = (target.region ? QUICK.region : (el && QUICK[el.type]) || []).slice();
    const issues = S.check ? S.check.issues.filter((x) => x.slide === slide().id && (!el || (x.elements || []).includes(el.id))) : [];
    if (issues.length) q.unshift("검사 결과 고치기");
    $("#memoQuick").innerHTML = q.map((t) => `<button data-q="${esc(t)}">${esc(t)}</button>`).join("");
    memoInput(); $("#memo").classList.add("show"); placeMemo(); ta.focus();
  }
  function closeMemo() { S.memo = null; $("#memo").classList.remove("show"); if (S.drawing) { S.drawing = null; renderMarks(); } }
  function memoInput() { if (S.memo && S.memo.key) keep(S.memo.key, $("#memoTa").value); const n = $("#memoTa").value.length; $("#memoCnt").textContent = `${n} / 2000`; $("#memoOk").disabled = !$("#memoTa").value.trim(); }
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
    const t = $("#memoTa").value.trim(); if (!t || !S.memo) return;
    const body = { action: "add", status: "draft", slide: slide().id, element: S.memo.element || null, text: t };
    if (S.memo.region) body.region = S.memo.region;
    const r = await api("POST", `/api/requests/${S.id}`, body);
    if (!r.ok) { toast("메모를 저장하지 못했습니다"); return; }
    if (S.memo.key) keep(S.memo.key, "");
    S.reqs = r.data; S.drawing = null; closeMemo(); afterReqs();
    toast("메모를 남겼습니다 — 아래 바에서 한꺼번에 보내기");
  }
  async function sendDrafts() {
    const n = S.reqs.filter((r) => r.status === "draft").length; if (!n) return;
    const r = await api("POST", `/api/requests/${S.id}`, { action: "send" });
    if (!r.ok) { toast("보내지 못했습니다"); return; }
    S.reqs = r.data; afterReqs(); await flushReqs(true);
    toast(S.session && S.session.connected ? `요청 ${n}개를 세션에 보냈습니다` : `요청 ${n}개를 대기로 올렸습니다 — 세션이 연결되면 전달됩니다`, 3500);
  }
  /** 이 슬라이드에 초안이 있으면 그 슬라이드만, 없으면 전체 초안을 지운다(Genspark 와 같은 범위) */
  async function discardDrafts() {
    const here = S.reqs.some((r) => r.status === "draft" && r.slide === slide().id);
    const r = await api("POST", `/api/requests/${S.id}`, here ? { action: "discard", slide: slide().id } : { action: "discard" });
    if (r.ok) { S.reqs = r.data; afterReqs(); toast(here ? "이 슬라이드의 메모를 지웠습니다" : "모든 메모를 지웠습니다"); }
  }
  /** 바로 요청(모드 바 ✨ 버튼) — 초안을 거치지 않고 대기로 올리고 즉시 전달 */
  async function quickRequest(text) {
    const r = await api("POST", `/api/requests/${S.id}`, { action: "add", status: "open", slide: slide().id, element: null, text });
    if (!r.ok) { toast("요청하지 못했습니다"); return; }
    S.reqs = r.data; afterReqs(); await flushReqs(true);
    toast(S.session && S.session.connected ? "세션에 바로 요청했습니다" : "요청을 남겼습니다 — 세션이 연결되면 전달됩니다", 3000);
  }
  function aiFix() {
    const s = slide(), its = S.check ? S.check.issues.filter((x) => x.slide === s.id) : [];
    if (!its.length) { toast("이 슬라이드는 검사 결과가 없습니다"); return; }
    quickRequest(`이 슬라이드의 레이아웃 검사 결과를 고쳐 줘 — 기존 디자인·구성은 유지하고, 요소를 지워서 경고를 없애지 말 것.\n` +
      its.map((x) => `- ${x.severity} ${x.rule}: ${x.message}`).join("\n"));
  }
  function aiPolish() { quickRequest("이 슬라이드를 다듬어 줘 — 기존 스타일·레이아웃 규칙은 유지하고, 내용 논리·문장 길이·정렬·여백만 정리. 원문(각주 근거)의 의미는 바꾸지 말 것."); }
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
  const TEXTY = new Set(["text", "pill", "rect", "ellipse"]);
  const SIZED = new Set(["text", "pill", "rect", "ellipse", "bullets", "table", "plan-table", "code", "plan"]);
  const TYPE_KO = { text: "글자", pill: "칩", rect: "상자", ellipse: "원", image: "그림", line: "선", arrow: "화살표", table: "표", "plan-table": "실행계획 표", code: "코드", plan: "실행계획", bullets: "글머리", curve: "곡선" };
  const SIZE_PRESETS = [10, 11, 12, 13, 14, 15, 16, 17, 18, 20, 22, 24, 28, 32, 36, 40, 48, 60, 72];
  function defSize(el) { return { pill: 14, code: 15, plan: 14, "plan-table": 15, table: 16 }[el.type] || 20; }
  function swatch(v) { return v ? Render.color(v) : "transparent"; }
  function renderFtb() {
    const F = $("#ftb"), el = selEl();
    if (S.mode !== "edit" || !el || S.editing) { F.classList.remove("show"); F.innerHTML = ""; return; }
    const lk = !!el.locked; let h = "";
    if (SIZED.has(el.type)) {
      const sz = el.size || defSize(el);
      if (TEXTY.has(el.type)) h += `<select data-f="font" title="글꼴"><option value="body"${el.font !== "mono" ? " selected" : ""}>본문 글꼴</option><option value="mono"${el.font === "mono" ? " selected" : ""}>고정폭(코드)</option></select>`;
      h += `<input class="num" type="number" min="6" max="400" step="1" data-f="size" value="${sz}" title="글자 크기(px) — PPT pt = px × 0.75">
        <button class="ib" data-f="sizePreset" title="크기 프리셋">▾</button><span class="pt" title="PowerPoint 글자 크기">${+(sz * 0.75).toFixed(2)}pt</span>`;
      if (TEXTY.has(el.type) || el.type === "bullets") h += `<button class="ib" data-f="color" title="글자색 — ${esc(el.color || "기본")}"><b style="text-decoration:underline;text-decoration-color:${swatch(el.color || "on-surface")};text-decoration-thickness:3px">A</b></button>`;
      if (TEXTY.has(el.type)) {
        const bold = el.bold === undefined ? el.type === "pill" : !!el.bold;
        h += `<span class="vsep"></span><button class="ib${bold ? " on" : ""}" data-f="bold" title="굵게 (Ctrl+B)"><b>B</b></button>`;
        const al = el.align || (el.type === "pill" || el.type === "ellipse" ? "center" : "left");
        h += `<span class="vsep"></span>` + [["left", "⯇≡", "왼쪽"], ["center", "≡", "가운데"], ["right", "≡⯈", "오른쪽"]].map(([k, i, t]) => `<button class="ib${al === k ? " on" : ""}" data-f="align" data-v="${k}" title="${t} 정렬">${i}</button>`).join("");
        h += `<button class="ib" data-f="spacing" title="줄 간격·세로 정렬">↕ ▾</button>`;
      }
    }
    if (["rect", "ellipse", "pill", "text", "plan"].includes(el.type)) h += `<span class="vsep"></span><button class="ib" data-f="fill" title="채우기 — ${esc(el.fill || "없음")}">🪣<span class="sw" style="background:${swatch(el.fill)}"></span></button>`;
    if (["rect", "ellipse", "pill", "text"].includes(el.type)) h += `<button class="ib" data-f="stroke" title="테두리 — ${esc(el.stroke || "없음")}">▢<span class="sw" style="background:${swatch(el.stroke)}"></span></button>`;
    if (isLine(el)) {
      h += `<button class="ib" data-f="color" title="선 색">━<span class="sw" style="background:${swatch(el.color || "on-surface")}"></span></button>
        <input class="num" type="number" min="0.5" max="20" step="0.5" data-f="width" value="${el.width || 2}" title="두께(px)">
        <button class="ib" data-f="head" title="화살 머리 — 누를 때마다 바뀜">${{ none: "—", end: "→", start: "←", both: "↔" }[el.head || (el.type === "arrow" ? "end" : "none")]}</button>
        <button class="ib" data-f="dash" title="선 모양 — 누를 때마다 바뀜">${{ solid: "실선", dash: "파선", dot: "점선" }[el.dash || "solid"]}</button>`;
    }
    h += `<span class="vsep"></span><button class="ib" data-f="dup" title="복제 (Ctrl+D)">⧉</button>
      <button class="ib" data-f="del" title="삭제 (Delete)" ${lk ? "disabled" : ""}>🗑</button>
      <button class="ib${lk ? " on" : ""}" data-f="lock" title="잠금 — 끌기·삭제 막기">🔒</button>
      <button class="ib" data-f="pos" title="위치 조정 — 정렬·순서·크기·좌표">✥ ▾</button>
      <span class="vsep"></span><button class="ib" data-f="memo" title="이 요소에 요청 메모(세션에 보냄)">💬</button>`;
    F.innerHTML = h; F.classList.add("show");
  }
  function mutate(fn) { const el = selEl(); if (!el) return; snapshot(); fn(el); if (isLine(el)) Object.assign(el, Render.lineBox(el)); afterChange(); }
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
  function zorder(k) {
    const s = slide(), el = selEl(); if (!el) return;
    snapshot(); const i = s.elements.indexOf(el); s.elements.splice(i, 1); delete el.z;
    const j = k === "front" ? s.elements.length : k === "back" ? 0 : k === "fwd" ? Math.min(s.elements.length, i + 1) : Math.max(0, i - 1);
    s.elements.splice(j, 0, el); afterChange();
  }
  function onFtb(e) {
    const t = e.target.closest("[data-f]"); if (!t) return;
    const f = t.dataset.f, el = selEl(); if (!el) return;
    if (e.type === "change") {
      if (f === "size") mutate((x) => { x.size = Math.max(6, Math.min(400, +t.value || defSize(x))); });
      if (f === "width") mutate((x) => { x.width = +t.value || 2; });
      if (f === "font") mutate((x) => { if (t.value === "body") delete x.font; else x.font = t.value; });
      return;
    }
    if (t.tagName === "INPUT" || t.tagName === "SELECT") return;
    if (f === "sizePreset") openMenu(t, SIZE_PRESETS.map((v) => ({ label: `${v}px · ${+(v * 0.75).toFixed(2)}pt`, on: (el.size || defSize(el)) === v, act: () => mutate((x) => { x.size = v; }) })));
    if (f === "color") palette(t, el.color, false, (c) => mutate((x) => { x.color = c; }));
    if (f === "fill") palette(t, el.fill, true, (c) => mutate((x) => { if (c) x.fill = c; else delete x.fill; }));
    if (f === "stroke") palette(t, el.stroke, true, (c) => mutate((x) => { if (c) x.stroke = c; else delete x.stroke; }));
    if (f === "bold") mutate((x) => { const cur = x.bold === undefined ? x.type === "pill" : !!x.bold; x.bold = !cur; });
    if (f === "align") mutate((x) => { x.align = t.dataset.v; });
    if (f === "spacing") {
      const lh = el.lineHeight || (el.type === "text" ? 1.4 : 1.2), va = el.valign || (el.type === "text" ? "top" : "middle");
      openMenu(t, [
        { h: `줄 간격 (지금 ${lh})` }, ...[1.0, 1.2, 1.4, 1.5, 1.6, 1.8, 2.0].map((v) => ({ label: String(v), on: Math.abs(lh - v) < 0.001, act: () => mutate((x) => { x.lineHeight = v; }) })), "-",
        { h: "세로 정렬" }, ...[["top", "위"], ["middle", "가운데"], ["bottom", "아래"]].map(([k, l]) => ({ label: l, on: va === k, act: () => mutate((x) => { x.valign = k; }) })),
      ]);
    }
    if (f === "head") mutate((x) => { const o = ["none", "end", "start", "both"]; x.head = o[(o.indexOf(x.head || (x.type === "arrow" ? "end" : "none")) + 1) % 4]; });
    if (f === "dash") mutate((x) => { const o = ["solid", "dash", "dot"]; x.dash = o[(o.indexOf(x.dash || "solid") + 1) % 3]; });
    if (f === "dup") dupEl();
    if (f === "del") delEl();
    if (f === "lock") mutate((x) => { if (x.locked) delete x.locked; else x.locked = true; });
    if (f === "pos") posMenu(t);
    if (f === "memo") openMemo({ element: el.id });
  }

  // ---------------------------------------------------------------- 오른쪽 클릭 메뉴
  function ctxMenu(e) {
    if (S.mode !== "edit") return;
    const node = e.target.closest("#host .rs-el"); if (!node) return;
    e.preventDefault(); select(node.dataset.id);
    const el = selEl(), lk = el && el.locked;
    openMenu({ x: e.clientX, y: e.clientY }, [
      { label: "복사", key: "Ctrl+C", act: () => { S.clip = clone(el); toast("요소 복사"); } },
      { label: "잘라내기", key: "Ctrl+X", disabled: lk, act: () => { S.clip = clone(el); delEl(); } },
      { label: "붙여넣기", key: "Ctrl+V", disabled: !S.clip, act: () => dupEl(S.clip) },
      { label: "복제", key: "Ctrl+D", act: () => dupEl() },
      { label: "삭제", key: "Delete", disabled: lk, act: () => delEl() }, "-",
      { label: "앞으로 가져오기", key: "Ctrl+]", act: () => zorder("fwd") }, { label: "뒤로 보내기", key: "Ctrl+[", act: () => zorder("bwd") },
      { label: "맨 앞으로", key: "Alt+Ctrl+]", act: () => zorder("front") }, { label: "맨 뒤로", key: "Alt+Ctrl+[", act: () => zorder("back") }, "-",
      { label: "글자 편집", key: "Enter", act: () => startEdit(el) },
      { label: "이 요소에 요청 메모", act: () => openMemo({ element: el.id }) },
    ]);
  }

  // ---------------------------------------------------------------- PPT 렌더 미리보기 · 내보내기
  async function loadPngs() { const r = await api("GET", `/api/render/${S.id}`); S.pngs = r.ok ? r.data.slides : []; }
  function renderPng() {
    if (!S.preview) return;
    const u = S.pngs[S.cur];
    $("#pngWrap").innerHTML = u ? `<img src="${u}" alt="">` : `<div class="empty">아직 렌더 없음 — "다시 렌더"</div>`;
    const stale = S.renderAt && S.deck && S.deck.updated && new Date(S.deck.updated).getTime() > S.renderAt;
    $("#pngInfo").textContent = u ? (stale ? "· 렌더 뒤에 편집됨 — 다시 렌더 필요" : "") : "";
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
    const fn = embed ? `${S.id}-fonts.pptx` : `${S.id}.pptx`;
    if (r.ok) {
      const a = $("#dl"); a.href = r.data.url; a.setAttribute("download", fn); a.style.display = ""; a.textContent = `⬇ ${fn}`;
      toast(embed ? `글꼴을 넣은 PPTX 를 만들었습니다 — 글꼴 ${(r.data.typefaces || []).join(", ")} · ${r.data.sizeKB}KB` : "PPTX 를 만들었습니다 — ⬇ 로 받기 (쓴 글꼴은 out/" + S.id + ".fonts.json 에 기록)", 5000);
    }
    else toast("내보내기 실패: " + (r.data && (r.data.error + " " + (r.data.log || "")) || r.status), 6000);
  }
  function exportMenu(btn) {
    openMenu(btn, [
      { icon: "📄", label: "PPTX 내보내기 (편집 가능한 도형)", act: () => doExport() },
      { icon: "🔤", label: "PPTX 내보내기 — 글꼴 포함 (PowerPoint 필요)", act: () => doExport(true) },
      { icon: "📋", label: "쓴 글꼴 기록 보기 (마지막 내보내기)", act: () => window.open(`/out/${S.id}.fonts.json`, "_blank") },
      { icon: "❓", label: "글꼴 받기·설치 안내", act: () => window.open("/studio/fonts.html", "_blank") },
      { icon: "🖼", label: S.preview ? "PowerPoint 렌더 미리보기 닫기" : "PowerPoint 렌더 미리보기 (나란히)", act: togglePreview },
      { icon: "↻", label: "PowerPoint 로 다시 렌더 (Windows)", act: () => { if (!S.preview) togglePreview(); doRender(); } },
    ], { right: true });
  }

  // ---------------------------------------------------------------- 속성 패널(전체 속성 — 고급)
  function colorOptions(cur, allowNone) {
    const T = S.tokens; let h = allowNone ? `<option value="">(없음)</option>` : ""; let found = !cur;
    for (const [g, names] of Object.entries(T.groups)) {
      h += `<optgroup label="${esc(g)}">` + names.map((n) => { if (n === cur) found = true; return `<option value="${n}"${n === cur ? " selected" : ""}>${n}  ${Render.color(n)}</option>`; }).join("") + `</optgroup>`;
    }
    if (!found && cur) h += `<option value="${esc(cur)}" selected>${esc(cur)} (직접)</option>`;
    return h;
  }
  function colorRow(label, key, el, allowNone) {
    const v = el[key] || "";
    return `<div class="row"><label>${label}</label><span class="sw" style="background:${v ? Render.color(v) : "transparent"}"></span><select class="colorSel" data-k="${key}" data-kind="color">${colorOptions(v, allowNone)}</select></div>`;
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

  function renderProps() {
    const P = $("#tab-props"), s = slide();
    if (!s) { P.innerHTML = ""; return; }
    const el = selEl();
    const list = `<div class="sec"><h3>요소 (${s.elements.length}) — 가려진 요소도 여기서 선택</h3><div class="ellist">${s.elements.map((e) => `<div data-sel="${esc(e.id)}" class="${e.id === S.sel ? "on" : ""}">${esc(elLabel(e))}${e.locked ? " 🔒" : ""}</div>`).join("")}</div></div>`;
    if (!el) {
      P.innerHTML = `<div class="sec"><h3>슬라이드 ${S.cur + 1} · ${esc(s.id)} · 레이아웃 ${esc(s.layout || "-")}</h3>
        <div class="row"><label>배경</label><select class="colorSel" data-slide="bg">${colorOptions(s.bg || "surface")}</select></div>
        <div class="hint">요소를 누르면 위 서식 줄과 여기서 고칠 수 있다. 색은 토큰 이름으로 고른다(색의 의미 유지).</div></div>${list}`;
      return;
    }
    let h = `<div class="sec"><h3>${esc(TYPE_KO[el.type] || el.type)} · ${esc(el.id)}</h3>`;
    if (isLine(el)) h += `<div class="row">${["x1", "y1", "x2", "y2"].map((k) => `<label style="width:auto">${k}</label><input type="number" data-k="${k}" value="${el[k]}">`).join("")}</div>`;
    else h += `<div class="row"><label style="width:auto">x</label><input type="number" data-k="x" value="${el.x}"><label style="width:auto">y</label><input type="number" data-k="y" value="${el.y}"></div>
      <div class="row"><label style="width:auto">w</label><input type="number" data-k="w" value="${el.w}"><label style="width:auto">h</label><input type="number" data-k="h" value="${el.h}"></div>`;
    h += `<div class="row"><label>순서</label><button class="chip sm" data-z="front">맨 앞</button><button class="chip sm" data-z="back">맨 뒤</button>
      <label style="width:auto;margin-left:6px"><input type="checkbox" data-k="locked" ${el.locked ? "checked" : ""}> 잠금</label></div></div>`;
    if (TEXTY.has(el.type)) {
      h += `<div class="sec"><h3>글자 — **굵게** · ==강조== · [[토큰|색 글자]] · {page}</h3><textarea data-k="text" style="min-height:70px;font-family:var(--font);font-size:13px">${esc(el.text || "")}</textarea>
        ${num("크기(px)", "size", el)}<div class="hint">PPT 글자 크기 = px × 0.75 pt</div>
        ${seg("굵게", "bold", { bold: el.bold === undefined ? (el.type === "pill" ? "1" : "0") : (el.bold ? "1" : "0") }, [["0", "보통"], ["1", "굵게"]])}
        ${seg("정렬", "align", el, [["left", "왼쪽"], ["center", "가운데"], ["right", "오른쪽"]], el.type === "pill" || el.type === "ellipse" ? "center" : "left")}
        ${seg("세로", "valign", el, [["top", "위"], ["middle", "가운데"], ["bottom", "아래"]], el.type === "text" ? "top" : "middle")}
        ${seg("글꼴", "font", el, [["body", "본문"], ["mono", "고정폭"]], "body")}
        ${num("줄 높이", "lineHeight", el, 0.05)}${colorRow("글자색", "color", el)}</div>`;
    }
    if (["rect", "ellipse", "pill", "text", "plan"].includes(el.type)) {
      h += `<div class="sec"><h3>면</h3>${colorRow("채우기", "fill", el, el.type === "text")}
        ${el.type !== "ellipse" && el.type !== "pill" ? `<div class="row"><label>모서리</label><select data-k="radius">${["", "r-s", "r-m", "r-l", "r-full"].map((r) => `<option value="${r}"${(el.radius || "") === r ? " selected" : ""}>${r || "없음"}</option>`).join("")}${typeof el.radius === "number" ? `<option selected value="${el.radius}">${el.radius}px</option>` : ""}</select></div>` : ""}
        ${colorRow("테두리", "stroke", el, true)}</div>`;
    }
    if (el.type === "image") h += `<div class="sec"><h3>그림</h3><div class="row"><label>경로</label><input type="text" data-k="src" value="${esc(el.src)}"></div><div class="hint">assetRoot 기준 경로. 모서리 핸들은 비율 유지.</div></div>`;
    if (isLine(el)) h += `<div class="sec"><h3>선</h3>${colorRow("색", "color", el)}${num("두께(px)", "width", el, 0.5)}
        ${seg("머리", "head", el, [["none", "없음"], ["end", "끝"], ["start", "시작"], ["both", "양쪽"]], el.type === "arrow" ? "end" : "none")}
        ${seg("점선", "dash", el, [["solid", "실선"], ["dash", "파선"], ["dot", "점선"]], "solid")}</div>`;
    if (el.type === "code") h += `<div class="sec"><h3>코드 — DBeaver 라이트 색, 줄 번호 필수</h3><textarea data-k="text" style="min-height:160px">${esc(el.text || "")}</textarea>
        ${seg("언어", "lang", el, [["sql", "SQL"], ["python", "Python"]], "sql")}
        ${num("크기(px)", "size", el)}${num("줄 높이", "lineHeight", el, 0.05)}${num("시작 번호", "start", el)}
        <div class="row"><label>강조 줄</label><input type="text" data-list="focus" value="${esc((el.focus || []).join(", "))}" placeholder="예: 1, 9"></div>
        <div class="row"><label>발췌</label><input type="text" data-list="show" value="${esc(showToText(el.show))}" placeholder="예: 2, 13-24 (비우면 전체)"></div>
        <div class="row"><button class="chip sm" data-fit="code">높이를 줄 수에 맞추기</button><span class="hint">표시 ${Render.codeLines(el).length}줄 (15~18줄 이내 권장)</span></div></div>`;
    if (el.type === "plan") h += `<div class="sec"><h3>실행계획 원문 — [[값]] = 경고 강조, [[ok:값]] = 개선 강조 (폭 불변)</h3><textarea data-k="text" style="min-height:180px">${esc(el.text || "")}</textarea>
        ${num("크기(px)", "size", el, 0.5)}${num("줄 높이", "lineHeight", el, 0.05)}</div>`;
    if (el.type === "bullets") h += `<div class="sec"><h3>글머리 — 줄마다 항목, 앞에 공백 두 칸 = 하위 항목</h3><textarea data-bul="1" style="min-height:140px;font-family:var(--font);font-size:13px">${esc(bulletsToText(el.items))}</textarea>
        ${num("크기(px)", "size", el)}${num("하위 크기", "subSize", el)}${num("줄 높이", "lineHeight", el, 0.05)}${num("항목 간격", "gap", el)}
        ${colorRow("점 색", "dot", el)}${colorRow("글자색", "color", el)}${colorRow("하위 글자색", "subColor", el)}</div>`;
    if (el.type === "table") h += `<div class="sec"><h3>표 — 줄 = 행, 칸은 " | " 로 구분 (첫 행 = 머리)</h3><textarea data-tbl="1" style="min-height:140px">${esc(tableToText(el.rows))}</textarea>
        <div class="row"><label>열 비율</label><input type="text" data-list="colW" value="${esc((el.colW || []).join(", "))}"></div>
        ${num("크기(px)", "size", el)}${colorRow("머리 면", "headFill", el)}${colorRow("머리 글자", "headColor", el)}</div>`;
    if (el.type === "plan-table") h += `<div class="sec"><h3>실행계획 표</h3><div class="hint">rows[].cells · depth(들여쓰기) · hl({열 번호: "warn"|"ok"}) · note(오른쪽 설명) — 아래 JSON 에서 고친다.</div></div>`;
    h += `<div class="sec"><h3>요소 JSON (고급)</h3><textarea id="elJson" style="min-height:120px">${esc(JSON.stringify(el, null, 1))}</textarea>
      <div class="row"><button class="chip sm" id="applyJson">JSON 적용</button><button class="chip sm" data-act="dupEl">복제 (Ctrl+D)</button><button class="chip sm" data-act="delEl">삭제 (Del)</button>
      <button class="chip sm" data-act="reqEl">이 요소에 요청</button></div></div>`;
    P.innerHTML = h + list;
  }
  function setProp(el, k, v) {
    if (["x", "y", "w", "h", "x1", "y1", "x2", "y2", "size", "subSize", "lineHeight", "width", "gap", "start"].includes(k)) { if (v === "" || v == null) delete el[k]; else el[k] = +v; }
    else if (k === "locked") { if (v) el.locked = true; else delete el.locked; }
    else if (k === "bold") el.bold = v === "1";
    else if (v === "" && ["fill", "stroke", "radius"].includes(k)) delete el[k];
    else el[k] = v;
    if (isLine(el)) Object.assign(el, Render.lineBox(el));
  }
  function onPropChange(e) {
    const t = e.target, el = selEl(), s = slide();
    if (t.dataset.slide === "bg") { snapshot(); s.bg = t.value; afterChange(); return; }
    if (!el || t.id === "elJson") return;
    snapshot();
    if (t.dataset.k) setProp(el, t.dataset.k, t.type === "checkbox" ? t.checked : t.value);
    else if (t.dataset.list) {
      if (t.dataset.list === "show") { const sh = textToShow(t.value); if (sh.length) el.show = sh; else delete el.show; }
      else { const a = t.value.split(/[,\s]+/).filter(Boolean).map(Number).filter((x) => !isNaN(x)); if (a.length) el[t.dataset.list] = a; else delete el[t.dataset.list]; }
    } else if (t.dataset.bul) el.items = textToBullets(t.value);
    else if (t.dataset.tbl) el.rows = textToTable(t.value);
    afterChange();
  }
  function onPropClick(e) {
    const b = e.target.closest("button, [data-sel]"); if (!b) return;
    const el = selEl(), s = slide();
    if (b.dataset.sel) { select(b.dataset.sel); return; }
    const sg = b.closest(".seg");
    if (sg && el) { snapshot(); setProp(el, sg.dataset.k, b.dataset.v); afterChange(); return; }
    if (b.dataset.z && el) { zorder(b.dataset.z); return; }
    if (b.dataset.fit === "code" && el) { snapshot(); el.h = Math.round(24 + Render.codeLines(el).length * (el.size || 15) * (el.lineHeight || 1.6)); afterChange(); return; }
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
  function renderReqs() {
    const R = $("#tab-reqs"), s = slide(); if (!s) return;
    const open = S.reqs.filter((r) => r.status !== "done").length;
    const c = $("#reqCnt"); c.textContent = open; c.style.display = open ? "" : "none";
    const list = S.reqs.filter((r) => !S.reqOnlySlide || r.slide === s.id);
    const idx = (sid) => S.deck.slides.findIndex((x) => x.id === sid) + 1;
    const drafts = S.reqs.filter((r) => r.status === "draft").length;
    R.innerHTML = `<div class="sec"><h3>Claude 에게 요청</h3>
      <div class="hint">◎ <b>선택</b> 모드에서 요소를 누르거나 ✐ <b>그리기</b> 모드에서 영역을 그려 메모를 단 뒤, 아래 바의 <b>보내기</b>로 한꺼번에 보낸다. 슬라이드 전체 요청은 여기에.</div>
      <textarea id="reqText" data-key="${esc(S.id + "/" + s.id)}" style="min-height:60px;font-family:var(--font);font-size:13px" placeholder="슬라이드 ${S.cur + 1} 전체에 대한 요청 — 예: 이 표를 두 장으로 나눠 줘 (Enter = 남기기, Shift+Enter = 줄바꿈)">${esc(typed(S.id + "/" + s.id))}</textarea>
      <div class="row"><button class="chip sm primary" id="reqAdd">메모 남기기</button>${drafts ? `<button class="chip sm" id="reqSend">초안 ${drafts}개 보내기</button>` : ""}</div>
      <div class="hint">${S.session && S.session.connected ? "세션 연결됨 — 보낸 요청은 바로 전달된다" : "세션 연결 없음 — 보낸 요청은 저장되고, 세션이 감시를 시작하면 전달된다"}</div></div>
      <div class="row"><span class="seg" id="reqFilter"><button data-v="1" class="${S.reqOnlySlide ? "on" : ""}">이 슬라이드</button><button data-v="0" class="${S.reqOnlySlide ? "" : "on"}">전체 (${S.reqs.length})</button></span></div>
      ${list.length ? list.slice().reverse().map((r) => `<div class="req ${r.status === "done" ? "done" : ""}" data-rid="${esc(r.id)}">
        <div class="meta"><span class="st ${esc(r.status || "open")}">${ST[r.status] || "대기"}</span>
          <a href="#" data-goto="${esc(r.slide)}" data-el="${esc(r.element || "")}">슬라이드 ${idx(r.slide) || "?"}${r.element ? " · " + esc(r.element) : ""}${r.region ? " · 영역" : ""}</a><span>${esc((r.created || "").replace("T", " "))}</span></div>
        <div class="txt">${esc(r.text)}</div>${r.reply ? `<div class="reply"><b>Claude</b> ${esc(r.reply)}</div>` : ""}
        <div class="acts">${r.status === "draft" ? "" : `<button class="chip sm" data-rs="${r.status === "done" ? "open" : "done"}">${r.status === "done" ? "다시 열기" : "완료로 표시"}</button>`}<button class="chip sm" data-rdel="1">삭제</button></div></div>`).join("") : `<div class="hint">요청이 없다.</div>`}`;
  }
  async function onReqClick(e) {
    const b = e.target.closest("button, a"); if (!b) return;
    if (b.id === "reqAdd") {
      const t = $("#reqText").value.trim(); if (!t) return;
      const r = await api("POST", `/api/requests/${S.id}`, { action: "add", status: "draft", slide: slide().id, element: null, text: t });
      if (r.ok) { keep(S.id + "/" + slide().id, ""); S.reqs = r.data; afterReqs(); toast("메모를 남겼습니다 — 아래 바에서 보내기"); }
      return;
    }
    if (b.id === "reqSend") { await sendDrafts(); return; }
    if (b.closest("#reqFilter")) { S.reqOnlySlide = b.dataset.v === "1"; renderReqs(); return; }
    const card = b.closest(".req"); if (!card) return;
    const rid = card.dataset.rid;
    if (b.dataset.goto !== undefined) {
      e.preventDefault();
      const i = S.deck.slides.findIndex((x) => x.id === b.dataset.goto);
      if (i >= 0) { S.cur = i; S.sel = b.dataset.el && elById(b.dataset.el, S.deck.slides[i]) ? b.dataset.el : null; renderAll(); revealThumb(S.cur); }
      return;
    }
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
  function renderSession(st) {
    S.session = st;
    const c = $("#sessChip"); if (!c) return;
    c.className = "chip sm " + (st.connected ? (st.working ? "busy" : "on") : "off");
    c.innerHTML = `<span class="dot"></span>` + (st.connected ? (st.working ? `세션 처리 중 ${st.working}` : "세션 연결됨") : "세션 연결 없음");
    c.title = st.connected ? `${st.label || "Claude Code"} · 마지막 확인 ${st.last_seen} (${st.age}초 전) · 대기 ${st.open} · 처리 중 ${st.working}`
      : `요청 감시가 실행 중이 아니다${st.last_seen ? ` — 마지막 확인 ${st.last_seen}` : ""}. 세션에서 watch_requests.py --stream 을 Monitor 로 실행하면 연결된다`;
  }
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
    H.innerHTML = `<div class="sec"><h3>기록 — ${esc(S.id)}</h3><div class="hint">편집기가 저장할 때마다(최근 50개)와 build 로 덮어쓰기 전에 남긴 자동 백업이다. 되돌리면 지금 상태도 기록에 남으므로 다시 돌아올 수 있다(Ctrl+Z 도 가능).</div></div>
      ${list.length ? list.map((h) => `<div class="hist"><span class="k ${h.kind}">${h.kind === "build" ? "빌드 전" : "저장 전"}</span><span>${esc(h.at.replace("T", " "))}</span><span class="sp"></span>
        <button class="chip sm" data-hf="${esc(h.file)}">되돌리기</button></div>`).join("") : `<div class="hint">기록이 없다.</div>`}`;
  }
  async function onHistClick(e) {
    const b = e.target.closest("[data-hf]"); if (!b) return;
    if (!confirm(`${b.closest(".hist").children[1].textContent} 시점으로 되돌릴까요? (지금 상태는 기록에 남습니다)`)) return;
    const r = await api("GET", `/api/history/${S.id}?f=${encodeURIComponent(b.dataset.hf)}`);
    if (!r.ok || !r.data || !r.data.slides) { toast("기록을 읽지 못했습니다"); return; }
    snapshot(); S.deck = r.data; S.deck.id = S.id; S.sel = null; afterChange(true); await save(true);
    toast("되돌렸습니다 (Ctrl+Z 로 취소 가능)"); loadHist();
  }

  // ---------------------------------------------------------------- 발표
  function present(fromCur) {
    const P = $("#present"); P.classList.add("show");
    S.pIdx = fromCur ? S.cur : 0; S.pStart = Date.now();
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
  }
  function endPresent() { $("#present").classList.remove("show"); if (document.fullscreenElement) document.exitFullscreen().catch(() => {}); goSlide(S.pIdx); }
  function presentKey(e) {
    const k = e.key;
    if (k === "Escape") { endPresent(); return; }
    if (["ArrowRight", "ArrowDown", "PageDown", " ", "Enter"].includes(k)) S.pIdx = Math.min(S.deck.slides.length - 1, S.pIdx + 1);
    else if (["ArrowLeft", "ArrowUp", "PageUp", "Backspace"].includes(k)) S.pIdx = Math.max(0, S.pIdx - 1);
    else if (k === "Home") S.pIdx = 0; else if (k === "End") S.pIdx = S.deck.slides.length - 1;
    else if (k.toLowerCase() === "n") $("#present").classList.toggle("notes");
    else return;
    e.preventDefault(); renderPresent();
  }

  // ---------------------------------------------------------------- 선택·끌기·크기 조절
  function select(id) { S.sel = id; drawSel(); renderProps(); renderFtb(); }
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
      const node = e.target.closest("#host .rs-el");
      if (!node) { select(null); closeMemo(); return; }
      select(node.dataset.id); openMemo({ element: node.dataset.id }); e.preventDefault(); return;
    }
    if (hd) { const el = selEl(); if (!el) return; drag = { mode: "resize", h: hd.dataset.h, el, orig: clone(el), p0: p, moved: false, before: deckJson() }; e.preventDefault(); return; }
    const node = e.target.closest("#host .rs-el");
    if (!node) { select(null); return; }
    const id = node.dataset.id; if (S.sel !== id) select(id);
    const el = selEl(); if (!el || el.locked) return;
    drag = { mode: "move", el, orig: clone(el), p0: p, moved: false, before: deckJson() };
    e.preventDefault();
  }
  function onMove(e) {
    if (S.pan) { const vp = $("#vpEdit"); vp.scrollLeft = S.pan.l - (e.clientX - S.pan.x); vp.scrollTop = S.pan.t - (e.clientY - S.pan.y); return; }
    if (S.drawing && S.drawing.p0) { drawMove(e); return; }
    if (!drag) return;
    const p = toSlide(e), dx = p.x - drag.p0.x, dy = p.y - drag.p0.y, free = e.shiftKey, el = drag.el, o = drag.orig;
    if (!drag.moved && Math.hypot(dx, dy) * scale < 3) return;
    drag.moved = true;
    if (drag.mode === "move") {
      const b0 = boxOf(o), nx = snap(b0.x + dx, free), ny = snap(b0.y + dy, free), mx = nx - b0.x, my = ny - b0.y;
      if (isLine(el)) { el.x1 = o.x1 + mx; el.x2 = o.x2 + mx; el.y1 = o.y1 + my; el.y2 = o.y2 + my; Object.assign(el, Render.lineBox(el)); } else { el.x = nx; el.y = ny; }
    } else if (drag.h === "p1" || drag.h === "p2") {
      const k = drag.h === "p1" ? ["x1", "y1"] : ["x2", "y2"];
      el[k[0]] = snap(o[k[0]] + dx, free); el[k[1]] = snap(o[k[1]] + dy, free); Object.assign(el, Render.lineBox(el));
    } else {
      let x1 = o.x, y1 = o.y, x2 = o.x + o.w, y2 = o.y + o.h; const h = drag.h;
      if (h.includes("w")) x1 = snap(o.x + dx, free); if (h.includes("e")) x2 = snap(o.x + o.w + dx, free);
      if (h.includes("n")) y1 = snap(o.y + dy, free); if (h.includes("s")) y2 = snap(o.y + o.h + dy, free);
      if (el.type === "image" && h.length === 2) { const ratio = o.w / o.h, w = Math.max(4, x2 - x1), hh = w / ratio; if (h.includes("n")) y1 = y2 - hh; else y2 = y1 + hh; }
      el.x = Math.round(Math.min(x1, x2 - 4)); el.y = Math.round(Math.min(y1, y2 - 4)); el.w = Math.round(Math.max(4, x2 - x1)); el.h = Math.round(Math.max(4, y2 - y1));
    }
    renderElementDom(el); drawSel(); renderMarks();
  }
  function onUp() {
    if (S.pan) { S.pan = null; document.body.classList.remove("panning"); return; }
    if (S.drawing && S.drawing.p0) { drawUp(); return; }
    if (!drag) return;
    const d = drag; drag = null;
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
    const mono = el.font === "mono" || el.type === "code" || el.type === "plan" || el.type === "table";
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
  function delEl() { const s = slide(), el = selEl(); if (!el || el.locked) return; snapshot(); s.elements.splice(s.elements.indexOf(el), 1); S.sel = null; afterChange(); }
  function dupEl(src) {
    const s = slide(), el = src || selEl(); if (!el) return;
    snapshot(); const c = clone(el); c.id = newElId(s); delete c.locked;
    if (isLine(c)) { c.x1 += 16; c.x2 += 16; c.y1 += 16; c.y2 += 16; Object.assign(c, Render.lineBox(c)); } else { c.x += 16; c.y += 16; }
    s.elements.push(c); S.sel = c.id; afterChange();
  }
  function addEl(kind) {
    const s = slide(); if (!s) return;
    const part = S.deck.part || "day1";
    const base = {
      text: { type: "text", x: 480, y: 320, w: 320, h: 40, text: "새 글자", size: 20, color: "on-surface", lineHeight: 1.4 },
      pill: { type: "pill", x: 560, y: 340, w: 120, h: 30, text: "칩", size: 14, fill: `${part}-container`, color: `on-${part}-container`, bold: true },
      rect: { type: "rect", x: 480, y: 280, w: 320, h: 160, fill: "surface-container", radius: "r-m" },
      ellipse: { type: "ellipse", x: 600, y: 320, w: 80, h: 80, fill: part, color: "white", text: "", size: 20, bold: true },
      arrow: { type: "arrow", x1: 480, y1: 360, x2: 800, y2: 360, color: "on-surface", width: 2, head: "end" },
      code: { type: "code", x: 64, y: 184, w: 640, h: 0, text: "SELECT d.item_cd\nFROM   trx_demand d\nWHERE  d.tenant_id = :t;", lang: "sql", size: 14, lineHeight: 1.6, radius: "r-m" },
      table: { type: "table", x: 64, y: 184, w: 640, h: 96, rows: [["열 1", "열 2"], ["값", "값"]], colW: [1, 1], size: 16, headFill: `${part}-container`, headColor: `on-${part}-container`, rule: "surface-container-high" },
      image: { type: "image", x: 560, y: 320, w: Math.round(40 * (S.brand.logoRatio || 765 / 237)), h: 40, src: S.brand.logo || "assets/brand/logo.png" },
    }[kind];
    if (!base) return;
    snapshot();
    const el = { id: newElId(s), ...base };
    if (isLine(el)) Object.assign(el, Render.lineBox(el));
    if (el.type === "code") el.h = Math.round(24 + Render.codeLines(el).length * el.size * el.lineHeight);
    s.elements.push(el); S.sel = el.id; afterChange();
  }
  function addMenu(btn) {
    openMenu(btn, [["text", "T", "글자"], ["pill", "◖◗", "칩"], ["rect", "▭", "상자"], ["ellipse", "◯", "원"], ["arrow", "→", "화살표"], ["table", "▦", "표 (2×2)"], ["code", "{ }", "코드"], ["image", "🖼", "로고"]]
      .map(([k, i, l]) => ({ icon: i, label: l, act: () => addEl(k) })));
  }
  function goSlide(i) { if (!S.deck) return; S.cur = Math.max(0, Math.min(S.deck.slides.length - 1, i)); S.sel = null; S.chkBox = S.chkBox && S.chkBox.slide === slide().id ? S.chkBox : null; closeMemo(); renderAll(); ensureThumbVisible(S.cur); }
  function dupSlide(i) { snapshot(); const c = clone(S.deck.slides[i]); c.id = newSlideId(); S.deck.slides.splice(i + 1, 0, c); S.cur = i + 1; S.sel = null; afterChange(true); }
  function delSlide(i) {
    if (S.deck.slides.length <= 1) return toast("마지막 슬라이드는 지울 수 없습니다");
    if (!confirm(`슬라이드 ${i + 1}을(를) 지울까요? (Ctrl+Z 로 되돌리기 가능)`)) return;
    snapshot(); S.deck.slides.splice(i, 1); S.sel = null; afterChange(true);
  }
  // ---------------------------------------------------------------- 슬라이드 추가 창 — 목적별 유형(studio/slide_types.json) 또는 레이아웃
  const AD = { tab: "type", group: "", data: null, layouts: null };
  async function openAddDlg() {
    $("#addDlg").classList.add("show"); $("#adQ").value = "";
    if (!AD.data) {
      $("#adBody").innerHTML = `<div class="hint">유형을 불러오는 중…</div>`;
      const r = await api("GET", `/api/slidetypes?part=${encodeURIComponent(S.deck.part || "day1")}`);
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
    $("#adGroups").innerHTML = [["", "전체"], ...d.groups.map((g) => [g.id, g.label])].map(([id, l]) =>
      `<button data-adgroup="${id}" class="${AD.group === id ? "on" : ""}">${esc(l)} <small>${id ? d.types.filter((t) => t.group === id).length : d.types.length}</small></button>`).join("");
    const show = d.types.filter((t) => t.slide && (!AD.group || t.group === AD.group) && (!q || `${t.label} ${t.purpose} ${t.layout} ${t.layoutLabel}`.toLowerCase().includes(q)));
    $("#adBody").innerHTML = d.groups.filter((g) => show.some((t) => t.group === g.id)).map((g) => `<div class="ad-gt">${esc(g.label)}<small>${esc(g.desc)}</small></div>
      <div class="ad-grid">${show.filter((t) => t.group === g.id).map((t) => `<button class="ad-card" data-adtype="${esc(t.id)}" title="${esc(t.purpose)}${t.image ? `\n이미지: ${esc(t.image)}` : ""}">
        <div class="ad-vp">${Render.renderSlide(t.slide, 1)}</div><b>${esc(t.label)}</b><small>${esc(t.purpose)}</small><span class="lay">${esc(t.layout)}${t.image ? " · 사진 자리" : ""}</span></button>`).join("")}</div>`).join("")
      || `<div class="hint">찾는 유형이 없습니다.</div>`;
    requestAnimationFrame(fitAdd);
  }
  function insertSlide(s) {
    snapshot(); S.deck.slides.splice(S.cur + 1, 0, s); S.cur += 1; S.sel = null; afterChange(true); closeAddDlg();
    toast("슬라이드를 추가했습니다 — 예시 내용을 고쳐 쓰세요 (Ctrl+Z 로 되돌리기)");
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
      { label: "슬라이드 복제", act: () => dupSlide(i) }, { label: "아래에 새 슬라이드…", act: () => openAddDlg() },
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
    setTimeout(() => { fitStage(); fitThumbs(); }, 0);
  }
  function toggleRight() { const n = !document.body.classList.contains("noright"); document.body.classList.toggle("noright", n); LS.set("noright", n ? "1" : "0"); setTimeout(() => { fitStage(); fitThumbs(); }, 0); }
  const HELP = [
    ["모드", "<kbd>E</kbd> 편집 · <kbd>M</kbd> 선택(요청 메모) · <kbd>D</kbd> 그리기(영역 메모)"],
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
    if (ctrl && kl === "s") { e.preventDefault(); save(); return; }
    if (k === "F5") { e.preventDefault(); present(e.shiftKey); return; }
    if (ctrl && k === "\\") { e.preventDefault(); toggleRight(); return; }
    if (ctrl && (k === "=" || k === "+")) { e.preventDefault(); setZoom(scale * 100 * 1.15); return; }
    if (ctrl && k === "-") { e.preventDefault(); setZoom(scale * 100 / 1.15); return; }
    if (ctrl && k === "0") { e.preventDefault(); setZoom(null); return; }
    if (ctrl && k === "1") { e.preventDefault(); setZoom(100); return; }
    if (inField) return;
    if (k === "Escape") { if (S.memo) { closeMemo(); return; } closeMenu(); select(null); return; }
    if (k === " " && !e.repeat) { spaceDown = true; document.body.classList.add("panning"); e.preventDefault(); return; }
    if (k === "?") { showHelp(); return; }
    if (!ctrl && !e.altKey) { if (kl === "e") return setMode("edit"); if (kl === "m") return setMode("pick"); if (kl === "d") return setMode("draw"); }
    if (ctrl && kl === "z" && !e.shiftKey) { e.preventDefault(); undo(); return; }
    if (ctrl && (kl === "y" || (kl === "z" && e.shiftKey))) { e.preventDefault(); redo(); return; }
    if (ctrl && kl === "d") { e.preventDefault(); dupEl(); return; }
    if (ctrl && kl === "c" && selEl()) { S.clip = clone(selEl()); toast("요소 복사"); return; }
    if (ctrl && kl === "x" && selEl() && !selEl().locked) { S.clip = clone(selEl()); delEl(); return; }
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
    if (k === "Enter" || k === "F2") { e.preventDefault(); startEdit(el); return; }
    const d = e.shiftKey ? GRID : 1, mv = { ArrowLeft: [-d, 0], ArrowRight: [d, 0], ArrowUp: [0, -d], ArrowDown: [0, d] }[k];
    if (mv && !el.locked) {
      e.preventDefault(); snapshot();
      if (isLine(el)) { el.x1 += mv[0]; el.x2 += mv[0]; el.y1 += mv[1]; el.y2 += mv[1]; Object.assign(el, Render.lineBox(el)); } else { el.x += mv[0]; el.y += mv[1]; }
      afterChange();
    }
  }

  // ---------------------------------------------------------------- 시작
  async function loadFonts() { const r = await api("GET", "/api/fonts"); S.fonts = r.ok ? r.data : { presets: [], current: "" }; renderFontChip(); }
  async function setFonts(name) {
    const r = await api("POST", "/api/fonts", { preset: name });
    if (!r.ok) { toast("글꼴 세트를 바꾸지 못했습니다"); return; }
    await applyFonts(r.data);
    toast(`글꼴 세트: ${name} — PPTX 는 다음 내보내기부터 적용`, 4000);
  }
  async function applyFonts(info) {  // 글꼴 정보·토큰을 다시 읽어 화면에 적용
    S.fonts = info; renderFontChip();
    S.tokens = await (await fetch("tokens.json", { cache: "no-store" })).json();
    Render.setTokens(S.tokens); $("#rs-css").textContent = Render.css();
    if (document.fonts && document.fonts.ready) await document.fonts.ready;
    if (S.deck) { renderAll(); revealThumb(S.cur); }
    if ($("#fontDlg").classList.contains("show")) showFonts();
  }
  // 작업 공간이 직접 지정한 글꼴 세트(nexa-slide.json fontPresets)를 쓰면 머리줄에 칩으로 알린다 — 누르면 글꼴 창
  function renderFontChip() {
    const f = S.fonts, c = $("#fontChip"); if (!c) return;
    const on = !!(f && f.source === "workspace");
    c.style.display = on ? "" : "none";
    if (on) { c.textContent = `글꼴 · ${(f.fonts.body || {}).latin || f.current} · 작업 공간`; c.title = `작업 공간이 직접 지정한 글꼴 세트 "${f.current}" — 눌러서 확인·수정`; }
  }
  const ROLE = { body: "본문", heading: "제목", mono: "코드" };
  function showFonts() {
    const f = S.fonts || { presets: [], fonts: {}, files: [] }, cur = f.current, ws = f.source === "workspace";
    const def = ws ? f.workspacePresets[cur] : f.fonts;  // 템플릿 세트면 지금 값으로 새 작업 공간 세트를 시작
    const files = f.files || [];
    $("#fontDlg .box").innerHTML = `<div class="row" style="align-items:center;gap:8px"><h3 style="margin:0;flex:1">글꼴 — 지금 세트 <b>${esc(cur || "(템플릿 기본)")}</b>
        <span class="bd ${ws ? "chg" : ""}" style="font-size:12px">${ws ? "작업 공간 지정" : "템플릿 기본"}</span></h3><button class="chip sm" data-fd="close">닫기</button></div>
      <div class="hint">기본 세트(default·modern)는 엔진 템플릿에 있고, 회사 서체 같은 전용 글꼴은 이 작업 공간이 <code>nexa-slide.json</code> 의 <code>fontPresets</code> 와 <code>fonts/</code> 폴더로 관리합니다.
        글꼴은 되도록 무료 글꼴로 — <a href="/studio/fonts.html" target="_blank">글꼴 받기·설치 안내 ↗</a> (쓰는 글꼴이 무료·시스템 기본·전용 중 무엇인지 확인)</div>
      <h4>역할별 글꼴</h4><table>${["body", "heading", "mono"].map((k) => { const v = (f.fonts || {})[k] || {}; const ms = v.measure || {};
        return `<tr><td><b>${ROLE[k]}</b> <code>${k}</code></td><td>${esc(v.latin || "-")} / ${esc(v.ea || "-")}<div style="font-family:${esc(v.css || "inherit")};font-size:18px;margin-top:2px">가나다 ABC 123 — 견본 글자</div>
          <div class="hint">측정 ${esc(ms.regular || "-")} · ${esc(ms.bold || "-")}</div></td></tr>`; }).join("")}</table>
      <h4>작업 공간 글꼴 파일 <span class="hint" style="margin:0">${esc(f.fontsDir || "")}</span></h4>
      ${files.length ? `<table>${files.map((x) => `<tr><td><code>${esc(x.file)}</code></td><td>${esc(x.family)} ${esc(x.style)}</td><td>${x.installed ? "설치됨" : `<b style="color:#93000A">미설치</b>`}</td></tr>`).join("")}</table>
        ${files.some((x) => !x.installed) ? `<div class="hint">PowerPoint 에서도 쓰려면 설치: <code>python3 nexa.py install_fonts</code> (편집기는 설치 없이 이 파일을 씁니다)</div>` : ""}`
        : `<div class="hint">fonts/ 에 글꼴 파일이 없습니다. 전용 글꼴은 이 폴더에 .ttf·.otf 로 둡니다.</div>`}
      <h4>${ws ? `작업 공간 세트 <code>${esc(cur)}</code> 수정` : "작업 공간 세트 만들기 (지금 값에서 시작)"}</h4>
      <div class="hint">역할마다 <code>css</code>(화면 글꼴 목록) · <code>latin</code>·<code>ea</code>(PPTX 글꼴 이름 — 영문·한글) · <code>measure</code>(검사용 파일, fonts/ 또는 설치 폴더에서 찾음). 빠진 역할은 기본값.</div>
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
    await applyFonts(r.data); toast("작업 공간 글꼴 세트를 저장했습니다 — PPTX 는 다음 내보내기부터", 4000);
  }
  function moreMenu(btn) {
    const f = S.fonts || { presets: [] };
    openMenu(btn, [
      { h: "글꼴 세트 — 템플릿 기본" }, ...f.presets.filter((p) => p.source !== "workspace").map((p) => ({ label: `${p.name} — ${p.label}`, on: p.name === f.current, act: () => setFonts(p.name) })),
      ...(f.presets.some((p) => p.source === "workspace") ? [{ h: "글꼴 세트 — 작업 공간 지정(nexa-slide.json)" }, ...f.presets.filter((p) => p.source === "workspace").map((p) => ({ label: `${p.name} — ${p.label}`, on: p.name === f.current, act: () => setFonts(p.name) }))] : []),
      { label: "글꼴 설정 보기·수정…", act: showFonts }, "-",
      { h: `템플릿: ${S.template ? S.template.label : "-"}` },
      { label: "단축키 보기", key: "?", act: showHelp },
      { label: "편집기 화면 배치 초기화", act: () => { ["mode", "btab", "bfold", "noright", "railW"].forEach((k) => LS.set(k, "")); location.reload(); } },
    ], { right: true });
  }
  async function loadConfig() {
    const r = await api("GET", "/api/config"); if (!r.ok) return;
    if (r.data.mode === "hub") { location.replace("/studio/home.html"); return false; }  // 작업 공간 없음 → 시작 페이지
    S.brand = r.data.brand || {}; S.template = r.data.template || null;
    document.title = `${r.data.title} — nexa-slide`;
    $("#appTitle").textContent = r.data.title || "nexa-slide";
    $("#appTitle").title = `작업 공간 ${r.data.path} · 포트 ${r.data.port}${S.template ? ` · 템플릿 ${S.template.name}` : ""}`;
    if (S.brand.logo) { const l = $("#brandLogo"); l.src = "/" + S.brand.logo; l.alt = S.brand.name || ""; l.style.display = ""; l.onerror = () => (l.style.display = "none"); }
    if (S.brand.favicon) $("#favicon").href = "/" + S.brand.favicon;
  }
  async function switchDeck(id) { if (id === S.id) return; if (S.dirty) await save(); await loadDeck(id); }
  async function init() {
    if (window.NexaMenu) NexaMenu.mount($("#menuBtn"));
    if ((await loadConfig()) === false) return;
    S.tokens = await (await fetch("tokens.json", { cache: "no-store" })).json();
    Render.setTokens(S.tokens); $("#rs-css").textContent = Render.css();
    await loadFonts();
    const r = await api("GET", "/api/decks"); S.decks = r.ok ? r.data : [];
    if (LS.get("noright", "0") === "1") document.body.classList.add("noright");
    const rw = +LS.get("railW", 0); if (rw) document.documentElement.style.setProperty("--railW", rw + "px");
    setMode(["edit", "pick", "draw"].includes(S.mode) ? S.mode : "edit"); setTool("rect");
    setBtab(S.btab); if (LS.get("bfold", "0") === "1") toggleBottom();
    if (!S.decks.length) { location.replace("/studio/home.html"); return; }  // 작업할 덱이 없으면 시작 페이지
    const [hid, hn] = decodeURIComponent(location.hash.slice(1)).split("/");
    await loadDeck(S.decks.some((d) => d.id === hid) ? hid : S.decks[0].id);
    if (hn) { goSlide(+hn - 1); revealThumb(S.cur, true); }
    window.addEventListener("load", () => revealThumb(S.cur, true), { once: true });
    window.addEventListener("hashchange", async () => {
      const [h, n] = decodeURIComponent(location.hash.slice(1)).split("/");
      if (h && h !== S.id && S.decks.some((d) => d.id === h)) await switchDeck(h);
      const k = +n - 1; if (n && k !== S.cur && k >= 0) goSlide(k);
      revealThumb(S.cur, true);
    });

    // 머리줄
    $("#deckTabs").addEventListener("click", (e) => { const b = e.target.closest("[data-deck]"); if (b) switchDeck(b.dataset.deck); });
    $("#tab-chg").addEventListener("click", onChangesClick); renderChanges();
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
    $("#presentBtn").onclick = () => present(false);
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
    $("#chkBtn").onclick = () => { S.chkOnlySlide = true; setBtab("check"); renderCheck(); };
    $("#aiFixBtn").onclick = aiFix; $("#aiPolishBtn").onclick = aiPolish;
    // 서식 줄
    $("#ftb").addEventListener("click", onFtb); $("#ftb").addEventListener("change", onFtb);
    // 메모 팝오버 · 보낼 요청 바
    $("#memoTa").addEventListener("input", memoInput);
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
      if (e.target.id === "addSlide") return openAddDlg();
      const t = e.target.closest(".thumb"); if (!t) return;
      const i = +t.dataset.i, act = e.target.dataset.act;
      if (act === "dup") dupSlide(i); else if (act === "del") delSlide(i); else goSlide(i);
    });
    left.addEventListener("contextmenu", (e) => { const t = e.target.closest(".thumb"); if (t) thumbMenu(e, +t.dataset.i); });
    left.addEventListener("dragstart", onThumbDragStart); left.addEventListener("dragover", onThumbDragOver); left.addEventListener("drop", onThumbDrop);
    left.addEventListener("dragend", () => { dragFrom = -1; $$(".thumb").forEach((x) => x.classList.remove("drop-before", "drop-after")); });
    const split = $("#railSplit");
    split.addEventListener("pointerdown", (e) => {
      e.preventDefault(); const x0 = e.clientX, w0 = left.getBoundingClientRect().width;
      const mv = (ev) => { const w = Math.max(140, Math.min(420, w0 + ev.clientX - x0)); document.documentElement.style.setProperty("--railW", w + "px"); fitThumbs(); fitStage(); };
      const up = () => { window.removeEventListener("pointermove", mv); window.removeEventListener("pointerup", up); LS.set("railW", Math.round(left.getBoundingClientRect().width)); };
      window.addEventListener("pointermove", mv); window.addEventListener("pointerup", up);
    });
    split.addEventListener("dblclick", () => { document.documentElement.style.removeProperty("--railW"); LS.set("railW", ""); setTimeout(() => { fitThumbs(); fitStage(); }, 0); });
    // 캔버스
    const stage = $("#stage"), vp = $("#vpEdit");
    stage.addEventListener("pointerdown", onDown);
    vp.addEventListener("pointerdown", (e) => { if (e.target === vp || e.target.id === "stageWrap") { if (spaceDown || e.button === 1) onDown(e); else { select(null); closeMemo(); } } });
    window.addEventListener("pointermove", onMove); window.addEventListener("pointerup", onUp);
    stage.addEventListener("dblclick", (e) => { if (S.mode !== "edit") return; const n = e.target.closest("#host .rs-el"); if (n) { select(n.dataset.id); startEdit(selEl()); } });
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
    const P = $("#tab-props"); P.addEventListener("change", onPropChange); P.addEventListener("click", onPropClick);
    $("#tab-reqs").addEventListener("click", onReqClick);
    $("#tab-reqs").addEventListener("input", (e) => { if (e.target.id === "reqText") keep(e.target.dataset.key, e.target.value); });
    $("#tab-reqs").addEventListener("keydown", (e) => { // 슬라이드 요청 칸도 메모 팝오버처럼: Enter = 메모 남기기(초안), Shift+Enter = 줄바꿈
      if (e.target.id === "reqText" && e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); $("#reqAdd").click(); }
    });
    $("#tab-hist").addEventListener("click", onHistClick);
    $("#notesTa").addEventListener("input", onNotes);
    // 발표 · 도움말
    $("#present").addEventListener("click", (e) => { S.pIdx = Math.min(S.deck.slides.length - 1, S.pIdx + (e.clientX < innerWidth / 3 ? -1 : 1)); S.pIdx = Math.max(0, S.pIdx); renderPresent(); });
    document.addEventListener("fullscreenchange", () => { if (!document.fullscreenElement && $("#present").classList.contains("show")) endPresent(); });
    setInterval(() => { if ($("#present").classList.contains("show")) renderPresent(); }, 1000);
    $("#help").addEventListener("click", () => $("#help").classList.remove("show"));
    // 전역
    new ResizeObserver(() => fitStage()).observe(vp);
    document.addEventListener("keydown", onKey);
    document.addEventListener("keyup", (e) => { if (e.key === " ") { spaceDown = false; if (!S.pan) document.body.classList.remove("panning"); } });
    document.addEventListener("pointerdown", (e) => { if (!e.target.closest(".menu") && !e.target.closest("#ftb") && !e.target.closest("#addBtn,#exportBtn,#moreBtn")) closeMenu(); });
    window.addEventListener("resize", () => { fitStage(); fitThumbs(); if ($("#present").classList.contains("show")) renderPresent(); });
    window.addEventListener("beforeunload", (e) => { if (S.dirty) { save(); e.preventDefault(); e.returnValue = ""; } });
    setInterval(poll, 2000);
  }
  init().catch((e) => { console.error(e); setStatus("error", "오류"); toast("초기화 오류: " + e.message, 6000); });
})();
