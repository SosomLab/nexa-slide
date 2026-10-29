/* nexa-slide 세션 칩·웹 AI 세션(B-5) - 슬라이드 편집기(studio.js)와 시트 화면(sheet.js)이 같이 쓴다.
     칩 문구(연결·처리 중·활동 훅·웹 세션 턴) · 칩 메뉴 · 웹 세션 시작 창 · 모델 바꾸기 · 진행 패널(SSE /api/wsession/events) · 턴 로그 · 보내기 신호(/api/flush)
   쓰는 쪽이 둘 것: 칩 단추(#sessChip, class chip) · 대화 상자(#sessDlg > .box)와 그 CSS(index.html·sheet.html 의 #sessDlg 규칙)
     const SESS = NexaSession.create({ api, toast, openMenu, esc, base, deckId: () => id, onChange(st, changed) })
     SESS.render(st, act)  SESS.menu(btn)  SESS.startDlg()  SESS.close()  SESS.flush(quiet)  SESS.offNote()  SESS.state()
   openMenu(anchor, items, opts) 은 {h} · {html} · {icon, label, act} · "-" 항목을 받는다. */
(function () {
  "use strict";
  const GRANTS = [["git", "git 기록", "add·commit·branch·switch·merge·stash·tag"], ["push", "push", "git push·pull·fetch - 원격으로 보냄"], ["root", "저장소 루트 접근", "작업 공간을 품은 저장소 루트의 문서(작업일지·README·docs) 읽기·쓰기"]];

  function create(o) {
    const { api, toast, openMenu, esc } = o, BASE = o.base || "";
    const $ = (s) => document.querySelector(s), $$ = (s) => [...document.querySelectorAll(s)];
    let cur = null;  // 마지막 세션 상태(/api/session · /api/version 의 session)
    const WSS = { src: null, events: [], agent: null, logTurn: 1 };

    // 세션이 없을 때 마지막 웹 세션이 왜 끝났는지(서버 재시작·유휴·사용자 중지) - /api/session 의 last
    function offNote() {
      const l = (cur || {}).last; if (!l || !l.reason) return "";
      const why = { "server-stop": "서버 재시작으로 세션 종료됨", idle: "유휴로 세션 종료됨", user: "사용자가 세션 중지", error: "오류로 세션 종료됨" }[l.reason] || `세션 종료됨(${l.reason})`;
      const m = /^\d{4}-(\d\d)-(\d\d)T(\d\d:\d\d)/.exec(l.stoppedAt || ""); return ` · ${why}${m ? `(${+m[1]}/${+m[2]} ${m[3]})` : ""}`;
    }
    function render(st, act) {
      const key = (x) => x && (x.connected + "/" + (x.agent || x.label || ""));
      const changed = key(cur) !== key(st);
      cur = st;
      if (o.onChange) o.onChange(st, changed);
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
        : `세션 연결 없음${st.last_seen ? ` - 마지막 확인 ${st.last_seen}` : ""}${offNote()}. 눌러서 웹 세션을 시작하거나, 터미널 세션에서 watch_requests.py --stream 을 Monitor 로 실행하면 연결된다`;
    }
    /** 웹 세션이 턴을 도는 중이거나 처리 중 요청이 있으면 true - 쓰는 쪽이 '처리 중' 표시·자동 저장 미루기에 쓴다 */
    const busy = () => !!(cur && cur.connected && (cur.working || (cur.kind === "web" && cur.state === "running")));

    function menu(btn) {
      const st = cur || {};
      const web = st.connected && st.kind === "web";
      const items = web
        ? [{ h: `웹 세션 · ${st.agent || ""} · ${st.model || ""}${st.user ? ` · ${st.user}` : ""}${st.allowWeb ? " · 웹 허용" : ""}${(st.grants || []).map((g) => " · " + g).join("")}` },
           ...(st.sessionId ? [{ icon: "#", label: `세션 ID ${st.sessionId.slice(0, 8)} 복사`, act: () => sidCopy(st) }, { icon: "›", label: "확인 명령(claude --resume) 복사", act: () => sidCopy(st, true) }] : []),
           { icon: "▶", label: "진행 보기", act: progress }, { icon: "⟳", label: "모델 바꾸기", act: modelDlg },
           { icon: "📄", label: "턴 로그", act: () => log(1) }, "-",
           { icon: "■", label: "세션 중지", act: stop }]
        : st.connected
          ? [{ h: `수동 세션 · ${st.label || ""}` }, { html: `<div class="hint" style="padding:4px 10px;max-width:280px">터미널의 Claude Code 세션이 요청 감시(watch_requests)로 맡고 있습니다. 웹 세션으로 바꾸려면 그 감시를 끝내세요.</div>` }]
          : [...(offNote() ? [{ h: offNote().replace(/^ · /, "") }] : []), { icon: "▶", label: "웹 세션 시작", act: startDlg }, { html: `<div class="hint" style="padding:4px 10px;max-width:280px">서버가 AI(claude·codex)를 띄워 화면에서 보낸 요청을 처리합니다. 터미널 세션(Monitor)과 함께 쓸 수 없습니다.</div>` }];
      openMenu(btn, items, { right: false });
    }
    async function sidCopy(st, cmd) {  // 세션 식별자 - ID 복사, cmd 면 그 폴더에서 claude --resume <ID>(보기만; 웹 세션이 도는 중에 이어 쓰면 대화가 섞인다)
      const text = cmd ? (st.cwd ? `cd "${st.cwd}"; ` : "") + `claude --resume ${st.sessionId}` : st.sessionId, what = cmd ? "확인 명령을" : "세션 ID 를";
      try { await navigator.clipboard.writeText(text); toast(`${what} 복사했습니다 - ${text}`, 5000); }
      catch (e) { const ta = document.createElement("textarea"); ta.value = text; ta.style.position = "fixed"; ta.style.opacity = "0"; document.body.appendChild(ta); ta.select(); const ok = document.execCommand && document.execCommand("copy"); ta.remove(); if (ok) toast(`${what} 복사했습니다 - ${text}`, 5000); else prompt(what, text); }
      if (!(st.turn > 0)) setTimeout(() => toast("이 세션은 아직 첫 턴 전이라 claude --resume 로 열리지 않습니다 - 요청을 하나 처리한 뒤에 다시 시도", 6000), 600);
    }
    function box(html) { $("#sessDlg .box").innerHTML = html; $("#sessDlg").classList.add("show"); }
    function close() { const d = $("#sessDlg"); if (d) d.classList.remove("show"); if (WSS.src) { WSS.src.close(); WSS.src = null; } }
    async function startDlg() {
      box(`<div class="hint">에이전트·로그인 상태를 확인하는 중…</div>`);
      const r = await api("GET", "/api/agent");
      if (!r.ok) { box(`<div class="hint">확인 실패: ${esc((r.data && r.data.error) || r.status)}</div><div class="row"><button class="chip sm" data-sd="close">닫기</button></div>`); return; }
      WSS.agent = r.data;
      const ag = r.data.agents, cura = r.data.agent, model = r.data.model;
      const opt = (name) => { const a = ag[name]; const ok = a.installed && a.loggedIn; return `<option value="${name}" ${name === cura ? "selected" : ""} ${ok ? "" : "disabled"}>${esc(a.label)}${a.verified ? "" : " (미확인)"}${ok ? "" : a.installed ? " - 로그인 안 됨" : " - 미설치"}</option>`; };
      const models = (name) => (r.data.models[name] || []).map((m) => `<option value="${esc(m)}" ${m === model ? "selected" : ""}>${esc(m)}</option>`).join("") + `<option value="__custom">직접 입력</option>`;
      box(`<div class="row" style="align-items:center;gap:8px"><h3 style="margin:0;flex:1">웹 세션 시작</h3><button class="chip sm" data-sd="close">닫기</button></div>
        <div class="hint">서버가 이 작업 공간에서 AI 를 턴마다 실행해 화면에서 보낸 요청을 처리합니다. 쓰기 범위는 이 작업 공간 폴더뿐이며 <code>nexa.py</code> 명령만 허용됩니다.</div>
        <label class="f">에이전트</label><select id="sdAgent">${opt("claude")}${opt("codex")}</select>
        <div class="hint" id="sdHint">${esc(ag[cura].hint || "")}${ag[cura].hint && ag[cura].doc ? ` (엔진 ${esc(ag[cura].doc)})` : ""}</div>
        <label class="f">모델 <span class="hint">(기본: ${esc(model)} — ${esc(r.data.sources.model)})</span></label>
        <div class="row" style="gap:6px"><select id="sdModel">${models(cura)}</select><input type="text" id="sdModelText" placeholder="모델 ID 직접 입력" style="display:none;flex:1"></div>
        <label class="f" style="display:flex;align-items:center;gap:8px;font-weight:400"><input type="checkbox" id="sdSave"> 이 작업 공간 기본으로 저장 <select id="sdSaveAs" style="font-size:12px"><option value="local">이 PC 만(nexa-slide.local.json)</option><option value="shared">공유(nexa-slide.json)</option></select></label>
        ${r.data.allowWeb ? `<label class="f" style="display:flex;align-items:center;gap:8px;font-weight:400"><input type="checkbox" id="sdWeb" ${r.data.canAllowWeb ? "" : "disabled"}> 이 세션에 웹 검색 허용(WebSearch·WebFetch) ${r.data.canAllowWeb ? "" : '<span class="hint">- 관리자만</span>'}</label>
        <div class="hint" id="sdWebWarn" style="display:none;color:var(--err)">이 세션이 외부 웹을 검색·열람합니다 - 작업 내용·요청 내용이 검색어·URL 로 외부에 전달될 수 있습니다(claude 만).</div>` : ""}
        <div class="hint">한도: 유휴 ${esc(String(r.data.limits.sessionIdleMinutes))}분 · 턴 ${esc(String(r.data.limits.sessionTurnMinutes))}분 · 동시 ${esc(String(r.data.limits.sessionMax))}</div>
        <div class="row" style="justify-content:flex-end;gap:8px"><button class="chip sm" data-sd="close">취소</button><button class="chip sm primary" data-sd="start">시작</button></div>`);
      $("#sdAgent").onchange = () => { const n = $("#sdAgent").value; $("#sdModel").innerHTML = models(n); $("#sdHint").textContent = (ag[n].hint || "") + (ag[n].hint && ag[n].doc ? ` (엔진 ${ag[n].doc})` : ""); };
      if ($("#sdWeb")) $("#sdWeb").onchange = () => { $("#sdWebWarn").style.display = $("#sdWeb").checked ? "" : "none"; };
      const av = GRANTS.filter(([k]) => (r.data.grants || {})[k]);  // git·push·저장소 루트 - 전역이 켜진 것만(관리자만 체크)
      if (av.length) $("#sessDlg [data-sd=start]").parentElement.insertAdjacentHTML("beforebegin", `<div id="sdGrants">${av.map(([k, l, h]) => `<label class="f" style="display:flex;align-items:center;gap:8px;font-weight:400"><input type="checkbox" data-grant="${k}" ${r.data.canGrant ? "" : "disabled"}> 이 세션에 ${l} 허용 <span class="hint">- ${h}${r.data.canGrant ? "" : " · 관리자만"}</span></label>`).join("")}</div>`);
      $$("#sdGrants [data-grant]").forEach((c) => (c.onchange = () => { if (c.dataset.grant === "push" && c.checked) { const g = $("#sdGrants [data-grant=git]"); if (g) g.checked = true; } }));
      $("#sdModel").onchange = () => { $("#sdModelText").style.display = $("#sdModel").value === "__custom" ? "" : "none"; };
    }
    async function start() {
      const agent = $("#sdAgent").value, model = $("#sdModel").value === "__custom" ? $("#sdModelText").value.trim() : $("#sdModel").value;
      if (!model) { toast("모델을 고르거나 입력하세요"); return; }
      const body = { action: "start", agent, model }; if ($("#sdSave").checked) body.saveAs = $("#sdSaveAs").value;
      if ($("#sdWeb") && $("#sdWeb").checked) body.allowWeb = true;
      const gr = $$("#sdGrants [data-grant]").filter((c) => c.checked).map((c) => c.dataset.grant); if (gr.length) body.grants = gr;
      const r = await api("POST", "/api/wsession", body);
      if (!r.ok) { toast("시작 실패: " + ((r.data && r.data.error) || r.status), 6000); return; }
      toast(`웹 세션 시작 - ${agent} · ${model}${r.data.allowWeb ? " · 웹 허용" : ""}${(r.data.grants || []).map((g) => " · " + g).join("")}`); render({ ...(cur || {}), connected: true, kind: "web", agent, model, user: r.data.startedBy, allowWeb: !!r.data.allowWeb, grants: r.data.grants || [], label: `web:${agent}`, open: r.data.open, working: r.data.working, last_seen: "", age: 0 });
      progress();
    }
    async function stop() {
      if (!confirm("웹 세션을 중지할까요? 실행 중인 턴이 있으면 바로 종료됩니다.")) return;
      const r = await api("POST", "/api/wsession", { action: "stop" });
      if (!r.ok) { toast("중지하지 못했습니다: " + ((r.data && r.data.error) || r.status), 5000); return; }
      toast("웹 세션을 중지했습니다"); close(); api("GET", "/api/session").then((x) => x.ok && render(x.data));
    }
    async function modelDlg() {
      const r = await api("GET", "/api/agent"); const st = cur || {};
      const list = r.ok ? (r.data.models[st.agent] || []) : [];
      box(`<div class="row" style="align-items:center;gap:8px"><h3 style="margin:0;flex:1">모델 바꾸기</h3><button class="chip sm" data-sd="close">닫기</button></div>
        <div class="hint">지금 ${esc(st.model || "")} · 턴 실행 중이면 끝난 뒤 적용됩니다.</div>
        <div class="row" style="gap:6px"><select id="sdModel">${list.map((m) => `<option value="${esc(m)}" ${m === st.model ? "selected" : ""}>${esc(m)}</option>`).join("")}<option value="__custom">직접 입력</option></select><input type="text" id="sdModelText" placeholder="모델 ID" style="display:none;flex:1"></div>
        <label class="f" style="display:flex;align-items:center;gap:8px;font-weight:400"><input type="checkbox" id="sdSave"> 이 작업 공간 기본으로 저장 <select id="sdSaveAs" style="font-size:12px"><option value="local">이 PC 만</option><option value="shared">공유</option></select></label>
        <div class="row" style="justify-content:flex-end;gap:8px"><button class="chip sm" data-sd="close">취소</button><button class="chip sm primary" data-sd="modelgo">바꾸기</button></div>`);
      $("#sdModel").onchange = () => { $("#sdModelText").style.display = $("#sdModel").value === "__custom" ? "" : "none"; };
    }
    async function setModel() {
      const model = $("#sdModel").value === "__custom" ? $("#sdModelText").value.trim() : $("#sdModel").value;
      if (!model) { toast("모델을 고르거나 입력하세요"); return; }
      const body = { action: "model", model }; if ($("#sdSave").checked) body.saveAs = $("#sdSaveAs").value;
      const r = await api("POST", "/api/wsession", body);
      if (!r.ok) { toast("바꾸지 못했습니다: " + ((r.data && r.data.error) || r.status), 5000); return; }
      toast(r.data.pendingModel ? `턴이 끝난 뒤 ${model} 로 바뀝니다` : `모델을 ${model} 로 바꿨습니다`); close();
    }
    function progress() {
      box(`<div class="row" style="align-items:center;gap:8px"><h3 style="margin:0;flex:1">웹 세션 진행</h3><span class="hint" id="sdState"></span><button class="chip sm" data-sd="log">턴 로그</button><button class="chip sm" data-sd="close">닫기</button></div>
        <div class="ev" id="sdEv"><div class="hint">연결 중…</div></div>
        <div class="row" style="justify-content:flex-end;gap:8px"><button class="chip sm" data-sd="model">모델 바꾸기</button><button class="chip sm" data-sd="stop">세션 중지</button></div>`);
      if (WSS.src) WSS.src.close();
      WSS.events = [];
      const ev = $("#sdEv"); ev.innerHTML = "";
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
        ev.appendChild(div); ev.scrollTop = ev.scrollHeight;
      };
      try {
        const src = new EventSource(`${BASE}/api/wsession/events`); WSS.src = src;
        ["state", "turn.start", "init", "text", "tool", "tool_result", "turn.end", "warn", "error", "model", "idle"].forEach((k) => src.addEventListener(k, (e2) => { try { const d = JSON.parse(e2.data); if (k === "state" && !d.seq) { $("#sdState").textContent = `${d.state} · ${d.agent || ""} · ${d.model || ""}`; } line({ ...d, type: d.type || k }); if (d.type === "state" || k === "state") $("#sdState").textContent = `${d.state}`; } catch (e) { /* 무시 */ } }));
        src.onerror = () => { const div = document.createElement("div"); div.className = "e warn"; div.textContent = "연결이 끊겨 다시 붙는 중…"; ev.appendChild(div); };
      } catch (e) { ev.textContent = "이 브라우저는 SSE 를 지원하지 않습니다"; }
    }
    async function log(n) {
      const r = await api("GET", `/api/wsession/log?turn=${n}`);
      const lines = r.ok ? r.data.lines : [];
      box(`<div class="row" style="align-items:center;gap:8px"><h3 style="margin:0;flex:1">턴 ${n} 로그 <span class="hint">(어댑터 출력 원문 ${lines.length}줄)</span></h3>
        <button class="chip sm" data-sd="logprev">◀</button><button class="chip sm" data-sd="lognext">▶</button><button class="chip sm" data-sd="progress">진행</button><button class="chip sm" data-sd="close">닫기</button></div>
        <div class="ev">${lines.length ? lines.map((l) => `<div class="e">${esc(l.length > 400 ? l.slice(0, 400) + " …" : l)}</div>`).join("") : '<div class="hint">로그 없음</div>'}</div>`);
      WSS.logTurn = n;
    }
    const dlg = $("#sessDlg");
    if (dlg) dlg.addEventListener("click", (e) => {
      if (e.target === dlg) { close(); return; }
      const b = e.target.closest("[data-sd]"); if (!b) return;
      const k = b.dataset.sd;
      if (k === "close") close(); else if (k === "start") start(); else if (k === "model") modelDlg(); else if (k === "modelgo") setModel();
      else if (k === "stop") stop(); else if (k === "log") log(1); else if (k === "progress") progress();
      else if (k === "logprev") log(Math.max(1, (WSS.logTurn || 1) - 1)); else if (k === "lognext") log((WSS.logTurn || 1) + 1);
    });
    /** 보내기 신호 - 세션이 요청 파일을 다시 보게(웹 세션은 바로 턴) */
    async function flush(quiet) {
      const r = await api("POST", `/api/flush/${encodeURIComponent(o.deckId())}`);
      if (!r.ok) { if (!quiet) toast("보내기 신호를 쓰지 못했습니다"); return; }
      if (r.data && r.data.session) render(r.data.session);
    }
    return { render, menu, startDlg, close, flush, offNote, busy, state: () => cur };
  }
  window.NexaSession = { create };
})();
