/* nexa-slide 시트 - 오른쪽 패널의 속성·기록·변경 탭과 그림 메뉴(sheet.js 의 NexaSheet.x 를 쓴다). 편집기(studio.js)의 같은 탭을 시트에 맞춘 것.
   - 속성: 고른 셀·범위(값·수식, 표시 형식, 글꼴, 채우기, 맞춤, 메모, 열 너비·행 높이, 탭 눈금선) 또는 고른 그림(이름·위치·크기·대체 텍스트·순서)을 바로 고친다
   - 기록: 저장 전 자동 백업(/api/history) - 그 시점으로 되돌리기(원장에 action restore)
   - 변경: 서버 원장(/api/changes, docs/change-ledger.md) - 탭 = 장, 셀·그림 = 요소. 확인하지 않은 변경은 격자에 파란 점선
   - 그림 오른쪽 클릭: 복제·지우기·순서·원래 크기·이름·대체 텍스트·속성·요청
   모든 고치기는 x.mutate 로 - 실행 취소·저장·다시 계산이 같이 된다. */
(function () {
  "use strict";
  const N = () => window.NexaSheet, X = () => window.NexaSheet && window.NexaSheet.x;
  const $ = (s, r = document) => r.querySelector(s), $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  const P = { tab: "reqs", changes: [], recent: [], latest: 0, keep: 0, more: false, ver: null, filter: "all", info: false, shown: new Set(), hidden: new Set(), off: false, loaded: false, pend: false };

  // ---------------------------------------------------------------- 패널 탭
  function showTab(t) {
    P.tab = t; const x = X(); if (x) x.LS.set("sheetSideTab", t === "reqs" ? "" : t);
    $$("#sideTabs [data-stab]").forEach((b) => b.classList.toggle("on", b.dataset.stab === t));
    $$("#side .spanel").forEach((p) => p.classList.toggle("on", p.id === "sp-" + t));
    if (t === "props") renderProps(true);
    if (t === "hist") loadHist();
    if (t === "chg") { if (!P.loaded) loadChanges(); else renderChanges(); }
  }

  // ---------------------------------------------------------------- 속성
  const selDraws = () => { const x = X(), S = N().S, sh = x.sheet(); if (!S.drawSel || !S.drawSel.size) return []; return (sh.drawings || []).map((d, i) => [x.drawId(d, i), d, i]).filter(([id]) => S.drawSel.has(id)); };
  function renderProps(force) {
    if (P.tab !== "props" || !N() || !N().S.deck) return;
    const box = $("#sp-props");
    if (!force && box.contains(document.activeElement)) { P.pend = true; return; }  // 고치는 중 - 칸을 떠날 때 다시 그린다
    P.pend = false;
    box.innerHTML = selDraws().length ? drawPropsHtml() : cellPropsHtml();
    const pv = $("[data-p=prev]", box); if (pv) fmtPrev();
  }
  function cellPropsHtml() {
    const x = X(), S = N().S, sh = x.sheet(), g = x.clampRange(S.sel), k = x.key(S.cur.r, S.cur.c), o = N().effCell(sh.cells[k]), raw = x.cellObj(sh, k);
    const opt = (v, cur, label) => `<option value="${esc(v)}"${v === (cur || "") ? " selected" : ""}>${esc(label)}</option>`;
    const known = x.FMTS.some(([f]) => f === (o.fmt || ""));
    const tog = (t, html, title) => `<button data-t="${t}" class="${o[t] ? "on" : ""}" title="${title}">${html}</button>`;
    const seg = (a, list) => list.map(([v, l]) => `<button data-a="${a}" data-v="${v}" class="${(o[a] || "") === v ? "on" : ""}">${l}</button>`).join("");
    const hex = (c, d) => (/^#[0-9a-f]{6}$/i.test(c || "") ? c : d);
    const cols = g.c1 === g.c2 ? x.colName(g.c1) : `${x.colName(g.c1)}~${x.colName(g.c2)}`, rows = g.r1 === g.r2 ? `${g.r1 + 1}` : `${g.r1 + 1}~${g.r2 + 1}`;
    const cw = (sh.cols && sh.cols[x.colName(S.cur.c)]) || "", rh = (sh.rows && sh.rows[String(S.cur.r + 1)]) || "";
    const sizes = [8, 9, 10, 11, 12, 14, 16, 18, 20, 24, 28, 36], cs = +(o.size || x.defSize());
    return `<div class="sec"><h3>셀 <span class="hint">${esc(sh.name)}!${esc(x.rangeName(g))}</span></h3><div class="pp">
        <label>값·수식</label><input type="text" data-p="input" value="${esc(x.rawText(sh, k))}" title="${esc(k)} - Enter 로 넣기(= 로 시작하면 수식)" spellcheck="false">
        <label>표시 형식</label><div class="two"><select data-p="fmtp">${x.FMTS.map(([f, l]) => opt(f, known ? o.fmt : "__", l)).join("")}<option value="__"${known ? "" : " selected"}>직접 입력</option></select><input type="text" data-p="fmt" value="${esc(o.fmt || "")}" placeholder="#,##0.00" spellcheck="false"></div>
        <label></label><div class="hint" data-p="prev"></div></div></div>
      <div class="sec"><h3>글꼴</h3><div class="pp">
        <label>꾸밈</label><div class="pseg">${tog("b", "<b>가</b>", "굵게 (Ctrl+B)")}${tog("i", "<i>가</i>", "기울임 (Ctrl+I)")}${tog("u", "<u>가</u>", "밑줄 (Ctrl+U)")}${tog("strike", "<s>가</s>", "취소선 (Ctrl+5)")}</div>
        <label>크기</label><select data-p="size">${(sizes.includes(cs) ? sizes : [...sizes, cs].sort((a, b) => a - b)).map((n) => opt(String(n), String(cs), n + "pt")).join("")}</select>
        <label>글자색</label><div class="pclr"><input type="color" data-p="color" value="${esc(hex(o.color, "#000000"))}"><span class="hint">${o.color ? esc(o.color) : "기본"}</span><span style="flex:1"></span><button class="chip sm" data-clr="color"${raw.color ? "" : " disabled"}>기본으로</button></div>
        <label>채우기</label><div class="pclr"><input type="color" data-p="fill" value="${esc(hex(o.fill, "#FFFFFF"))}"><span class="hint">${o.fill ? esc(o.fill) : "없음"}</span><span style="flex:1"></span><button class="chip sm" data-clr="fill"${raw.fill ? "" : " disabled"}>없음</button></div></div></div>
      <div class="sec"><h3>맞춤</h3><div class="pp">
        <label>가로</label><div class="pseg">${seg("align", [["", "일반"], ["left", "왼쪽"], ["center", "가운데"], ["right", "오른쪽"]])}</div>
        <label>세로</label><div class="pseg">${seg("valign", [["", "아래"], ["middle", "가운데"], ["top", "위"]])}</div>
        <label>줄바꿈</label><label style="color:inherit"><input type="checkbox" data-p="wrap"${o.wrap ? " checked" : ""}> 칸 너비에서 줄을 바꾼다</label></div></div>
      <div class="sec"><h3>메모 <span class="hint">${esc(k)}</span></h3><div class="pp" style="grid-template-columns:1fr"><textarea data-p="note" placeholder="메모 없음 - 적으면 칸 오른쪽 위에 빨간 삼각형">${esc(raw.note || "")}</textarea></div></div>
      <div class="sec"><h3>크기 <span class="hint">열 ${esc(cols)} · 행 ${esc(rows)}</span></h3><div class="pp">
        <label>열 너비</label><div class="two"><input type="number" min="0" data-p="colw" value="${esc(cw)}" placeholder="기본"><span>px</span></div>
        <label>행 높이</label><div class="two"><input type="number" min="0" data-p="rowh" value="${esc(rh)}" placeholder="기본"><span>px</span></div></div></div>
      <div class="sec"><h3>탭 <span class="hint">${esc(sh.name)}</span></h3><div class="pp">
        <label>눈금선</label><label style="color:inherit"><input type="checkbox" data-p="grid"${(sh.grid !== undefined ? sh.grid !== false : true) ? " checked" : ""}> 보이기</label>
        <label>틀 고정</label><span class="hint">${sh.freeze ? esc(sh.freeze) + " 왼쪽 위" : "없음"}</span>
        <label>그림</label><span class="hint">${(sh.drawings || []).length}개 - 누르면 고른다</span></div></div>`;
  }
  function drawPropsHtml() {
    const x = X(), list = selDraws();
    const ord = `<div class="pseg"><button data-z="back" title="맨 뒤로">⇊ 맨 뒤</button><button data-z="bwd" title="뒤로">↓ 뒤로</button><button data-z="fwd" title="앞으로">↑ 앞으로</button><button data-z="front" title="맨 앞으로">⇈ 맨 앞</button></div>`;
    if (list.length > 1) {
      const same = (k) => (list.every(([, d]) => d[k] === list[0][1][k]) ? list[0][1][k] : "");
      return `<div class="sec"><h3>그림 ${list.length}개</h3><div class="hint" style="margin-bottom:8px">${list.map(([id]) => `<code>${esc(id)}</code>`).join(" · ")}</div><div class="pp">
          <label>크기</label><div class="two"><input type="number" min="8" data-d="w" value="${esc(same("w"))}" placeholder="너비"><span>×</span><input type="number" min="8" data-d="h" value="${esc(same("h"))}" placeholder="높이"></div>
          <label>순서</label>${ord}</div>
        <div class="row" style="margin-top:10px;gap:6px;flex-wrap:wrap"><button class="chip sm" data-da="req">이 그림들에 요청</button><span style="flex:1"></span><button class="chip sm" data-da="del">지우기</button></div></div>`;
    }
    const [id, d] = list[0];
    return `<div class="sec"><h3>그림 <span class="hint">${esc(id)}</span></h3><img class="pthumb" src="${esc(x.assetUrl(d.src) || "")}" alt=""><div class="pp">
        <label>이름(id)</label><input type="text" data-d="id" value="${esc(id)}" spellcheck="false" title="요청 대상 id - 탭 안에서 겹치지 않게">
        <label>파일</label><code title="${esc(d.src || "")}" style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(d.src || "")}</code>
        <label>고정 칸</label><input type="text" data-d="at" value="${esc(d.at || "A1")}" spellcheck="false" title="그림 왼쪽 위가 붙는 칸">
        <label>칸 안 위치</label><div class="two"><input type="number" data-d="dx" value="${esc(+d.dx || 0)}" title="가로 px"><span>,</span><input type="number" data-d="dy" value="${esc(+d.dy || 0)}" title="세로 px"></div>
        <label>크기</label><div class="two"><input type="number" min="8" data-d="w" value="${esc(+d.w || 120)}"><span>×</span><input type="number" min="8" data-d="h" value="${esc(+d.h || 60)}"></div>
        <label></label><label style="color:inherit"><input type="checkbox" data-d="lock" checked> 비율 고정</label>
        <label>대체 텍스트</label><input type="text" data-d="alt" value="${esc(d.alt || "")}" placeholder="그림 설명(엑셀 대체 텍스트)">
        <label>순서</label>${ord}</div>
      <div class="row" style="margin-top:10px;gap:6px;flex-wrap:wrap"><button class="chip sm" data-da="natural" title="그림 파일의 원래 픽셀 크기로">원래 크기</button><button class="chip sm" data-da="dup">복제</button><button class="chip sm" data-da="req">이 그림에 요청</button><span style="flex:1"></span><button class="chip sm" data-da="del">지우기</button></div></div>`;
  }
  function fmtPrev() {
    const box = $("#sp-props"), f = $("[data-p=fmt]", box).value, S = N().S, sh = X().sheet(), o = N().effCell(sh.cells[X().key(S.cur.r, S.cur.c)]);
    const v = typeof o.v === "number" ? o.v : 1234.5;
    $("[data-p=prev]", box).textContent = "보기: " + (f ? N().fmtNumber(v, f) : N().display({ v }));
  }
  /** 고른 범위 모두에 서식 - undefined 는 지우기(테마 셀 스타일이 준 값이면 끈다). 셀 서식 창(Ctrl+1)과 같은 규칙 */
  function setPatch(patch) {
    const x = X(), S = N().S;
    x.mutate(() => {
      const sh = x.sheet();
      x.eachCell(S.sel, (r, c, k) => {
        const o = { ...x.cellObj(sh, k), ...patch };
        for (const kk of Object.keys(patch)) if (patch[kk] === undefined) { const st = x.styleOf(o.s); if (st && st[kk]) o[kk] = kk === "size" ? x.defSize() : false; else delete o[kk]; }
        x.putCell(sh, k, o);
      });
    });
  }
  function onPropsInput(e) {
    const t = e.target;
    if (t.dataset.p === "fmt") fmtPrev();
    if (t.dataset.p === "fmtp" && t.value !== "__") { $("[data-p=fmt]", $("#sp-props")).value = t.value; fmtPrev(); setPatch({ fmt: t.value || undefined }); }
    if (t.dataset.d === "w" || t.dataset.d === "h") {  // 비율 고정 - 한쪽을 바꾸면 다른 쪽도(그리기는 change 때)
      const lk = $("[data-d=lock]", $("#sp-props")), d = selDraws()[0];
      if (lk && lk.checked && d && +d[1].w && +d[1].h && +t.value > 0) { const o = $(`[data-d=${t.dataset.d === "w" ? "h" : "w"}]`, $("#sp-props")); o.value = Math.round(t.dataset.d === "w" ? (+t.value * d[1].h) / d[1].w : (+t.value * d[1].w) / d[1].h); }
    }
  }
  function onPropsChange(e) {
    const t = e.target, x = X(), S = N().S, p = t.dataset.p, dk = t.dataset.d;
    if (p === "input") { const k = x.key(S.cur.r, S.cur.c); x.mutate(() => { const sh = x.sheet(); N().setInput(sh, k, t.value); x.growSize(sh, S.cur.r, S.cur.c); }); return; }
    if (p === "fmt") return setPatch({ fmt: t.value.trim() || undefined });
    if (p === "size") return setPatch({ size: +t.value === x.defSize() ? undefined : +t.value });
    if (p === "color" || p === "fill") return setPatch({ [p]: t.value.toUpperCase() });
    if (p === "wrap") return setPatch({ wrap: t.checked || undefined });
    if (p === "note") { const k = x.key(S.cur.r, S.cur.c), v = t.value.trim(); return x.mutate(() => { const sh = x.sheet(), o = { ...x.cellObj(sh, k) }; if (v) o.note = t.value; else delete o.note; x.putCell(sh, k, o); }); }
    if (p === "colw" || p === "rowh") {
      const g = x.clampRange(S.sel), v = Math.round(+t.value);
      return x.mutate(() => {
        const sh = x.sheet(), ax = p === "colw" ? "cols" : "rows", a = p === "colw" ? g.c1 : g.r1, b = p === "colw" ? g.c2 : g.r2;
        sh[ax] = sh[ax] || {};
        for (let i = a; i <= b; i++) { const kk = p === "colw" ? x.colName(i) : String(i + 1); if (t.value === "" || !(v > 0)) delete sh[ax][kk]; else sh[ax][kk] = v; }
        if (!Object.keys(sh[ax]).length) delete sh[ax];
      });
    }
    if (p === "grid") return x.mutate(() => { x.sheet().grid = t.checked; });
    if (dk) return drawChange(dk, t);
  }
  function onPropsClick(e) {
    const x = X(), b = e.target.closest("button"); if (!b || !$("#sp-props").contains(b)) return;
    if (b.dataset.t) { const o = N().effCell(x.sheet().cells[x.key(N().S.cur.r, N().S.cur.c)]); return setPatch({ [b.dataset.t]: o[b.dataset.t] ? undefined : true }); }
    if (b.dataset.a !== undefined) return setPatch({ [b.dataset.a]: b.dataset.v || undefined });
    if (b.dataset.clr) return setPatch({ [b.dataset.clr]: undefined });
    if (b.dataset.z) return drawOrder(b.dataset.z);
    if (b.dataset.da) return drawAct(b.dataset.da);
  }
  // ---------------------------------------------------------------- 그림 고치기
  /** 고른 그림마다 fn(d) - 고친 그림은 id 를 남긴다(요청 대상이 그대로이게) */
  function drawEdit(fn) {
    const x = X(), ids = new Set(N().S.drawSel || []);
    x.mutate(() => { const sh = x.sheet(); (sh.drawings || []).forEach((d, i) => { const id = x.drawId(d, i); if (!ids.has(id)) return; if (!d.id) d.id = id; fn(d); }); });
  }
  function drawChange(k, t) {
    const x = X(), S = N().S;
    if (k === "lock") return;
    if (k === "id") {
      const v = t.value.trim(), [old] = selDraws()[0] || []; if (!old || !v || v === old) return renderProps(true);
      if ((x.sheet().drawings || []).some((d, i) => x.drawId(d, i) === v)) { x.toast(`이 탭에 이미 '${v}' 그림이 있습니다`); return renderProps(true); }
      drawEdit((d) => { d.id = v; }); S.drawSel = new Set([v]); x.markDrawings(); return;
    }
    if (k === "at") { const p = x.parseRef(t.value); if (!p) { x.toast("칸 주소를 적으세요(예: B3)"); return renderProps(true); } return drawEdit((d) => { d.at = x.key(p.r, p.c); }); }
    if (k === "alt") return drawEdit((d) => { if (t.value.trim()) d.alt = t.value.trim(); else delete d.alt; });
    const v = Math.round(+t.value); if (!isFinite(v)) return;
    if (k === "w" || k === "h") {
      const box = $("#sp-props"), lk = $("[data-d=lock]", box), w = +$("[data-d=w]", box).value, h = +$("[data-d=h]", box).value;
      return drawEdit((d) => { if (lk && lk.checked) { if (w > 0) d.w = Math.max(8, Math.round(w)); if (h > 0) d.h = Math.max(8, Math.round(h)); } else if (v > 0) d[k] = Math.max(8, v); });
    }
    if (k === "dx" || k === "dy") return drawEdit((d) => { if (v) d[k] = v; else delete d[k]; });
  }
  function drawOrder(how) {
    const x = X(), ids = new Set(N().S.drawSel || []); if (!ids.size) return;
    x.mutate(() => {
      const sh = x.sheet(), all = (sh.drawings || []).map((d, i) => { if (ids.has(x.drawId(d, i)) && !d.id) d.id = x.drawId(d, i); return d; });
      const on = (d) => ids.has(x.drawId(d, 0));
      if (how === "front") sh.drawings = [...all.filter((d) => !on(d)), ...all.filter(on)];
      else if (how === "back") sh.drawings = [...all.filter(on), ...all.filter((d) => !on(d))];
      else if (how === "fwd") { for (let i = all.length - 2; i >= 0; i--) if (on(all[i]) && !on(all[i + 1])) [all[i], all[i + 1]] = [all[i + 1], all[i]]; sh.drawings = all; }
      else { for (let i = 1; i < all.length; i++) if (on(all[i]) && !on(all[i - 1])) [all[i], all[i - 1]] = [all[i - 1], all[i]]; sh.drawings = all; }
    });
    x.toast({ front: "맨 앞으로", back: "맨 뒤로", fwd: "앞으로", bwd: "뒤로" }[how] + " 옮겼습니다");
  }
  function drawAct(a) {
    const x = X(), S = N().S, list = selDraws(); if (!list.length) return;
    if (a === "del") return x.drawDelete();
    if (a === "req") { document.body.classList.remove("noside"); showTab("reqs"); $("#reqWhole").checked = false; $("#reqText").focus(); return; }
    if (a === "natural") {
      const im = $(`#draws img.drw[data-did="${CSS.escape(list[0][0])}"]`);
      if (!im || !im.naturalWidth) return x.toast("그림 파일을 읽지 못했습니다");
      return drawEdit((d) => { d.w = im.naturalWidth; d.h = im.naturalHeight; });
    }
    if (a === "dup") {
      const sh = x.sheet(), have = new Set((sh.drawings || []).map(x.drawId)), out = [];
      x.mutate(() => {
        for (const [id, d] of list) { let n = 2, nid = `${id}-${n}`; while (have.has(nid)) nid = `${id}-${++n}`; have.add(nid); const c = { ...x.clone(d), id: nid, dx: (+d.dx || 0) + 12, dy: (+d.dy || 0) + 12 }; sh.drawings.push(c); out.push(nid); }
      });
      S.drawSel = new Set(out); x.markDrawings(); x.toast(`그림 ${out.length}개를 복제했습니다`);
    }
    if (a === "alt") { const v = prompt("대체 텍스트 - 그림 설명", list[0][1].alt || ""); if (v != null) drawEdit((d) => { if (v.trim()) d.alt = v.trim(); else delete d.alt; }); }
    if (a === "rename") {
      const v = prompt("그림 이름(id) - 요청 대상으로 쓰인다", list[0][0]); if (v == null || !v.trim() || v.trim() === list[0][0]) return;
      if ((x.sheet().drawings || []).some((d, i) => x.drawId(d, i) === v.trim())) return x.toast(`이 탭에 이미 '${v.trim()}' 그림이 있습니다`);
      drawEdit((d) => { d.id = v.trim(); }); S.drawSel = new Set([v.trim()]); x.markDrawings();
    }
  }
  /** 그림 오른쪽 클릭 메뉴 - 슬라이드 요소 메뉴(studio.js ctxMenu)와 같은 묶음 */
  function drawMenu(e) {
    const x = X(), list = selDraws(); if (!list.length) return;
    const one = list.length === 1, src = one ? x.assetUrl(list[0][1].src) : null;
    x.openMenu({ x: e.clientX, y: e.clientY }, [
      { h: one ? `그림 ${list[0][0]}` : `그림 ${list.length}개` },
      { label: "복제", act: () => drawAct("dup") },
      { label: one ? "지우기" : `지우기 (${list.length}개)`, key: "Delete", act: () => drawAct("del") }, "-",
      { label: "앞으로 가져오기", act: () => drawOrder("fwd") }, { label: "뒤로 보내기", act: () => drawOrder("bwd") },
      { label: "맨 앞으로", act: () => drawOrder("front") }, { label: "맨 뒤로", act: () => drawOrder("back") }, "-",
      { label: "원래 크기", disabled: !one, act: () => drawAct("natural") },
      { label: "이름(id) 바꾸기…", disabled: !one, act: () => drawAct("rename") },
      { label: "대체 텍스트…", disabled: !one, act: () => drawAct("alt") },
      { label: "속성…", act: () => { document.body.classList.remove("noside"); showTab("props"); } }, "-",
      { label: one ? "이 그림에 요청 메모" : `이 그림 ${list.length}개에 요청 메모`, act: () => drawAct("req") },
      ...(src ? [{ label: "그림 새 탭에서 열기", act: () => window.open(src, "_blank") }] : []),
    ]);
  }

  // ---------------------------------------------------------------- 기록(자동 백업)
  async function loadHist() {
    const x = X(), H = $("#sp-hist"); if (!x || !N().S.id) return;
    H.innerHTML = `<div class="hint">불러오는 중…</div>`;
    const r = await x.api("GET", `/api/history/${encodeURIComponent(N().S.id)}`);
    const list = r.ok && Array.isArray(r.data) ? r.data : [];
    H.innerHTML = `<div class="sec"><h3>기록 - ${esc(N().S.deck.title || N().S.id)}</h3><div class="hint">이 화면이 저장할 때마다·밖에서 바뀌기 직전에 남긴 자동 백업입니다(최근 50개 - 장기 보관이 아닙니다). 무엇이 바뀌었는지는 변경 탭. 되돌리면 지금 상태도 기록에 남으므로 다시 돌아올 수 있습니다(Ctrl+Z 도 가능).</div></div>
      ${list.length ? list.map((h) => `<div class="hist"><span class="k ${esc(h.kind)}">${h.kind === "build" ? "빌드 전" : h.kind === "ext" ? "외부 변경 전" : "저장 전"}</span><span>${esc(String(h.at || "").replace("T", " "))}</span><span class="sp"></span><button class="chip sm" data-hf="${esc(h.file)}" data-hat="${esc(String(h.at || "").replace("T", " "))}">되돌리기</button></div>`).join("") : `<div class="hint">기록이 없습니다.</div>`}`;
  }
  /** 백업 시점으로 - 실행 취소에 남기고, 저장은 원장에 action restore 로(편집기 restoreFrom 과 같다) */
  async function restoreFrom(file, label) {
    const x = X(), S = N().S;
    if (!confirm(`${label} 시점으로 되돌릴까요? (지금 상태는 기록에 남습니다)`)) return false;
    const r = await x.api("GET", `/api/history/${encodeURIComponent(S.id)}?f=${encodeURIComponent(file)}`);
    const d = r.ok && r.data;
    if (!d || d.kind !== "sheet" || !Array.isArray(d.sheets) || !d.sheets.length) { x.toast("기록을 읽지 못했습니다(시트 문서가 아님)"); return false; }
    if (!Array.isArray(d.slides)) d.slides = [];
    d.sheets.forEach(x.normSheet);
    await x.setupVba(d);
    const tid = x.sheet().id;
    x.snapshot(); S.deck = d; S.struct = []; S.drawSel = null;
    S.ti = Math.max(0, d.sheets.findIndex((t) => t.id === tid));
    S.saveMeta = { action: "restore", note: file };
    x.afterChange();
    x.toast("되돌렸습니다 (Ctrl+Z 로 취소 가능)"); return true;
  }

  // ---------------------------------------------------------------- 변경(서버 원장)
  const seenKey = () => "chgSeen-" + N().S.id;
  const isMine = (g) => g.origin === "editor" && !!g.actor && g.actor.tab === X().TAB;
  const orgKey = (g) => (g.origin === "editor" ? (isMine(g) ? "mine" : "editor") : g.origin);
  const ORG_LABEL = { mine: "편집", editor: "협업", claude: "AI", build: "빌드", external: "외부" };
  function orgTitle(g) {
    const a = g.actor || {}, out = [];
    if (g.origin === "editor") out.push(isMine(g) ? "현재 화면에서 수정" : `다른 창(${a.tab || "?"})에서 수정 - 협업`);
    if (g.origin === "claude") out.push(a.label ? `세션 ${a.label}` : "AI 세션", a.request ? `요청 ${a.request}` : "", g.confidence === "inferred" ? "정황으로 추정(세션 연결·처리 중 요청)" : "서버 API 로 저장(정확)");
    if (g.origin === "build") out.push(a.note || "build_deck");
    if (g.origin === "external") out.push(g.action === "startup" ? "서버가 꺼진 사이에 바뀜(출처 모름)" : "출처를 알 수 없는 외부 변경(파일 직접 수정)");
    if (a.note && g.origin !== "build") out.push(a.note);
    if (g.merge) out.push(`병합 저장 ${g.merge.saves}회${g.merge.conflicts.length ? ` · 같은 곳 충돌 ${g.merge.conflicts.length}건` : ""}`);
    return out.filter(Boolean).join(" · ");
  }
  const orgBadge = (g) => { const k = orgKey(g); return `<span class="org o-${esc(k)}${g.confidence === "inferred" ? " inf" : ""}" title="${esc(orgTitle(g))}">${esc(ORG_LABEL[k] || g.origin)}${g.confidence === "inferred" ? " 추정" : ""}</span>`; };
  const chgSummary = (sum) => ["수정", "추가", "삭제", "이동"].filter((k) => sum && sum[k]).map((k) => `${sum[k]}탭 ${k}`).join(" · ");
  const inFilter = (g, f) => f === "all" || (f === "mine" ? isMine(g) : f === "editor" ? g.origin === "editor" && !isMine(g) : g.origin === f);
  const isOn = (g, seen = +X().LS.get(seenKey(), 0)) => P.shown.has(g.seq) || (!P.hidden.has(g.seq) && g.last > seen);
  function ago(ts) { const t = Date.parse(ts || ""); if (!t) return ""; const d = (Date.now() - t) / 1000; if (d < 60) return "방금"; if (d < 3600) return `${Math.floor(d / 60)}분`; if (d < 86400) return `${Math.floor(d / 3600)}시간`; return `${Math.floor(d / 86400)}일`; }
  const hhmm = (ts) => { const d = new Date(ts || 0); return isNaN(d) ? "" : d.toTimeString().slice(0, 5); };
  const dayText = (ts) => { const d = new Date(ts || 0); if (isNaN(d)) return ""; return d.toDateString() === new Date().toDateString() ? "오늘" : `${d.getMonth() + 1}/${d.getDate()}`; };
  const isCellId = (id) => /^[A-Z]{1,3}\d+$/.test(id);
  /** 표시할 변경 - {탭 id: {cells: Set, draws: Set}} */
  function marked() {
    const out = {}; if (P.off) return out;
    const seen = +X().LS.get(seenKey(), 0);
    for (const g of P.changes) {
      if (!isOn(g, seen)) continue;
      for (const it of g.items || []) {
        if (it.gone) continue;
        const m = (out[it.sid] = out[it.sid] || { cells: new Set(), draws: new Set() });
        for (const e of it.els || []) if (!e.gone) ((e.kinds || []).includes("그림") ? m.draws : m.cells).add(e.id);
      }
    }
    return out;
  }
  async function loadChanges(more) {
    const x = X(), S = N().S; if (!x || !S.id) return;
    const before = more && P.changes.length ? `&before=${P.changes[P.changes.length - 1].seq}` : "";
    const r = await x.api("GET", `/api/changes/${encodeURIComponent(S.id)}?group=1&recent=1&limit=40${before}`); if (!r.ok) return;
    const gs = r.data.groups || [];
    P.changes = more ? P.changes.concat(gs) : gs;
    if (!more) { P.recent = r.data.recent || []; P.latest = r.data.latest || 0; P.keep = r.data.keep; }
    P.more = !!r.data.more; P.loaded = true;
    renderChanges(); renderMarks();
  }
  function renderMarks() {
    const x = X(), S = N().S, box = $("#chgMarks"); if (!x || !S.deck || !box) return;
    const all = marked(), m = all[x.sheet().id] || { cells: new Set(), draws: new Set() };
    let n = 0; for (const v of Object.values(all)) n += v.cells.size + v.draws.size;
    const c = $("#chgCnt"); if (c) { c.hidden = !n; c.textContent = n > 99 ? "99+" : String(n); c.title = `확인하지 않은 변경 - 셀·그림 ${n}개`; }
    // 칸마다 범위(병합이면 병합 전체, 같은 병합은 한 번) - 놓기는 placeMarks(선택 표시와 같은 좌표·틀 고정 규칙)
    const sh = x.sheet(), seen = new Set(), out = [];
    for (const k of m.cells) {
      if (out.length >= 800) break;
      const p = x.parseRef(k); if (!p || p.r >= x.G.rows || p.c >= x.G.cols || x.rowHidden(sh, p.r) || x.colHidden(sh, p.c)) continue;
      const g = x.mergeAt(sh, p.r, p.c) || { r1: p.r, c1: p.c, r2: p.r, c2: p.c }, id = x.rangeName(g);
      if (!seen.has(id)) { seen.add(id); out.push(g); }
    }
    P.marks = out; P.markTab = sh.id;
    box.innerHTML = out.map(() => `<div class="cm"></div>`).join("");
    placeMarks();
    $$("#draws img.drw").forEach((im) => im.classList.toggle("chg", m.draws.has(im.dataset.did)));
  }
  /** 변경 표시 놓기 - 지금 격자 좌표(rectOf)로, 틀 고정 칸은 스크롤을 따라가고 스크롤 쪽은 고정 칸 밑으로 가린다(sheet.js placeQ 와 같다) */
  function placeMarks() {
    const x = X(), box = $("#chgMarks"); if (!x || !box || !P.marks) return;
    if (P.markTab !== x.sheet().id) return renderMarks();  // 탭이 바뀌었다 - 그 탭의 표시로
    [...box.children].forEach((el, i) => {
      const g = P.marks[i]; if (!g) return;
      const R = x.rectOf(g), p = x.paneOf(g.r1, g.c1), X0 = R.x + p.dx, Y0 = R.y + p.dy, w = R.w + 1, h = R.h + 1;
      const t = p.cy == null ? 0 : Math.max(0, p.cy - Y0), l = p.cx == null ? 0 : Math.max(0, p.cx - X0);
      Object.assign(el.style, { left: X0 + "px", top: Y0 + "px", width: w + "px", height: h + "px", clipPath: t || l ? `inset(${t}px 0 0 ${l}px)` : "", visibility: t >= h || l >= w ? "hidden" : "" });
    });
  }
  function renderChanges() {
    const S = N().S, box = $("#sp-chg"); if (!box || P.tab !== "chg") return;
    const F = [["all", "전체", "모든 변경 - 이 화면·다른 창·AI·빌드·외부"], ["mine", "편집", "현재 화면에서 수정"], ["editor", "협업", "다른 창에서 수정"], ["claude", "AI", "AI 에서 수정, 파일 직접 수정은 추정"], ["build", "빌드", "build_deck"], ["external", "외부", "출처를 알 수 없는 변경 - 파일 직접 수정, 서버가 꺼진 사이의 변경"]];
    const cnt = (k) => P.changes.filter((g) => inFilter(g, k)).length;
    const list = P.changes.filter((g) => inFilter(g, P.filter));
    const recent = P.recent.filter((r) => r.exists).slice(0, 8);
    box.innerHTML = `<div class="sec"><div class="chg-top"><h3>변경 - ${esc(S.deck.title || S.id)}</h3>
        <button class="chg-ibtn${P.info ? " on" : ""}" data-chg-info="1" title="설명 보기/숨기기"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="9.5"/><path d="M12 11v6"/><circle cx="12" cy="7.5" r=".6" fill="currentColor"/></svg></button></div>
      ${P.info ? `<div class="hint chg-info">이 화면·다른 창·AI·외부에서 시트가 바뀔 때마다 서버가 원장(최근 ${P.keep || 1000}건)에 셀·그림 단위로 남깁니다. 항목을 누르면 그 탭·셀로 갑니다. 확인하지 않은 변경(내 편집 포함)은 격자에 파란 점선으로 표시하고, "확인함"은 지금까지를 미표시로, "최근 3개 표시"는 최근 묶음 3개를 표시, "표시 끄기"는 모든 표시를 감춥니다. 되돌리기는 백업(최근 50개)이 남아 있을 때만.</div>` : ""}
      <div class="chg-fil">${F.map(([k, l, t]) => `<button data-chgf="${k}" class="${P.filter === k ? "on" : ""}" title="${esc(t)}">${l}${cnt(k) ? ` <b>${cnt(k)}</b>` : ""}</button>`).join("")}</div>
      <div class="chg-acts"><button class="chip sm" data-chg-seen="1" title="최근 변경까지 확인한 것으로 - 모든 묶음을 미표시로">확인함</button><button class="chip sm" data-chg-recent="1" title="가장 최근 변경 묶음 3개를 표시(내 편집 포함)">최근 3개 표시</button><button class="chip sm${P.off ? " on" : ""}" data-chg-off="1" title="변경 기록을 보지 않고 작업 - 점선을 모두 감춘다">${P.off ? "표시 켜기" : "표시 끄기"}</button></div></div>
      ${recent.length ? `<div class="sec"><h3>최근 수정 대상</h3><table class="chg-tbl"><colgroup><col class="n"><col><col class="o"><col class="a"></colgroup>${recent.map((r) => { const k = [r.kind === "수정" ? "" : r.kind, ...(r.kinds || []), ...(r.extra || [])].filter(Boolean).join("·"); return `<tr data-csid="${esc(r.sid)}"><td class="n">${esc(r.title || r.sid)}</td><td class="hint" title="${esc(k)}">${esc(k)}</td><td class="o">${orgBadge(r)}</td><td class="hint a" title="${esc(r.ts || "")}">${esc(ago(r.ts))}</td></tr>`; }).join("")}</table></div>` : ""}
      ${list.length ? list.map(groupHtml).join("") + (P.more ? `<div class="row" style="justify-content:center;margin:8px 0"><button class="chip sm" data-chg-more="1">더 보기</button></div>` : `<div class="hint" style="text-align:center;margin:8px 0">원장의 시작</div>`)
        : `<div class="hint">${P.changes.length ? "이 필터에 해당하는 변경이 없습니다." : "아직 기록된 변경이 없습니다."}</div>`}`;
  }
  function groupHtml(g) {
    const on = isOn(g), kcls = { 추가: "k-add", 삭제: "k-del" };
    const tag = g.action === "accept" ? " · AI 제안 받기" : g.action === "restore" ? " · 되돌리기" : g.action === "startup" ? " · 서버 꺼진 사이" : "";
    const fields = (g.fields || []).filter((f) => f !== "sheets");
    return `<div class="chg-rec${on ? " on" : ""}"><div class="chg-h"><b title="${esc(g.ts || "")}${g.count > 1 ? ` ~ ${esc(g.ts_end || "")}` : ""}">${esc(dayText(g.ts))} ${esc(hhmm(g.ts))}</b>${orgBadge(g)}<span class="hint">${g.actor && g.actor.label ? esc(g.actor.label) + " · " : ""}${esc(chgSummary(g.summary))}${fields.length ? ` · 문서 ${esc(fields.join("·"))}` : ""}${g.count > 1 ? ` · 저장 ${g.count}회` : ""}${tag}${g.merge ? ` · <span class="chg-mtag">병합${g.merge.conflicts.length ? ` · 충돌 ${g.merge.conflicts.length}` : ""}</span>` : ""}</span>
      ${g.backupExists ? `<button class="chip sm" data-chg-restore="${esc(g.backup)}" data-chg-at="${esc((g.ts || "").replace("T", " ").slice(0, 16))}" title="이 변경 직전 상태로 되돌린다(지금 상태도 기록에 남는다)">직전으로</button>` : `<button class="chip sm" disabled title="백업이 50개 상한으로 지워져 되돌릴 수 없습니다">직전으로</button>`}
      <button class="chip sm chg-tg" data-chg-tg="${g.seq}" title="이 묶음의 변경을 격자에 파란 점선으로 ${on ? "그만 표시" : "표시"}">${on ? "숨기기" : "표시"}</button></div>` +
      (g.items || []).map((it) => `<div class="chg-it${it.gone ? " gone" : ""}" ${it.gone ? "" : `data-csid="${esc(it.sid)}"`}>
        <span class="k ${kcls[it.kind] || ""}">${esc(it.kind)}</span> <b>${esc(it.title || it.sid)}</b>${it.moved ? ` <span class="hint">(순서 ${it.moved[0]} → ${it.moved[1]})</span>` : ""}${it.extra && it.extra.length ? ` <span class="hint">· ${esc(it.extra.join("·"))}</span>` : ""}${it.truncated ? ` <span class="hint">· ${it.truncated}개 더</span>` : ""}
        ${(it.els || []).slice(0, 60).map((e) => `<div class="chg-el${e.gone ? " gone" : ""}" ${e.gone ? "" : `data-cel="${esc(e.id)}"`}><code>${esc(e.id)}</code> ${esc((e.kinds || []).join("·"))}${e.before || e.after ? `<div class="chg-tx">${e.before ? `<s>${esc(e.before)}</s>` : ""}${e.before && e.after ? " → " : ""}${e.after ? `<span>${esc(e.after)}</span>` : ""}</div>` : ""}</div>`).join("")}${(it.els || []).length > 60 ? `<div class="hint" style="margin-left:14px">… ${(it.els || []).length - 60}개 더</div>` : ""}</div>`).join("") + `</div>`;
  }
  function redraw() { renderChanges(); renderMarks(); }
  async function onChgClick(e) {
    const x = X(), S = N().S, t = e.target;
    if (t.closest("[data-chg-info]")) { P.info = !P.info; return renderChanges(); }
    const f = t.closest("[data-chgf]"); if (f) { P.filter = f.dataset.chgf; x.LS.set("sheetChgFilter", P.filter === "all" ? "" : P.filter); return renderChanges(); }
    if (t.closest("[data-chg-seen]")) { x.LS.set(seenKey(), P.latest); P.shown.clear(); P.hidden.clear(); return redraw(); }
    if (t.closest("[data-chg-recent]")) { P.changes.slice(0, 3).forEach((g) => { P.hidden.delete(g.seq); P.shown.add(g.seq); }); return redraw(); }
    if (t.closest("[data-chg-off]")) { P.off = !P.off; x.LS.set("sheetChgOff", P.off ? "1" : ""); return redraw(); }
    if (t.closest("[data-chg-more]")) return loadChanges(true);
    const rs = t.closest("[data-chg-restore]"); if (rs) { await restoreFrom(rs.dataset.chgRestore, rs.dataset.chgAt); return; }
    const tg = t.closest("[data-chg-tg]");
    if (tg) { const k = +tg.dataset.chgTg, g = P.changes.find((z) => z.seq === k); if (!g) return; if (isOn(g)) { P.shown.delete(k); P.hidden.add(k); } else { P.hidden.delete(k); P.shown.add(k); } return redraw(); }
    const it = t.closest("[data-csid]"); if (!it) return;
    const i = S.deck.sheets.findIndex((s) => s.id === it.dataset.csid); if (i < 0) return x.toast("그 탭이 지금은 없습니다");
    if (i !== S.ti) x.switchTab(i);
    const el = t.closest("[data-cel]"), id = el && el.dataset.cel;
    if (id && isCellId(id)) { const p = x.parseRef(id); if (p) { S.drawSel = null; x.markDrawings(); x.selectCell(p.r, p.c); x.scrollIntoView(p.r, p.c); } }
    else if (id) { if ((x.sheet().drawings || []).some((d, j) => x.drawId(d, j) === id)) { x.drawPick(id, false); const im = $(`#draws img.drw[data-did="${CSS.escape(id)}"]`); if (im) im.scrollIntoView({ block: "nearest", inline: "nearest" }); } else x.toast("그 그림이 지금은 없습니다"); }
    renderMarks();
  }

  // ---------------------------------------------------------------- 시작·훅
  function init() {
    const x = X(); if (!x) return;
    P.filter = x.LS.get("sheetChgFilter", "") || "all"; P.off = x.LS.get("sheetChgOff", "") === "1";
    $("#sideTabs").addEventListener("click", (e) => { const b = e.target.closest("[data-stab]"); if (b) showTab(b.dataset.stab); });
    const pp = $("#sp-props");
    pp.addEventListener("input", onPropsInput);
    pp.addEventListener("change", onPropsChange);
    pp.addEventListener("click", onPropsClick);
    pp.addEventListener("keydown", (e) => { e.stopPropagation(); if (e.key === "Enter" && e.target.tagName === "INPUT") { e.preventDefault(); e.target.blur(); } if (e.key === "Escape") { e.target.blur(); renderProps(true); x.focusGrid(); } });
    pp.addEventListener("focusout", () => setTimeout(() => { if (P.pend && !pp.contains(document.activeElement)) renderProps(); }, 0));
    $("#sp-hist").addEventListener("click", async (e) => { const b = e.target.closest("[data-hf]"); if (b && (await restoreFrom(b.dataset.hf, b.dataset.hat))) loadHist(); });
    $("#sp-chg").addEventListener("click", onChgClick);
    const t = x.LS.get("sheetSideTab", ""); if (t && t !== "reqs") showTab(t);
  }
  let started = false, lastVer = null;
  window.NexaSheetSide = {
    showTab, drawMenu, P, renderProps, loadChanges, restoreFrom,
    onPlace() { if (started) placeMarks(); },
    onSel() { if (!started) return; renderProps(); const m = marked(), x = X(), cur = m[x.sheet().id]; $$("#draws img.drw").forEach((im) => im.classList.toggle("chg", !!(cur && cur.draws.has(im.dataset.did)))); },
    onRender() {
      if (!started && X() && N().S.deck) { started = true; init(); loadChanges(); }
      if (!started) return;
      renderProps(); renderMarks();
    },
    onVersion(v) { if (!started || !v || v.changes == null) return; if (lastVer == null) { lastVer = v.changes; return; } if (v.changes !== lastVer) { lastVer = v.changes; loadChanges(); if (P.tab === "hist") loadHist(); } },
  };
})();
