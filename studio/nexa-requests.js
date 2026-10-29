/* nexa-slide 요청 관리 - 슬라이드 편집기(studio.js)와 시트 화면(sheet.js)이 같이 쓴다(docs/collab.md 0단계 "한 뿌리").
     요청 목록 읽기·동기화(/api/version 의 requests 버전) · 후속 요청(thread) 묶기 · 최근 24시간 보기 규칙 · 요청 카드 · 후속 요청 입력칸
     · 첨부(붙여넣기·끌어다 놓기·파일 → /api/attach/<id>, 축소판·라이트박스) · 상태 바꾸기·삭제 · 세션 안내 · 요청 기록·찾기 창([더보기])
   편집 대상별로 다른 것은 어댑터(target)만 둔다 - 슬라이드: 장·요소·영역, 시트: 탭·범위.
     const RQ = NexaRequests.create({
       api, toast, esc, base, deckId: () => id, session: SESS(wsession.js),
       getReqs: () => list, setReqs: (list) => …, onChange: () => 화면의 배지·표시 다시 그리기,
       target: { key(r) 대상 묶음(장·탭 id), current() 지금 묶음, label(r) 링크 글, num(r) #N 찾기 번호, scope "슬라이드"|"탭",
                 goto(r) 그 대상으로 이동, extra(r) 카드에 덧붙일 html(선택) },
       att: { boxes: {슬롯: 선택자}, onRender(슬롯)(선택) }, fileInput: "#attFile" })
   카드 CSS 는 nexa-requests.css. */
(function () {
  "use strict";
  const ST = { draft: "초안", open: "대기", working: "처리 중", done: "완료" };
  const DAY_MS = 864e5;
  const CLIP = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 11.5l-8.5 8.5a5 5 0 0 1-7-7l9-9a3.3 3.3 0 0 1 4.7 4.7l-9 9a1.6 1.6 0 0 1-2.3-2.3l8-8"/></svg>';

  function create(o) {
    const { api, toast, esc } = o, BASE = o.base || "", T = o.target;
    const $ = (s) => document.querySelector(s);
    const reqs = () => o.getReqs() || [];
    const url = () => `/api/requests/${encodeURIComponent(o.deckId())}`;
    let fu = null, version = null;  // 후속 요청 입력칸이 열린 요청 id · 요청 파일 버전
    let props = {};  // AI 제안(동시 편집 3단계 첫 조각) - 요청 id → {items}

    // ---------------------------------------------------------------- 읽기·동기화
    async function load() {
      const r = await api("GET", url());
      o.setReqs(r.ok && Array.isArray(r.data) ? r.data : []);
      const pr = await api("GET", `/api/proposals/${encodeURIComponent(o.deckId())}`);  // 제안은 요청과 함께 바뀐다(save_deck --propose 뒤 세션이 요청을 done 으로)
      props = {}; if (pr.ok && Array.isArray(pr.data)) for (const x of pr.data) props[x.request] = x;
      const v = await api("GET", `/api/version/${encodeURIComponent(o.deckId())}`); if (v.ok) version = v.data.requests;
      o.onChange && o.onChange();
    }
    /** /api/version 응답을 받아 요청 파일이 바뀌었으면 다시 읽는다(편집기·시트의 2초 폴링이 부른다) */
    async function sync(v) {
      if (!v || v.requests === undefined || v.requests === version) return false;
      version = v.requests; await load(); return true;
    }
    /** 요청 API - 성공하면 목록을 바꾸고 화면을 다시 그린다. flush 면 세션에 보내기 신호 */
    async function post(body, opts = {}) {
      const r = await api("POST", url(), body);
      if (!r.ok) { if (opts.err !== false) toast((opts.err || "요청을 처리하지 못했습니다") + ": " + ((r.data && r.data.error) || r.status), 5000); return null; }
      if (Array.isArray(r.data)) o.setReqs(r.data); else await load();
      o.onChange && o.onChange();
      if (opts.flush && o.session) await o.session.flush(true);
      return r;
    }
    const connected = () => { const st = o.session && o.session.state(); return !!(st && st.connected); };
    function agentName() {  // 요청 상대 이름 - 연결된 세션의 에이전트, 연결 없으면 "AI"
      const st = (o.session && o.session.state()) || {};
      if (!st.connected) return "AI";
      const a = (st.agent || st.label || "").toLowerCase();
      return /codex/.test(a) ? "Codex" : /claude/.test(a) ? "Claude" : "AI";
    }

    // ---------------------------------------------------------------- 묶기·보기 규칙
    const threadKey = (r) => r.thread || r.id;
    // 후속 요청 - 같은 thread(뿌리 요청 id)를 한 묶음으로. 묶음 안은 오래된 순, 묶음끼리는 최근 활동이 위
    function threads(list) {
      const m = new Map();
      for (const r of list) { const k = threadKey(r); if (!m.has(k)) m.set(k, []); m.get(k).push(r); }
      const gs = [...m.values()].map((g) => g.sort((a, b) => String(a.created || "").localeCompare(String(b.created || "")) || String(a.id).localeCompare(String(b.id))));
      return gs.sort((a, b) => String(b[b.length - 1].created || "").localeCompare(String(a[a.length - 1].created || "")));
    }
    // 기본 보기 = 최근 24시간에 진행(만듦·상태 변경·답)된 것 + 아직 끝나지 않은 것. 이전 것은 [더보기] 기록 창에서
    const recent = (r) => r.status !== "done" || Date.now() - Date.parse(r.updated || r.created || "") < DAY_MS;
    /** 후속 요청의 대상 - 후속에 slide 가 없으면 뿌리 요청의 것 */
    const rootOf = (r) => (r.slide ? r : reqs().find((x) => x.id === r.thread) || r);

    // ---------------------------------------------------------------- 첨부
    const store = { busy: 0 };
    const slot = (w) => (store[w] = store[w] || []);
    const isImg = (a) => /^image\//.test(a.type || "");
    const attUrl = (a) => BASE + (a.url || "/" + a.path);  // 중계(/w/<id>/)면 접두를 붙인 주소
    const boxes = (o.att && o.att.boxes) || {};
    function attRender(w) {
      const box = boxes[w] && $(boxes[w]); if (!box) return;
      box.innerHTML = slot(w).map((a, i) => `<span class="a" title="${esc(a.name)} · ${Math.round((a.size || 0) / 1024)}KB" data-attv="${w}:${i}">${isImg(a) ? `<img src="${esc(attUrl(a))}" alt="">` : `<span>📄</span>`}<span class="n">${esc(a.name)}</span><button class="x" data-attx="${w}:${i}" title="빼기">✕</button></span>`).join("")
        + (store.busy ? `<span class="a"><span class="spin"></span><span class="n">올리는 중…</span></span>` : "");
      if (o.att && o.att.onRender) o.att.onRender(w);
    }
    function attUpload(w, files) {
      const list = [...files].filter((f) => f && f.size);
      list.forEach((f) => {
        const rd = new FileReader(); store.busy++; attRender(w);
        rd.onload = async () => {
          const data = String(rd.result).split(",")[1] || "";
          const name = f.name && f.name !== "image.png" ? f.name : `clip-${new Date().toISOString().slice(11, 19).replace(/:/g, "")}.${(f.type.split("/")[1] || "png").replace("jpeg", "jpg")}`;
          const r = await api("POST", `/api/attach/${encodeURIComponent(o.deckId())}`, { name, type: f.type, data });
          store.busy--;
          if (!r.ok) { toast("첨부하지 못했습니다: " + ((r.data && r.data.error) || r.status), 5000); attRender(w); return; }
          slot(w).push(r.data); attRender(w);
        };
        rd.onerror = () => { store.busy--; attRender(w); toast("파일을 읽지 못했습니다"); };
        rd.readAsDataURL(f);
      });
    }
    function attFromClipboard(w, e) {
      const files = [];
      for (const it of (e.clipboardData && e.clipboardData.items) || []) if (it.kind === "file") { const f = it.getAsFile(); if (f) files.push(f); }
      if (!files.length) return false;
      e.preventDefault(); e.stopPropagation(); attUpload(w, files); return true;  // 같은 이벤트가 바깥 핸들러에도 닿아 두 번 올라가지 않게
    }
    function attWire(el, w) {  // 붙여넣기·끌어다 놓기
      if (!el || el.dataset.attWired) return; el.dataset.attWired = "1";
      el.addEventListener("paste", (e) => attFromClipboard(w, e));
      el.addEventListener("dragover", (e) => { if ([...e.dataTransfer.types].includes("Files")) { e.preventDefault(); el.classList.add("dropping"); } });
      el.addEventListener("dragleave", () => el.classList.remove("dropping"));
      el.addEventListener("drop", (e) => { if (e.dataTransfer.files.length) { e.preventDefault(); e.stopPropagation(); el.classList.remove("dropping"); attUpload(w, e.dataTransfer.files); } });
    }
    function attPick(w) { const f = $(o.fileInput || "#attFile"); f.onchange = () => { attUpload(w, f.files); f.value = ""; }; f.click(); }
    function attListHtml(list, rid) {  // 요청 카드의 축소판(읽기 전용) - 누르면 라이트박스(새 창 없음)
      if (!list || !list.length) return "";
      return `<div class="att ro">${list.map((a, i) => `<a class="a" href="${esc(attUrl(a))}" data-lb="${esc(rid || "")}:${i}" title="${esc(a.name)}">${isImg(a) ? `<img src="${esc(attUrl(a))}" alt="" loading="lazy">` : "📄"}<span class="n">${esc(a.name)}</span></a>`).join("")}</div>`;
    }
    const lbItems = (list) => (list || []).map((a) => ({ url: attUrl(a), name: a.name, size: a.size, type: a.type }));
    function attLightbox(rid, i) {  // 그 요청의 첨부부터, 토글로 같은 대상(장·탭)의 모든 요청 첨부
      const r = reqs().find((x) => x.id === rid); if (!r || !window.NexaLightbox) return;
      const k = T.key(rootOf(r));
      const all = reqs().filter((x) => T.key(rootOf(x)) === k && x.attachments && x.attachments.length).flatMap((x) => lbItems(x.attachments));
      NexaLightbox.open(lbItems(r.attachments), i, { title: T.label(rootOf(r)), alt: { label: `이 ${T.scope}의 모든 요청 첨부`, items: all } });
    }
    const attButton = (w) => `<button class="att-btn" data-attach="${w}" title="그림 붙여넣기(Ctrl+V) · 끌어다 놓기 · 파일 고르기">${CLIP}＋ 첨부</button>`;

    // ---------------------------------------------------------------- 카드
    function fuFormHtml(r) {  // 마지막 요청 아래 인라인 입력칸 - 앞선 답은 접어서 인용
      return `<div class="fu-form">${r.reply ? `<details><summary>앞선 답 보기</summary><div class="quote">${esc(r.reply)}</div></details>` : ""}
        <textarea id="fuText" placeholder="이어서 묻거나 답하기 (Enter = 보내기, Shift+Enter = 줄바꿈 · 그림은 Ctrl+V)"></textarea><div class="att" id="fuAtt"></div>
        <div class="row" style="gap:6px;justify-content:flex-end">${attButton("fu")}<span style="flex:1"></span><button class="chip sm" data-fucancel="1">취소</button><button class="chip sm primary" data-fusend="1">보내기</button></div></div>`;
    }
    /** 요청 카드 한 장 - 요청 패널과 기록 창이 같이 쓴다. hl = 찾기 강조 함수, fu = 후속 요청 단추·입력칸 */
    function cardHtml(r, k, last, opt) {
      const hl = (opt && opt.hl) || esc, withFu = !opt || opt.fu !== false;
      const eng = r.engineRequest ? `<a class="fu-tag" href="${esc(BASE.startsWith("/w/") ? `/engine?q=%23${r.engineRequest}` : "#")}" ${BASE.startsWith("/w/") ? 'target="_blank"' : ""} title="${esc(r.engineNote || "엔진 변경 요청으로 넘긴 요청 - 관리자 승인·처리·적용 뒤 자동으로 다시 열린다")}" style="text-decoration:none">엔진 요청 #${r.engineRequest}</a>` : "";
      return `<div class="req ${r.status === "done" ? "done" : ""}${k ? " fu" : ""}" data-rid="${esc(r.id)}">
        <div class="meta"><span class="st ${esc(r.status || "open")}">${r.status === "working" ? `<span class="spin"></span> ` : ""}${ST[r.status] || "대기"}</span>${k ? `<span class="fu-tag">후속</span>` : `<a href="#" data-goto="${esc(r.id)}">${esc(T.label(r))}</a>`}<span>${esc((r.created || "").replace("T", " "))}</span>${r.updated && r.updated !== r.created ? `<span title="마지막 진행">↻ ${esc(r.updated.replace("T", " "))}</span>` : ""}${eng}</div>${r.engineNote ? `<div class="hint" style="margin:2px 0 4px">${esc(r.engineNote)}</div>` : ""}
        <div class="txt">${hl(r.text)}</div>${T.extra ? T.extra(r) : ""}${propHtml(r)}${attListHtml(r.attachments, r.id)}${r.reply ? `<div class="reply${r.status !== "done" ? " ask" : ""}"><b>${agentName()}</b> ${hl(r.reply)}</div>` : ""}
        <div class="acts">${r.status === "draft" ? "" : `<button class="chip sm" data-rs="${r.status === "done" ? "open" : "done"}" ${r.status === "done" ? 'title="같은 요청을 세션에 다시 보냅니다(답을 달려면 후속 요청)"' : ""}>${r.status === "done" ? "다시 열기" : "완료로 표시"}</button>`}${withFu && last && r.status !== "draft" ? `<button class="chip sm primary" data-fu="1" title="이 요청에 이어서 묻거나 답합니다 - 앞선 요청과 답이 함께 세션에 전달됩니다">후속 요청</button>` : ""}<button class="chip sm" data-rdel="1">삭제</button></div>
        ${withFu && last && fu === r.id ? fuFormHtml(r) : ""}</div>`;
    }
    /** AI 제안 - 파일에 아직 반영되지 않은 큰 변경. 장(시트는 탭)마다, 펼치면 그 안의 요소(셀)마다 골라 받거나 버린다 */
    function propHtml(r) {
      const P = props[r.id]; if (!P || !P.items || !P.items.length) return "";
      return `<div class="prop" data-prop="${esc(r.id)}"><div class="row" style="gap:6px"><b>AI 제안 ${P.items.length}곳</b><span class="hint" style="margin:0">아직 반영 안 됨 - 골라 받으면 지금 문서와 합쳐 저장</span></div>
        <div class="prop-its">${P.items.map((it) => `<label><input type="checkbox" data-pit="${esc(it.id)}" checked> <span class="k">${esc(it.kind)}</span> ${esc(it.title)}${it.detail ? ` <span class="hint" style="margin:0">${esc(it.detail)}</span>` : ""}</label>${propSubs(it)}`).join("")}</div>
        <div class="row" style="gap:6px;justify-content:flex-end"><button class="chip sm" data-pdis="1">버리기</button><button class="chip sm" data-pacc="1">고른 것 받기</button><button class="chip sm primary" data-pall="1">모두 받기</button></div></div>`;
    }
    function propSubs(it) {
      if (!it.subs || !it.subs.length) return "";
      const what = it.id.startsWith("t:") ? "셀" : "요소";
      return `<details class="prop-subs"><summary>${what} ${it.subs.length}개 하나씩 고르기</summary>${it.subs.map((s) => `<label><input type="checkbox" data-pit="${esc(s.id)}" data-pof="${esc(it.id)}" checked> <span class="k">${esc(s.kind)}</span> ${esc(s.title)}${s.detail ? ` <span class="hint" style="margin:0">${esc(s.detail)}</span>` : ""}</label>`).join("")}</details>`;
    }
    /** 고른 것 - 장·탭을 통째로(그 안 요소·셀이 모두 골라져 있으면) 또는 고른 요소·셀만 */
    function propPicked(pv) {
      const out = [];
      for (const c of pv.querySelectorAll("[data-pit]:not([data-pof])")) {
        const subs = [...pv.querySelectorAll("[data-pof]")].filter((x) => x.dataset.pof === c.dataset.pit);
        if (!subs.length || (c.checked && !c.indeterminate)) { if (c.checked) out.push(c.dataset.pit); }
        else out.push(...subs.filter((x) => x.checked).map((x) => x.dataset.pit));
      }
      return out;
    }
    document.addEventListener("change", (e) => { if (e.target.matches && e.target.matches("input[data-pit]")) propSync(e.target); });  // 화면의 클릭 처리는 단추만 넘기므로 여기서
    function propSync(cb) {  // 장·탭 칸 ↔ 그 안 요소·셀 칸
      const pv = cb.closest("[data-prop]"); if (!pv) return;
      const kids = (id) => [...pv.querySelectorAll("[data-pof]")].filter((x) => x.dataset.pof === id);
      if (!cb.dataset.pof) { for (const x of kids(cb.dataset.pit)) x.checked = cb.checked; cb.indeterminate = false; return; }
      const par = [...pv.querySelectorAll("[data-pit]:not([data-pof])")].find((x) => x.dataset.pit === cb.dataset.pof); if (!par) return;
      const k = kids(cb.dataset.pof), n = k.filter((x) => x.checked).length;
      par.checked = n > 0; par.indeterminate = n > 0 && n < k.length;
    }
    async function propAct(rid, action, items) {
      const r = await api("POST", `/api/proposals/${encodeURIComponent(o.deckId())}`, { action, request: rid, ...(items ? { items } : {}) });
      if (!r.ok) { toast("제안을 처리하지 못했습니다: " + ((r.data && r.data.error) || r.status), 5000); return; }
      toast(action === "discard" ? "제안을 버렸습니다" : `제안을 받았습니다${(r.data.conflicts || []).length ? ` · 그 사이 바뀐 곳 ${r.data.conflicts.length}건은 제안 값으로` : ""}${r.data.left ? ` · 남은 제안 ${r.data.left}곳` : ""}`, 4000);
      await load();
      if (action === "accept" && o.onDeckChanged) o.onDeckChanged();  // 화면이 곧 다시 읽게(실시간 연결·폴링도 알아챈다)
    }
    const threadsHtml = (list, opt) => threads(list).map((g) => `<div class="thread${g.length > 1 ? " multi" : ""}">${g.map((r, k) => cardHtml(r, k, k === g.length - 1, opt)).join("")}</div>`).join("");
    /** 카드 목록을 그린 뒤 - 첨부 상자·후속 입력칸 배선 */
    function afterRender() {
      attRender("tab");
      if (fu && $("#fuText")) { attRender("fu"); attWire($("#fuText"), "fu"); $("#fuText").focus(); }
      if ($("#reqHist")) renderHist();
    }
    /** 세션 안내 - 연결 상태와 "대기 n건이 처리되지 않음 → 웹 세션 시작" */
    function sessionHint() {
      const st = (o.session && o.session.state()) || {};
      const open = reqs().filter((r) => r.status === "open").length;
      return `<div class="hint">${st.connected ? (st.kind === "web" ? (st.state === "running" ? `웹 세션이 처리 중(턴 ${st.turn || "?"}) - 새로 보낸 요청은 이 턴이 끝난 뒤 바로 처리된다` : "웹 세션 대기 중 - 보낸 요청은 바로 처리된다") : "세션 연결됨 - 보낸 요청은 바로 전달된다") : `세션 연결 없음 - 보낸 요청은 저장되고, 세션이 감시를 시작하면 전달된다${o.session ? o.session.offNote() : ""}`}</div>
      ${!st.connected && open ? `<div class="warn" style="font-size:12px;margin-top:6px">세션이 꺼져 있어 대기 요청 ${open}건이 처리되지 않습니다 - <a href="#" data-sess-start>웹 세션 시작</a></div>` : ""}`;
    }

    // ---------------------------------------------------------------- 보내기
    /** 새 요청 - body 에 대상(slide·range 등)을 담아 온다. 슬롯의 첨부를 붙이고 비운다 */
    async function add(body, w, opts = {}) {
      if (store.busy) { toast("첨부를 올리는 중입니다"); return null; }
      if (w && slot(w).length) body.attachments = slot(w).slice();
      const r = await post(body, { err: "요청하지 못했습니다", flush: opts.flush });
      if (r && w) { store[w] = []; attRender(w); }
      return r;
    }
    async function fuSend(parentId) {
      const t = ($("#fuText") && $("#fuText").value.trim()) || ""; if (!t && !slot("fu").length) return;
      if (store.busy) { toast("첨부를 올리는 중입니다"); return; }
      const parent = fu; fu = null;
      const r = await add({ action: "add", status: "open", parent: parentId, text: t || "(첨부 참고)" }, "fu", { flush: true });
      if (!r) { fu = parent; return; }
      toast(connected() ? "후속 요청을 세션에 보냈습니다" : "후속 요청을 남겼습니다 - 세션이 연결되면 전달됩니다");
    }
    function setFu(id) { fu = id; store.fu = []; o.onChange && o.onChange(); }

    // ---------------------------------------------------------------- 요청 기록·찾기 창([더보기]) - 편집 화면 위에 겹쳐 뜬다. 대상 링크를 누르면 닫고 그 대상으로
    const RH = { q: "", scope: "all", st: "", tg: null };
    function openHist() {
      if ($("#reqHist")) { $("#reqHist input").focus(); return; }
      const back = document.createElement("div"); back.id = "reqHist";
      back.innerHTML = `<div class="box"><div class="rh-hd"><h3>요청 기록<small id="rhCnt"></small></h3><button type="button" class="chip sm" id="rhClose" title="닫기 (Esc)">✕</button></div>
        <div class="rh-sb"><input type="search" placeholder="내용·답으로 찾기 - 기본 퍼지(띄어쓰기·한두 글자 차이 허용) · #4 = ${T.scope} 4, #4,5,7-10 = 여러 개" autocomplete="off" value="${esc(RH.q)}"><span id="rhTg" title="찾기 방식 - 기본은 퍼지(띄어쓰기·한두 글자 차이 허용)"></span></div>
        <div class="rh-fl"><span>범위</span><span class="seg" id="rhScope"><button data-v="all">전체</button><button data-v="here">이 ${T.scope}</button></span><span>상태</span><span class="seg" id="rhSt"><button data-v="">전체</button>${Object.entries(ST).map(([k, v]) => `<button data-v="${k}">${v}</button>`).join("")}</span><span class="err" id="rhErr"></span></div>
        <div class="list" id="rhList"></div></div>`;
      document.body.appendChild(back);
      RH.tg = window.NexaSearch ? NexaSearch.toggles(back.querySelector("#rhTg"), "reqs", renderHist) : null;
      const q = back.querySelector("input");
      q.addEventListener("input", () => { RH.q = q.value; renderHist(); });
      back.addEventListener("keydown", (e) => { if (e.key === "Escape") { closeHist(); e.preventDefault(); } e.stopPropagation(); });
      back.addEventListener("mousedown", (e) => { if (e.target === back) closeHist(); });
      back.querySelector("#rhClose").onclick = closeHist;
      back.addEventListener("click", (e) => {
        const b = e.target.closest("#rhScope button, #rhSt button"); if (!b) return;
        if (b.closest("#rhScope")) RH.scope = b.dataset.v; else RH.st = b.dataset.v;
        renderHist();
      });
      back.querySelector("#rhList").addEventListener("click", (e) => click(e));
      renderHist(); q.focus();
    }
    function closeHist() { const b = $("#reqHist"); if (b) b.remove(); }
    function renderHist() {
      const back = $("#reqHist"); if (!back) return;
      const S = window.NexaSearch;
      // "#4" = 4번째 대상(장·탭)의 요청("#4,5,7-10" 처럼 여러 개·범위) - 나머지 낱말만 글 찾기에 쓴다
      const { nums, text } = S ? S.split(RH.q) : { nums: new Set(), text: RH.q };
      const M = S ? S.matcher(text, RH.tg ? RH.tg() : {}) : { empty: !text.trim(), hl: esc, any: (xs) => xs.some((x) => String(x || "").includes(text)) };
      const here = T.current(), all = reqs().filter((r) => (RH.scope !== "here" || T.key(rootOf(r)) === here) && (!RH.st || r.status === RH.st) && (!nums.size || nums.has(T.num(rootOf(r)))));
      // 찾기는 대화(묶음) 단위 - 묶음 안 어느 요청이든 맞으면 묶음 전체를 보여 준다(앞뒤 맥락)
      const hit = M.empty ? all : threads(all).filter((g) => g.some((r) => M.any([r.text, r.reply, r.element, r.range, ...(r.elements || []), ...((r.attachments || []).map((a) => a.name))]))).flat();
      back.querySelectorAll("#rhScope button").forEach((b) => b.classList.toggle("on", b.dataset.v === RH.scope));
      back.querySelectorAll("#rhSt button").forEach((b) => b.classList.toggle("on", b.dataset.v === RH.st));
      back.querySelector("#rhErr").textContent = M.error ? `정규식 오류: ${M.error}` : "";
      const n = reqs().length;
      back.querySelector("#rhCnt").textContent = M.empty && !nums.size && !RH.st && RH.scope === "all" ? `전체 ${n}건` : `${hit.length} / ${n}건`;
      back.querySelector("#rhList").innerHTML = hit.length ? threadsHtml(hit, { hl: M.hl, fu: false }) : `<div class="hint" style="padding:20px;text-align:center">${n ? "찾는 요청이 없습니다" : "요청이 없다."}</div>`;
    }

    // ---------------------------------------------------------------- 누르기 - 공통 동작이면 처리하고 true
    async function click(e) {
      const b = e.target.closest("button, a"); if (!b) return false;
      if (b.dataset.sessStart !== undefined) { e.preventDefault(); if (o.session) o.session.startDlg(); return true; }
      if (b.dataset.lb !== undefined) { e.preventDefault(); const [rid, i] = b.dataset.lb.split(":"); attLightbox(rid, +i); return true; }
      if (b.dataset.attach) { attPick(b.dataset.attach); return true; }
      if (b.dataset.attx) { const [w, i] = b.dataset.attx.split(":"); slot(w).splice(+i, 1); attRender(w); return true; }
      const v = e.target.closest("[data-attv]"); if (v && window.NexaLightbox) { const [w, i] = v.dataset.attv.split(":"); NexaLightbox.open(lbItems(slot(w)), +i); return true; }
      if (b.id === "reqMore") { openHist(); return true; }
      const pv = b.closest("[data-prop]");
      if (pv && (b.dataset.pacc || b.dataset.pall || b.dataset.pdis)) {  // AI 제안 받기·버리기
        const rid = pv.dataset.prop, picked = propPicked(pv);
        if (b.dataset.pdis) { if (confirm("이 제안을 버릴까요? (문서는 그대로입니다)")) await propAct(rid, "discard"); return true; }
        if (b.dataset.pacc && !picked.length) { toast("받을 곳을 고르세요"); return true; }
        await propAct(rid, "accept", b.dataset.pall ? null : picked); return true;
      }
      const card = b.closest(".req"); if (!card) return false;
      const rid = card.dataset.rid, r = reqs().find((x) => x.id === rid);
      if (b.dataset.goto !== undefined) {
        e.preventDefault();
        if (b.closest("#reqHist")) closeHist();  // 기록 창에서 대상 링크 → 창을 닫고 그 대상으로
        if (r) T.goto(r);
        return true;
      }
      if (b.dataset.fu) { setFu(fu === rid ? null : rid); return true; }
      if (b.dataset.fucancel) { setFu(null); return true; }
      if (b.dataset.fusend) { await fuSend(rid); return true; }
      let body = null;
      if (b.dataset.rs) body = { action: "update", id: rid, status: b.dataset.rs };
      if (b.dataset.rdel) { if (!confirm("이 요청을 지울까요?")) return true; body = { action: "delete", id: rid }; }
      if (body) { await post(body, { err: "요청을 바꾸지 못했습니다" }); return true; }
      return false;
    }
    /** 요청 패널의 키 - 후속 입력칸 Enter = 보내기 · Esc = 닫기 */
    function keydown(e) {
      if (e.target.id !== "fuText") return false;
      if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); fuSend(e.target.closest(".req").dataset.rid); return true; }
      if (e.key === "Escape") { setFu(null); return true; }
      return false;
    }

    return {
      ST, load, sync, post, add, threads, threadsHtml, cardHtml, recent, rootOf, agentName, sessionHint, afterRender, click, keydown,
      openHist, closeHist, renderHist, fuSend, setFu, fu: () => fu, connected, attButton,
      att: { store, slot, render: attRender, upload: attUpload, fromClipboard: attFromClipboard, wire: attWire, pick: attPick, listHtml: attListHtml, lbItems, lightbox: attLightbox, url: attUrl },
    };
  }
  window.NexaRequests = { create };
})();
