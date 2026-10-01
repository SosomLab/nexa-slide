/* 슬라이드 스튜디오 편집기 — 덱 JSON 편집(자동 저장·외부 변경 감지·요청 메모·PPTX 내보내기·PPT 렌더 미리보기).
   렌더링은 render.js(Render.*) 가 한다. 서버 API 는 server.py 참고. */
(function () {
  "use strict";
  window.RENDER_BASE = "/";
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const esc = (s) => Render.esc(s == null ? "" : s);
  const GRID = 8, SW = 1280, SH = 720;

  const S = {
    tokens: null, decks: [], id: null, deck: null, version: null, reqVersion: "0",
    cur: 0, sel: null, undo: [], redo: [], dirty: false, saving: false, conflict: false,
    reqs: [], reqOnlySlide: true, layouts: [], preview: false, pngs: [], renderAt: 0, editing: null, clip: null,
    tab: "props", brand: {}, session: null, check: null, chkOnlySlide: false, chkBox: null,
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

  function setStatus(kind, text) {
    const s = $("#status"); s.className = "chip sm " + kind; s.textContent = text;
  }

  // ---------------------------------------------------------------- 기록(실행 취소)·저장
  /** 변경 직전에 부른다: 현재 덱을 실행 취소 스택에 넣는다 */
  function snapshot() {
    S.undo.push(JSON.stringify(S.deck));
    if (S.undo.length > 150) S.undo.shift();
    S.redo = [];
    updUndo();
  }
  function updUndo() { $("#undoBtn").disabled = !S.undo.length; $("#redoBtn").disabled = !S.redo.length; }
  function undo() {
    if (!S.undo.length) return;
    S.redo.push(JSON.stringify(S.deck)); S.deck = JSON.parse(S.undo.pop());
    afterChange(true);
  }
  function redo() {
    if (!S.redo.length) return;
    S.undo.push(JSON.stringify(S.deck)); S.deck = JSON.parse(S.redo.pop());
    afterChange(true);
  }
  /** 변경 후: 화면 갱신 + 자동 저장 예약 */
  function afterChange(full) {
    if (S.cur >= S.deck.slides.length) S.cur = S.deck.slides.length - 1;
    if (S.sel && !selEl()) S.sel = null;
    S.dirty = true; setStatus("dirty", "저장 대기");
    updUndo();
    if (full) { renderAll(); ensureThumbVisible(S.cur); } else { renderCanvas(); renderThumb(S.cur); renderProps(); }
    scheduleSave();
  }
  let saveT = 0;
  function scheduleSave() { clearTimeout(saveT); saveT = setTimeout(save, 700); }
  async function save(force) {
    if (!S.deck || S.conflict && !force) return;
    if (S.saving) { scheduleSave(); return; }
    S.saving = true; setStatus("dirty", "저장 중…");
    const body = S.deck;
    const r = await api("PUT", `/api/deck/${S.id}?base=${encodeURIComponent(S.version || "")}${force ? "&force=1" : ""}`, body);
    S.saving = false;
    if (r.ok) {
      S.version = r.data.version; S.deck.updated = r.data.updated; scheduleCheck();
      if (JSON.stringify(body) === JSON.stringify(S.deck)) S.dirty = false;
      S.conflict = false; banner(false);
      setStatus(S.dirty ? "dirty" : "saved", S.dirty ? "저장 대기" : "저장됨");
      if (S.dirty) scheduleSave();
    } else if (r.status === 409) {
      S.conflict = true; setStatus("conflict", "충돌");
      banner(true, "저장하려는 사이 덱 파일이 밖에서(Claude 등) 바뀌었습니다. 어느 쪽을 남길까요?");
    } else {
      setStatus("error", "저장 실패"); toast("저장 실패: " + (r.data && r.data.error || r.status));
    }
  }
  function banner(on, msg) { $("#banner").classList.toggle("show", !!on); if (msg) $("#bannerMsg").textContent = msg; }

  // ---------------------------------------------------------------- 불러오기·외부 변경 감지
  async function loadDeck(id, keep) {
    const r = await fetch(`/api/deck/${id}`, { cache: "no-store" });
    if (!r.ok) { toast("덱을 불러오지 못했습니다"); return false; }
    const deck = await r.json();
    if (keep && S.deck && S.id === id) snapshot(); // 외부 변경도 실행 취소로 되돌릴 수 있게
    else { S.undo = []; S.redo = []; }
    S.id = id; S.deck = deck; S.version = r.headers.get("X-Deck-Version");
    S.dirty = false; S.conflict = false; banner(false);
    if (!keep) { S.cur = 0; S.sel = null; }
    if (S.cur >= deck.slides.length) S.cur = Math.max(0, deck.slides.length - 1);
    if (S.sel && !selEl()) S.sel = null;
    setStatus("saved", "저장됨"); updUndo();
    await loadReqs();
    await loadPngs();
    S.chkBox = null; scheduleCheck(50);
    renderAll();
    revealThumb(S.cur, true);
    return true;
  }
  async function poll() {
    if (!S.id) return;
    try {
      const r = await api("GET", `/api/version/${S.id}`);
      if (!r.ok) return;
      if (r.data.session) renderSession(r.data.session);
      if (r.data.requests !== S.reqVersion) { await loadReqs(); }
      if (r.data.deck !== S.version && !S.saving) {
        if (S.dirty || S.editing) {
          if (!S.conflict) { S.conflict = true; setStatus("conflict", "충돌"); banner(true, "편집 중에 덱 파일이 밖에서(Claude 등) 바뀌었습니다. 어느 쪽을 남길까요?"); }
        } else {
          await loadDeck(S.id, true);
          toast("밖에서 바뀐 덱을 다시 불러왔습니다 (Ctrl+Z 로 되돌리기 가능)");
        }
      }
    } catch (e) { setStatus("error", "서버 끊김"); }
  }

  // ---------------------------------------------------------------- 그리기
  function renderAll() { renderThumbs(); renderCanvas(); renderProps(); renderReqs(); renderNotes(); renderPng(); location.hash = `${S.id}/${S.cur + 1}`; }

  function openCount(slideId) { return S.reqs.filter((r) => r.status !== "done" && r.slide === slideId).length; }
  function thumbHtml(s, i) {
    const n = openCount(s.id);
    return `<div class="thumb${i === S.cur ? " cur" : ""}" data-i="${i}" draggable="true"><span class="num">${i + 1}</span>
      <div class="vp">${Render.renderSlide(s, i + 1)}</div>
      <div class="tools"><button data-act="dup" title="복제">복제</button><button data-act="del" title="삭제">삭제</button></div>
      ${n ? `<span class="badge">요청 ${n}</span>` : ""}${chkBadge(s.id)}</div>`;
  }
  function chkBadge(sid) {
    if (!S.check) return "";
    const its = S.check.issues.filter((x) => x.slide === sid); if (!its.length) return "";
    const e = its.filter((x) => x.severity === "ERROR").length;
    return `<span class="cbadge${e ? " err" : ""}" title="레이아웃 검사 — ERROR ${e} · WARNING ${its.length - e}">⚠ ${its.length}</span>`;
  }
  function fitThumbs() { $$("#left .thumb .vp").forEach((v) => { v.firstElementChild.style.transform = `scale(${v.clientWidth / SW})`; }); }
  function renderThumbs() {
    // 목록을 다시 그려도 스크롤 위치는 그대로 둔다(내용 교체 순간 높이가 줄어 위치가 밀리는 것 방지)
    const L = $("#left"), top = L.scrollTop;
    L.innerHTML = S.deck.slides.map(thumbHtml).join("") + `<button class="chip" id="addSlide">＋ 새 슬라이드</button>`;
    fitThumbs();
    L.scrollTop = top;
  }
  /** 현재 슬라이드 썸네일이 목록에서 일부라도 가려져 있을 때만, 온전히 보일 만큼만 스크롤한다 */
  function ensureThumbVisible(i) {
    const L = $("#left"), t = $(`#left .thumb[data-i="${i}"]`); if (!L || !t) return;
    const lr = L.getBoundingClientRect(), tr = t.getBoundingClientRect(), m = 8;
    if (tr.top < lr.top) L.scrollTop -= lr.top - tr.top + m;
    else if (tr.bottom > lr.bottom) L.scrollTop += tr.bottom - lr.bottom + m;
  }
  /** 선택이 코드로 바뀐 경우(다시 읽기·주소 이동·외부 변경): 레이아웃이 끝난 뒤 한 번 더 맞춘다.
      center=true 면 가려져 있을 때 목록 가운데로 가져온다(새로 연 화면에서 위치를 찾기 쉽게) */
  function revealThumb(i, center) {
    const go = () => {
      const L = $("#left"), t = $(`#left .thumb[data-i="${i}"]`); if (!L || !t) return;
      const lr = L.getBoundingClientRect(), tr = t.getBoundingClientRect();
      const hidden = tr.top < lr.top || tr.bottom > lr.bottom;
      if (hidden && center) L.scrollTop += (tr.top + tr.height / 2) - (lr.top + lr.height / 2);
      else ensureThumbVisible(i);
    };
    go();
    requestAnimationFrame(() => requestAnimationFrame(go));
  }
  function renderThumb(i) {
    const t = $(`#left .thumb[data-i="${i}"]`); if (!t) return renderThumbs();
    t.outerHTML = thumbHtml(S.deck.slides[i], i); fitThumbs();
  }

  let scale = 1;
  function fitStage() {
    const vp = $("#vpEdit"), st = $("#stage");
    scale = Math.min(vp.clientWidth / SW, vp.clientHeight / SH) || 0.5;
    st.style.transform = `scale(${scale})`;
    const pw = $("#pngWrap"), vp2 = $("#vpPng");
    if (S.preview) pw.style.transform = `scale(${Math.min(vp2.clientWidth / SW, vp2.clientHeight / SH) || 0.5})`;
    drawSel();
  }
  function renderCanvas() {
    const s = slide();
    $("#host").innerHTML = s ? Render.renderSlide(s, S.cur + 1) : "";
    drawSel(); fitStage();
  }
  function renderElementDom(el) {
    const node = $(`#host .rs-el[data-id="${CSS.escape(el.id)}"]`);
    if (node) node.outerHTML = Render.renderElement(el, S.cur + 1); else renderCanvas();
  }
  function boxOf(el) { return isLine(el) ? Render.lineBox(el) : el; }
  function drawSel() {
    const ov = $("#ov"); const el = selEl();
    if (!el || S.editing) { ov.innerHTML = ""; drawChkBox(); return; }
    const b = boxOf(el), hs = 11 / scale, bw = 2 / scale;
    let h = `<div class="selbox${el.locked ? " locked" : ""}" style="left:${b.x - bw}px;top:${b.y - bw}px;width:${b.w + 2 * bw}px;height:${b.h + 2 * bw}px;border-width:${bw}px"></div>`;
    if (!el.locked) {
      const pts = isLine(el)
        ? [["p1", el.x1, el.y1], ["p2", el.x2, el.y2]]
        : [["nw", b.x, b.y], ["n", b.x + b.w / 2, b.y], ["ne", b.x + b.w, b.y], ["e", b.x + b.w, b.y + b.h / 2],
           ["se", b.x + b.w, b.y + b.h], ["s", b.x + b.w / 2, b.y + b.h], ["sw", b.x, b.y + b.h], ["w", b.x, b.y + b.h / 2]];
      h += pts.map(([d, x, y]) => `<div class="hd" data-h="${d}" style="left:${x - hs / 2}px;top:${y - hs / 2}px;width:${hs}px;height:${hs}px;border-width:${bw}px;cursor:${d.length === 2 && d[0] !== "p" ? d + "-resize" : d === "n" || d === "s" ? "ns-resize" : d === "e" || d === "w" ? "ew-resize" : "move"}"></div>`).join("");
    }
    ov.innerHTML = h; drawChkBox();
  }

  // ---------------------------------------------------------------- PPT 렌더 미리보기
  async function loadPngs() {
    const r = await api("GET", `/api/render/${S.id}`);
    S.pngs = r.ok ? r.data.slides : [];
  }
  function renderPng() {
    if (!S.preview) return;
    const u = S.pngs[S.cur];
    $("#pngWrap").innerHTML = u ? `<img src="${u}" alt="">` : `<div class="empty">아직 렌더 없음 — "다시 렌더"</div>`;
    const stale = S.renderAt && S.deck && S.deck.updated && new Date(S.deck.updated).getTime() > S.renderAt;
    $("#pngInfo").textContent = u ? (stale ? "· 렌더 뒤에 편집됨 — 다시 렌더 필요" : "") : "";
    fitStage();
  }
  async function doRender() {
    const b = $("#renderBtn"); b.disabled = true; b.innerHTML = `<span class="spin"></span> PowerPoint 렌더 중`;
    if (S.dirty) await save();
    const r = await api("POST", `/api/render/${S.id}`);
    b.disabled = false; b.textContent = "다시 렌더";
    if (r.ok) { S.pngs = r.data.slides; S.renderAt = Date.now(); renderPng(); toast("PowerPoint 렌더 완료"); }
    else toast("렌더 실패: " + (r.data && (r.data.error + " " + (r.data.log || "")) || r.status), 5000);
  }
  async function doExport() {
    const b = $("#exportBtn"); b.disabled = true; b.innerHTML = `<span class="spin"></span> 만드는 중`;
    if (S.dirty) await save();
    const r = await api("POST", `/api/export/${S.id}`);
    b.disabled = false; b.textContent = "PPTX 내보내기";
    if (r.ok) {
      const a = $("#dl"); a.href = r.data.url; a.setAttribute("download", `${S.id}.pptx`); a.style.display = ""; a.textContent = `⬇ ${S.id}.pptx`;
      toast(`${r.data.path} 생성 — 오른쪽 위 링크로 받기`);
    } else toast("내보내기 실패: " + (r.data && (r.data.error + " " + (r.data.log || "")) || r.status), 6000);
  }

  // ---------------------------------------------------------------- 속성 패널
  function colorOptions(cur, allowNone) {
    const T = S.tokens; let h = allowNone ? `<option value="">(없음)</option>` : "";
    let found = !cur;
    for (const [g, names] of Object.entries(T.groups)) {
      h += `<optgroup label="${esc(g)}">` + names.map((n) => { if (n === cur) found = true; return `<option value="${n}"${n === cur ? " selected" : ""}>${n}  ${Render.color(n)}</option>`; }).join("") + `</optgroup>`;
    }
    if (!found && cur) h += `<option value="${esc(cur)}" selected>${esc(cur)} (직접)</option>`;
    return h;
  }
  function colorRow(label, key, el, allowNone) {
    const v = el[key] || "";
    return `<div class="row"><label>${label}</label><span class="sw" style="background:${v ? Render.color(v) : "transparent"}"></span>
      <select class="colorSel" data-k="${key}" data-kind="color">${colorOptions(v, allowNone)}</select></div>`;
  }
  const num = (label, key, el, step = 1) => `<div class="row"><label>${label}</label><input type="number" step="${step}" data-k="${key}" value="${el[key] == null ? "" : el[key]}"></div>`;
  function seg(label, key, el, opts, dflt) {
    const v = el[key] || dflt;
    return `<div class="row"><label>${label}</label><span class="seg" data-k="${key}">${opts.map(([k, t]) => `<button data-v="${k}" class="${k === v ? "on" : ""}">${t}</button>`).join("")}</span></div>`;
  }
  const TEXTY = new Set(["text", "pill", "rect", "ellipse"]);
  const TYPE_KO = { text: "글자", pill: "칩", rect: "상자", ellipse: "원", image: "그림", line: "선", arrow: "화살표", table: "표", "plan-table": "실행계획 표", code: "코드", plan: "실행계획", bullets: "글머리" };
  function elLabel(e) {
    const t = e.text || (e.items && (typeof e.items[0] === "string" ? e.items[0] : e.items[0] && e.items[0].text)) || e.src || "";
    return `${e.id} · ${TYPE_KO[e.type] || e.type}${t ? " · " + Render.plain(String(t)).slice(0, 28) : ""}`;
  }
  function bulletsToText(items) {
    return (items || []).map((it) => typeof it === "string" ? it : [it.text || "", ...(it.sub || []).map((x) => "  " + x)].join("\n")).join("\n");
  }
  function textToBullets(t) {
    const out = [];
    for (const line of t.split("\n")) {
      if (!line.trim()) continue;
      if (/^\s/.test(line) && out.length) {
        let last = out[out.length - 1];
        if (typeof last === "string") last = out[out.length - 1] = { text: last, sub: [] };
        last.sub.push(line.trim());
      } else out.push(line.trim());
    }
    return out;
  }
  const CELL_SPLIT = /\s*\|\s*(?![^[]*\]\])/;
  const tableToText = (rows) => (rows || []).map((r) => r.join(" | ")).join("\n");
  const textToTable = (t) => t.split("\n").filter((l) => l.trim()).map((l) => l.split(CELL_SPLIT));
  const showToText = (sh) => (sh || []).map(([a, b]) => (a === b ? `${a}` : `${a}-${b}`)).join(", ");
  function textToShow(t) {
    const out = [];
    for (const p of t.split(/[,\s]+/).filter(Boolean)) { const m = p.match(/^(\d+)(?:-(\d+))?$/); if (m) out.push([+m[1], +(m[2] || m[1])]); }
    return out;
  }

  function renderProps() {
    const P = $("#tab-props"), s = slide();
    if (!s) { P.innerHTML = ""; return; }
    const el = selEl();
    const list = `<div class="sec"><h3>요소 (${s.elements.length}) — 가려진 요소도 여기서 선택</h3><div class="ellist">${s.elements.map((e) => `<div data-sel="${esc(e.id)}" class="${e.id === S.sel ? "on" : ""}">${esc(elLabel(e))}${e.locked ? " 🔒" : ""}</div>`).join("")}</div></div>`;
    if (!el) {
      P.innerHTML = `<div class="sec"><h3>슬라이드 ${S.cur + 1} · ${esc(s.id)} · 레이아웃 ${esc(s.layout || "-")}</h3>
        <div class="row"><label>배경</label><select class="colorSel" data-slide="bg">${colorOptions(s.bg || "surface")}</select></div>
        <div class="hint">요소를 클릭하면 속성을 고칠 수 있다. 색은 토큰 이름으로 고른다(색의 의미 유지).</div></div>${list}`;
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
        ${seg("글꼴", "font", el, [["body", "맑은 고딕"], ["mono", "Consolas"]], "body")}
        ${num("줄 높이", "lineHeight", el, 0.05)}
        ${colorRow("글자색", "color", el)}</div>`;
    }
    if (["rect", "ellipse", "pill", "text", "plan"].includes(el.type)) {
      h += `<div class="sec"><h3>면</h3>${colorRow("채우기", "fill", el, el.type === "text")}
        ${el.type !== "ellipse" && el.type !== "pill" ? `<div class="row"><label>모서리</label><select data-k="radius">${["", "r-s", "r-m", "r-l", "r-full"].map((r) => `<option value="${r}"${(el.radius || "") === r ? " selected" : ""}>${r || "없음"}</option>`).join("")}${typeof el.radius === "number" ? `<option selected value="${el.radius}">${el.radius}px</option>` : ""}</select></div>` : ""}
        ${colorRow("테두리", "stroke", el, true)}</div>`;
    }
    if (el.type === "image") h += `<div class="sec"><h3>그림</h3><div class="row"><label>경로</label><input type="text" data-k="src" value="${esc(el.src)}"></div><div class="hint">저장소 기준 경로. 모서리 핸들은 비율 유지.</div></div>`;
    if (isLine(el)) {
      h += `<div class="sec"><h3>선</h3>${colorRow("색", "color", el)}${num("두께(px)", "width", el, 0.5)}
        ${seg("머리", "head", el, [["none", "없음"], ["end", "끝"], ["start", "시작"], ["both", "양쪽"]], el.type === "arrow" ? "end" : "none")}
        ${seg("점선", "dash", el, [["solid", "실선"], ["dash", "파선"], ["dot", "점선"]], "solid")}</div>`;
    }
    if (el.type === "code") {
      h += `<div class="sec"><h3>코드 — DBeaver 라이트 색, 줄 번호 필수</h3><textarea data-k="text" style="min-height:160px">${esc(el.text || "")}</textarea>
        ${seg("언어", "lang", el, [["sql", "SQL"], ["python", "Python"]], "sql")}
        ${num("크기(px)", "size", el)}${num("줄 높이", "lineHeight", el, 0.05)}${num("시작 번호", "start", el)}
        <div class="row"><label>강조 줄</label><input type="text" data-list="focus" value="${esc((el.focus || []).join(", "))}" placeholder="예: 1, 9"></div>
        <div class="row"><label>발췌</label><input type="text" data-list="show" value="${esc(showToText(el.show))}" placeholder="예: 2, 13-24 (비우면 전체)"></div>
        <div class="row"><button class="chip sm" data-fit="code">높이를 줄 수에 맞추기</button><span class="hint">표시 ${Render.codeLines(el).length}줄 (15~18줄 이내 권장)</span></div></div>`;
    }
    if (el.type === "plan") {
      h += `<div class="sec"><h3>실행계획 원문 — [[값]] = 경고 강조, [[ok:값]] = 개선 강조 (폭 불변)</h3><textarea data-k="text" style="min-height:180px">${esc(el.text || "")}</textarea>
        ${num("크기(px)", "size", el, 0.5)}${num("줄 높이", "lineHeight", el, 0.05)}</div>`;
    }
    if (el.type === "bullets") {
      h += `<div class="sec"><h3>글머리 — 줄마다 항목, 앞에 공백 두 칸 = 하위 항목</h3><textarea data-bul="1" style="min-height:140px;font-family:var(--font);font-size:13px">${esc(bulletsToText(el.items))}</textarea>
        ${num("크기(px)", "size", el)}${num("하위 크기", "subSize", el)}${num("줄 높이", "lineHeight", el, 0.05)}${num("항목 간격", "gap", el)}
        ${colorRow("점 색", "dot", el)}${colorRow("글자색", "color", el)}${colorRow("하위 글자색", "subColor", el)}</div>`;
    }
    if (el.type === "table") {
      h += `<div class="sec"><h3>표 — 줄 = 행, 칸은 " | " 로 구분 (첫 행 = 머리)</h3><textarea data-tbl="1" style="min-height:140px">${esc(tableToText(el.rows))}</textarea>
        <div class="row"><label>열 비율</label><input type="text" data-list="colW" value="${esc((el.colW || []).join(", "))}"></div>
        ${num("크기(px)", "size", el)}${colorRow("머리 면", "headFill", el)}${colorRow("머리 글자", "headColor", el)}</div>`;
    }
    if (el.type === "plan-table") h += `<div class="sec"><h3>실행계획 표</h3><div class="hint">rows[].cells · depth(들여쓰기) · hl({열 번호: "warn"|"ok"}) · note(오른쪽 설명) — 아래 JSON 에서 고친다.</div></div>`;
    h += `<div class="sec"><h3>요소 JSON (고급)</h3><textarea id="elJson" style="min-height:120px">${esc(JSON.stringify(el, null, 1))}</textarea>
      <div class="row"><button class="chip sm" id="applyJson">JSON 적용</button><button class="chip sm" data-act="dupEl">복제 (Ctrl+D)</button><button class="chip sm" data-act="delEl">삭제 (Del)</button>
      <button class="chip sm" data-act="reqEl">이 요소에 요청</button></div></div>`;
    P.innerHTML = h + list;
  }

  function setProp(el, k, v) {
    if (["x", "y", "w", "h", "x1", "y1", "x2", "y2", "size", "subSize", "lineHeight", "width", "gap", "start"].includes(k)) {
      if (v === "" || v == null) { delete el[k]; } else el[k] = +v;
    } else if (k === "locked") { if (v) el.locked = true; else delete el.locked; }
    else if (k === "bold") el.bold = v === "1";
    else if (v === "" && ["fill", "stroke", "radius"].includes(k)) delete el[k];
    else el[k] = v;
    if (isLine(el)) Object.assign(el, Render.lineBox(el));
  }
  function onPropChange(e) {
    const t = e.target, el = selEl(), s = slide();
    if (t.dataset.slide === "bg") { snapshot(); s.bg = t.value; afterChange(); return; }
    if (!el) return;
    if (t.id === "elJson") return;
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
    if (b.dataset.z && el) {
      snapshot(); const i = s.elements.indexOf(el); s.elements.splice(i, 1);
      delete el.z; if (b.dataset.z === "front") s.elements.push(el); else s.elements.unshift(el);
      afterChange(); return;
    }
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
    if (b.dataset.act === "reqEl") { switchTab("reqs"); $("#reqText") && $("#reqText").focus(); }
  }

  // ---------------------------------------------------------------- 요청 메모
  async function loadReqs() {
    const r = await api("GET", `/api/requests/${S.id}`);
    S.reqs = r.ok ? r.data : [];
    const v = await api("GET", `/api/version/${S.id}`); if (v.ok) S.reqVersion = v.data.requests;
    renderReqs(); if (S.deck) renderThumbs();
  }
  function renderReqs() {
    const R = $("#tab-reqs"), s = slide(); if (!s) return;
    const open = S.reqs.filter((r) => r.status !== "done").length;
    const nOpen = S.reqs.filter((r) => r.status === "open").length;
    const ST = { open: "대기", working: "처리 중", done: "완료" };
    const c = $("#reqCnt"); c.textContent = open; c.style.display = open ? "" : "none";
    const target = S.sel ? `슬라이드 ${S.cur + 1}(${s.id}) · 요소 ${S.sel}` : `슬라이드 ${S.cur + 1}(${s.id}) 전체`;
    const list = S.reqs.filter((r) => !S.reqOnlySlide || r.slide === s.id);
    const idx = (sid) => S.deck.slides.findIndex((x) => x.id === sid) + 1;
    R.innerHTML = `<div class="sec"><h3>Claude에게 요청 — ${esc(target)}</h3>
      <textarea id="reqText" style="min-height:70px;font-family:var(--font);font-size:13px" placeholder="예: 이 표를 두 장으로 나눠 줘 / 제목을 더 짧게"></textarea>
      <div class="row"><button class="chip sm primary" id="reqAdd">요청 남기기</button><button class="chip sm" id="reqFlush" ${nOpen ? "" : "disabled"} title="여러 메모를 남긴 뒤 한꺼번에, 대기 시간 없이 세션에 보낸다">지금 보내기${nOpen ? ` (${nOpen})` : ""}</button></div>
      <div class="hint">${S.session && S.session.connected ? "세션 연결됨 — 남긴 요청은 몇 초 뒤 자동 전달된다" : "세션 연결 없음 — 요청은 저장되고, 세션이 감시를 시작하면 전달된다"}. 처리 상태·답변이 여기 표시된다</div></div>
      <div class="row"><span class="seg" id="reqFilter"><button data-v="1" class="${S.reqOnlySlide ? "on" : ""}">이 슬라이드</button><button data-v="0" class="${S.reqOnlySlide ? "" : "on"}">전체 (${S.reqs.length})</button></span></div>
      ${list.length ? list.slice().reverse().map((r) => `<div class="req ${r.status === "done" ? "done" : ""}" data-rid="${esc(r.id)}">
        <div class="meta"><span class="st ${esc(r.status || "open")}">${ST[r.status] || "대기"}</span>
          <a href="#" data-goto="${esc(r.slide)}" data-el="${esc(r.element || "")}">슬라이드 ${idx(r.slide) || "?"}${r.element ? " · " + esc(r.element) : ""}</a><span>${esc((r.created || "").replace("T", " "))}</span></div>
        <div class="txt">${esc(r.text)}</div>${r.reply ? `<div class="reply"><b>Claude</b> ${esc(r.reply)}</div>` : ""}
        <div class="acts"><button class="chip sm" data-rs="${r.status === "done" ? "open" : "done"}">${r.status === "done" ? "다시 열기" : "완료로 표시"}</button><button class="chip sm" data-rdel="1">삭제</button></div></div>`).join("") : `<div class="hint">요청이 없다.</div>`}`;
  }
  async function onReqClick(e) {
    const b = e.target.closest("button, a"); if (!b) return;
    if (b.id === "reqAdd") {
      const t = $("#reqText").value.trim(); if (!t) return;
      const r = await api("POST", `/api/requests/${S.id}`, { action: "add", slide: slide().id, element: S.sel, text: t });
      if (r.ok) { S.reqs = r.data; renderReqs(); renderThumb(S.cur); toast("요청을 남겼습니다"); }
      return;
    }
    if (b.id === "reqFlush") { await flushReqs(); return; }
    if (b.closest("#reqFilter")) { S.reqOnlySlide = b.dataset.v === "1"; renderReqs(); return; }
    const card = b.closest(".req"); if (!card) return;
    const rid = card.dataset.rid;
    if (b.dataset.goto !== undefined) {
      e.preventDefault();
      const i = S.deck.slides.findIndex((x) => x.id === b.dataset.goto);
      if (i >= 0) { S.cur = i; S.sel = b.dataset.el && elById(b.dataset.el, S.deck.slides[i]) ? b.dataset.el : null; renderAll(); }
      return;
    }
    let body = null;
    if (b.dataset.rs) body = { action: "update", id: rid, status: b.dataset.rs };
    if (b.dataset.rdel) { if (!confirm("이 요청을 지울까요?")) return; body = { action: "delete", id: rid }; }
    if (body) { const r = await api("POST", `/api/requests/${S.id}`, body); if (r.ok) { S.reqs = r.data; renderReqs(); renderThumbs(); } }
  }

  // ---------------------------------------------------------------- 레이아웃 검사 (check_layout.py)
  let chkT = 0;
  function scheduleCheck(ms = 600) { clearTimeout(chkT); chkT = setTimeout(runCheck, ms); }
  async function runCheck() {
    if (!S.id) return;
    const r = await api("GET", `/api/check/${S.id}`); if (!r.ok) return;
    S.check = r.data; renderCheck(); renderThumbs(); drawChkBox();
  }
  function renderCheck() {
    const C = $("#tab-check"), c = S.check; if (!C) return;
    const cnt = $("#chkCnt");
    if (!c) { C.innerHTML = `<div class="hint">검사 중…</div>`; cnt.style.display = "none"; return; }
    const tot = c.errors + c.warnings; cnt.textContent = tot; cnt.style.display = tot ? "" : "none";
    cnt.style.background = c.errors ? "#BA1A1A" : "#7D5700";
    const s = slide(), list = c.issues.filter((x) => !S.chkOnlySlide || (s && x.slide === s.id));
    C.innerHTML = `<div class="sec"><h3>레이아웃 검사 — ERROR ${c.errors} · WARNING ${c.warnings}</h3>
      <div class="hint">저장할 때마다 다시 검사한다. 항목을 누르면 그 슬라이드·요소로 간다. ERROR 는 고칠 것, WARNING 은 눈으로 확인할 것.
      최소 글자 ${Object.entries(c.minFontPt).map(([k, v]) => `${k} ${v}pt`).join(" · ")} (nexa-slide.json "check")</div>
      <div class="row"><span class="seg" id="chkFilter"><button data-v="0" class="${S.chkOnlySlide ? "" : "on"}">전체 (${c.issues.length})</button><button data-v="1" class="${S.chkOnlySlide ? "on" : ""}">이 슬라이드</button></span>
      <button class="chip sm" id="chkRun">다시 검사</button></div></div>
      ${list.length ? list.map((x, k) => `<div class="chk" data-k="${c.issues.indexOf(x)}"><span class="sev ${x.severity}">${x.severity}</span>
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
    const f = e.target.closest("#chkFilter button"); if (f) { S.chkOnlySlide = f.dataset.v === "1"; renderCheck(); return; }
    const it = e.target.closest(".chk"); if (!it || !S.check) return;
    const x = S.check.issues[+it.dataset.k]; const i = S.deck.slides.findIndex((s) => s.id === x.slide);
    if (i < 0) return;
    S.chkBox = x; S.cur = i; S.sel = x.elements && elById(x.elements[0], S.deck.slides[i]) ? x.elements[0] : null;
    renderAll(); revealThumb(S.cur); drawChkBox(); switchTab("check");
  }

  // ---------------------------------------------------------------- 세션 연결(요청 감시)
  function renderSession(st) {
    S.session = st;
    const c = $("#sessChip"); if (!c) return;
    const mode = st.connected ? (st.working ? "busy" : "on") : "off";
    c.className = "chip sm " + mode;
    c.innerHTML = `<span class="dot"></span>` + (st.connected
      ? (st.working ? `세션 처리 중 ${st.working}` : "세션 연결됨")
      : "세션 연결 없음");
    c.title = st.connected
      ? `${st.label || "Claude Code"} · 마지막 확인 ${st.last_seen} (${st.age}초 전) · 대기 ${st.open} · 처리 중 ${st.working}`
      : `요청 감시가 실행 중이 아니다${st.last_seen ? ` — 마지막 확인 ${st.last_seen}` : ""}. 세션에서 watch_requests.py --stream 을 Monitor 로 실행하면 연결된다`;
    const f = $("#flushBtn");
    f.style.display = st.open ? "" : "none";
    f.textContent = `요청 보내기 (${st.open})`;
  }
  async function flushReqs() {
    const r = await api("POST", `/api/flush/${S.id}`);
    if (!r.ok) { toast("보내기 신호를 쓰지 못했습니다"); return; }
    renderSession(r.data.session);
    toast(r.data.session.connected ? "열린 요청을 세션에 바로 보냅니다" : "세션 연결이 없어 보내지 못했습니다 — 요청은 저장돼 있고, 세션이 감시를 시작하면 전달됩니다", 4000);
  }

  // ---------------------------------------------------------------- 노트
  function renderNotes() {
    const s = slide(), n = s ? s.notes || "" : "";
    if (document.activeElement !== $("#notesTa")) $("#notesTa").value = n;
    $("#notesInfo").textContent = n ? `${n.length}자` : "비어 있음";
  }
  let notesSnap = false, notesT = 0;
  function onNotes() {
    const s = slide(); if (!s) return;
    if (!notesSnap) { snapshot(); notesSnap = true; }
    s.notes = $("#notesTa").value; $("#notesInfo").textContent = s.notes ? `${s.notes.length}자` : "비어 있음"; S.dirty = true; setStatus("dirty", "저장 대기");
    clearTimeout(notesT); notesT = setTimeout(() => { notesSnap = false; }, 1500);
    scheduleSave();
  }

  // ---------------------------------------------------------------- 선택·끌기·크기 조절
  function select(id) { S.sel = id; drawSel(); renderProps(); renderReqs(); }
  function toSlide(e) { const r = $("#stage").getBoundingClientRect(); return { x: (e.clientX - r.left) / scale, y: (e.clientY - r.top) / scale }; }
  let drag = null;
  function onDown(e) {
    if (e.button !== 0 || S.editing) return;
    const hd = e.target.closest(".hd");
    const p = toSlide(e);
    if (hd) {
      const el = selEl(); if (!el) return;
      drag = { mode: "resize", h: hd.dataset.h, el, orig: clone(el), p0: p, moved: false, before: JSON.stringify(S.deck) };
      e.preventDefault(); return;
    }
    const node = e.target.closest("#host .rs-el");
    if (!node) { select(null); return; }
    const id = node.dataset.id; if (S.sel !== id) select(id);
    const el = selEl();
    if (!el || el.locked) return;
    drag = { mode: "move", el, orig: clone(el), p0: p, moved: false, before: JSON.stringify(S.deck) };
    e.preventDefault();
  }
  function onMove(e) {
    if (!drag) return;
    const p = toSlide(e), dx = p.x - drag.p0.x, dy = p.y - drag.p0.y, free = e.shiftKey, el = drag.el, o = drag.orig;
    if (!drag.moved && Math.hypot(dx, dy) * scale < 3) return;
    drag.moved = true;
    if (drag.mode === "move") {
      const b0 = boxOf(o);
      const nx = snap(b0.x + dx, free), ny = snap(b0.y + dy, free), mx = nx - b0.x, my = ny - b0.y;
      if (isLine(el)) { el.x1 = o.x1 + mx; el.x2 = o.x2 + mx; el.y1 = o.y1 + my; el.y2 = o.y2 + my; Object.assign(el, Render.lineBox(el)); }
      else { el.x = nx; el.y = ny; }
    } else if (drag.h === "p1" || drag.h === "p2") {
      const k = drag.h === "p1" ? ["x1", "y1"] : ["x2", "y2"];
      el[k[0]] = snap(o[k[0]] + dx, free); el[k[1]] = snap(o[k[1]] + dy, free);
      Object.assign(el, Render.lineBox(el));
    } else {
      let x1 = o.x, y1 = o.y, x2 = o.x + o.w, y2 = o.y + o.h; const h = drag.h;
      if (h.includes("w")) x1 = snap(o.x + dx, free); if (h.includes("e")) x2 = snap(o.x + o.w + dx, free);
      if (h.includes("n")) y1 = snap(o.y + dy, free); if (h.includes("s")) y2 = snap(o.y + o.h + dy, free);
      if (el.type === "image" && h.length === 2) { // 그림은 모서리로 비율 유지
        const ratio = o.w / o.h, w = Math.max(4, x2 - x1), hh = w / ratio;
        if (h.includes("n")) y1 = y2 - hh; else y2 = y1 + hh;
      }
      el.x = Math.round(Math.min(x1, x2 - 4)); el.y = Math.round(Math.min(y1, y2 - 4));
      el.w = Math.round(Math.max(4, x2 - x1)); el.h = Math.round(Math.max(4, y2 - y1));
    }
    renderElementDom(el); drawSel();
  }
  function onUp() {
    if (!drag) return;
    const d = drag; drag = null;
    if (d.moved) { S.undo.push(d.before); S.redo = []; afterChange(); }
  }

  // ---------------------------------------------------------------- 글자 직접 편집
  function startEdit(el) {
    if (!el || el.locked) return;
    let raw;
    if (TEXTY.has(el.type) || el.type === "code" || el.type === "plan") raw = el.text || "";
    else if (el.type === "bullets") raw = bulletsToText(el.items);
    else if (el.type === "table") raw = tableToText(el.rows);
    else return;
    const b = boxOf(el);
    const ed = document.createElement("div");
    ed.className = "editor"; ed.setAttribute("contenteditable", "plaintext-only");
    if (ed.contentEditable !== "plaintext-only") ed.setAttribute("contenteditable", "true");
    const mono = el.font === "mono" || el.type === "code" || el.type === "plan" || el.type === "table";
    Object.assign(ed.style, { left: b.x + "px", top: b.y + "px", minWidth: Math.max(80, b.w) + "px", minHeight: Math.max(24, b.h) + "px",
      fontSize: (el.size || 20) + "px", lineHeight: (el.lineHeight || 1.4), fontFamily: mono ? "Consolas, 'Malgun Gothic', monospace" : "'Malgun Gothic', sans-serif" });
    ed.textContent = raw;
    $("#stage").appendChild(ed);
    S.editing = { el, ed, before: JSON.stringify(S.deck) };
    drawSel(); ed.focus();
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
    let t = E.ed.innerText.replace(/\r/g, "").replace(/\n$/, "");
    E.ed.remove();
    const el = E.el;
    if (commit) {
      const old = el.type === "bullets" ? bulletsToText(el.items) : el.type === "table" ? tableToText(el.rows) : el.text || "";
      if (t !== old) {
        S.undo.push(E.before); S.redo = [];
        if (el.type === "bullets") el.items = textToBullets(t);
        else if (el.type === "table") el.rows = textToTable(t);
        else el.text = t;
        afterChange(); return;
      }
    }
    drawSel();
  }

  // ---------------------------------------------------------------- 요소·슬라이드 조작
  function newElId(s) { let n = s.elements.length + 1; while (s.elements.some((e) => e.id === "e" + String(n).padStart(2, "0"))) n++; return "e" + String(n).padStart(2, "0"); }
  function newSlideId() { let n = S.deck.slides.length + 1; while (S.deck.slides.some((s) => s.id === "s" + String(n).padStart(2, "0"))) n++; return "s" + String(n).padStart(2, "0"); }
  function delEl() { const s = slide(), el = selEl(); if (!el) return; snapshot(); s.elements.splice(s.elements.indexOf(el), 1); S.sel = null; afterChange(); }
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
      image: { type: "image", x: 560, y: 320, w: Math.round(40 * (S.brand.logoRatio || 765 / 237)), h: 40, src: S.brand.logo || "assets/brand/logo.png" },
    }[kind];
    if (!base) return;
    snapshot();
    const el = { id: newElId(s), ...base };
    if (isLine(el)) Object.assign(el, Render.lineBox(el));
    if (el.type === "code") el.h = Math.round(24 + Render.codeLines(el).length * el.size * el.lineHeight);
    s.elements.push(el); S.sel = el.id; afterChange();
  }
  function goSlide(i) { if (!S.deck) return; S.cur = Math.max(0, Math.min(S.deck.slides.length - 1, i)); S.sel = null; renderAll(); ensureThumbVisible(S.cur); }
  function dupSlide(i) { snapshot(); const c = clone(S.deck.slides[i]); c.id = newSlideId(); S.deck.slides.splice(i + 1, 0, c); S.cur = i + 1; S.sel = null; afterChange(true); }
  function delSlide(i) {
    if (S.deck.slides.length <= 1) return toast("마지막 슬라이드는 지울 수 없습니다");
    if (!confirm(`슬라이드 ${i + 1}을(를) 지울까요? (Ctrl+Z 로 되돌리기 가능)`)) return;
    snapshot(); S.deck.slides.splice(i, 1); S.sel = null; afterChange(true);
  }
  async function layoutMenu(btn) {
    if (!S.layouts.length) { const r = await api("GET", "/api/layouts"); S.layouts = r.ok ? r.data : []; }
    closeMenu();
    const m = document.createElement("div"); m.className = "menu"; m.id = "menu";
    m.innerHTML = S.layouts.map((l) => `<button data-l="${l.name}">${esc(l.label)} <span class="hint">${l.name}</span></button>`).join("");
    const r = btn.getBoundingClientRect(); m.style.left = r.left + "px"; m.style.top = Math.max(8, r.top - 12 - S.layouts.length * 34) + "px";
    document.body.appendChild(m);
    m.addEventListener("click", async (e) => {
      const b = e.target.closest("button"); if (!b) return; closeMenu();
      const res = await api("POST", "/api/newslide", { layout: b.dataset.l, part: S.deck.part || "day1", id: newSlideId() });
      if (!res.ok) return toast("새 슬라이드 실패");
      snapshot(); S.deck.slides.splice(S.cur + 1, 0, res.data); S.cur += 1; S.sel = null; afterChange(true);
    });
  }
  function closeMenu() { const m = $("#menu"); if (m) m.remove(); }

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

  // ---------------------------------------------------------------- 탭·키보드
  function switchTab(t) { S.tab = t; $$(".tabs .chip").forEach((b) => b.classList.toggle("on", b.dataset.tab === t)); $$(".panel").forEach((p) => p.classList.toggle("on", p.id === "tab-" + t)); }
  function onKey(e) {
    const inField = /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement.tagName) || S.editing;
    const k = e.key, ctrl = e.ctrlKey || e.metaKey;
    if (ctrl && k.toLowerCase() === "s") { e.preventDefault(); save(); return; }
    if (inField) return;
    if (ctrl && k.toLowerCase() === "z" && !e.shiftKey) { e.preventDefault(); undo(); return; }
    if (ctrl && (k.toLowerCase() === "y" || (k.toLowerCase() === "z" && e.shiftKey))) { e.preventDefault(); redo(); return; }
    if (ctrl && k.toLowerCase() === "d") { e.preventDefault(); dupEl(); return; }
    if (ctrl && k.toLowerCase() === "c" && selEl()) { S.clip = clone(selEl()); toast("요소 복사"); return; }
    if (ctrl && k.toLowerCase() === "v" && S.clip) { e.preventDefault(); dupEl(S.clip); return; }
    if (k === "PageDown") { goSlide(S.cur + 1); e.preventDefault(); return; }
    if (k === "PageUp") { goSlide(S.cur - 1); e.preventDefault(); return; }
    if (!selEl() && (k === "Home" || k === "End")) { goSlide(k === "Home" ? 0 : S.deck.slides.length - 1); e.preventDefault(); return; }
    const el = selEl();
    if (!el) { if (k === "ArrowDown" || k === "ArrowRight") { goSlide(S.cur + 1); e.preventDefault(); } else if (k === "ArrowUp" || k === "ArrowLeft") { goSlide(S.cur - 1); e.preventDefault(); } return; }
    if (k === "Escape") { select(null); return; }
    if (k === "Delete" || k === "Backspace") { e.preventDefault(); if (!el.locked) delEl(); return; }
    if (k === "Enter" || k === "F2") { e.preventDefault(); startEdit(el); return; }
    const d = e.shiftKey ? GRID : 1, mv = { ArrowLeft: [-d, 0], ArrowRight: [d, 0], ArrowUp: [0, -d], ArrowDown: [0, d] }[k];
    if (mv && !el.locked) {
      e.preventDefault(); snapshot();
      if (isLine(el)) { el.x1 += mv[0]; el.x2 += mv[0]; el.y1 += mv[1]; el.y2 += mv[1]; Object.assign(el, Render.lineBox(el)); }
      else { el.x += mv[0]; el.y += mv[1]; }
      afterChange();
    }
  }

  // ---------------------------------------------------------------- 시작
  /** 글꼴 세트(tokens.json fontPresets) — 목록을 채우고 현재 값을 고른다 */
  async function loadFonts() {
    const r = await api("GET", "/api/fonts"); if (!r.ok) return;
    $("#fontSel").innerHTML = r.data.presets.map((p) => `<option value="${esc(p.name)}">글꼴: ${esc(p.name)} — ${esc(p.label)}</option>`).join("");
    $("#fontSel").value = r.data.current;
  }
  /** 세트를 바꾸면 서버가 tokens.json 을 고치고, 편집 화면은 토큰을 다시 읽어 바로 다시 그린다 */
  async function setFonts(name) {
    const r = await api("POST", "/api/fonts", { preset: name });
    if (!r.ok) { toast("글꼴 세트를 바꾸지 못했습니다"); await loadFonts(); return; }
    S.tokens = await (await fetch("tokens.json", { cache: "no-store" })).json();
    Render.setTokens(S.tokens);
    $("#rs-css").textContent = Render.css();
    if (document.fonts && document.fonts.ready) await document.fonts.ready;
    if (S.deck) { renderAll(); revealThumb(S.cur); }
    toast(`글꼴 세트: ${name} — PPTX 는 다음 내보내기부터 적용(칩·코드 폭은 build_deck 다시 빌드 때 맞춰진다)`, 5000);
  }
  /** 작업 공간 이름·브랜드(로고·파비콘) — nexa-slide.json */
  async function loadConfig() {
    const r = await api("GET", "/api/config"); if (!r.ok) return;
    S.brand = r.data.brand || {};
    document.title = `${r.data.title} — nexa-slide`;
    $("#appTitle").textContent = r.data.title || "nexa-slide";
    $("#appTitle").title = `작업 공간 ${r.data.path} · 포트 ${r.data.port}`;
    if (S.brand.logo) { const l = $("#brandLogo"); l.src = "/" + S.brand.logo; l.alt = S.brand.name || ""; l.style.display = ""; l.onerror = () => (l.style.display = "none"); }
    if (S.brand.favicon) $("#favicon").href = "/" + S.brand.favicon;
  }
  async function init() {
    await loadConfig();
    S.tokens = await (await fetch("tokens.json", { cache: "no-store" })).json();
    Render.setTokens(S.tokens);
    $("#rs-css").textContent = Render.css();
    await loadFonts();
    $("#fontSel").addEventListener("change", (e) => setFonts(e.target.value));
    const r = await api("GET", "/api/decks"); S.decks = r.ok ? r.data : [];
    $("#deckSel").innerHTML = S.decks.map((d) => `<option value="${d.id}">${esc(d.id)} — ${esc(d.title)} (${d.slides}장)</option>`).join("");
    if (!S.decks.length) { setStatus("error", "덱 없음"); toast("decks 에 덱이 없습니다 — build_deck.py 로 먼저 만드세요", 6000); return; }
    const [hid, hn] = decodeURIComponent(location.hash.slice(1)).split("/");
    const id = S.decks.some((d) => d.id === hid) ? hid : S.decks[0].id;
    $("#deckSel").value = id;
    await loadDeck(id);
    if (hn) { goSlide(+hn - 1); revealThumb(S.cur, true); }
    // 창 크기·글꼴 로드가 늦게 끝나 썸네일 높이가 바뀌어도 선택한 슬라이드가 보이게
    window.addEventListener("load", () => revealThumb(S.cur, true), { once: true });
    // 주소를 직접 고치거나 뒤로/앞으로 가기로 #덱/번호 가 바뀌면 그 슬라이드로
    window.addEventListener("hashchange", async () => {
      const [h, n] = decodeURIComponent(location.hash.slice(1)).split("/");
      if (h && h !== S.id && S.decks.some((d) => d.id === h)) {
        if (S.dirty) await save();
        $("#deckSel").value = h;
        await loadDeck(h);
      }
      const k = +n - 1;
      if (n && k !== S.cur && k >= 0) goSlide(k);
      revealThumb(S.cur, true);
    });

    $("#deckSel").addEventListener("change", async (e) => { if (S.dirty) await save(); await loadDeck(e.target.value); });
    $("#undoBtn").onclick = undo; $("#redoBtn").onclick = redo;
    $("#exportBtn").onclick = doExport;
    $("#previewBtn").onclick = () => { S.preview = !S.preview; document.body.classList.toggle("preview", S.preview); $("#previewBtn").classList.toggle("on", S.preview); renderPng(); setTimeout(fitStage, 0); };
    $("#renderBtn").onclick = doRender;
    $("#flushBtn").onclick = flushReqs;
    api("GET", "/api/session").then((r) => r.ok && renderSession(r.data));
    $("#bnTheirs").onclick = async () => { S.dirty = false; await loadDeck(S.id, true); toast("외부 버전을 불러왔습니다 (Ctrl+Z 로 내 편집 복구 가능)"); };
    $("#bnMine").onclick = async () => { S.conflict = false; await save(true); };
    $$("[data-add]").forEach((b) => (b.onclick = () => addEl(b.dataset.add)));
    $$(".tabs .chip").forEach((b) => (b.onclick = () => switchTab(b.dataset.tab)));

    const left = $("#left");
    left.addEventListener("click", (e) => {
      if (e.target.id === "addSlide") return layoutMenu(e.target);
      const t = e.target.closest(".thumb"); if (!t) return;
      const i = +t.dataset.i, act = e.target.dataset.act;
      if (act === "dup") dupSlide(i); else if (act === "del") delSlide(i); else goSlide(i);
    });
    left.addEventListener("dragstart", onThumbDragStart);
    left.addEventListener("dragover", onThumbDragOver);
    left.addEventListener("drop", onThumbDrop);
    left.addEventListener("dragend", () => { dragFrom = -1; $$(".thumb").forEach((x) => x.classList.remove("drop-before", "drop-after")); });

    const stage = $("#stage");
    stage.addEventListener("pointerdown", onDown);
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
    stage.addEventListener("dblclick", (e) => { const n = e.target.closest("#host .rs-el"); if (n) { select(n.dataset.id); startEdit(selEl()); } });
    $("#vpEdit").addEventListener("pointerdown", (e) => { if (e.target.id === "vpEdit") select(null); });

    const P = $("#tab-props");
    P.addEventListener("change", onPropChange);
    P.addEventListener("click", onPropClick);
    $("#tab-reqs").addEventListener("click", onReqClick);
    $("#tab-check").addEventListener("click", onChkClick);
    $("#notesTa").addEventListener("input", onNotes);
    const nb = $("#notesBar"), setFold = (f) => { nb.classList.toggle("fold", f); $("#notesFold").textContent = f ? "펴기" : "접기"; fitStage(); };
    try { setFold(localStorage.getItem("rs-notes-fold") === "1"); } catch (e) { /* 저장소 없음 */ }
    $("#notesFold").onclick = () => { const f = !nb.classList.contains("fold"); setFold(f); try { localStorage.setItem("rs-notes-fold", f ? "1" : "0"); } catch (e) { /* 무시 */ } };
    new ResizeObserver(() => fitStage()).observe($("#vpEdit"));
    document.addEventListener("keydown", onKey);
    document.addEventListener("pointerdown", (e) => { if (!e.target.closest("#menu") && e.target.id !== "addSlide") closeMenu(); });
    window.addEventListener("resize", () => { fitStage(); fitThumbs(); });
    window.addEventListener("beforeunload", (e) => { if (S.dirty) { save(); e.preventDefault(); e.returnValue = ""; } });
    setInterval(poll, 2000);
  }
  init().catch((e) => { console.error(e); setStatus("error", "오류"); toast("초기화 오류: " + e.message, 6000); });
})();
